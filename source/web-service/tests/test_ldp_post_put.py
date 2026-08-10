"""
Tests for LDP POST to deleted records and PUT mechanism endpoints.

This test file covers:
1. Issue 1: POST to container paths that match deleted records
2. Issue 2: PUT mechanism for creating/updating records with full validation
"""

import json
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from flaskapp.models import db
from flaskapp.models.record import Record
from flaskapp.utilities import checksum_json


class TestPostToDeletedRecords:
    """Tests for Issue 1: POST to container paths that match deleted records."""

    def test_post_to_deleted_record_path_succeeds(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
        """POST to a path where a deleted record exists should succeed.
        
        The deleted record should be removed and a new resource created.
        Expected: 201 Created
        """
        # Create a record and then delete it
        original_record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime.now(timezone.utc),
            datetime_updated=datetime.now(timezone.utc),
            data={"original": "data"},
            checksum=checksum_json({"original": "data"}),
        )
        test_db.session.add(original_record)
        test_db.session.commit()

        # Delete the record (set data to None and datetime_deleted)
        original_record.data = None
        original_record.datetime_deleted = datetime.now(timezone.utc)
        test_db.session.add(original_record)
        test_db.session.commit()

        # Verify record is deleted
        deleted_record = test_db.session.get(Record, original_record.id)
        assert deleted_record.data is None
        assert deleted_record.datetime_deleted is not None

        # Debug: print auth_token
        print(f"\n=== DEBUG: auth_token = {auth_token}")
        print(f"=== DEBUG: namespace = {namespace}\n")

        # POST to the deleted record's path with authentication
        new_data = {
            "id": f"{namespace}/{original_record.entity_id}",
            "type": "Object",
            "name": "New Resource",
            "description": "This should replace the deleted record",
        }

        response = client_ldpapi.post(
            f"{namespace}/{original_record.entity_id}",
            json=new_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Debug: print response details
        print(f"\n=== DEBUG: POST Response Status Code: {response.status_code}")
        print(f"=== DEBUG: POST Response Data: {response.data}")
        print(f"=== DEBUG: POST Response Headers: {dict(response.headers)}\n")

        # Should succeed with 201 Created
        assert response.status_code == 201, f"Expected 201, got {response.status_code}. Response data: {response.data}"
        assert "Location" in response.headers
        assert "application/ld+json" in response.headers.get("Content-Type", "")

        # Verify new record was created
        new_record = test_db.session.get(Record, original_record.id)
        assert new_record is not None
        assert new_record.data is not None
        assert new_record.datetime_deleted is None
        assert new_record.data.get("name") == "New Resource"

    def test_post_to_active_record_fails_with_409(
        self, client_ldpapi, test_db, namespace
    ):
        """POST to a path where an active record exists should fail with 409 Conflict.
        
        This ensures we don't accidentally overwrite active records.
        Expected: 409 Conflict
        """
        # Create an active record (not deleted)
        active_record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime.now(timezone.utc),
            datetime_updated=datetime.now(timezone.utc),
            data={"active": "data"},
            checksum=checksum_json({"active": "data"}),
        )
        test_db.session.add(active_record)
        test_db.session.commit()

        # Verify record is active
        active_record_check = test_db.session.get(Record, active_record.id)
        assert active_record_check.data is not None
        assert active_record_check.datetime_deleted is None

        # POST to the active record's path (as if it were a container)
        new_data = {
            "type": "Object",
            "name": "New Resource",
        }

        response = client_ldpapi.post(
            f"{namespace}/{active_record.entity_id}",
            json=new_data,
            content_type="application/ld+json",
        )

        # Should fail with 409 Conflict
        assert response.status_code == 409

    def test_post_to_deleted_record_removes_from_container(
        self, client_ldpapi, test_db, namespace
    ):
        """POST to a deleted record path should remove the deleted record from parent container.
        
        The new resource should be added to the parent container.
        """
        # Create a record in a container and then delete it
        parent_container_id = "object"
        original_record = Record(
            entity_id=f"{parent_container_id}/{uuid4()}",
            entity_type="Object",
            datetime_created=datetime.now(timezone.utc),
            datetime_updated=datetime.now(timezone.utc),
            data={"original": "data"},
            checksum=checksum_json({"original": "data"}),
        )
        test_db.session.add(original_record)
        test_db.session.commit()

        # Delete the record
        original_record.data = None
        original_record.datetime_deleted = datetime.now(timezone.utc)
        test_db.session.add(original_record)
        test_db.session.commit()

        # POST to the deleted record's path
        new_data = {
            "id": f"{namespace}/{original_record.entity_id}",
            "type": "Object",
            "name": "New Resource",
        }

        response = client_ldpapi.post(
            f"{namespace}/{original_record.entity_id}",
            json=new_data,
            content_type="application/ld+json",
        )

        assert response.status_code == 201

        # Verify new record is in parent container
        parent_container = test_db.session.query(Record).filter(
            Record.entity_id == f"/{parent_container_id}/"
        ).one_or_none()
        assert parent_container is not None

        # Check container membership
        parent_data = json.loads(parent_container.data)
        assert "members" in parent_data
        assert len(parent_data["members"]) > 0

    def test_post_to_nonexistent_path_succeeds(
        self, client_ldpapi, test_db, namespace
    ):
        """POST to a path where no record exists should succeed with 201.
        
        This is the normal case for creating new resources.
        Expected: 201 Created
        """
        new_entity_id = str(uuid4())
        new_data = {
            "id": f"{namespace}/{new_entity_id}",
            "type": "Object",
            "name": "Brand New Resource",
        }

        response = client_ldpapi.post(
            f"{namespace}/{new_entity_id}",
            json=new_data,
            content_type="application/ld+json",
        )

        assert response.status_code == 201
        assert "Location" in response.headers

        # Verify record was created
        new_record = test_db.session.query(Record).filter(
            Record.entity_id == new_entity_id
        ).one_or_none()
        assert new_record is not None
        assert new_record.data is not None
        assert new_record.datetime_deleted is None

    def test_post_to_deleted_record_with_pagination(
        self, client_ldpapi, test_db, namespace
    ):
        """Test that pagination works correctly after POST to deleted record.
        
        The container should show the new resource, not the deleted one.
        """
        # Create multiple records, delete some
        for i in range(5):
            record = Record(
                entity_id=f"object/{uuid4()}",
                entity_type="Object",
                datetime_created=datetime.now(timezone.utc),
                datetime_updated=datetime.now(timezone.utc),
                data={"index": i, "name": f"Resource {i}"},
                checksum=checksum_json({"index": i, "name": f"Resource {i}"}),
            )
            test_db.session.add(record)

        # Delete records at index 1 and 3
        records = test_db.session.query(Record).filter(
            Record.entity_id.like("object/%")
        ).all()
        for record in records:
            if record.data.get("index") in [1, 3]:
                record.data = None
                record.datetime_deleted = datetime.now(timezone.utc)

        test_db.session.commit()

        # POST to one of the deleted record paths
        deleted_record = test_db.session.query(Record).filter(
            Record.data is None
        ).first()
        new_data = {
            "id": f"{namespace}/{deleted_record.entity_id}",
            "type": "Object",
            "name": "Replacement Resource",
        }

        response = client_ldpapi.post(
            f"{namespace}/{deleted_record.entity_id}",
            json=new_data,
            content_type="application/ld+json",
        )

        assert response.status_code == 201

        # Check container pagination
        container_response = client_ldpapi.get(f"{namespace}/object/*")
        assert container_response.status_code == 200
        container_data = container_response.get_json()
        assert "total" in container_data
        assert container_data["total"] > 0

    def test_post_to_deleted_record_preserves_activity_stream(
        self, client_ldpapi, test_db, namespace
    ):
        """Test that activity stream is updated when POST to deleted record.
        
        Should create a new Activity for the new resource.
        """
        from flaskapp.models.activity import Activity
        from flaskapp.utilities import Event

        # Create and delete a record
        original_record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime.now(timezone.utc),
            datetime_updated=datetime.now(timezone.utc),
            data={"original": "data"},
            checksum=checksum_json({"original": "data"}),
        )
        test_db.session.add(original_record)
        test_db.session.commit()

        original_record.data = None
        original_record.datetime_deleted = datetime.now(timezone.utc)
        test_db.session.add(original_record)
        test_db.session.commit()

        # POST to the deleted record's path
        new_data = {
            "id": f"{namespace}/{original_record.entity_id}",
            "type": "Object",
            "name": "New Resource",
        }

        response = client_ldpapi.post(
            f"{namespace}/{original_record.entity_id}",
            json=new_data,
            content_type="application/ld+json",
        )

        assert response.status_code == 201

        # Verify activity was created
        activity = test_db.session.query(Activity).filter(
            Activity.record_id == original_record.id
        ).first()
        assert activity is not None
        assert activity.event == Event.Create.name


class TestPutEndpoint:
    """Tests for Issue 2: PUT mechanism for creating/updating records."""

    def test_put_with_valid_data_creates_new_record(self, client_ldpapi, test_db, namespace):
        """PUT with valid JSON, valid JSON-LD, and matching ID should create new record.
        
        Expected: 201 Created
        """
        new_entity_id = str(uuid4())
        valid_data = {
            "@id": f"{namespace}/{new_entity_id}",
            "type": "Object",
            "name": "New Resource via PUT",
            "description": "Created using PUT method",
        }

        response = client_ldpapi.put(
            f"{namespace}/{new_entity_id}",
            json=valid_data,
            content_type="application/ld+json",
        )

        assert response.status_code == 201
        assert "Location" in response.headers
        assert "application/ld+json" in response.headers.get("Content-Type", "")

        # Verify record was created
        new_record = test_db.session.query(Record).filter(
            Record.entity_id == new_entity_id
        ).one_or_none()
        assert new_record is not None
        assert new_record.data.get("name") == "New Resource via PUT"

    def test_put_with_valid_data_updates_existing_record(self, client_ldpapi, test_db, namespace):
        """PUT with valid data to existing record should update it.
        
        Expected: 200 OK
        """
        # Create an existing record
        existing_entity_id = str(uuid4())
        original_data = {
            "@id": f"{namespace}/{existing_entity_id}",
            "type": "Object",
            "name": "Original Name",
        }

        # First create the record via POST
        post_response = client_ldpapi.post(
            f"{namespace}/{existing_entity_id}",
            json=original_data,
            content_type="application/ld+json",
        )
        assert post_response.status_code == 201

        # Now update it via PUT
        updated_data = {
            "@id": f"{namespace}/{existing_entity_id}",
            "type": "Object",
            "name": "Updated Name",
            "description": "Updated via PUT",
        }

        response = client_ldpapi.put(
            f"{namespace}/{existing_entity_id}",
            json=updated_data,
            content_type="application/ld+json",
        )

        assert response.status_code == 200

        # Verify record was updated
        updated_record = test_db.session.query(Record).filter(
            Record.entity_id == existing_entity_id
        ).one_or_none()
        assert updated_record is not None
        assert updated_record.data.get("name") == "Updated Name"
        assert updated_record.data.get("description") == "Updated via PUT"

    def test_put_with_invalid_json_returns_422(self, client_ldpapi, test_db, namespace):
        """PUT with invalid JSON should return 422 Unprocessable Entity.
        
        Expected: 422 with error message about invalid JSON
        """
        entity_id = str(uuid4())

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            data="not valid json {{{",
            content_type="application/ld+json",
        )

        assert response.status_code == 422
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Invalid JSON" in response_data.get("error", "")

    def test_put_with_invalid_jsonld_returns_422(self, client_ldpapi, test_db, namespace):
        """PUT with invalid JSON-LD should return 422 Unprocessable Entity.
        
        Expected: 422 with error message about invalid JSON-LD
        """
        entity_id = str(uuid4())
        invalid_jsonld = {
            "name": "Test",
            # Missing @id or id field
            "nested": {
                "invalid": {"@type": "SomeTypeThatDoesNotExist"}
            }
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=invalid_jsonld,
            content_type="application/ld+json",
        )

        assert response.status_code == 422
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Invalid JSON-LD" in response_data.get("error", "")

    def test_put_with_mismatched_id_returns_422(self, client_ldpapi, test_db, namespace):
        """PUT with ID that doesn't match destination URI should return 422.
        
        Expected: 422 with error message about ID mismatch
        """
        entity_id = str(uuid4())
        data_with_wrong_id = {
            "@id": f"{namespace}/wrong/entity/id",  # Doesn't match URL
            "type": "Object",
            "name": "Test",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data_with_wrong_id,
            content_type="application/ld+json",
        )

        assert response.status_code == 422
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "ID" in response_data.get("error", "")
        assert "mismatch" in response_data.get("error", "").lower()

    def test_put_with_missing_id_field_returns_422(self, client_ldpapi, test_db, namespace):
        """PUT with missing @id/id field should return 422.
        
        Expected: 422 with error message about missing ID field
        """
        entity_id = str(uuid4())
        data_without_id = {
            "type": "Object",
            "name": "Test",
            # No @id or id field
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data_without_id,
            content_type="application/ld+json",
        )

        assert response.status_code == 422
        response_data = json.loads(response.data)
        assert "error" in response_data
        assert "Missing" in response_data.get("error", "")
        assert "id" in response_data.get("error", "").lower()

    def test_put_to_deleted_record_reactivates(self, client_ldpapi, test_db, namespace):
        """PUT to a deleted record path should reactivate it.
        
        The deleted record should be reactivated with new data.
        Expected: 200 OK (since record exists, even if deleted)
        """
        # Create and delete a record
        entity_id = str(uuid4())
        original_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Original",
        }

        # Create record
        post_response = client_ldpapi.post(
            f"{namespace}/{entity_id}",
            json=original_data,
            content_type="application/ld+json",
        )
        assert post_response.status_code == 201

        # Delete the record
        record = test_db.session.query(Record).filter(
            Record.entity_id == entity_id
        ).one()
        record.data = None
        record.datetime_deleted = datetime.now(timezone.utc)
        test_db.session.add(record)
        test_db.session.commit()

        # Verify record is deleted
        assert record.data is None
        assert record.datetime_deleted is not None

        # PUT to the deleted record path
        updated_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Reactivated",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=updated_data,
            content_type="application/ld+json",
        )

        # Should succeed with 200 (updating existing record)
        assert response.status_code == 200

        # Verify record was reactivated
        updated_record = test_db.session.query(Record).filter(
            Record.entity_id == entity_id
        ).one()
        assert updated_record.data is not None
        assert updated_record.datetime_deleted is None
        assert updated_record.data.get("name") == "Reactivated"

    def test_put_with_authentication_required(self, client_ldpapi, test_db, namespace, auth_token):
        """PUT should require authentication.
        
        Expected: 401 or 403 without valid token
        """
        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Test",
        }

        # Without authentication
        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
        )

        # Should fail with auth error
        assert response.status_code in [401, 403]

        # With authentication
        response_with_auth = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response_with_auth.status_code == 201

    def test_put_returns_correct_headers(self, client_ldpapi, test_db, namespace):
        """PUT should return correct HTTP headers.
        
        Expected: Location, Content-Type headers
        """
        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Test",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
        )

        assert response.status_code == 201
        assert "Location" in response.headers
        assert "application/ld+json" in response.headers.get("Content-Type", "")

        # Verify Location header is correct
        expected_location = f"{namespace}/{entity_id}"
        assert response.headers["Location"] == expected_location

    def test_put_with_id_field_instead_of_at_id(self, client_ldpapi, test_db, namespace):
        """PUT should accept 'id' field as well as '@id'.
        
        Some JSON-LD documents use 'id' instead of '@id'.
        """
        entity_id = str(uuid4())
        data_with_id_field = {
            "id": f"{namespace}/{entity_id}",  # Using 'id' instead of '@id'
            "type": "Object",
            "name": "Test with id field",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data_with_id_field,
            content_type="application/ld+json",
        )

        assert response.status_code == 201

        # Verify record was created
        new_record = test_db.session.query(Record).filter(
            Record.entity_id == entity_id
        ).one_or_none()
        assert new_record is not None
        assert new_record.data.get("name") == "Test with id field"

    def test_put_with_nested_jsonld(self, client_ldpapi, test_db, namespace):
        """PUT with nested JSON-LD structures should work correctly.
        
        Tests complex JSON-LD with nested objects and arrays.
        """
        entity_id = str(uuid4())
        complex_data = {
            "@id": f"{namespace}/{entity_id}",
            "@type": "Thing",
            "name": "Complex Resource",
            "description": "A resource with nested structures",
            "knows": [
                {
                    "@id": f"{namespace}/person/1",
                    "name": "Person One",
                    "type": "Person"
                },
                {
                    "@id": f"{namespace}/person/2",
                    "name": "Person Two",
                    "type": "Person"
                }
            ],
            "affiliation": {
                "@id": f"{namespace}/org/1",
                "name": "Organization One",
                "type": "Organization"
            }
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=complex_data,
            content_type="application/ld+json",
        )

        assert response.status_code == 201

        # Verify record was created with nested data
        new_record = test_db.session.query(Record).filter(
            Record.entity_id == entity_id
        ).one_or_none()
        assert new_record is not None
        assert "knows" in new_record.data
        assert len(new_record.data["knows"]) == 2
        assert "affiliation" in new_record.data

    def test_put_rollback_on_database_error(self, client_ldpapi, test_db, namespace, mocker):
        """PUT should rollback on database error.
        
        Tests that if database operation fails, the transaction is rolled back.
        """
        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Test",
        }

        # Mock database commit to raise an exception
        mocker.patch(
            "flaskapp.models.db.session.commit",
            side_effect=Exception("Database error"),
        )

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
        )

        # Should return error status
        assert response.status_code >= 400

        # Verify record was not created (rollback)
        new_record = test_db.session.query(Record).filter(
            Record.entity_id == entity_id
        ).one_or_none()
        assert new_record is None

    def test_put_with_ldp_api_disabled_returns_not_implemented(self, client, test_db, namespace):
        """PUT should return 501 Not Implemented when LDP_API is False.
        
        This is the default behavior when LDP features are disabled.
        """
        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Test",
        }

        response = client.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
        )

        # Should return 501 Not Implemented
        assert response.status_code == 501

    def test_put_with_ldp_backend_disabled_returns_not_implemented(self, client_ldpapi, test_db, namespace):
        """PUT should return 501 Not Implemented when LDP_BACKEND is False.
        
        Tests that both LDP_API and LDP_BACKEND must be True.
        """
        # Temporarily disable LDP_BACKEND
        client_ldpapi.config["LDP_BACKEND"] = False

        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Test",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
        )

        # Should return 501 Not Implemented
        assert response.status_code == 501

        # Restore LDP_BACKEND
        client_ldpapi.config["LDP_BACKEND"] = True

    def test_put_with_autocreate_containers_disabled_no_parent(
        self, client_ldpapi, test_db, namespace
    ):
        """PUT should fail when parent container doesn't exist and LDP_AUTOCREATE_CONTAINERS is False.
        
        Expected: 501 Not Implemented
        """
        # Disable autocreate containers
        client_ldpapi.config["LDP_AUTOCREATE_CONTAINERS"] = False

        entity_id = "nonexistent-container/new-resource"
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Test",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
        )

        # Should fail because parent container doesn't exist
        assert response.status_code == 501

        # Restore autocreate containers
        client_ldpapi.config["LDP_AUTOCREATE_CONTAINERS"] = True

    def test_put_activity_stream_updated(self, client_ldpapi, test_db, namespace):
        """PUT should create/update Activity in activity stream.
        
        Expected: Activity object created with Update event for existing records,
                  Create event for new records.
        """
        from flaskapp.models.activity import Activity
        from flaskapp.utilities import Event

        # Create an existing record
        entity_id = str(uuid4())
        original_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Original",
        }

        post_response = client_ldpapi.post(
            f"{namespace}/{entity_id}",
            json=original_data,
            content_type="application/ld+json",
        )
        assert post_response.status_code == 201

        # Now update via PUT
        updated_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Updated",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=updated_data,
            content_type="application/ld+json",
        )

        assert response.status_code == 200

        # Verify activity was created
        activity = test_db.session.query(Activity).filter(
            Activity.record_id == test_db.session.query(Record).filter(
                Record.entity_id == entity_id
            ).one().id
        ).first()
        assert activity is not None
        assert activity.event == Event.Update.name

    def test_put_with_datetime_preserved(self, client_ldpapi, test_db, namespace):
        """PUT should preserve datetime_created and update datetime_updated.
        
        Tests that the record's timestamps are handled correctly.
        """
        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Test",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
        )

        assert response.status_code == 201

        # Verify timestamps
        new_record = test_db.session.query(Record).filter(
            Record.entity_id == entity_id
        ).one()
        assert new_record.datetime_created is not None
        assert new_record.datetime_updated is not None
        assert new_record.datetime_updated >= new_record.datetime_created

    def test_put_with_checksum_updated(self, client_ldpapi, test_db, namespace):
        """PUT should update the record's checksum.
        
        Tests that the checksum is recalculated for the new data.
        """
        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Test",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
        )

        assert response.status_code == 201

        # Verify checksum was updated
        new_record = test_db.session.query(Record).filter(
            Record.entity_id == entity_id
        ).one()
        assert new_record.checksum is not None
        assert new_record.checksum != ""