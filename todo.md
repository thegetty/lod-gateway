# TODO List

## Issue 1: POST to Deleted Record Paths

### Phase 1: Analysis
- [x] Read and understand current POST handling in `container_post_item()`
- [x] Identify where deleted records are rejected
- [x] Understand record deletion mechanism (data=None, datetime_deleted)

### Phase 2: Implementation (COMPLETED)
- [x] Modify `container_post_item()` in `records.py`:
  - [x] Check if record exists
  - [x] Check if record is deleted (data is None AND datetime_deleted is not None)
  - [x] If deleted, remove the deleted record
  - [x] Continue with normal POST flow
- [x] Test POST to deleted record path
- [x] Verify deleted record is removed
- [x] Verify new resource is created correctly

### Phase 3: Integration Testing
- [ ] Test POST to active record path (should still fail with 409)
- [ ] Test container membership updates
- [ ] Test pagination after operation

## Issue 2: PUT Mechanism

### Phase 1: Analysis (COMPLETED)
- [x] Check if `record_update()` exists in `storage_utilities/record.py`
- [x] Review existing update mechanisms
- [x] Understand activity stream integration
- [x] Review graph store update mechanism

**Findings:**
- `record_update()` exists and handles versioning if KEEP_LAST_VERSION is True
- `record_update()` sets `datetime_deleted = None` (re-activates deleted records)
- `process_activity()` creates Activity objects for Create/Update/Delete events
- Graph store updates happen in `records.py` via `graph_expand()` and `graph_replace()`
- Container membership is handled by `handle_container_requirements()`

### Phase 2: Validation Functions (COMPLETED)
- [x] Create `validate_json(body)` function
- [x] Create `validate_jsonld(body)` function
- [x] Create `validate_id_match(json_ld, destination_uri)` function
- [x] Add error responses for validation failures

### Phase 3: PUT Handler Implementation (COMPLETED)
- [x] Create `container_put_item(entity_id)` function in `records.py`
- [x] Add PUT route: `@records.route("/<path:entity_id>", methods=["PUT"])`
- [x] Implement authentication check
- [x] Parse and validate request body
- [x] Check if record exists
- [x] If exists: call `record_update()`
- [x] If not exists: call `record_create()`
- [x] Handle graph store updates (if PROCESS_RDF)
- [x] Update activity stream
- [x] Update parent container
- [x] Return appropriate status code (200/201)

### Phase 4: Error Handling (COMPLETED)
- [x] Handle invalid JSON (return 422)
- [x] Handle invalid JSON-LD (return 422)
- [x] Handle ID mismatch (return 422)
- [x] Handle database errors (rollback and return 500)
- [x] Handle graph store errors (rollback and return error)

### Phase 5: Testing (PENDING)
- [ ] Test PUT with valid data (create new record) - expect 201
- [ ] Test PUT with valid data (update existing) - expect 200
- [ ] Test PUT with invalid JSON - expect 422
- [ ] Test PUT with invalid JSON-LD - expect 422
- [ ] Test PUT with mismatched ID - expect 422
- [ ] Test activity stream updates
- [ ] Test graph store updates
- [ ] Test parent container updates
- [ ] Test rollback on failure

## General Tasks
- [ ] Use venv: `/Users/bosteen/workspace/lod-gateway/.venv`
- [ ] Add changes to git and commit after each small step
- [ ] Do NOT add spec.md and todo.md to git
- [ ] Use black for linting
- [ ] Re-read files after editing to verify changes

## Order of Operations
1. Complete Issue 1 implementation and testing
2. Complete Issue 2 implementation and testing
3. Final integration testing
4. Documentation updates