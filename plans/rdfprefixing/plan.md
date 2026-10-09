# Plan: RDF id prefix decoupling and related prefix bugs

Slug: rdfprefixing
Status: IN-PROGRESS
Created: 2026-09-01
Outcome: `RDFidPrefix` is taken entirely from a new `FULL_RDF_ID_PREFIX` env var when set (else current derivation), trailing-slash trimming actually works, `FULL_BASE_GRAPH` derives from `RDFidPrefix`, profile SPARQL queries use a `RDFidPrefix`-prefixed copy of the data, and `revert_triplestore_if_possible` drops the correct graph URI on deletes.

## Out of Scope
- `idPrefix` derivation logic (display/URL prefix) - only its trailing-slash bug is fixed
- The `idPrefixer` skip-absolute-URIs behavior (pre-existing; documented, not changed)
- Container rollback in `revert_triplestore_if_possible` (explicit FIXME, untouched)
- `Dockerfile.*`, `docker-compose.yml` (new env var flows through existing `env_file: .env`)
- Running the test suite in this environment (handled externally via docker/CircleCI; results pasted back by user)

## Steps

- [x] 1. PROBE: confirm `containerRecursiveCallback` never mutates its input structure
  method: read source/web-service/flaskapp/utilities.py:144 (`data = copy.copy(data)` at every recursion level), 178/207 (recursive calls return new containers reassigned into the local copy); note the TOP-mode exception at 179-180 (nested containers aliased, not copied)
  confirms: the original top-level dict (record.data) is never written to, so its `id`/`@id` can be re-read from `record.data`/`subdata` at the profile-query site without retaining a variable
  breaks: top-level dict mutated in place -> retain an explicit copy of the original before prefixing instead, revise step 6

- [x] 2. PROBE: confirm every caller of `revert_triplestore_if_possible` passes relative (unprefixed) or client-supplied absolute ids
  method: read source/web-service/flaskapp/routes/ingest.py:188-194 (idmap values = raw client `id`), ingest.py:243-245 (ids_to_refresh = client ids), source/web-service/flaskapp/storage_utilities/graph.py:346-415
  confirms: the delete branch (graph.py ~370) is the only call site receiving a bare relative id, and `idPrefixer` semantics (skip values with a URI scheme) make prefixing it idempotent for absolute ids
  breaks: any caller already passing RDFidPrefix-absolute ids to the delete branch -> prefixing them again would be a no-op only if scheme-check matches; verify before implementing step 7

- [x] 3. Add a RED test class `TestRDFIdPrefixConfig` to source/web-service/tests/test_flaskapp.py
  What: 4 tests using `monkeypatch.setenv`/`delenv` + a fresh `create_app()`:
    (a) `FULL_RDF_ID_PREFIX=https://g.example/graph` set -> `app.config["RDFidPrefix"] == "https://g.example/graph"`
    (b) unset -> falls back to `BASE_URL[/NAMESPACE_FOR_RDF]` (existing behavior)
    (c) set to empty string `""` -> falls back to existing behavior
    (d) trailing slash on `BASE_URL` (and/or the env var) is stripped from BOTH `idPrefix` and `RDFidPrefix` (proves the no-op `[:-1]` fix)
  verify: `pytest source/web-service/tests/test_flaskapp.py -k TestRDFIdPrefixConfig` -> 4 FAILED before step 4 (RED), captured by user run

- [x] 4. Wire `FULL_RDF_ID_PREFIX` env var + fix trailing-slash no-op in source/web-service/flaskapp/__init__.py (~150-172)
  Replace the two no-op `app.config["idPrefix"][:-1]` / `app.config["RDFidPrefix"][:-1]` blocks with real `.rstrip("/")` assignments, and make `RDFidPrefix` resolve as:
    `FULL_RDF_ID_PREFIX` (if set and non-empty) -> use it verbatim
    else -> existing `BASE_URL[/NAMESPACE_FOR_RDF]` derivation
  Keep `NAMESPACE_FOR_RDF` derivation unchanged. Add an INFO log when the override is in effect.
  verify: `pytest source/web-service/tests/test_flaskapp.py -k TestRDFIdPrefixConfig` -> 4 PASSED (user run)

- [x] 5. Change `FULL_BASE_GRAPH` derivation to use `RDFidPrefix` in source/web-service/flaskapp/__init__.py (~470-477)
  Replace `f'{BASE_URL}/{NAMESPACE_FOR_RDF}/{basegraph}'` with `f'{app.config["RDFidPrefix"]}/{basegraph}'`.
  Add a test to test_flaskapp.py: with `FULL_RDF_ID_PREFIX` and `RDF_BASE_GRAPH` set, `FULL_BASE_GRAPH == f"{RDFidPrefix}/{basegraph}"`.
  verify: `pytest source/web-service/tests/test_flaskapp.py -k base_graph` -> PASSED (user run)

- [x] 6. Fix profile SPARQL query to use the graph (RDFidPrefix) URI in source/web-service/flaskapp/routes/records.py `entity_record` (~1410-1535)
  At the profile-query call (~1527), re-derive the original unprefixed data and build a graph-prefixed id (display prefixing never mutated `record.data`/`subdata`, per probe 1):
    `original = subdata or record.data`
    `graph_prefixed = inflate_relative_uris(original, attr)`
    pass `uri=graph_prefixed[attr]` instead of `uri=data[attr]`
  Do NOT feed the graph-prefixed copy back into the response body (response keeps `data` = idPrefix-prefixed). `inflate_relative_uris` resolves context `urlprefixes` itself, matching the display path.
  Add a test to test_routes_records.py: with a mocked `get_data_using_profile_query` (mocker) and a divergent `RDFidPrefix`, assert the `uri` kwarg passed equals the RDFidPrefix-prefixed id while the response body id is still idPrefix-prefixed.
  verify: `pytest source/web-service/tests/test_routes_records.py -k profile` -> PASSED (user run)

- [x] 7. Fix unprefixed `graph_delete` in the missing-record path of `revert_triplestore_if_possible`, source/web-service/flaskapp/storage_utilities/graph.py (~365-376)
  In the record-missing/None path (data rollback of a failed ingest; not a code action), prefix `relative_id` with the RDFidPrefix before `graph_delete`, using `idPrefixer` semantics (already-absolute ids with a URI scheme pass through unchanged) so the DROP target matches the graph URIs the write paths create.
  Add a unit test (new file tests/test_graph_revert.py or to test_flaskapp.py) with a mocked `graph_delete` asserting the DROP target is `f"{RDFidPrefix}/{relative_id}"` and that an already-absolute id is passed through unchanged.
  verify: `pytest source/web-service/tests/test_graph_revert.py` -> PASSED (user run)

- [x] 8. Document `FULL_RDF_ID_PREFIX` in documentation/configuration.md
  Add a row to the env-var table next to `RDF_NAMESPACE` (line ~32): `FULL_RDF_ID_PREFIX` | *(none)* | Full base URI (scheme + host included) used as the prefix for RDF named graph URIs, overriding the `BASE_URL`/`RDF_NAMESPACE` derivation. When set, `FULL_BASE_GRAPH` and all triplestore graph URIs derive from it; unset/empty falls back to existing behavior. Mention it takes precedence over `RDF_NAMESPACE`.
  verify: `grep -n FULL_RDF_ID_PREFIX documentation/configuration.md` shows the new row; user review of diff

- [ ] 9. VERIFY: full suite + all Test Criteria in specs/requirements.md
  verify: user runs the external docker/CircleCI suite and pastes results; every criterion in specs/requirements.md passes, no regressions

- [ ] 10. Revisit any stuck or unfinished steps. If still stuck, record the blocker in stuck.md

- [ ] 11. Back-propagate: fold confirmed learnings into specs/requirements.md and (where system-level) root specs/

- [ ] 12. Update README.md to document the new `FULL_RDF_ID_PREFIX` env var and the FULL_BASE_GRAPH/profile-query behavior

- [ ] 13. Set `Status: COMPLETE` in plan.md

## Referenced Spec Files
Per-effort (this directory/specs/):
- specs/requirements.md - functional requirements, the new env var contract, and executable test criteria
Shared (project root specs/), read-only:
- (none exist yet; created in step 10 if system-level learnings warrant)

## Plan Assumptions
1. VERIFIED - `RDFidPrefix`/`idPrefix` are set in `__init__.py` (~150-172) and the no-op `[:-1]` blocks are real (sliced value discarded)
2. VERIFIED - the only graph-write prefix choke point is `inflate_relative_uris` (graph.py:38); all write paths (records post/put, delete, ingest, revert-record) route through it or an inline `RDFidPrefix` f-string
3. VERIFIED - `containerRecursiveCallback` copies at every level (utilities.py:144) and never mutates the caller's top-level dict; TOP-mode (`recursive=False`) aliases nested containers so `del context["@base"]` can mutate the original `@context` sub-dict only - the top-level id is never affected (formal re-check in step 1)
4. REASONABLE - all `revert_triplestore_if_possible` callers pass relative or client-absolute ids (probed in step 2)
5. FRAGILE - `FULL_BASE_GRAPH` is the only other place a graph URI is derived from `BASE_URL`/`NAMESPACE_FOR_RDF` independently of `RDFidPrefix` (grepped; step 5 re-verifies)
6. REASONABLE - `get_data_using_profile_query` is the sole profile-query caller and currently receives the display-prefixed `data[attr]` (records.py ~1527)

## Task Dependencies
| Step | Inputs | Outputs | Blocks |
|------|--------|---------|--------|
| 1 | utilities.py | confirmed non-mutation | 6 |
| 2 | ingest.py, graph.py | confirmed id shapes | 7 |
| 3 | test_flaskapp.py | RED tests | 4 |
| 4 | step 3 | env var + rstrip fix | 5, 6, 8 |
| 5 | step 4 (RDFidPrefix) | FULL_BASE_GRAPH fix + test | 8 |
| 6 | step 1 | profile-query fix + test | 8 |
| 7 | step 2 | revert delete fix + test | 9 |
| 8 | - | configuration.md entry | 13 |
| 9 | steps 4-7 | full-suite evidence | 10 |
| 10-13 | - | closure | - |

## Open Questions
- [x] Env var name: confirmed by user as `FULL_RDF_ID_PREFIX` (the "FULL" signals a complete URI, scheme included). Impacted steps 3,4,11 + spec - updated.
- [x] Step-6 profile fix `urlprefixes`: resolved by design - `inflate_relative_uris` (used in step 6) resolves context-derived urlprefixes itself, so the graph-prefixed copy matches the display path exactly. No separate action needed.

## Failure Scenarios
1. `FULL_RDF_ID_PREFIX` set but `PROCESS_RDF` also on a deploy that still has old `RDF_NAMESPACE` docs -> ops keeps old namespace in tooling; mitigated by docs steps 8/12 and INFO log in step 4.
2. `containerRecursiveCallback` actually does mutate nested containers (probe 1 breaks) -> entity_record response and `record.data` would silently diverge; caught by probe before step 6.
3. A caller of `revert_triplestore_if_possible` passes an already-absolute display URI -> step 7 double-prefixes unless scheme-skip holds; caught by probe 2.
4. `FULL_BASE_GRAPH` change alters base-graph filter behavior for existing deployments that relied on the old derivation -> regression surfaces in full suite (step 9) or prod base-graph filtering; flagged for user to validate against their `RDF_BASE_GRAPH` deploy.
