# LOD Gateway

LOD Gateway is a fast, reliable Linked Open Data document store with integrated graph expansion and graph query features. It stores and serves JSON and JSON-LD documents via a REST API, optionally processes JSON-LD into RDF triples, and supports Linked Data Platform (LDP) containers, Memento versioning, and Activity Streams.

## Key Features

- **Document storage** -- store and retrieve JSON and JSON-LD documents via a simple REST API
- **Graph expansion** -- optional JSON-LD to RDF triple expansion with Fuseki, GraphDB, or Neptune backends
- **SPARQL querying** -- execute SPARQL queries against the RDF graph via endpoint or YASGUI web interface
- **Content Negotiation** -- standard HTTP content negotiation and [Content Negotiation by Profile](documentation/content_negotiation.md)
- **Linked Data Platform** -- hierarchical container support with POST/PUT resource management ([LDP API](documentation/ldp.md))
- **Memento versioning** -- automatic version history with Memento-compliant timemaps ([Versioning](documentation/versioning.md))
- **Activity Streams** -- paginated change history with datetime navigation and entity-type filtering ([Activity Streams](documentation/activitystreams.md))
- **Sub-addressing** -- resolve nested paths within documents to parent resources
- **Base graph deduplication** -- remove common triples from named graphs to reduce storage

The LOD Gateway operates at three [service levels](documentation/product_tour.md) depending on configuration: JSON document store, JSON-LD with RDF processing, and full LDP mode.

## Quick Start

Clone the repository, copy the example configuration, build the containers, and start the application:

```bash
git clone https://github.com/thegetty/lod-gateway
cd lod-gateway
cp .env.example .env
docker compose build
docker compose up --detach
```

Create the database schema on first run:

```bash
docker compose exec web flask db upgrade
```

The LOD Gateway runs at `http://localhost:5100` by default. Change the port via `FLASK_RUN_PORT` in `.env`.

View application logs:

```bash
docker compose logs --follow
```

Stop the application:

```bash
docker compose down
```

## API Overview

LOD Gateway uses a namespace prefix in all URLs. The format is `{base-url}/{namespace}/{resource}`. For example, `http://localhost:5100/museum/collection/object/123`.

### Core Endpoints

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/{entity-id}` | Retrieve a record | No |
| `GET` | `/{entity-id}/*` | Prefix search (browse matching paths) | No |
| `POST` | `/ingest` | Batch ingest, update, delete, or refresh records | Yes |
| `DELETE` | `/ingest` (via `_delete`) | Delete a record (soft delete) | Yes |

### Health Checks

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/health` | Check database connectivity | No |
| `GET` | `/authhealth` | Check database connectivity with authentication | Yes |
| `GET` | `/rdfhealth` | Check database and SPARQL endpoint connectivity | No |

### Additional Endpoints

- **[Activity Streams](documentation/activitystreams.md)** -- paginated change history, entity-type filtering, datetime navigation, per-record streams
- **[Versioning](documentation/versioning.md)** -- Memento timemaps (`/-tm-/{entity-id}`), version retrieval (`/-VERSION-/{entity-id}`), version deletion
- **[LDP Containers](documentation/ldp.md)** -- container listing, POST and PUT resource management, slug support
- **[SPARQL](documentation/product_tour.md#sparql-get-sparql)** -- query endpoint at `/sparql` (GET and POST), YASGUI UI at `/sparql-ui`
- **[Content Negotiation](documentation/content_negotiation.md)** -- standard mimetype negotiation and Content Negotiation by Profile
- **Dashboard** -- web interface at `/dashboard`

All endpoints require `Authorization: Bearer {token}` header for authenticated operations, where `{token}` matches the `AUTHORIZATION_TOKEN` environment variable.

### OpenAPI / Swagger UI

The LOD Gateway generates an OpenAPI specification dynamically. Access the Swagger UI at `/{namespace}/openapi/` and the raw OpenAPI JSON at `/{namespace}/openapi/openapi.json`.

## Documentation

| Document | Description |
|----------|-------------|
| [Product Tour](documentation/product_tour.md) | Conceptual overview, service levels, common scenarios |
| [LDP API](documentation/ldp.md) | Linked Data Platform container support, POST and PUT operations |
| [Activity Streams](documentation/activitystreams.md) | Activity stream endpoints, pagination, datetime navigation |
| [Versioning](documentation/versioning.md) | Memento versioning, timemaps, ETags, version lifecycle |
| [Content Negotiation](documentation/content_negotiation.md) | Mimetype negotiation and Content Negotiation by Profile |
| [Configuration](documentation/configuration.md) | Complete environment variable reference |
| [Deployment](documentation/deployment.md) | Production deployment, reverse proxy, worker tuning, logging |

## Testing

Run the test suite:

```bash
docker compose run --rm \
    -e APPLICATION_NAMESPACE="ns" \
    -e DATABASE=sqlite:// \
    -e AUTHORIZATION_TOKEN=AuthToken \
    web pytest
```

Run tests in watch mode with `pywatch`:

```bash
docker compose run --rm \
    -e APPLICATION_NAMESPACE="ns" \
    -e DATABASE=sqlite:// \
    -e AUTHORIZATION_TOKEN=AuthToken \
    web ptw
```

## License

Copyright (c) The J. Paul Getty Trust 2019--2025.

The Getty name, logos, and trademarks are owned by the J. Paul Getty Trust and are subject to [the J. Paul Getty Trust Trademark Policy for Open Source Projects](https://www.getty.edu/legal/trademarks/opensource.html).