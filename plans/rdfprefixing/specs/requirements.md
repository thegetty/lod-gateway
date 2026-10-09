# RDF prefix decoupling - requirements

## Purpose
Allow the triplestore (graph) namespace to be configured independently of the display/URL namespace, and fix three prefix bugs found during that investigation.

## Functional Behavior
1. New env var `FULL_RDF_ID_PREFIX`:
   - Set to a non-empty value: `app.config["RDFidPrefix"]` equals that value (trailing slash stripped).
   - Unset or empty: current behavior, `RDFidPrefix = BASE_URL[/NAMESPACE_FOR_RDF]` (NAMESPACE_FOR_RDF = RDF_NAMESPACE or APPLICATION_NAMESPACE fallback).
   - An INFO log is emitted when the override is in effect.
2. `idPrefix` and `RDFidPrefix` both have trailing slashes stripped (assignment actually performed, unlike the current no-op `[:-1]` expressions).
3. `FULL_BASE_GRAPH` = `f"{RDFidPrefix}/{RDF_BASE_GRAPH}"` (was `BASE_URL/NAMESPACE_FOR_RDF/basegraph`).
4. `entity_record` GET: the profile-based SPARQL query (`get_data_using_profile_query`) receives a `RDFidPrefix`-prefixed top-level id built from the original unprefixed data; the response body keeps `idPrefix`-prefixed ids.
5. `revert_triplestore_if_possible` delete branch: the `DROP GRAPH` target is the `RDFidPrefix`-prefixed id; ids that already carry a URI scheme (absolute) are passed through unchanged.

## Constraints
- `idPrefix` (display) derivation and all display/URL usages are unchanged.
- `idPrefixer`'s skip-absolute-URI behavior is unchanged (client-supplied absolute ids always determine the graphstore id).
- No changes to `docker-compose.yml` or `Dockerfile.*`; the env var flows through `env_file: .env`.

## Test Criteria (executed externally by user via docker/CircleCI; suite root: source/web-service)
| # | Criterion | Command | Pass condition |
|---|-----------|---------|----------------|
| T1 | `FULL_RDF_ID_PREFIX` set -> config equals it, slash-stripped | `pytest tests/test_flaskapp.py -k TestRDFIdPrefixConfig` | exit 0 |
| T2 | unset / empty -> fallback to BASE_URL derivation | same as T1 | exit 0 |
| T3 | trailing slash stripped from idPrefix and RDFidPrefix | same as T1 | exit 0 |
| T4 | FULL_BASE_GRAPH == f"{RDFidPrefix}/{basegraph}" when both vars set | `pytest tests/test_flaskapp.py -k base_graph` | exit 0 |
| T5 | profile query uri uses RDFidPrefix; body uses idPrefix (divergent prefixes) | `pytest tests/test_routes_records.py -k profile` | exit 0 |
| T6 | revert delete DROPs `f"{RDFidPrefix}/{id}"`; absolute ids unchanged | `pytest tests/test_graph_revert.py` | exit 0 |
| T7 | no regressions | full suite | exit 0, no new failures |

## Edge Cases & Error Handling
- `FULL_RDF_ID_PREFIX` with trailing slash: stripped, never double-slashed in graph URIs.
- Empty string `FULL_RDF_ID_PREFIX` treated as unset.
- Revert of a record whose id already contains a scheme (`https:`, `urn:`, or context urlprefix): not re-prefixed.
- Base graph record absent at startup: existing `base_graph_filter` behavior (warning + empty set, or ProgrammingError -> set) unchanged.
