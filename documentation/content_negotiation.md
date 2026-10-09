# Content Negotiation

([back to README](/README.md))

## Overview

When RDF processing is enabled, the LOD Gateway supports two forms of content negotiation:

- **Standard HTTP content negotiation** -- request an alternate RDF serialization (Turtle, N-Triples, etc.) via the `Accept` header or the `format` / `_mediatype` query parameters.
- **Content Negotiation by Profile (CNBP)** -- request a transformed view of a resource using a SPARQL CONSTRUCT pattern, via the `Accept-Profile` header or the `_profile` query parameter.

Both mechanisms can be combined in a single request. The Gateway resolves the desired profile and format, then returns the resource accordingly.

## Standard Mimetype Negotiation

Request an alternate RDF serialization of a stored resource.

### Request methods

Use one of the following approaches, listed in order of priority:

1. **Query parameter `_mediatype` or `format`** -- highest priority. Accepts a MIME type or shorthand format name.
2. **`Accept` header** -- standard HTTP content negotiation. The Gateway selects the best match from the available formats.

**Examples:**

```bash
# Request Turtle format using the format parameter
curl "http://localhost:5100/museum/collection/object/123?format=turtle"

# Request N-Triples using the Accept header
curl -H "Accept: application/n-triples" \
  http://localhost:5100/museum/collection/object/123
```

### Supported formats

| MIME Type | Shorthand |
|-----------|-----------|
| `application/ld+json` | `json-ld` (default) |
| `text/turtle` | `turtle` |
| `application/n-triples` | `nt`, `nt11` |
| `application/rdf+xml` | `xml` |
| `text/n3` | `n3` |
| `application/n-quads` | `nquads` |
| `application/trig` | `trig` |

The `format` and `_mediatype` parameters also accept the shorthand values. The MIME type `application/ntriples` is accepted as an alias for `application/n-triples`.

### Plain-text override

Browsers may attempt to download responses with RDF MIME types instead of displaying them. Add `&plaintext=true` or `&force-plain-text=true` to the query string to force the response `Content-Type` to `text/plain; charset=UTF-8`:

```bash
curl "http://localhost:5100/museum/collection/object/123?format=nt&plaintext=true"
```

### ETag behavior

When the Gateway reformats a resource into an alternate RDF serialization, the response does not include an `ETag` header. The ETag is only computed for the stored JSON-LD representation. Use ETags for cache validation only on requests that return the default JSON-LD format.

## Content Negotiation by Profile

Profiles transform the base resource into a custom view using SPARQL CONSTRUCT queries. Each profile is matched against the resource type and returns a filtered or remapped set of triples.

### Request methods

Use one of the following, listed in priority order:

1. **Query parameter `_profile`** -- highest priority. Accepts a single profile URI.
2. **`Accept-Profile` header** -- accepts one or more profile URIs with optional quality values.

**Examples:**

```bash
# Request a profile using the query parameter
curl "http://localhost:5100/museum/collection/object/123?_profile=http://example.org/profile/dublin-core"

# Request a profile using the Accept-Profile header
curl -H "Accept-Profile: <http://example.org/profile/dublin-core>" \
  http://localhost:5100/museum/collection/object/123
```

When a profile is requested, the Gateway executes the matching SPARQL CONSTRUCT pattern against the graph store and returns the result. The response `Content-Type` reflects the requested format (or defaults to JSON-LD).

### Combined profile and format request

Request both a profile and an RDF format in the same call:

```bash
curl -H "Accept-Profile: <http://example.org/profile/dublin-core>" \
  -H "Accept: text/turtle" \
  http://localhost:5100/museum/collection/object/123
```

### Response headers

When a profile is applied, the response includes a `Link` header declaring the profile URI:

```
Link: <http://example.org/profile/dublin-core>; rel="profile"
```

### Profile errors

If the requested profile URI does not match any configured pattern for the resource type, the Gateway returns `400 Bad Request`:

```json
{
  "title": "Profile is not supported",
  "detail": "Profile \"http://example.org/profile/unknown\" is not supported for this resource."
}
```

## Link Header Discovery

Resource responses include `Link` headers that advertise available formats and profiles. Use these headers to discover what a resource can be retrieved as.

**Example Link header:**

```
Link: <http://localhost:5100/museum/collection/-tm-/object/123>; rel="timemap"; type="application/link-format",
      <http://localhost:5100/museum/collection/-tm-/object/123>; rel="timemap"; type="application/json",
      <http://localhost:5100/museum/collection/object/123>; rel="original timegate",
      <http://localhost:5100/museum/collection/object/123?_mediatype=application/ld+json>; rel="canonical"; type="application/ld+json",
      <http://localhost:5100/museum/collection/object/123?_mediatype=text/turtle&_profile=http://example.org/profile/dublin-core>; rel="alternate"; type="text/turtle"; format="http://example.org/profile/dublin-core"
```

Link relation values:

| `rel` | Description |
|-------|-------------|
| `canonical` | The base JSON-LD representation of the resource |
| `alternate` | A profiled or reformatted view of the resource |
| `profile` | Declares which profile the current response conforms to |
| `timemap` | Memento timemap for version history |

## Configuration

Profiles are loaded at startup via environment variables. Both require `PROCESS_RDF=True`.

| Variable | Description |
|----------|-------------|
| `CONTENT_PROFILE_DATA_URL` | URL to a JSON-encoded PatternSet export. The Gateway fetches and parses patterns from this URL on startup. |
| `CONTENT_PROFILE_DATA` | JSON-encoded PatternSet data provided inline as an environment variable. Takes priority over `CONTENT_PROFILE_DATA_URL` when both are set. |

When profiles are loaded successfully, the Gateway sets `CONTENT_PROFILE_PATTERNS_AVAILABLE=True` and indexes the patterns by entity type for fast lookup.

The `X-LODGATEWAY-CAPABILITIES` response header indicates whether content profiles are active:

```
X-LODGATEWAY-CAPABILITIES: JSON-LD: 'True', Content Profiles: 'True'
```

## Writing SPARQL Patterns for Profiles

Profiles are defined using the [`gettysparqlpatterns`](https://github.com/thegetty/getty-sparql-patterns) library. Each pattern is a SPARQL CONSTRUCT query with a single `$URI` keyword parameter representing the resource URI.

### Pattern requirements

- **SPARQL CONSTRUCT query** containing the `$URI` keyword parameter
- **`profile_uri`** -- a unique URI identifying the profile
- **`applies_to`** -- a list of entity types the profile applies to (e.g. `["HumanMadeObject", "Person"]`)
- **`stype`** -- set to `"construct"`

### Creating patterns with gettysparqlpatterns

Install the library and create a PatternSet:

```python
from gettysparqlpatterns import PatternSet

p = PatternSet(name="Content Profiles")

p.add_pattern(
    name="dc:title",
    sparql_pattern="""
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
CONSTRUCT {
  <$URI> dc:title ?title .
} WHERE {
  <$URI> rdfs:label ?title .
}
""",
    stype="construct",
    profile_uri="urn:getty:dctitle",
    applies_to=["InformationObject", "Person", "HumanMadeObject"],
)
```

### Exporting patterns

Export the PatternSet to JSON for loading into the Gateway:

```python
import json

pattern_export = p.export_patterns()
print(json.dumps(pattern_export, indent=2))
```

The exported JSON follows this structure:

```json
{
  "name": "Content Profiles",
  "description": "No description given.",
  "url": null,
  "patterns": [
    {
      "name": "dc:title",
      "description": "No description given",
      "sparql_pattern": "PREFIX dc: <...> CONSTRUCT { <$URI> dc:title ?title . } WHERE { <$URI> rdfs:label ?title . }",
      "stype": "construct",
      "keyword_parameters": ["URI"],
      "default_values": {},
      "applies_to": ["InformationObject", "Person", "HumanMadeObject"],
      "ask_filter": null,
      "framing": null,
      "profile_uri": "urn:getty:dctitle"
    }
  ]
}
```

### Loading patterns into the Gateway

Set `CONTENT_PROFILE_DATA` to the exported JSON string, or set `CONTENT_PROFILE_DATA_URL` to a URL hosting the JSON. The Gateway loads and indexes patterns on startup.

Restart the container after updating profile data.

## Unsupported CNBP Features

The LOD Gateway does not implement the following CNBP access patterns:

- **Profile parameter in the `Accept` header** -- `Accept: application/ld+json;profile="<http://...>"` is not supported. Use `Accept-Profile` or `_profile` instead.
- **Link header in the request** -- sending profile preferences via `Link` headers in the request is not supported. Use `Accept-Profile` or `_profile` instead.

These patterns are omitted to reduce parsing complexity and to keep the API surface testable via standard query parameters and headers.

## Response Priority Summary

When multiple negotiation parameters are present, the Gateway resolves them in this order:

1. **Mimetype priority:** `_mediatype` or `format` query parameter > `Accept` header
2. **Profile priority:** `_profile` query parameter > `Accept-Profile` header > default profile

If neither mimetype nor profile parameters match any available configuration, the Gateway returns the resource as JSON-LD with no transformation.

## Request Flow

The Gateway processes content negotiation in the following stages:

1. Check `If-None-Match` header against stored ETag. Return `304 Not Modified` if the checksum matches.
2. Parse request headers and query parameters to determine desired mimetype and profile.
3. If `relativeid=true` is set, return the raw JSON-LD without prefixing relative IDs.
4. Prefix all relative IDs to absolute URIs.
5. If the request is for JSON-LD with no profile, return the prefixed JSON-LD directly.
6. If a profile is requested, execute the matching SPARQL CONSTRUCT pattern against the graph store.
7. Reformat the result into the requested RDF serialization, if applicable.
8. Return the response with appropriate `Content-Type` and `Link` headers.