# Record: rdfprefixing
**Step 1: PROBE containerRecursiveCallback non-mutation** - 2026-09-01
Status: Completed
verify: read utilities.py:144 (`data = copy.copy(data)`), 172-196/197-215 (each container level re-entered via recursion, writes only to local copy) -> pass. Original top-level dict never written; TOP mode (recursive=False) aliases nested containers only, matching the plan's documented exception.
**Step 2: PROBE revert caller id shapes** - 2026-09-01
Status: Completed
verify: read ingest.py:188-194 (idmap values = raw client `id`), ingest.py:243-245 (ids_to_refresh from client ids), graph.py:366-376 (delete path passes raw relative_id to graph_delete), graph.py:377-402 (record path re-inflates DB data via inflate_relative_uris, absolute ids skipped) -> pass. Step 7 premise holds: idPrefixer-semantics prefixing of relative_id in the delete path is idempotent for already-absolute ids.
**Step 3: RED tests TestRDFIdPrefixConfig** - 2026-09-01
Status: Completed (RED verification deferred to external run)
verify: added 4 tests to source/web-service/tests/test_flaskapp.py (set/unset/empty/trailing-slash), using monkeypatch + create_app(), expected values from .env.example (BASE_URL=http://localhost:5100, APPLICATION_NAMESPACE=museum/collection, RDF_NAMESPACE=ns). Cannot run suite locally (docker/CircleCI per user); RED+GREEN evidence to be captured in Step 8 external run.
**Step 4: FULL_RDF_ID_PREFIX env var + trailing-slash fix** - 2026-09-01
Status: Completed (GREEN verification deferred to external run)
verify: source/web-service/flaskapp/__init__.py - override branch (env var set/non-empty -> used verbatim + INFO log, empty string treated as unset), fallback branch unchanged, both no-op `[:-1]` expressions now assigned back. Deviation noted: RED evidence cannot be captured separately from GREEN because the suite only runs externally after all implementation; a `git stash` run of the new tests against pre-implementation code would show RED if desired.
**Step 5: FULL_BASE_GRAPH from RDFidPrefix** - 2026-09-01
Status: Completed (test verification deferred to external run)
verify: __init__.py FULL_BASE_GRAPH now f"{RDFidPrefix}/{basegraph}" (also removes a latent double-slash when NAMESPACE_FOR_RDF is empty, which the old f-string produced).
**Step 5 (cont.): FULL_BASE_GRAPH tests** - 2026-09-01
Status: Completed (verification deferred to external run)
verify: two tests added (override + fallback derivation). base_graph_filter mocked out (monkeypatch flaskapp.base_graph_filter) so app creation does not write a basegraph record into the shared test DB - prevents cross-test contamination of record-count assertions in later test files.
**Step 6: profile query uses RDFidPrefix URI** - 2026-09-01
Status: Completed (verification deferred to external run)
verify: records.py entity_record profile block now rebuilds the query URI via inflate_relative_uris(subdata or record.data, attr) - probe 1 confirmed the display prefixing pass never mutates the original. Scope note: the fix applies to both prefixed and unprefixed responses (the uri kwarg feeds only the SPARQL query, which must address graph URIs regardless of response prefixing); the previous relativeid+profile combination sent a bare relative URI that could never match the graphstore. Test added: test_profile_query_uses_rdfidprefix (mocked get_data_using_profile_query, divergent RDFidPrefix, asserts uri kwarg + body + non-mutation).
**Step 7: revert missing-record path prefixes the DROP target** - 2026-09-01
Status: Completed (verification deferred to external run)
verify: graph.py revert_triplestore_if_possible missing-record path now calls idPrefixer("id", relative_id, prefix=RDFidPrefix) before graph_delete; idPrefixer (utilities.py:234) skips values with an allowed URI scheme (ALLOWED_SCHEMES), so client-absolute ids pass through unchanged - idempotent with the write path. Log message updated to the actual graph URI. Test added: tests/test_graph_revert.py (2 tests, mocked get_record/graph_delete).
**Step 8: documentation/configuration.md** - 2026-09-01
Status: Completed
verify: added FULL_RDF_ID_PREFIX row to the RDF and Graph Processing table (takes precedence over BASE_URL/RDF_NAMESPACE derivation; empty = fallback), noted RDF_NAMESPACE is ignored when the override is set, and documented FULL_BASE_GRAPH = {RDFidPrefix}/{RDF_BASE_GRAPH} in the RDF_BASE_GRAPH row.
**Step 9: VERIFY (full external suite)** - PENDING
Status: Blocked on user run
verify: all implementation steps (3-8) complete; local py_compile passes on all modified files; test suite must be run in docker/CircleCI per user's workflow.
