# Configuration

The LOD Gateway is configured entirely through environment variables. In development, these are set in the `.env` file. In production, they are typically managed through a secrets management system or orchestration platform.

Values in `.env` files should not be quoted unless you intend the quotes to be part of the value. The Gateway reads values verbatim.

([back to README](/README.md))

## Required Variables

| Variable | Description |
|----------|-------------|
| `AUTHORIZATION_TOKEN` | Bearer token for authenticated operations. Clients must send `Authorization: Bearer {token}`. |
| `BASE_URL` | Base URL of the application, e.g. `https://data.getty.edu`. Used for RDF URIs and resource identifiers. |
| `DATABASE` | Full database connection URL, e.g. `postgresql://user:pass@host/dbname`. For in-memory SQLite testing: `sqlite:////app/app.db`. |
| `LOD_AS_DESC` | Short description of the deployed instance. Used in Activity Stream summaries and the dashboard. |

## Application Namespace

| Variable | Default | Description |
|----------|---------|-------------|
| `APPLICATION_NAMESPACE` | *(none)* | Vanity path segment in URLs, e.g. `museum/collection`. All API routes are served under this path. Set to empty string or `/` to serve at the root. |

## RDF and Graph Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `PROCESS_RDF` | `False` | Set to `True` to enable JSON-LD to RDF expansion. Requires `SPARQL_QUERY_ENDPOINT` and `SPARQL_UPDATE_ENDPOINT`. |
| `SPARQL_QUERY_ENDPOINT` | *(none)* | SPARQL query endpoint URL of the graph store. Required when `PROCESS_RDF=True`. |
| `SPARQL_UPDATE_ENDPOINT` | *(none)* | SPARQL update endpoint URL of the graph store. Required when `PROCESS_RDF=True`. |
| `SPARQL_QUERY_AUTHENTICATION` | `False` | Set to `True` to require authentication on the `/sparql` endpoint and `/sparql-ui` interface. |
| `FULL_RDF_ID_PREFIX` | *(none)* | Full base URI (scheme, host, path included, e.g. `https://graph.example.org/rdf`) used as the prefix for RDF named graph URIs in the triplestore. When set to a non-empty value it fully specifies the prefix and takes precedence over the `BASE_URL`/`RDF_NAMESPACE` derivation below, decoupling triplestore graph URIs from API/display URLs. When unset or empty, the prefix is derived as `BASE_URL[/RDF_NAMESPACE]`. | 
| `RDF_NAMESPACE` | *(same as APPLICATION_NAMESPACE)* | Separate namespace for RDF named graph URIs. Use when the RDF namespace must differ from the API namespace. Ignored when `FULL_RDF_ID_PREFIX` is set. |
| `RDF_BASE_GRAPH` | *(none)* | Entity ID of the base graph resource. Triples in the base graph are removed from other named graphs to avoid duplication. The base graph URI is `{RDFidPrefix}/{RDF_BASE_GRAPH}`, where `RDFidPrefix` is `FULL_RDF_ID_PREFIX` if set, else derived from `BASE_URL`/`RDF_NAMESPACE`. |
| `USE_PYLD_REFORMAT` | `True` | Set to `True` to use PyLD for JSON-LD expansion and reformatting. Set to `False` to use RDFLib. |
| `RDF_CONTEXT_CACHE` | *(none)* | JSON-encoded context documents to preload into the document loader. Speeds up expansion by avoiding external context fetches. |
| `RDF_CONTEXT_CACHE_EXPIRES` | `30` | Duration in seconds that context documents remain in cache. |
| `CONTEXTPREFIX_TTL` | `43200` | Duration in seconds that RDF prefix lists (derived from resolved contexts) are cached. Default is 12 hours. |
| `TESTMODE_BASEGRAPH` | `False` | **Testing only.** Reload the base graph into memory when ingested. In production, restart workers to reload. |

## Versioning and Memento

| Variable | Default | Description |
|----------|---------|-------------|
| `KEEP_LAST_VERSION` | `False` | Set to `True` to enable Memento versioning. Previous versions are created on every update. |
| `KEEP_VERSIONS_AFTER_DELETION` | `False` | Set to `True` to retain versions after a record is deleted. |
| `VERSIONING_AUTHENTICATION` | `True` | Set to `True` to require authentication for retrieving previous versions via `/-VERSION-/{entity-id}`. |
| `MEMENTO_PREFERRED_FORMAT` | `application/link-format` | Default format for timemap responses. Accepts `application/json` or `application/link-format`. |
| `LINK_HEADER_PREV_VERSION` | `False` | Set to `True` to include a `Link` header with a reference to the previous version on resource responses. |

## Linked Data Platform

| Variable | Default | Description |
|----------|---------|-------------|
| `LDP_BACKEND` | `False` | Set to `True` to enable LDP container bookkeeping. Required for all LDP functionality. |
| `LDP_API` | `False` | Set to `True` to enable LDP API features (Link headers, container endpoints, POST/PUT). Depends on `LDP_BACKEND=True`. |
| `LDP_AUTOCREATE_CONTAINERS` | `False` | Set to `True` to automatically create parent containers when ingesting resources at nested paths. |
| `LDP_AUTOCREATE_CONTAINERS_w_COMMIT` | `False` | Variant of `LDP_AUTOCREATE_CONTAINERS` that also commits the database transaction within the same operation. |
| `LDP_VALIDATE_SLUGS` | `False` | Set to `True` to validate `Slug` headers on POST requests to LDP containers. |
| `LDP_PAGE_SIZE` | `200` | Number of items per page for LDP container listings. |
| `LDP_ID_GEN` | `uuid` | Method for generating identifiers when POSTed resources lack an ID. Currently only `uuid` is supported. |

## Sub-Addressing

| Variable | Default | Description |
|----------|---------|-------------|
| `SUBADDRESSING` | `False` | Set to `True` to enable sub-addressing. Resolves nested paths within documents to their parent resource. |
| `SUBADDRESSING_DEPTH` | *(none)* | Legacy variable. Set but not consumed by route logic. |
| `SUBADDRESSING_MIN_PARTS` | `1` | Minimum number of path segments to search when resolving sub-addressed paths. |
| `SUBADDRESSING_MAX_PARTS` | `4` | Maximum number of path segments to search when resolving sub-addressed paths. |

## Content Prefixing

| Variable | Default | Description |
|----------|---------|-------------|
| `PREFIX_RECORD_IDS` | `RECURSIVE` | Controls how `id` values are prefixed. `RECURSIVE` (default) prefixes all relative IDs recursively. `TOP` prefixes only the top-level ID. `NONE` disables all prefixing. Can be overridden per-request with `?relativeid=true`. |

## JSON Serialization

| Variable | Default | Description |
|----------|---------|-------------|
| `JSON_SORT_KEYS` | `False` | Set to `True` to sort JSON output keys alphabetically. Affects ETag computation. |
| `JSON_AS_ASCII` | `False` | Set to `True` to escape non-ASCII characters in JSON output. |

## Content Negotiation by Profile

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTENT_PROFILE_DATA_URL` | *(none)* | URL to fetch a JSON-encoded PatternSet export for content profile SPARQL patterns. |
| `CONTENT_PROFILE_DATA` | *(none)* | JSON-encoded PatternSet data as a string. Alternative to `CONTENT_PROFILE_DATA_URL` for inline profile data. |

## Pagination and Browse

| Variable | Default | Description |
|----------|---------|-------------|
| `ITEMS_PER_PAGE` | `100` | Number of items per page for Activity Stream and dashboard pagination. |
| `BROWSE_PAGE_SIZE` | `200` | Number of records returned per page for prefix search (glob browse) results. |

## Local Thesaurus

| Variable | Default | Description |
|----------|---------|-------------|
| `LOCAL_THESAURUS_URL` | *(none)* | URL to a CSV file containing Local Thesaurus data. Required only when `APPLICATION_NAMESPACE=local/thesaurus`. Requires SQLite database. |

## Dashboard

| Variable | Default | Description |
|----------|---------|-------------|
| `LINK_BANK` | *(none)* | JSON defining custom link groups for the Dashboard documentation section. See the example below. |

**LINK_BANK format:**

```json
{
  "groups": [
    {
      "name": "Documentation",
      "links": [
        { "name": "API Reference", "url": "https://docs.example.com/api" },
        { "name": "Data Guide", "url": "https://docs.example.com/data" }
      ]
    }
  ]
}
```

## Flask and Gunicorn

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_GZIP_COMPRESSION` | `False` | Set to `True` to enable gzip compression of responses. |
| `FLASK_STRICT_SLASHES` | `True` | Set to `False` to allow URLs with and without trailing slashes to resolve to the same route. |
| `FLASK_RUN_PORT` | `5100` | Port number for the Flask development server. |
| `FLASK_APP` | `/app/flaskapp` | Path to the Flask application module. |
| `FLASK_ENV` | `production` | Flask environment. Set to `development` to enable SQL query logging. |
| `WEB_WORKERS` | `1` | Number of Gunicorn worker processes. Typical range: 2-4 per CPU core. |
| `WEB_TIMEOUT` | `600` | Gunicorn worker timeout in seconds. |
| `WORKER_CLASS` | `gevent` | Gunicorn worker class. Options: `gthreads` (with `WEB_THREADS`) or `gevent` (with `WORKER_CONNECTIONS`). |
| `WORKER_CONNECTIONS` | `100` | Maximum concurrent connections per gevent worker. |
| `WEB_THREADS` | *(none)* | Number of threads per worker when `WORKER_CLASS=gthreads`. |

## Reverse Proxy (Werkzeug ProxyFix)

These variables configure Werkzeug ProxyFix for deployments behind reverse proxies.

| Variable | Default | Description |
|----------|---------|-------------|
| `WERKZEUG_PROXY_FIX` | `false` | Set to `true` to enable ProxyFix. Must be enabled for the following settings to take effect. |
| `WERKZEUG_X_FOR` | `1` | Trust `X-Forwarded-For` header from trusted proxies. |
| `WERKZEUG_X_PREFIX` | `1` | Rewrite subpath of proxied requests. Set to `0` to preserve original path. |
| `WERKZEUG_X_HOST` | `1` | Preserve the external domain name from `X-Forwarded-Host`. Set to `0` to ignore. |

Note: `X-Proto` is always enabled to preserve HTTP/HTTPS scheme in `url_for()` output.

## Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG_LEVEL` | `INFO` | Log verbosity level. Values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Higher levels log fewer messages. |
| `JSON_LOGGING` | `false` | Set to `true` to output log messages in JSON format for structured log processing. |
| `ACCESS_JSON_LOGGING` | `false` | Set to `true` to format Gunicorn access logs as JSON. |

## External Services

| Variable | Default | Description |
|----------|---------|-------------|
| `EXTERNALHTTPCALLS_TIMELIMIT` | `45` | Timeout in seconds for external HTTP calls (SPARQL queries, context document fetches). |
| `DB_UPGRADE_ON_START` | `true` | Whether to run `flask db upgrade` automatically on container startup. |

## Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_DIALECT` | Auto-detected | Database dialect override. Values: `base` (default), `postgresql`. Auto-detected from the database connection when possible. |