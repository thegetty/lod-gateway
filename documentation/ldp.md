# Linked Data Platform Backend and API

([back to ToC](/README.md))

## Overview

The [Linked Data Platform (LDP)](https://www.w3.org/TR/ldp/#ldpc) is a W3C standard that defines a set of rules for interacting with web resources using HTTP. It provides a way to access, create, update, and delete RDF resources over HTTP in a standardized manner.

When LDP features are enabled, the LOD Gateway extends its document store with container structures. The service presents a single root container at `/`, and every resource lives within that hierarchy either directly or through nested containers. The API is extended with container resolution, pagination, POST for creating resources, and PUT for creating or updating resources at specific URIs.

For a complete interactive API reference, visit the Swagger UI at `/{namespace}/openapi/` or download the OpenAPI spec from `/{namespace}/openapi/openapi.json`.

## API Reference

All LDP write operations (POST, PUT, DELETE) require authentication. Include the `Authorization: Bearer {token}` header with every request, where `{token}` matches the `AUTHORIZATION_TOKEN` environment variable.

### HTTP Methods

| Method | Target | Description | Status Codes |
|--------|--------|-------------|--------------|
| GET | Container | Returns 303 redirect to first page | 303 |
| GET | Container page | Returns paginated member list | 200 |
| GET | Resource | Returns the resource | 200, 404 |
| POST | Container | Creates a new resource or container inside the container | 201, 409 |
| PUT | Resource | Creates or replaces a resource at the target URI | 200, 201, 422 |
| PUT | Container | Creates or updates a container at the target URI | 200, 201, 409, 422 |
| DELETE | Resource | Soft-deletes the resource | 200, 404 |
| DELETE | Container | Deletes empty containers only | 200, 404 |

### Container vs Resource Operations

| Operation | Container | Resource |
|-----------|-----------|----------|
| GET | 303 redirect to first page | 200 with resource data |
| POST | 201 (creates child resource or container) | Not applicable |
| PUT | 201 (create) or 200 (update) | 201 (create) or 200 (update) |
| DELETE | 200 (empty containers only) | 200 (soft delete) |

### Configuration Prerequisites

LDP support requires RDF processing. Enable these environment variables:

- `PROCESS_RDF=True` -- required for all LDP functionality.
- `LDP_BACKEND=True` -- enables the database models for containers and membership. Enable this first on existing instances to populate containers gradually in the background.
- `LDP_API=True` -- exposes the LDP REST API (container resolution, pagination, POST, PUT, DELETE).
- `LDP_AUTOCREATE_CONTAINERS=True` -- auto-creates missing parent containers when POST or PUT targets a nested path.

`LDP_BACKEND` can run independently of `LDP_API`. This lets you migrate an existing LOD Gateway instance gradually: enable `LDP_BACKEND` and `LDP_AUTOCREATE_CONTAINERS` first, refresh your data through the `/ingest` endpoint, then enable `LDP_API` when containers are populated.

On a new instance, enable all flags from the start.

---

## LDP Concepts

LDP introduces two major categories of resources:

- **Linked Data Platform Resources (LDPRs)** -- web resources that follow LDP interaction patterns.
- **Linked Data Platform Containers (LDPCs)** -- specialized LDPRs that manage membership of other resources.

An **RDF Source (LDP-RS)** is an LDPR whose state is represented entirely as RDF. It supports GET, POST, PUT, and DELETE, and the server exposes its content as an RDF graph.

A **BasicContainer** is the simplest form of an LDP container. It is an RDF Source that also manages linked membership using `ldp:contains` triples. It supports resource creation via POST and PUT, and behaves like a folder or collection.

### How BasicContainers and RDF Resources Work Together

A BasicContainer describes its own metadata (currently `dcterms:title` and `dcterms:description` only) and maintains a set of `ldp:contains` triples pointing to resources within it.

When a client POSTs to a BasicContainer, the server creates a new resource and adds a membership triple linking to it. When a client PUTs to a resource URI, the server creates or replaces the resource and updates the parent container's membership accordingly.

### LOD Gateway LDP Scope

The LOD Gateway supports a narrower portion of the full LDP specification:

- A single root container at `/` holds every resource, directly or through nested containers.
- Only `ldp:BasicContainer` is supported, with direct managed membership.
- The container hierarchy mirrors the URL path. A resource at `/annotations/test/12345` has the following hierarchy:

```
/ (root)
    --ldp:contains--> /annotations/
        --ldp:contains--> /annotations/test/
            --ldp:contains--> /annotations/test/12345
```

- Containers hold either other BasicContainers or JSON-LD named graphs. Binary or Non-RDF content is not supported.
- Container metadata is limited to `dcterms:title` and `dcterms:description`.
- Pagination follows the [LDP-PAGING specification](https://www.w3.org/TR/ldp-paging/). All container responses are paginated regardless of size. Containers-first ordering is used, followed by member JSON-LD resources.
- ID generation for POST uses UUID (configured via `LDP_ID_GEN`; only `uuid` is currently supported).

---

## LDP GET

Retrieve a resource or list the members of a container.

### GET a Resource

```
GET /{namespace}/{entity-id}
```

Returns the resource as JSON-LD with prefixed URIs.

**Response headers:** `Content-Type`, `ETag`, `Last-Modified`, `Link` (timemap, canonical), and `Link: <ldp#Resource>; rel="type"` when LDP is enabled.

**Status codes:**

| Code | Meaning |
|------|---------|
| 200 | Resource found |
| 404 | Resource not found or deleted |

### GET a Container

```
GET /{namespace}/{container-path}/
```

Returns an HTTP 303 redirect to the first page of the container. All containers are paginated, regardless of how many members they hold.

Follow the redirect to receive a paginated JSON-LD response. See the [Pagination](#pagination) section for details.

---

## LDP POST

Create a new resource inside a container. The server manages the resource URI through rebasing.

```
POST /{namespace}/{container-path}/
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| Authorization | Yes | `Bearer {token}` |
| Content-Type | Yes | `application/ld+json` |
| Slug | No | Desired leaf identifier for the new resource |

**Status codes:**

| Code | Meaning |
|------|---------|
| 201 | Resource created. `Location` header contains the resource URI. |
| 409 | A resource with that ID already exists and is active. |

**Response headers:** `Location`, `Content-Type`, `ETag`, `Last-Modified`, `Link`.

### How POST Handles IDs

The body may include an `id` or `@id` property. The server rebases relative IDs to match the container's path. If no ID is present, the server generates a UUID.

A `Slug` header overrides the top-level ID and replaces it with the slug value. Nested relative IDs are preserved under the new slug path.

See [Appendix A: POST Rebasing Examples](#appendix-a-post-rebasing-examples) for detailed examples of how rebasing works.

### Example: POST without Slug

```bash
curl -X POST http://localhost:5100/demo/my-container/ \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -d '{
    "@context": "https://www.w3.org/ns/anno.jsonld",
    "type": "Annotation",
    "body": {
      "type": "TextualBody",
      "value": "I like this page!"
    },
    "target": "http://www.example.com/index.html"
  }'
# -> 201 Created
# Location: http://localhost:5100/demo/my-container/d4c28721-d8a8-4d5f-9f22-7ae6bc0d5ad2
```

The server assigns a UUID since no ID was provided.

### Example: POST with Slug

```bash
curl -X POST http://localhost:5100/demo/my-container/ \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -H "Slug: my-annotation" \
  -d '{
    "@context": "https://www.w3.org/ns/anno.jsonld",
    "id": "draft-annotation",
    "type": "Annotation",
    "body": { "type": "TextualBody", "value": "Note" },
    "target": "http://www.example.com/page"
  }'
# -> 201 Created
# Location: http://localhost:5100/demo/my-container/my-annotation
```

The `Slug` header replaces the body ID. The resource is stored at the slug path.

### Example: POST with Nested Path (Auto-Create Containers)

```bash
curl -X POST http://localhost:5100/demo/my-container/ \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -H "Slug: sub-folder/new-resource" \
  -d '{
    "@context": {"dcterms": "http://purl.org/dc/terms/"},
    "type": "Dataset",
    "dcterms:title": "Nested Resource"
  }'
# -> 201 Created
# Location: http://localhost:5100/demo/my-container/sub-folder/new-resource
```

When `LDP_AUTOCREATE_CONTAINERS=True`, the server creates the intermediate `sub-folder/` container automatically.

---

## LDP PUT

Create or replace a resource at a specific URI. PUT is idempotent: calling it multiple times with the same body produces the same result.

Unlike POST, which targets a container and lets the server determine the resource URI, PUT targets the resource URI directly. The body `id` or `@id` must match the destination URI.

```
PUT /{namespace}/{entity-id}
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| Authorization | Yes | `Bearer {token}` |
| Content-Type | Yes | `application/ld+json` |

**Status codes:**

| Code | Meaning |
|------|---------|
| 201 | New resource or container created. `Location` header contains the resource URI. |
| 200 | Existing resource or container updated. |
| 409 | Conflict -- a Resource exists where a container was requested. |
| 422 | Invalid JSON, invalid JSON-LD, ID mismatch, or missing parent container. |

**Response headers:** `Location`, `Content-Type`, `ETag`, `Last-Modified`, `Link` (timemap, canonical, LDP Resource type).

### ID Validation Rules

PUT validates that the top-level `id` or `@id` in the request body matches the destination URI. The following cases are accepted:

| Body `id` / `@id` | Destination URI | Result |
|-------------------|-----------------|--------|
| `object/foo` | `/{namespace}/object/foo` | Accepted -- IDs match |
| `foo` (leaf name only) | `/{namespace}/object/foo` | Accepted -- remapped to destination path |
| *(no id or @id)* | `/{namespace}/object/foo` | Accepted -- destination URI injected as `@id` |
| `wrong/path` | `/{namespace}/object/foo` | Rejected -- 422 ID mismatch |

Rebasing applies the same rules as POST: relative IDs are resolved against the destination URI, absolute URIs are preserved, and blank nodes (`_:...`) are left unchanged.

### Example: Create a New Resource

```bash
curl -X PUT http://localhost:5100/demo/object/foo \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -d '{
    "@context": {"dcterms": "http://purl.org/dc/terms/"},
    "@id": "object/foo",
    "type": "Object",
    "dcterms:title": "My Resource"
  }'
# -> 201 Created
# Location: http://localhost:5100/demo/object/foo
```

### Example: Update an Existing Resource

```bash
curl -X PUT http://localhost:5100/demo/object/foo \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -d '{
    "@context": {"dcterms": "http://purl.org/dc/terms/"},
    "@id": "object/foo",
    "type": "Object",
    "dcterms:title": "Updated Title"
  }'
# -> 200 OK
```

### Example: PUT Without Explicit ID (Destination URI Injected)

```bash
curl -X PUT http://localhost:5100/demo/object/bar \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -d '{
    "@context": {"dcterms": "http://purl.org/dc/terms/"},
    "type": "Object",
    "dcterms:title": "ID injected from URL"
  }'
# -> 201 Created
# Stored at object/bar with @id set to "object/bar"
```

### Example: PUT with Leaf-Only ID (Remapped)

```bash
curl -X PUT http://localhost:5100/demo/object/baz \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -d '{
    "@context": {"dcterms": "http://purl.org/dc/terms/"},
    "@id": "baz",
    "type": "Object",
    "dcterms:title": "Leaf ID remapped"
  }'
# -> 201 Created
# The leaf "baz" is remapped to "object/baz" to match the destination
```

### Example: PUT with Mismatched ID (Rejected)

```bash
curl -X PUT http://localhost:5100/demo/object/foo \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -d '{
    "@context": {"dcterms": "http://purl.org/dc/terms/"},
    "@id": "wrong/entity/id",
    "type": "Object",
    "dcterms:title": "Bad ID"
  }'
# -> 422 Unprocessable Entity
```

The body ID `wrong/entity/id` does not match the destination `object/foo`.

### PUT vs POST

| | POST | PUT |
|---|---|---|
| Target | Container | Resource or Container |
| Resource URI | Server assigns or rebases | Client specifies via URL |
| Slug header | Supported | Not applicable |
| Idempotent | No | Yes |
| Creates intermediate containers | Yes (when `LDP_AUTOCREATE_CONTAINERS` enabled) | Yes (when `LDP_AUTOCREATE_CONTAINERS` enabled) |
| Create status | 201 | 201 |
| Update status | N/A | 200 |
| Conflict on existing ID | 409 | Replaces (200) or 409 (container blocked by Resource) |

### PUT Container Support

PUT can create or update containers, not just resources. When the request body declares itself as an `ldp:BasicContainer` (via `@context` and `@type`), the server treats it as a container operation.

**Create a new container:**

```bash
curl -X PUT http://localhost:5100/demo/my-container/ \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -d '{
    "@context": {
      "ldp": "http://www.w3.org/ns/ldp#",
      "dcterms": "http://purl.org/dc/terms/"
    },
    "@type": "ldp:BasicContainer",
    "dcterms:title": "My New Container",
    "dcterms:description": "A nested container"
  }'
# -> 201 Created
```

The container ID is derived from the destination URI. Only `dcterms:title` and `dcterms:description` are captured from the payload.

**Update an existing container:**

```bash
curl -X PUT http://localhost:5100/demo/my-container/ \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -d '{
    "@context": {
      "ldp": "http://www.w3.org/ns/ldp#",
      "dcterms": "http://purl.org/dc/terms/"
    },
    "@type": "ldp:BasicContainer",
    "dcterms:title": "Updated Title"
  }'
# -> 200 OK
```

**Container blocked by Resource (409 Conflict):**

If a Resource record already exists at the destination path, PUT cannot create or update a container at that location. The server returns 409 Conflict.

```bash
curl -X PUT http://localhost:5100/demo/object/foo/ \
  -H "Authorization: Bearer AuthToken" \
  -H "Content-Type: application/ld+json" \
  -d '{
    "@context": {
      "ldp": "http://www.w3.org/ns/ldp#",
      "dcterms": "http://purl.org/dc/terms/"
    },
    "@type": "ldp:BasicContainer",
    "dcterms:title": "Cannot create"
  }'
# -> 409 Conflict
```

### Container Requirements

PUT requires the parent container to exist. When `LDP_AUTOCREATE_CONTAINERS=True`, missing parent containers are created automatically. When disabled, PUT returns 422 if the parent container is missing.

PUT cannot target the root container (`/`).

---

## LDP DELETE

Delete a resource or an empty container.

```
DELETE /{namespace}/{entity-id}
```

**Headers:** `Authorization: Bearer {token}`

**Status codes:**

| Code | Meaning |
|------|---------|
| 200 | Resource or empty container deleted (soft delete). |
| 404 | Resource not found. |

Resources are soft-deleted: the data is removed but metadata and activity stream history are preserved. A previously deleted resource can be recreated by POSTing or PUTting to its path.

Containers can only be deleted when empty. Remove all child resources and nested containers first.

---

## Pagination

LOD Gateway containers are always paginated, following the [LDP PAGING specification](https://www.w3.org/TR/ldp-paging/). The `Prefer` request header is not currently supported.

### Navigation Flow

1. **Request the container** -- GET returns HTTP 303 redirecting to the first page.

```http
GET /demo/components/
# -> 303 See Other, redirect to ?page=1
```

2. **Fetch the first page** -- follow the redirect.

```http
GET /demo/components/?page=1
```

The response headers include `Link` headers for navigation:

```
Link: </demo/components/?page=1>; rel="first"
Link: </demo/components/?page=2>; rel="next"
Link: </demo/components/?page=11020>; rel="last"
```

The body contains the member list for that page in the `ldp:contains` property.

3. **Follow the `next` link** until no `next` link is present.

`first` and `last` are always present. `next` and `previous` appear only when applicable.

### Page Size

Page size is controlled by a server-side `max-member-count` configuration (same mechanism as the Activitystream pagination). The number of items per page is not guaranteed, and empty pages may appear when items are deleted during iteration.

### Pagination in Response Headers and Body

Pagination links are available in both HTTP `Link` headers and as RDF triples in the response body under `dcterms:hasPart`. This dual representation lets clients use whichever is more convenient.

### Example Container Page Response

```json
{
  "@context": [
    {
      "ldp": "http://www.w3.org/ns/ldp#",
      "dcterm": "http://purl.org/dc/terms/",
      "getty": "https://data.getty.edu/local/thesaurus/",
      "@base": "https://data.getty.edu/demo/",
      "first": { "@id": "getty:pagination/first", "@type": "@id" },
      "last":  { "@id": "getty:pagination/last",  "@type": "@id" },
      "next":  { "@id": "getty:pagination/next",  "@type": "@id" },
      "prev":  { "@id": "getty:pagination/prev",  "@type": "@id" }
    }
  ],
  "@id": "component/my-container/",
  "dcterm:title": "My Container",
  "@type": ["ldp:BasicContainer", "ldp:Container"],
  "ldp:contains": [
    {
      "@id": "component/my-container/newitems/",
      "dcterm:type": "ldp:BasicContainer",
      "dcterm:available": "2026-02-03T00:26:35+0000"
    }
  ],
  "dcterms:hasPart": {
    "@id": "component/my-container/?page=1",
    "@type": ["ldp:Resource", "ldp:Page"],
    "first": "component/my-container/?page=1",
    "last":  "component/my-container/?page=6",
    "next":  "component/my-container/?page=2"
  }
}
```

### Response Body Details

- **`@base`** -- all relative URIs in the response are prefixed by this value.
- **`ldp:contains`** -- member resources on this page. Items across pages are unique; combine pages to get the full membership list.
- **`dcterms:type`** -- verbatim value of the first `@type`/`type` from the resource. May be a relative term requiring the resource's own `@context` to resolve.
- **`dcterms:available`** -- timestamp when the resource was first added to the container.
- **`dcterms:hasPart`** -- pagination metadata. The LDP Paging specification does not define how to represent `ldp:Page` in RDF, so `dcterms:hasPart` is used. `first` and `last` are always present. `next` and `prev` appear when applicable.

---

## Current Limitations

### Other Container Classes

Only `ldp:BasicContainer` containers are supported. Containers capture only `dcterms:title` and `dcterms:description`. Other triples are discarded.

### Container Deletion

Containers can only be deleted when empty. A container may hold hundreds of thousands of resources, and cascading deletion is not supported within a single request. Remove all child resources and nested containers before deleting a container.

### PATCH Support

PATCH is not supported. LOD Gateway containers do not contain arbitrary data beyond `dcterms:title` and `dcterms:description`, and there is no mechanism for partial updates to resources. Use PUT for full resource replacement.

### Versioning, Slugs, and POST

A POST with a Slug ID fails with HTTP 409 if an active resource or a previous version of a resource already exists at that ID. PUT at the same URI replaces the resource (returns 200 if the resource exists, 201 if it is new). Use PUT when you need idempotent upsert semantics.

---

## Appendix A: POST Rebasing Examples

When a JSON-LD document is POSTed to a container, the server rebases relative `@id` properties to match the destination container path. This section shows how rebasing behaves in different scenarios.

All examples below are POSTed to `/my-container/` on `https://data.getty.edu/demo`.

### Rebasing Rules

- **Absolute URIs** are unchanged. `"@id": "https://remote/server/aat/123450"` stays as-is.
- **Blank nodes** are unchanged. `"@id": "_:b1"` stays as-is.
- **`@base` in the context** is used to resolve relative URIs to the destination path.
- **`Slug` header** replaces the top-level ID and rebases nested relative IDs under the new slug path.

### Example 1: Simple Annotation (No ID, No Slug)

Request body:

```json
{
  "@context": "https://www.w3.org/ns/anno.jsonld",
  "type": "Annotation",
  "body": {
    "type": "TextualBody",
    "value": "I like this page!",
    "format": "text/plain"
  },
  "target": "http://www.example.com/index.html"
}
```

The server assigns a UUID:

```json
{
  "@context": "http://www.w3.org/ns/anno.jsonld",
  "@id": "https://data.getty.edu/demo/my-container/d4c28721-d8a8-4d5f-9f22-7ae6bc0d5ad2",
  "type": "Annotation",
  "body": {
    "type": "TextualBody",
    "value": "I like this page!",
    "format": "text/plain"
  },
  "target": "http://www.example.com/index.html"
}
```

### Example 2: Annotation Collection with Slug

Request body (POSTed with `Slug: not-this`):

```json
{
  "@context": ["https://www.w3.org/ns/anno.jsonld", {"@base": "urn:"}],
  "type": "AnnotationCollection",
  "id": "this",
  "first": [
    {
      "id": "this/1",
      "body": { "id": "http://some/aat/classification" },
      "target": "http://www.example.com/irises.jpg",
      "agent": {
        "type": "Software",
        "name": "ML classification service"
      }
    },
    {
      "id": "this/2",
      "body": {
        "type": "TextualBody",
        "value": "A collection of flowers",
        "format": "text/plain"
      },
      "target": "http://www.example.com/irises.jpg"
    }
  ]
}
```

The slug replaces the top-level ID, and nested IDs are rebased under the slug:

```json
{
  "@context": "https://www.w3.org/ns/anno.jsonld",
  "type": "AnnotationCollection",
  "id": "https://data.getty.edu/demo/my-container/not-this",
  "first": [
    {
      "id": "https://data.getty.edu/demo/my-container/not-this/1",
      "body": { "id": "http://some/aat/classification" },
      "target": "http://www.example.com/irises.jpg",
      "agent": {
        "type": "Software",
        "name": "ML classification service"
      }
    },
    {
      "id": "https://data.getty.edu/demo/my-container/not-this/2",
      "body": {
        "type": "TextualBody",
        "value": "A collection of flowers",
        "format": "text/plain"
      },
      "target": "http://www.example.com/irises.jpg"
    }
  ]
}
```

Note the shift from `this` to `not-this` in the top-level ID, and how child IDs followed (`this/1` became `not-this/1`). The absolute URI `http://some/aat/classification` is preserved.

### Example 3: Complex @graph-based JSON-LD with Slug

Request body (POSTed with `Slug: newitems/780`):

```json
{
  "@graph": [
    {"@id": "items/780"},
    {"@id": "items/780/anno/456"},
    {"@id": "#frag"},
    {"@id": "_:b1"},
    {"@id": "items/780/absolute/path"},
    {"@id": "someotherthing/annotation"},
    {"@id": "http://another.host/things?id=1#part"}
  ],
  "@id": "items/780",
  "@type": "https://www.w3.org/2004/03/trix/rdfg-1/Graph",
  "@context": {"name": "http://schema.org/name", "@base": "urn:"}
}
```

Result (retrieved with `?relativeid=true`):

```json
{
  "@graph": [
    {"@id": "my-container/newitems/780"},
    {"@id": "my-container/newitems/780/anno/456"},
    {"@id": "my-container#frag"},
    {"@id": "_:b1"},
    {"@id": "my-container/newitems/780/absolute/path"},
    {"@id": "my-container/someotherthing/annotation"},
    {"@id": "http://another.host/things?id=1#part"}
  ],
  "@id": "my-container/newitems/780",
  "@type": "https://www.w3.org/2004/03/trix/rdfg-1/Graph",
  "@context": {
    "name": "http://schema.org/name",
    "@base": "https://data.getty.edu/demo/"
  }
}
```

Relative references are rebased under the new slug path. The fragment `#frag` is rebased to the container root. The blank node `_:b1` is preserved. The absolute URI from another host is unchanged.

**Important:** This POST requires `LDP_AUTOCREATE_CONTAINERS=True` because the slug `newitems/780` implies an intermediate container at `newitems/`. The server auto-creates it:

```
GET /my-container/newitems/?page=1
```

Returns a new BasicContainer with the created resource listed in `ldp:contains`.

---

## Appendix B: PUT Rebasing Examples

PUT applies the same rebasing rules as POST, but the body ID must match (or be remappable to) the destination URI.

### Example 1: PUT with Matching Full Path ID

PUT to `/demo/object/foo` with body `id: "object/foo"`:

```json
{
  "@context": {"dcterms": "http://purl.org/dc/terms/"},
  "id": "object/foo",
  "type": "Object",
  "dcterms:title": "Resource with correct id"
}
# -> 201 Created
```

### Example 2: PUT with Leaf ID (Remapped to Full Path)

PUT to `/demo/object/bar` with body `@id: "bar"`:

```json
{
  "@context": {"dcterms": "http://purl.org/dc/terms/"},
  "@id": "bar",
  "type": "Object",
  "dcterms:title": "Leaf ID remapped"
}
# -> 201 Created
# Stored at object/bar, @id remapped to "object/bar"
```

### Example 3: PUT with Nested Relative IDs

PUT to `/demo/graph/main` with nested relative IDs:

```json
{
  "@context": {"@base": "urn:"},
  "@id": "graph/main",
  "@graph": [
    {"@id": "graph/main/part/1"},
    {"@id": "graph/main/part/2"},
    {"@id": "http://external.org/term"}
  ]
}
# -> 201 Created
# Nested IDs rebased to match destination
# Absolute URI preserved
```

### Example 4: PUT with Mismatched ID (Rejected)

PUT to `/demo/object/foo` with body `@id: "other/bar"`:

```json
{
  "@context": {"dcterms": "http://purl.org/dc/terms/"},
  "@id": "other/bar",
  "type": "Object",
  "dcterms:title": "Wrong path"
}
# -> 422 Unprocessable Entity
# Error: The @id in the body (other/bar) does not match the destination URI (object/foo)
```