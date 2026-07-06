# LDP Implementation Specification

## Overview
This document specifies the implementation of two LDP-related fixes for the LOD Gateway:
1. Allow POSTing to container paths that match deleted records
2. Implement PUT mechanism for records

## Issue 1: POST to Deleted Record Paths

### Current Behavior
- When a record is deleted, `record.data` is set to `None` and `datetime_deleted` is set
- The record still exists in the database
- Currently, `container_post_item()` in `records.py` (lines 340-355) rejects POST requests to any path where a record exists, even if deleted
- Error: "Cannot POST a resource to a LOD Gateway resource. Needs to be a valid ldp:BasicContainer"

### Required Behavior
- POST to a container path should be allowed if the matching record is deleted
- The path should be treated as a container for the new resource
- The deleted record should be removed/replaced by the new resource

### Implementation Details

#### Modified Logic in `container_post_item()`
1. Check if record exists at entity_id
2. If record exists but is deleted (`data is None` and `datetime_deleted is not None`):
   - Treat the path as available for new resource creation
   - Delete the deleted record (or mark as replaced)
   - Proceed with normal POST flow
3. If record exists and is not deleted:
   - Continue to reject with 409 Conflict

#### Database Operations
- Delete the deleted record from Record table
- Remove from container membership if present
- Clear any associated graph store entries
- Create new record with POSTed data

#### Container Updates
- Add new resource to parent container
- Update container membership triples
- Maintain pagination integrity

## Issue 2: PUT Mechanism Implementation

### Overview
Implement a PUT endpoint that allows updating or creating records with full validation and integration.

### HTTP Methods
- `PUT /<path:entity_id>` - when `LDP_API` is True

### Validation Requirements

#### 1. Valid JSON Check
- Return HTTP 422 if body is not valid JSON
- Parse JSON and validate structure

#### 2. Valid JSON-LD Check
- Return HTTP 422 if body is not valid JSON-LD
- Use `pyld.jsonld.expand()` to validate
- Return error with reason

#### 3. ID Matching Check
- Extract `id` or `@id` from JSON body
- Compare with destination URI (relative to service root)
- Return HTTP 422 if they don't match
- Error message should explain the mismatch

### Success Responses

#### HTTP 201 - Created
- New record created successfully
- Location header with new resource URI
- Content-Type: application/ld+json

#### HTTP 200 - Updated
- Existing record updated successfully
- Return updated resource representation

### Integration with Existing Mechanisms

#### Activity Stream
- Create Activity object with Event.Update
- Link to the updated/created record
- Add to activity stream

#### Graph Store
- If `PROCESS_RDF` is True:
  - Expand JSON-LD to RDF
  - Update graph store with new triples
  - Handle graph store errors with rollback

#### Parent Container
- Update parent container's membership
- Add to container if not already present
- Maintain container pagination

### Error Handling

| Status Code | Condition |
|-------------|-----------|
| 400 | Invalid request format |
| 401/403 | Authentication failed |
| 404 | Parent container not found |
| 422 | Invalid JSON, Invalid JSON-LD, ID mismatch |
| 500 | Database error, Graph store error |

### Implementation Steps (COMPLETED)

1. [x] Create new route handler `container_put_item(entity_id)`
2. [x] Add validation functions:
   - [x] `validate_json(body)`
   - [x] `validate_jsonld(body)`
   - [x] `validate_id_match(json_ld, destination_uri)`
3. [x] Implement PUT logic:
   - [x] Check if record exists
   - [x] If exists: update (record_update)
   - [x] If not exists: create (record_create)
4. [x] Integrate with activity stream
5. [x] Integrate with graph store
6. [x] Update parent container
7. [x] Handle errors and rollbacks
8. [ ] Add tests

## File Changes Required

### source/web-service/flaskapp/routes/records.py
- Modify `container_post_item()` to handle deleted records
- Add new `container_put_item()` function
- Add PUT route decorator

### source/web-service/flaskapp/storage_utilities/record.py
- Verify `record_update()` exists and works correctly
- May need to add update functionality if not present

### source/web-service/flaskapp/errors.py
- Add new error status for ID mismatch if needed

### source/web-service/flaskapp/models/record.py
- May need to add update method if not present

## Testing Requirements

### Issue 1 Tests
1. POST to path of deleted record should succeed
2. POST to path of active record should fail with 409
3. Deleted record should be removed from database
4. New resource should be in parent container
5. Pagination should work correctly after operation

### Issue 2 Tests
1. PUT with valid JSON, valid JSON-LD, matching ID should succeed (201/200)
2. PUT with invalid JSON should return 422
3. PUT with invalid JSON-LD should return 422
4. PUT with mismatched ID should return 422
5. Activity stream should be updated
6. Graph store should be updated (if PROCESS_RDF)
7. Parent container should be updated
8. Rollback on graph store failure

## Environment Variables to Check
- `LDP_API` - Must be True for both features
- `LDP_BACKEND` - Must be True for LDP features
- `PROCESS_RDF` - Determines graph store integration
- `LDP_AUTOCREATE_CONTAINERS` - May affect behavior

## Dependencies
- pyld (JSON-LD processing)
- Flask (route handling)
- SQLAlchemy (database operations)
- Existing storage utilities