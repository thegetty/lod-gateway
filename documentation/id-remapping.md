# ID Remapping on LDP POST and PUT

([back to ToC](/README.md))

Worked examples of how the LDP write path remaps id values on POST and PUT. Each example shows the incoming request body and the stored (relative) form; the first example also shows the prefixed form served from the graph store. It complements the [LDP API documentation](ldp.md), which covers the API itself.

## The Problem

LOD Gateway serves every record from a URI: a record stored at
`component/123456` is served from `https://data.getty.edu/component/123456`.
The gateway therefore requires the top-level identifier of a document to match
the address the document will be served from.

But authors upload documents whose ids reflect *their* context, not the
gateway's:

- a relative id like `note/1`, which only means something against the
  document's own base;
- an id that already contains the destination path (`component/123456`);
- an id pointing somewhere else entirely (`collection`);
- a local absolute path (`/people/123456`) that names another item in the
  store without committing to a host;
- a full URI, same-host or not;
- no id at all, or an empty/null id, meaning "assign one".

The write path remaps (rebases) id values so the stored document is
self-consistent with the address it will be served from, while leaving
references that must not move (other hosts, local absolute paths, blank
nodes) exactly where they are. This document walks the rules through small
examples, all using the linked.art `@context`:

```json
"@context": "https://linked.art/ns/v1/linked-art.json"
```

Every stored form below is the actual output of the rebasing code
(`prefix_rdf_ids` / `transform_id` in
`flaskapp/storage_utilities/representation.py`), run with server root
`https://data.getty.edu/` and container `component`.

## The Core Rules

For every id value in the document (top-level, nested, bare, fragment-only):

| Id value | With a destination (Slug on POST, URL path on PUT) |
|---|---|
| Relative, no scheme (`note/1`, `item/5`) | Rebased: resolved against the destination so it lands under the address the record is served from |
| Fragment-only (`#frag`) | Anchored to the destination: `component/123456#frag` |
| Already container-prefixed (`component/...`) | Stripped of the container prefix and rejoined under the destination (idempotent when it already matches) |
| Local absolute path (`/people/123456`) | **Left untouched**, in every position: it names another item in the store host-independently |
| Full URI, same host (`https://data.getty.edu/item/5`) | Normalized to its relative form and rebased like any relative id |
| Full URI, other host (`https://example.org/thing`) | **Left untouched** |
| Blank node (`_:b1`) | **Left untouched** |
| Query string / fragment (`item/1?ver=2#state`) | Preserved through rebasing |

Top-level id handling:

| Upload | POST | PUT |
|---|---|---|
| Id matching the destination | Stored as-is | Stored as-is |
| Relative / leaf id | Rebased under the destination | Remapped onto the destination path |
| `Slug` header + any top-level id | The slug wins: destination is `container/slug` | Slug header is **ignored**; the URL path is the destination |
| No id, or `""` / `null` / whitespace id | Slug value, or a generated id (uuid by default), under the uploaded key | Destination URI injected under the uploaded key |
| Id failing the valid-id rule (e.g. a space) | Treated as missing: generated id | Treated as missing: destination URI injected |
| Local absolute path as the top-level id | Treated as missing: generated id | Treated as missing: destination URI injected |
| Full URI, same host | Normalized to relative, then handled as above | Same |
| Full URI, other host | Rejected (422): the record would be served from a different host | Rejected (422 ID mismatch) |

A `null` top-level id is mapped to `""` before JSON-LD validation (pyld
rejects a null `@id`), so absent, `null`, and `""` all take the missing-id
pathway. The `id` vs `@id` key form of the upload is retained: the slug
value, a generated id, or the injected destination is written under the key
the upload used.

## POST Examples

All POSTs target `https://data.getty.edu/component/` (container
`component`). "Incoming" is the request body; "stored" is the record body
the gateway keeps, in its relative (host-rooted) form.

### P1. No id, with a Slug

The document carries no top-level id (here expressed as `null`). The `Slug`
header assigns the destination: `component/123456`. The nested relative id
`note/1` rebases under it.

Incoming, `POST /component/` with `Slug: 123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "",
  "referred_to_by": {"id": "note/1"}
}
```

NB `"id": null` will be treated the same way as a special edge-case for the top-level identifier.

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "referred_to_by": {"id": "component/123456/note/1"}
}
```

Note the key form: the upload used `id`, so the stored (and served) document
uses `id`, not `@id`.

### P2. Id already matches the destination

The upload is addressed to the exact destination. Nothing changes.

Incoming, `POST /component/` with `Slug: 123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "referred_to_by": {"id": "component/123456/note/1"}
}
```

Stored: unchanged.

### P3. Id points elsewhere

The top-level id names some other item; the `Slug` wins for the
destination. The nested relative id rebases under the destination, **not**
under the original top-level id.

Incoming, `POST /component/` with `Slug: 123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "collection",
  "referred_to_by": {"id": "item/1"}
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "referred_to_by": {"id": "component/123456/item/1"}
}
```

### P4. Nested local absolute path

`/people/123456` is a host-independent reference to another item in the
store. It is left untouched while everything else rebases.

Incoming, `POST /component/` with `Slug: 123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "collection",
  "about": {"id": "/people/123456"}
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "about": {"id": "/people/123456"}
}
```

### P5. Empty or null id, key form retained

`""` and `null` are missing ids. With a slug, the slug value is written
under the key the upload used.

Incoming, `POST /component/` with `Slug: 4321`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "",
  "referred_to_by": {"id": "note/1"}
}
```

Stored (identical for `"id": null`):

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/4321",
  "referred_to_by": {"id": "component/4321/note/1"}
}
```

### P6. No slug, bare leaf id

With no `Slug` header, a relative top-level id resolves against the
container. The top level id is treated like an implicit Slug id request.

Incoming, `POST /component/`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "123456",
  "referred_to_by": {"id": "note/1"}
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "referred_to_by": {"id": "component/note/1"}
}
```

### P7. No slug, no id

The server generates an identifier (a UUID by default) via the same slug
mechanism.

Incoming, `POST /component/` (no `Slug` header, no top-level id):

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "referred_to_by": {"id": "note/1"}
}
```

Stored (`8f2c…` stands for the generated UUID):

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "@id": "component/8f2c…",
  "referred_to_by": {"id": "component/8f2c…/note/1"}
}
```

A document with no id key gets the generated id under `@id`; a document
whose id key was present but empty/null keeps its own key form (P5).

### P8. No slug, local absolute path as the top-level id

A local absolute path cannot name a resource in the store, so it is treated
as a missing id: the server generates one. It is **not** stored at
`component/people/123456`.

Incoming, `POST /component/`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "/people/123456"
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/8f2c…"
}
```

### P9. No slug, id already container-prefixed

Values already under the container are stripped and rejoined under it, so a
correctly-prefixed document passes through unchanged.

Incoming, `POST /component/`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "referred_to_by": {"id": "component/note/9"}
}
```

Stored: unchanged. This mimics the JSON-LD relative forms that the /ingest
route requires and that can be retrieved from the store with ?relativeids=true.

### P10. Fragments, full URIs, blank nodes

A combined edge-case document, `POST /component/` with `Slug: 123456`:

Incoming:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "123456",
  "depicts": {"id": "#frag"},
  "iiif_manifest": {"id": "https://data.getty.edu/item/5"},
  "external": {"id": "https://example.org/thing"},
  "anonymous_agent": {"id": "_:b1"},
  "versioned": {"id": "item/1?ver=2#state"}
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "depicts": {"id": "component/123456#frag"},
  "iiif_manifest": {"id": "component/123456/item/5"},
  "external": {"id": "https://example.org/thing"},
  "anonymous_agent": {"id": "_:b1"},
  "versioned": {"id": "component/123456/item/1?ver=2#state"}
}
```

- `#frag` anchors to the destination.
- The same-host full URI is normalized to relative and rebased.
- The other-host full URI, the blank node, and the query string + fragment
  survive untouched or preserved.

## PUT Examples

PUT targets the URL path directly: `PUT /component/123456`. A `Slug` header
is ignored. Nested relative ids rebase against the destination's
**container** (`component`), not the full destination path.

### U1. Id matches the destination

Incoming, `PUT /component/123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "referred_to_by": {"id": "component/123456/note/1"}
}
```

Stored: unchanged.

### U2. Leaf name only

The id is remapped onto the destination path.

Incoming, `PUT /component/123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "123456",
  "referred_to_by": {"id": "note/1"}
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "referred_to_by": {"id": "component/note/1"}
}
```

### U3. No id (or empty / null id)

The destination URI is injected under the key the upload used.

Incoming, `PUT /component/123456` (identical for `"id": ""` or
`"id": null`):

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "referred_to_by": {"id": "note/1"}
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "@id": "component/123456",
  "referred_to_by": {"id": "component/note/1"}
}
```

### U4. Invalid id

An id that fails the valid-id rule (e.g. a space) is treated as missing:
the destination URI is injected. 201, not 422.

Incoming, `PUT /component/123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "has space!",
  "referred_to_by": {"id": "note/1"}
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "referred_to_by": {"id": "component/note/1"}
}
```

### U5. Local absolute path as the top-level id

Invalid as a resource id: the destination URI is injected. Nested local
absolute paths are left untouched.

Incoming, `PUT /component/123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "/people/123456",
  "about": {"id": "/people/789"}
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "about": {"id": "/people/789"}
}
```

### U6. Same-host full URI

Normalized to relative; it then matches the destination.

Incoming, `PUT /component/123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "https://data.getty.edu/component/123456",
  "referred_to_by": {"id": "note/1"}
}
```

Stored:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "component/123456",
  "referred_to_by": {"id": "component/note/1"}
}
```

### U7. Mismatched id

A relative id that does not resolve to the destination is rejected.

Incoming, `PUT /component/123456`:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "other/999"
}
```

Result: **422** - ID mismatch. Nothing is stored.

### U8. Slug header is ignored

`PUT /component/123456` with `Slug: other` behaves exactly like U1: the
destination is the URL path, and the `Slug` header has no effect.

## Serving and the Graph Store

Records are stored in relative form (the "stored" columns above). On the way
out, `idPrefixer` (in `flaskapp/utilities.py`) joins the store prefix onto
every relative id. The RDF graph store and the JSON-LD served from
`https://data.getty.edu/` use the same prefix, so the output for P1 in both
forms is:

```json
{
  "@context": "https://linked.art/ns/v1/linked-art.json",
  "type": "InformationObject",
  "id": "https://data.getty.edu/component/123456",
  "referred_to_by": {"id": "https://data.getty.edu/component/123456/note/1"}
}
```

Per-id behavior of the prefixer:

| Stored id | Prefixed output |
|---|---|
| `component/123456` | `https://data.getty.edu/component/123456` |
| `component/123456/note/1` | `https://data.getty.edu/component/123456/note/1` |
| `/people/123456` (local absolute) | `https://data.getty.edu/people/123456` |
| `https://example.org/thing` (other host) | unchanged |
| `_:b1` (blank node) | unchanged |

The prefix is configurable at deploy time (`FULL_RDF_ID_PREFIX`); the rules
are identical for whatever prefix is configured. The write-side rebasing
never needs the prefix: it works purely on relative forms and local absolute
paths.

## Where This Lives in the Code

| Concern | Location |
|---|---|
| Write-side rebasing (all of P1-P10, U1-U8) | `prefix_rdf_ids` / `transform_id` in `flaskapp/storage_utilities/representation.py` |
| Top-level id validity (missing / null / empty / local absolute) | `Representation._has_top_level_id` |
| `null` id mapped to `""` before validation | `Representation.json_ld` setter |
| Destination assignment on POST (slug, generated id) | `POST` in `flaskapp/routes/records.py` |
| Destination injection on PUT | `PUT` in `flaskapp/routes/records.py` |
| Export-side prefixing (graph store, served JSON-LD) | `idPrefixer` in `flaskapp/utilities.py` |
