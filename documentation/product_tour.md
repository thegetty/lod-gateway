# LOD Gateway Product Tour

([back to README](/README.md)

A product tour guide for the LOD Gateway, explaining its capabilities and how it solves problems when working with JSON and JSON-LD data.

---

## Executive Summary

The **LOD Gateway** is a fast, reliable document store designed for the Semantic Web and Linked Data ecosystem. It provides a simple REST API for storing and retrieving JSON and JSON-LD documents, with optional graph processing, versioning, and Linked Data Platform (LDP) support.

### What Problems Does It Solve?

| Problem | Solution |
|---------|----------|
| Storing and retrieving JSON/JSON-LD documents | Simple REST API with predictable URIs |
| Converting JSON-LD to RDF triples | Automatic expansion with configurable RDF engines |
| Querying RDF data | SPARQL endpoint integration |
| Tracking document changes | Activity Streams API |
| Managing document versions | Memento-compliant versioning |
| Organizing data hierarchically | Sub-addressing and LDP containers |
| Customizing output formats | Content negotiation by profile |
| Deduplicating common triples | Base graph filtering |

---

## Service Levels

The LOD Gateway can operate at three capability levels, each building on the previous. You can enable or disable features by configuring environment variables.

### Level 1: JSON Document Store

**Configuration:** `PROCESS_RDF=False`

A simple, high-performance JSON document store with no RDF processing.

**Features:**
- Store and retrieve JSON documents
- Predictable REST API with stable URIs
- Activity Streams for change tracking
- Sub-addressing for nested data
- Memento versioning (if enabled)

**Use Cases:**
- High-volume JSON document storage where versioning or activity-stream functionality is useful
- APIs that don't require RDF semantics
- Prototyping and development
- Systems where RDF overhead is undesirable

**Example:**
```bash
# Store a simple JSON document
curl -X POST http://localhost:5100/museum/collection/ingest \
  -H "Authorization: Bearer AuthToken" \
  -d '{"id": "exhibit/123", "_label": "Renaissance Art"}'

# Retrieve it
curl http://localhost:5100/museum/collection/exhibit/123
```

---

### Level 2: JSON-LD with RDF Processing

**Configuration:** `PROCESS_RDF=True`, `SPARQL_QUERY_ENDPOINT` and `SPARQL_UPDATE_ENDPOINT` set

**Backend Requirements**:
- Requires a SPARQL 1.1 compliant backend such as Fuseki, GraphDB, AWS Neptune, or other compatible graph stores
- Backend must support SPARQL Update 1.1 for graph synchronization


Adds RDF processing capabilities to the JSON store.

**Features:**
- All Level 1 features
- Automatic JSON-LD to RDF expansion
- Named graph storage per document
- SPARQL query endpoint
- SPARQL UI (YASGUI)
- RDF format output (Turtle, N-Triples, etc.)
- Base graph deduplication
- Content Negotiation (w3c) and Content Negotiation by Profile (w3c)

**Use Cases:**
- Working with JSON-LD and RDF semantics
- Querying data with SPARQL
- Integrating with other RDF endpoints
- Semantic web applications
- Linked data publishing

**Example:**
```bash
# Ingest a JSON-LD document
curl -X POST http://localhost:5100/museum/collection/ingest \
  -H "Authorization: Bearer AuthToken" \
  -d '{
    "@context": "https://linked.art/ns/v1/linked-art.json",
    "id": "object/123",
    "type": "HumanMadeObject",
    "_label": "Ancient Vase"
  }'

# Query with SPARQL
curl "http://localhost:5100/museum/collection/sparql?query=SELECT ?id WHERE { ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://linked.art/types/Object> }"

# Get RDF output
curl http://localhost:5100/museum/collection/object/123?format=turtle
```

---

### Level 3: LDP Mode

**Configuration:** `PROCESS_RDF=True`, `LDP_BACKEND=True`, `LDP_API=True`

**Backend Requirements**:
- Requires a SPARQL 1.1 compliant backend such as Fuseki, GraphDB, AWS Neptune, or other compatible graph stores
- Backend must support SPARQL Update 1.1 for graph synchronization


Adds Linked Data Platform container support to Level 2.

**Features:**
- ✅ All Level 2 features
- ✅ LDP containers (hierarchical organization)
- ✅ Container membership management
- ✅ LDP pagination
- ✅ Slug-based resource creation
- ✅ Container metadata (title, description)
- ✅ Auto-create containers for nested paths

**Use Cases:**
- Hierarchical data organization
- Collections and sub-collections
- Annotation systems
- Resource management portals
- Complex data structures

**Example:**
```bash
# Create a container with nested resources
curl -X POST http://localhost:5100/museum/collection/exhibitions/renaissance/ \
  -H "Authorization: Bearer AuthToken" \
  -H "Slug: renaissance-art" \
  -d '{
    "@context": "https://linked.art/ns/v1/linked-art.json",
    "id": "exhibitions/renaissance/art",
    "type": "HumanMadeObject",
    "_label": "Renaissance Artworks"
  }'

# List container contents
curl http://localhost:5100/museum/collection/exhibitions/renaissance/
```

---

## Core API Functionality

### Ingest (`POST /ingest`)

Store, update, or delete documents in a single atomic operation.

**Capabilities:**
- Batch ingest multiple documents
- Delete documents (`"_delete": true`)
- Refresh graph from JSON-LD (`"_refresh": true`)
  - When upgrading from a previous level, this can be used to update the graphstore and LDP container index due to any changes made on a lower level.
- Relative URI support for cross-document references

**Problem Solved:** Simplifies bulk data loading and ensures data consistency.

```json
{
  "id": "object/123",
  "_delete": true
}
```

---

### GET (`GET /{entity-type}/{entity-id}`)

Retrieve a single document by its URI.

**Capabilities:**
- Content negotiation (JSON, RDF formats) by HTTP Header or QSA GET parameters '_mediatype'/'format'
- ETag support for caching
- Last-Modified headers
- Sub-addressing for nested paths

**Problem Solved:** Predictable, cacheable document retrieval with flexible output formats.

---

### Activity Streams (`GET /activity-stream`)

Track all changes to documents in the system.

**Capabilities:**
- Per-document activity streams
- System-wide activity streams
- Filtered streams by entity type
- Pagination support

**Problem Solved:** Audit trails and change history for compliance and debugging.


### SPARQL (`GET /sparql`)

Query the RDF graph using SPARQL 1.1.

**Backend Requirements**:
- Requires a SPARQL 1.1 compliant backend such as Fuseki, GraphDB, AWS Neptune, or other compatible graph stores
- Backend must support SPARQL Update 1.1 for graph synchronization


**Capabilities:**
- CONSTRUCT, SELECT, ASK queries
- Named graph queries
- UNION queries across graphs
- YASGUI web interface

**Problem Solved:** Powerful, standard query language for RDF data exploration.

---

## Optional Features

### Memento Versioning

**Configuration:** `KEEP_LAST_VERSION=True`

Maintains historical versions of documents.

**Capabilities:**
- Automatic version creation on each update
- Memento-compliant timemaps
- Access to past versions
- ETag-based version comparison

**Use Cases:**
- Tracking document evolution
- Compliance with archival requirements
- Debugging and rollback
- Time-sensitive data

**Example:**
```bash
# Get timemap for a resource
curl http://localhost:5100/museum/collection/object/123/-tm-

# Get a specific version
curl "http://localhost:5100/museum/collection/-VERSION-/abc123"
```

---

### Sub-Addressing

**Configuration:** `SUBADDRESSING=True`

Access nested paths within a document.

**Capabilities:**
- Hierarchical path resolution
- Automatic parent discovery
- Location header for parent URI

**Use Cases:**
- Accessing nested JSON properties
- Partial document retrieval
- Annotation systems

**Example:**
```bash
# Access nested path within a document
curl http://localhost:5100/museum/collection/place/c038/name

# Returns only the nested "name" property
```

---

### Prefix Search

**Configuration:** Automatic with sub-addressing

Search for existing paths by prefix.

**Capabilities:**
- Search from longest to shortest path
- First match wins
- 404 if no match found

**Use Cases:**
- Finding nested resources
- Auto-complete functionality
- Path resolution

---

## Content Negotiation

The LOD Gateway supports two types of content negotiation:

### Standard Mimetype Negotiation

Use `Accept` headers or `format`/`_mediatype` query parameters.

**Supported Formats:**
- `application/ld+json` (default)
- `text/turtle`
- `application/n-triples`
- `application/rdf+xml`
- `text/n3`
- `application/n-quads`
- `application/trig`

**Example:**
```bash
# Request Turtle format
curl -H "Accept: text/turtle" http://localhost:5100/museum/collection/object/123

# Or use format parameter
curl http://localhost:5100/museum/collection/object/123?format=nt
```

---

### Content Negotiation by Profile (CNBP)

Use `Accept-Profile` headers or `_profile` query parameters.

**Capabilities:**
- Profile-based data transformation
- SPARQL pattern matching
- Multiple profile support
- Profile discovery via Link headers

**Use Cases:**
- Custom data views
- Aggregated data presentations
- Specialized API endpoints
- Legacy system integration

**Example:**
```bash
# Request data in a specific profile
curl -H "Accept-Profile: <http://example.org/profile/v1>" \
  http://localhost:5100/museum/collection/object/123

# Or use query parameter
curl http://localhost:5100/museum/collection/object/123&_profile=http://example.org/profile/v1
```

**Creating Profiles:**
Profiles are defined using SPARQL CONSTRUCT queries that transform the base data. Load them via:
```bash
curl -X POST http://localhost:5100/museum/collection/content/profiles \
  -H "Authorization: Bearer AuthToken" \
  -d @profile.json
```

---

### Automatic JSON-LD Expansion

When `PROCESS_RDF=True`, JSON-LD documents are automatically expanded into RDF triples.

**Backend Requirements**:
- Requires a SPARQL 1.1 compliant backend such as Fuseki, GraphDB, AWS Neptune, or other compatible graph stores
- Backend must support SPARQL Update 1.1 for graph synchronization


**Capabilities:**
- Context resolution and caching
- Blank node handling
- Graph structure preservation
- Named graph association

---

### Base Graph Deduplication

**Configuration:** `RDF_BASE_GRAPH` set to an entity ID

Removes common triples from all named graphs.

**Use Cases:**
- Reducing graph size
- Improving query performance
- Managing common vocabulary triples

**Example:**
```json
{
  "@id": "_basegraph",
  "@graph": [
    {"@id": "schema:label", "@type": "rdf:Property"},
    {"@id": "schema:name", "@type": "rdf:Property"}
  ]
}
```

---

## Capabilities Summary

The LOD Gateway indicates its capabilities via the `X-LODGATEWAY-CAPABILITIES` response header.

**Example Response:**
```
X-LODGATEWAY-CAPABILITIES: 
  JSON-LD: 'True', 
  Base Graph: 'http://example.org/_basegraph', 
  Subaddressing: 'True', 
  Versioning: 'True',
  LDP: 'True'
```

---

## Switching Service Levels

You can downgrade from a higher level to a lower one by changing environment variables.

### Downgrade Examples:

**LDP → Level 2:**
```bash
LDP_BACKEND=False
LDP_API=False
```

**Level 2 → Level 1:**
```bash
PROCESS_RDF=False
SPARQL_QUERY_ENDPOINT=
SPARQL_UPDATE_ENDPOINT=
```

**Notes:**
- Downgrading is safe and immediate
- Upgrading may require data refresh
- LDP containers become regular resources when LDP is disabled. LDP container membership is no longer updated
- Graph data persists but is no longer updated
- *NB updates can be reprocessed using the /ingest _refresh functionality after upgrading, and what changed can be found from the activity-stream*

---

## Quick Reference: Common Scenarios

| Scenario | Configuration |
|----------|---------------|
| Simple JSON storage | `PROCESS_RDF=False` |
| JSON-LD with SPARQL | `PROCESS_RDF=True` |
| Hierarchical data | `PROCESS_RDF=True`, `LDP_BACKEND=True` |
| Versioned documents | `KEEP_LAST_VERSION=True` |
| Profile-based APIs | `PROCESS_RDF=True` + custom profiles |
| Max performance | `PROCESS_RDF=False` |
| Full feature set | All features enabled |

---

## Getting Started

1. **Choose your level:** Decide which features you need
2. **Configure environment:** Set appropriate variables
3. **Build and run:** `docker compose build && docker compose up`
4. **Test ingestion:** Upload a sample document
5. **Explore features:** Try SPARQL, versioning, or LDP

For detailed API documentation, see:
- [Ingest API](/README.md#ingest)
- [SPARQL Endpoint](/README.md#sparql)
- [LDP API](ldp.md)
- [Content Negotiation](content_negotiation.md)

---

*Last updated: 2026*
