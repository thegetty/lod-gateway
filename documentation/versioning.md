# Versioning and Memento

The LOD Gateway supports document versioning through a Memento-compliant API. When enabled, the Gateway retains previous versions of records and makes them accessible through timemaps and version-specific endpoints.

([back to README](/README.md))

## Configuration

Versioning is controlled by the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `KEEP_LAST_VERSION` | `False` | Set to `True` to enable versioning. Previous versions are created whenever a record is updated. |
| `KEEP_VERSIONS_AFTER_DELETION` | `False` | Set to `True` to retain versions after a record is deleted. When `False`, all versions are deleted when the current record is deleted. |
| `VERSIONING_AUTHENTICATION` | `True` | Set to `True` to require authentication for retrieving previous versions. Set to `False` to allow unauthenticated access to version history. |
| `MEMENTO_PREFERRED_FORMAT` | `application/link-format` | Default format for timemap responses. Accepts `application/json` or `application/link-format`. Can be overridden per-request via `Accept` header. |
| `LINK_HEADER_PREV_VERSION` | `False` | Set to `True` to include a `Link` header pointing to the previous version on every resource response. |

## How Versioning Works

When `KEEP_LAST_VERSION=True`, every update to a record creates a new version entry. The Gateway stores the previous state before applying the update. These versions are accessible through Memento timemaps and direct version endpoints.

The timemap for a resource is always available at `/-tm-/{entity-id}`, regardless of whether versioning is enabled. When versioning is disabled, the timemap contains only the current version as the sole memento.

## Timemaps

Every resource has an associated timemap accessible at:

```
GET /{namespace}/-tm-/{entity-id}
```

The timemap returns a list of all versions of the resource, ordered from newest to oldest. The first entry is the timemap itself (self), followed by the original resource URI, then the version entries.

### Timemap Response Formats

Timemaps support two formats, selected via the `Accept` header or the `MEMENTO_PREFERRED_FORMAT` default.

**application/link-format:**

```
<http://host/ns/-tm-/object/123>;rel="self";until="2025-01-15T10:45:00";from="2025-01-10T01:00:00+0000",
<http://host/ns/object/123>;rel="original",
<http://host/ns/-VERSION-/a1b2c3d4>;datetime="2025-01-15T10:45:00+0000";rel="last memento",
<http://host/ns/-VERSION-/e5f6a7b8>;datetime="2025-01-12T14:30:00+0000";rel="memento",
<http://host/ns/-VERSION-/c9d0e1f2>;datetime="2025-01-10T01:00:00+0000";rel="first memento"
```

**application/json:**

```json
[
  {
    "uri": "http://host/ns/-tm-/object/123",
    "rel": "self",
    "until": "2025-01-15T10:45:00",
    "from": "2025-01-10T01:00:00+0000"
  },
  {
    "uri": "http://host/ns/object/123",
    "rel": "original"
  },
  {
    "uri": "http://host/ns/-VERSION-/a1b2c3d4",
    "datetime": "2025-01-15T10:45:00+0000",
    "rel": "last memento"
  },
  {
    "uri": "http://host/ns/-VERSION-/e5f6a7b8",
    "datetime": "2025-01-12T14:30:00+0000",
    "rel": "memento"
  },
  {
    "uri": "http://host/ns/-VERSION-/c9d0e1f2",
    "datetime": "2025-01-10T01:00:00+0000",
    "rel": "first memento"
  }
]
```

### Timemap Link Relations

| Relation | Description |
|----------|-------------|
| `self` | The timemap URI itself |
| `original` | The current resource (timegate) |
| `first memento` | The oldest version |
| `last memento` | The newest version |
| `memento` | An intermediate version |

When a resource has only one version, the entry carries `rel="first last memento"`.

### Accept-Datetime Header

You can request a version of a resource as of a specific datetime using the `Accept-Datetime` header. The Gateway returns a `302` redirect to the appropriate version:

```bash
curl -I -H "Accept-Datetime: Thu, 15 Jan 2025 10:30:00 GMT" \
  http://localhost:5100/museum/collection/object/123
```

The Gateway finds the version closest to the requested datetime (without exceeding it) and redirects to that version's URI.

### Timemap Link Header

Resource responses include `Link` headers pointing to the timemap in both available formats:

```
Link: <http://host/ns/-tm-/object/123>; rel="timemap"; type="application/link-format",
      <http://host/ns/-tm-/object/123>; rel="timemap"; type="application/json",
      <http://host/ns/object/123>; rel="original timegate"
```

## Version Endpoints

### GET /-VERSION-/{entity-id}

Retrieves a specific previous version of a record. The `{entity-id}` here is the version UUID found in the timemap, not the original resource ID.

Authentication is required if `VERSIONING_AUTHENTICATION=True` (the default).

**Example:**

```bash
curl -H "Authorization: Bearer AuthToken" \
  http://localhost:5100/museum/collection/-VERSION-/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

Returns the full record data as it existed at that version, with the same content negotiation support as the main resource endpoint.

**Status codes:**

- `200` -- version found and returned
- `401` -- authentication required or invalid token
- `404` -- no version with that UUID exists

### DELETE /-VERSION-/{entity-id}

Deletes a specific previous version. Requires authentication via `Authorization: Bearer {token}`.

**Example:**

```bash
curl -X DELETE \
  -H "Authorization: Bearer AuthToken" \
  http://localhost:5100/museum/collection/-VERSION-/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response:**

```json
{"message": "-VERSION-/a1b2c3d4-e5f6-7890-abcd-ef1234567890 deleted."}
```

**Status codes:**

- `200` -- version deleted successfully
- `401` -- authentication required or invalid token
- `404` -- no version with that UUID exists
- `503` -- database error

## ETags

Versioned resources include an `ETag` header with a SHA-256 checksum on `GET` and `HEAD` responses. The ETag follows [RFC 7232](https://datatracker.ietf.org/doc/html/rfc7232).

The checksum is enclosed in double quotes. When the response is gzip or deflate compressed, the ETag appends `:gzip` or `:deflate` to the checksum value.

### If-None-Match

The `If-None-Match` header is supported for `GET` and `HEAD` requests. Supply the checksum without the `:gzip`/`:deflate` suffix and without surrounding quotes.

- If the checksum matches the current resource, the Gateway returns `304 Not Modified` with an empty body.
- If the checksum does not match, the Gateway returns `200 OK` with the full resource.

### If-Match

The `If-Match` header is not currently supported.

### Computing the ETag Locally

```python
import hashlib
import json

def checksum_json(json_obj):
    """Compute SHA-256 checksum of a JSON-serializable object."""
    checksum = hashlib.sha256()
    checksum.update(json.dumps(json_obj, sort_keys=True).encode("utf-8"))
    return checksum.hexdigest()
```

## Memento-Datetime Header

When versioning is enabled, resource responses include a `Memento-Datetime` header indicating when the current version was created:

```
Memento-Datetime: Thu, 15 Jan 2025 10:45:00 GMT
```

## Deletion Behavior

The `KEEP_VERSIONS_AFTER_DELETION` variable controls what happens to versions when a record is deleted:

- **`False` (default)** -- all previous versions are deleted along with the current record. The timemap still exists but contains only the original reference with no mementos.
- **`True`** -- all versions are retained even after deletion. The current resource returns `404`, but the timemap remains accessible and all versions can still be retrieved. If data for the same entity ID is ingested again, the version history continues from where it left off.

## Compatibility

The LOD Gateway implements a subset of the [Memento RFC 7089](https://www.rfc-editor.org/rfc/rfc7089.txt) specification. The timemap ordering is reverse chronological (newest to oldest), which is not required by the specification but aids client processing.

## Use Cases

- **Document evolution** -- track how records change over time
- **Compliance** -- maintain historical records for regulatory requirements
- **Rollback** -- retrieve a previous version and re-ingest it to restore state
- **Debugging** -- compare versions to identify when data changed