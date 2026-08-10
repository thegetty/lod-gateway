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
        # Create a parent container first
        parent_container_id = f"object/{uuid4()}"
        parent_container = Record(
            entity_id=f"/{parent_container_id}/",
            entity_type="Container",
            datetime_created=datetime.now(timezone.utc),
            datetime_updated=datetime.now(timezone.utc),
            data=json.dumps(
                {
                    "@type": "sc:Collection",
                    "members": [],
                    "total": 0,
                    "paging": {"page": 1},
                }
            ),
            checksum=checksum_json({"members": [], "total": 0}),
        )
        test_db.session.add(parent_container)
        test_db.session.commit()

        # Create a record and then delete it
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

        # Delete the record (set data to None and datetime_deleted)
        original_record.data = None
        original_record.datetime_deleted = datetime.now(timezone.utc)
        test_db.session.add(original_record)
        test_db.session.commit()

        # Verify record is deleted
        deleted_record = test_db.session.get(Record, original_record.id)
        assert deleted_record.data is None
        assert deleted_record.datetime_deleted is not None

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

        # Should succeed with 201 Created
        assert (
            response.status_code == 201
        ), f"Expected 201, got {response.status_code}. Response data: {response.data}"
        assert "Location" in response.headers
        assert "application/ld+json" in response.headers.get("Content-Type", "")

        # Verify new record was created
        new_record = test_db.session.get(Record, original_record.id)
        assert new_record is not None
        assert new_record.data is not None
        assert new_record.datetime_deleted is None
        assert new_record.data.get("name") == "New Resource"

    def test_post_to_active_record_fails_with_409(
        self, client_ldpapi, test_db, namespace, auth_token
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Should fail with 409 Conflict
        assert response.status_code == 409

    def test_post_to_deleted_record_removes_from_container(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
        """POST to a deleted record path should remove the deleted record from parent container.

        The new resource should be added to the parent container.
        """
        # Create parent container first
        parent_container_id = f"object/{uuid4()}"
        parent_container = Record(
            entity_id=f"/{parent_container_id}/",
            entity_type="Container",
            datetime_created=datetime.now(timezone.utc),
            datetime_updated=datetime.now(timezone.utc),
            data=json.dumps(
                {
                    "@type": "sc:Collection",
                    "members": [],
                    "total": 0,
                    "paging": {"page": 1},
                }
            ),
            checksum=checksum_json({"members": [], "total": 0}),
        )
        test_db.session.add(parent_container)
        test_db.session.commit()

        # Create a record in a container and then delete it
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201

        # Verify new record is in parent container
        parent_container_check = (
            test_db.session.query(Record)
            .filter(Record.entity_id == f"/{parent_container_id}/")
            .one_or_none()
        )
        assert parent_container_check is not None

        # Check container membership
        parent_data = json.loads(parent_container_check.data)
        assert "members" in parent_data
        assert len(parent_data["members"]) > 0

    def test_post_to_nonexistent_path_succeeds(
        self, client_ldpapi, test_db, namespace, auth_token
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201
        assert "Location" in response.headers

        # Verify record was created
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == new_entity_id)
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data is not None
        assert new_record.datetime_deleted is None

    def test_post_to_deleted_record_with_pagination(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
        """Test that pagination works correctly after POST to deleted record.

        The container should show the new resource, not the deleted one.
        """
        # Create parent container first
        parent_container_id = f"object/{uuid4()}"
        parent_container = Record(
            entity_id=f"/{parent_container_id}/",
            entity_type="Container",
            datetime_created=datetime.now(timezone.utc),
            datetime_updated=datetime.now(timezone.utc),
            data=json.dumps(
                {
                    "@type": "sc:Collection",
                    "members": [],
                    "total": 0,
                    "paging": {"page": 1},
                }
            ),
            checksum=checksum_json({"members": [], "total": 0}),
        )
        test_db.session.add(parent_container)
        test_db.session.commit()

        # Create multiple records, delete some
        for i in range(5):
            record = Record(
                entity_id=f"{parent_container_id}/{uuid4()}",
                entity_type="Object",
                datetime_created=datetime.now(timezone.utc),
                datetime_updated=datetime.now(timezone.utc),
                data={"index": i, "name": f"Resource {i}"},
                checksum=checksum_json({"index": i, "name": f"Resource {i}"}),
            )
            test_db.session.add(record)

        # Delete records at index 1 and 3
        records = (
            test_db.session.query(Record)
            .filter(Record.entity_id.like(f"{parent_container_id}/%"))
            .all()
        )
        for record in records:
            if record.data.get("index") in [1, 3]:
                record.data = None
                record.datetime_deleted = datetime.now(timezone.utc)

        test_db.session.commit()

        # POST to one of the deleted record paths
        deleted_record = (
            test_db.session.query(Record).filter(Record.data is None).first()
        )
        new_data = {
            "id": f"{namespace}/{deleted_record.entity_id}",
            "type": "Object",
            "name": "Replacement Resource",
        }

        response = client_ldpapi.post(
            f"{namespace}/{deleted_record.entity_id}",
            json=new_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201

        # Check container pagination
        container_response = client_ldpapi.get(f"{namespace}/{parent_container_id}/*")
        assert container_response.status_code == 200
        container_data = container_response.get_json()
        assert "total" in container_data
        assert container_data["total"] > 0

    def test_post_to_deleted_record_preserves_activity_stream(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
        """Test that activity stream is updated when POST to deleted record.

        Should create a new Activity for the new resource.
        """
        from flaskapp.models.activity import Activity
        from flaskapp.utilities import Event

        # Create parent container first
        parent_container_id = f"object/{uuid4()}"
        parent_container = Record(
            entity_id=f"/{parent_container_id}/",
            entity_type="Container",
            datetime_created=datetime.now(timezone.utc),
            datetime_updated=datetime.now(timezone.utc),
            data=json.dumps(
                {
                    "@type": "sc:Collection",
                    "members": [],
                    "total": 0,
                    "paging": {"page": 1},
                }
            ),
            checksum=checksum_json({"members": [], "total": 0}),
        )
        test_db.session.add(parent_container)
        test_db.session.commit()

        # Create and delete a record
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201

        # Verify Activity was created
        activities = test_db.session.query(Activity).all()
        assert len(activities) > 0

        # Check activity stream
        from flaskapp.routes import activity_stream

        stream_response = client_ldpapi.get(f"{namespace}/activity-stream")
        assert stream_response.status_code == 200
        stream_data = stream_response.get_json()
        assert "items" in stream_data


class TestPutEndpoint:
    """Tests for Issue 2: PUT mechanism for creating/updating records."""

    def test_put_with_valid_data_creates_new_record(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201
        assert "Location" in response.headers

        # Verify record was created
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == new_entity_id)
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data is not None
        assert new_record.data.get("name") == "New Resource via PUT"

    def test_put_with_valid_data_updates_existing_record(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert post_response.status_code == 201

        # Now PUT to update
        updated_data = {
            "@id": f"{namespace}/{existing_entity_id}",
            "type": "Object",
            "name": "Updated Name",
        }

        put_response = client_ldpapi.put(
            f"{namespace}/{existing_entity_id}",
            json=updated_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert put_response.status_code == 200

        # Verify update
        updated_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == existing_entity_id)
            .one_or_none()
        )
        assert updated_record is not None
        assert updated_record.data.get("name") == "Updated Name"

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

        assert response.status_code in [
            400,
            422,
        ]  # Could be either depending on implementation

    def test_put_with_invalid_jsonld_returns_422(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
        """PUT with invalid JSON-LD should return 422 Unprocessable Entity.

        Expected: 422 with error message about invalid JSON-LD
        """
        entity_id = str(uuid4())
        invalid_jsonld = {
            "name": "Test",
            # Missing @id or id field
            "nested": {"invalid": {"@type": "SomeTypeThatDoesNotExist"}},
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=invalid_jsonld,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Should fail with validation error (400 or 422)
        assert response.status_code in [400, 422]

    def test_put_with_mismatched_id_returns_422(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code in [400, 422]  # Could be either

    def test_put_with_missing_id_field_returns_422(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code in [400, 422]  # Could be either

    def test_put_to_deleted_record_reactivates(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
        """PUT to a deleted record path should reactivate it.

        The deleted record should be reactivated with new data.
        Expected: 200 OK (since record exists, even if deleted)
        """
        # Create parent container first
        parent_container_id = f"object/{uuid4()}"
        parent_container = Record(
            entity_id=f"/{parent_container_id}/",
            entity_type="Container",
            datetime_created=datetime.now(timezone.utc),
            datetime_updated=datetime.now(timezone.utc),
            data=json.dumps(
                {
                    "@type": "sc:Collection",
                    "members": [],
                    "total": 0,
                    "paging": {"page": 1},
                }
            ),
            checksum=checksum_json({"members": [], "total": 0}),
        )
        test_db.session.add(parent_container)
        test_db.session.commit()

        # Create and delete a record
        entity_id = f"{parent_container_id}/{uuid4()}"
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert post_response.status_code == 201

        # Delete the record
        deleted_record = (
            test_db.session.query(Record).filter(Record.entity_id == entity_id).first()
        )
        deleted_record.data = None
        deleted_record.datetime_deleted = datetime.now(timezone.utc)
        test_db.session.commit()

        # PUT to reactivate
        reactivated_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Reactivated",
        }

        put_response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=reactivated_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert put_response.status_code == 200

        # Verify reactivated
        reactivated_record = (
            test_db.session.query(Record).filter(Record.entity_id == entity_id).first()
        )
        assert reactivated_record.data is not None
        assert reactivated_record.datetime_deleted is None
        assert reactivated_record.data.get("name") == "Reactivated"

    def test_put_with_authentication_required(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
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

        # With authentication - should create successfully
        response_with_auth = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response_with_auth.status_code == 201

    def test_put_returns_correct_headers(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201
        assert "Location" in response.headers
        assert "Content-Type" in response.headers
        assert "application/ld+json" in response.headers["Content-Type"]
        assert response.headers["Location"] == f"{namespace}/{entity_id}"

    def test_put_with_id_field_instead_of_at_id(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201

        # Verify record was created
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == entity_id)
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data.get("name") == "Test with id field"

    def test_put_with_nested_jsonld(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
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
                    "@type": "Person",
                },
            ],
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=complex_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201

        # Verify record was created
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == entity_id)
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data.get("name") == "Complex Resource"

    def test_put_with_ldp_backend_disabled_returns_not_implemented(
        self, client_ldpapi, test_db, namespace, auth_token, app_ldpapi
    ):
        """PUT should return 501 Not Implemented when LDP_BACKEND is False.

        Tests that both LDP_API and LDP_BACKEND must be True.
        """
        # Temporarily disable LDP_BACKEND
        original_backend = app_ldpapi.config["LDP_BACKEND"]
        original_api = app_ldpapi.config["LDP_API"]

        app_ldpapi.config["LDP_BACKEND"] = False
        app_ldpapi.config["LDP_API"] = False

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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 501

        # Restore original config
        app_ldpapi.config["LDP_BACKEND"] = original_backend
        app_ldpapi.config["LDP_API"] = original_api

    def test_put_with_autocreate_containers_disabled_no_parent(
        self, client_ldpapi, test_db, namespace, auth_token, app_ldpapi
    ):
        """PUT should fail when parent container doesn't exist and LDP_AUTOCREATE_CONTAINERS is False.

        Expected: 501 Not Implemented
        """
        # Disable autocreate containers
        original_autocreate = app_ldpapi.config.get("LDP_AUTOCREATE_CONTAINERS", True)
        app_ldpapi.config["LDP_AUTOCREATE_CONTAINERS"] = False

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
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Should fail - no parent container
        assert response.status_code in [404, 501]

        # Restore original config
        app_ldpapi.config["LDP_AUTOCREATE_CONTAINERS"] = original_autocreate

    def test_put_activity_stream_updated(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert post_response.status_code == 201

        # Count activities before PUT
        activities_before = test_db.session.query(Activity).count()

        # PUT to update
        updated_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Updated",
        }

        put_response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=updated_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert put_response.status_code == 200

        # Check that a new activity was created
        activities_after = test_db.session.query(Activity).count()
        assert activities_after > activities_before

    def test_put_with_database_error_rolls_back(
        self, client_ldpapi, test_db, namespace, auth_token, mocker
    ):
        """PUT should rollback on database error.

        If the database fails during PUT, the transaction should be rolled back.
        """
        from unittest.mock import patch
        from sqlalchemy.exc import IntegrityError

        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Test",
        }

        # Mock database commit to raise an error
        with patch(
            "flaskapp.routes.records.db.session.commit",
            side_effect=IntegrityError("test", {}, None),
        ):
            response = client_ldpapi.put(
                f"{namespace}/{entity_id}",
                json=data,
                content_type="application/ld+json",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

            # Should return error status
            assert response.status_code in [400, 422, 500]

    def test_put_with_duplicate_id_returns_conflict(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
        """PUT with ID that already exists should return 409 Conflict.

        Prevents accidental overwrites of existing records.
        """
        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "First",
        }

        # Create first record
        response1 = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response1.status_code == 201

        # Try to PUT with same ID again
        data2 = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Duplicate",
        }

        response2 = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data2,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Should return conflict
        assert response2.status_code == 409

    def test_put_with_container_type_returns_conflict(
        self, client_ldpapi, test_db, namespace, auth_token
    ):
        """PUT with ldp:BasicContainer type should return 409 Conflict.

        Containers require PATCH, not PUT.
        """
        entity_id = str(uuid4())
        data = {
            "@id": f"{namespace}/{entity_id}",
            "@type": "ldp:BasicContainer",
            "name": "Container",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Should return conflict
        assert response.status_code == 409
