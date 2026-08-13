# Deployment

This document covers production deployment of the LOD Gateway, including container orchestration, reverse proxy configuration, worker tuning, and logging.

([back to README](/README.md))

## Container Architecture

The LOD Gateway consists of one production container:

- **`web`** -- the Flask application served by Gunicorn. This is the only container required in production.

For development and testing, the `docker-compose.yml` also includes:

- **`postgres`** -- PostgreSQL database server
- **`fuseki`** -- Apache Jena Fuseki graph store

In production, replace these with external database and graph store services.

## Starting the Application

Build and start the application:

```bash
docker compose build
docker compose up --detach
```

On first run, create the database schema:

```bash
docker compose exec web flask db upgrade
```

Alternatively, set `DB_UPGRADE_ON_START=true` in `.env` to run migrations automatically on container startup.

## Production Database

The LOD Gateway supports PostgreSQL and SQLite. Use PostgreSQL for production.

Set the `DATABASE` variable to a full connection string:

```
DATABASE=postgresql://user:password@host:5432/dbname
```

The database schema is managed via Alembic. Run `flask db upgrade` after deploying new versions of the application.

## Graph Store Integration

When `PROCESS_RDF=True`, the LOD Gateway connects to an external SPARQL endpoint for graph storage and querying. Compatible graph stores include:

- Apache Jena Fuseki
- Ontotext GraphDB
- Amazon Neptune
- Any SPARQL Update 1.1-compliant endpoint

Configure the endpoints:

```
SPARQL_QUERY_ENDPOINT=http://fuseki:3030/ds/sparql
SPARQL_UPDATE_ENDPOINT=http://fuseki:3030/ds/update
```

When graph processing is enabled, the Gateway expands JSON-LD into RDF triples and stores them in named graphs. The named graph URI is constructed from `BASE_URL` + `RDF_NAMESPACE` + resource `@id`.

## Worker Configuration

The `web` container runs Gunicorn to serve the Flask application. Tune the worker settings for your deployment:

| Variable | Default | Description |
|----------|---------|-------------|
| `WEB_WORKERS` | `1` | Number of worker processes. Use 2-4 per CPU core. |
| `WEB_TIMEOUT` | `600` | Worker timeout in seconds. Increase if SPARQL queries or large ingests take longer. |
| `WORKER_CLASS` | `gevent` | Worker class. Use `gevent` for I/O-bound workloads, `gthreads` for thread-based concurrency. |
| `WORKER_CONNECTIONS` | `100` | Max concurrent connections per gevent worker. |
| `WEB_THREADS` | *(none)* | Threads per worker when `WORKER_CLASS=gthreads`. Use 2-4. |

**gevent configuration:**

```
WORKER_CLASS=gevent
WORKER_CONNECTIONS=100
WEB_WORKERS=4
```

**gthreads configuration:**

```
WORKER_CLASS=gthreads
WEB_THREADS=4
WEB_WORKERS=4
```

Gunicorn workers are automatically reloaded approximately every 1000 requests. Manual restart is recommended after configuration changes that affect worker state, such as base graph updates.

## Reverse Proxy Configuration

When deploying behind a reverse proxy (nginx, Apache, etc.), configure Werkzeug ProxyFix to preserve client information:

```
WERKZEUG_PROXY_FIX=true
WERKZEUG_X_FOR=1
WERKZEUG_X_PREFIX=1
WERKZEUG_X_HOST=1
```

| Variable | Purpose |
|----------|---------|
| `WERKZEUG_PROXY_FIX` | Enable ProxyFix middleware |
| `WERKZEUG_X_FOR` | Trust `X-Forwarded-For` for client IP |
| `WERKZEUG_X_PREFIX` | Rewrite request subpath |
| `WERKZEUG_X_HOST` | Preserve `X-Forwarded-Host` for correct URL generation |

`X-Proto` is always enabled to ensure `url_for()` generates correct HTTP/HTTPS schemes.

### nginx Example

```nginx
server {
    listen 80;
    server_name data.example.org;

    location / {
        proxy_pass http://localhost:5100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Gzip Compression

Enable response compression to reduce bandwidth:

```
FLASK_GZIP_COMPRESSION=True
```

## Logging

### Application Logs

Set the log level via `DEBUG_LEVEL`:

```
DEBUG_LEVEL=INFO
```

Levels from least to most severe: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Setting the level to `WARNING` logs only warnings and above.

The Python logger outputs all levels to STDOUT and only `ERROR`/`CRITICAL` to STDERR.

### Structured Logging

Enable JSON-formatted log output for integration with log aggregators:

```
JSON_LOGGING=true
ACCESS_JSON_LOGGING=true
```

### Gunicorn Logs

Gunicorn outputs its own log messages and access logs. HTTP 5xx responses are logged to STDERR by default. Access log format is controlled by `ACCESS_JSON_LOGGING`.

## External HTTP Timeouts

The Gateway makes external HTTP calls for SPARQL queries and context document fetching. Set a timeout to prevent hanging connections:

```
EXTERNALHTTPCALLS_TIMELIMIT=45
```

Value is in seconds. The SPARQL endpoint will return a `504 Gateway Timeout` if a query exceeds this limit.

## Secrets Management

In production, manage environment variables through your secrets management system (HashiCorp Vault, AWS Secrets Manager, Docker secrets, etc.) rather than `.env` files.

Critical secrets include:

- `AUTHORIZATION_TOKEN` -- bearer token for authenticated API operations
- `DATABASE` -- database connection string (contains credentials)
- `SPARQL_QUERY_ENDPOINT` / `SPARQL_UPDATE_ENDPOINT` -- may contain credentials

## Health Checks

The LOD Gateway provides three health check endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Database connectivity check |
| `GET /authhealth` | Database check with authentication. Validates bearer token. |
| `GET /rdfhealth` | Database and SPARQL endpoint check. More resource-intensive. |

All return `200 OK` when healthy, `503 Service Unavailable` when unhealthy. Use `/health` for basic load balancer probes and `/rdfhealth` for deeper integration testing.

## Updating the Application

1. Pull the latest code or image
2. Build new containers: `docker compose build`
3. Run database migrations: `docker compose exec web flask db upgrade`
4. Restart containers: `docker compose up --detach`

After updating, verify the application via the `/health` and `/rdfhealth` endpoints.

## Capabilities Header

The Gateway includes an `X-LODGATEWAY-CAPABILITIES` header on every response, indicating which features are enabled:

```
X-LODGATEWAY-CAPABILITIES: JSON-LD: 'True', Subaddressing: 'True', Versioning: 'True', LDP: 'True'
```

Clients can inspect this header to determine available functionality.

## Strict Slashes

By default, Flask treats URLs with and without trailing slashes as different routes. Set `FLASK_STRICT_SLASHES=False` to normalize this behavior:

```
FLASK_STRICT_SLASHES=False
```

## Database Migration Notes

Alembic manages schema migrations. The `flask db upgrade` command applies all pending migrations. In production:

- Set `DB_UPGRADE_ON_START=true` to run migrations automatically on container startup
- Or run `docker compose exec web flask db upgrade` manually before restarting
- Always verify the schema version matches the application version after migration