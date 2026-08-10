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


class TestPostToDeletedRecords:
    """Tests for Issue 1: POST to container paths that match deleted records."""

    def test_post_to_deleted_record_path_succeeds(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """POST to a container where a deleted record exists should succeed.

        The deleted record should be removed and a new resource created.
        Expected: 201 Created
        """
        # Create a record first via POST to a container
        entity_id = str(uuid4())
        original_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Original",
        }

        # Create record via POST to container
        post_response = client_ldpapi.post(
            f"{namespace}/object/",
            json=original_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert post_response.status_code == 201

        # Find the record and delete it
        record = (
            test_db.session.query(Record).filter_by(entity_id=entity_id).one_or_none()
        )
        if record:
            record.data = None
            record.datetime_deleted = datetime.now(timezone.utc)
            test_db.session.add(record)
            test_db.session.commit()

            # Verify record is deleted
            assert record.data is None
            assert record.datetime_deleted is not None

        # POST to the same container again with new data
        new_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "New Resource",
            "description": "This should replace the deleted record",
        }

        response = client_ldpapi.post(
            f"{namespace}/object/",
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
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == entity_id)
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data is not None
        assert new_record.datetime_deleted is None
        assert new_record.data.get("name") == "New Resource"

    def test_post_to_active_record_fails_with_409(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """POST to a container where an active record with the same ID exists should fail with 409 Conflict.

        This ensures we don't accidentally overwrite active records.
        Expected: 409 Conflict
        """
        # Create an active record via POST
        entity_id = str(uuid4())
        original_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Original",
        }

        post_response = client_ldpapi.post(
            f"{namespace}/object/",
            json=original_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert post_response.status_code == 201

        # Verify record is active
        record = (
            test_db.session.query(Record).filter_by(entity_id=entity_id).one_or_none()
        )
        if record:
            assert record.data is not None
            assert record.datetime_deleted is None

            # POST to the same container again with same ID (should fail with 409)
            new_data = {
                "@id": f"{namespace}/{entity_id}",
                "type": "Object",
                "name": "Duplicate",
            }

            response = client_ldpapi.post(
                f"{namespace}/object/",
                json=new_data,
                content_type="application/ld+json",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

            # Should fail with 409 Conflict
            assert response.status_code == 409

    def test_post_to_nonexistent_path_succeeds(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """POST to a container where no record exists should succeed with 201.

        This is the normal case for creating new resources.
        Expected: 201 Created
        """
        entity_id = str(uuid4())
        new_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Brand New Resource",
        }

        response = client_ldpapi.post(
            f"{namespace}/object/",
            json=new_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201
        assert "Location" in response.headers

        # Verify record was created
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == entity_id)
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data is not None
        assert new_record.datetime_deleted is None

    def test_post_to_deleted_record_with_pagination(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """Test that pagination works correctly after POST to container.

        The container should show the new resource.
        """
        # Create multiple records via POST to container
        entity_ids = [str(uuid4()) for _ in range(5)]
        for eid in entity_ids:
            data = {
                "@id": f"{namespace}/{eid}",
                "type": "Object",
                "name": f"Resource {eid[:8]}",
            }
            response = client_ldpapi.post(
                f"{namespace}/object/",
                json=data,
                content_type="application/ld+json",
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            assert response.status_code == 201

        # Delete some records (index 1 and 3)
        deleted_ids = [entity_ids[1], entity_ids[3]]
        for eid in deleted_ids:
            record = (
                test_db.session.query(Record).filter_by(entity_id=eid).one_or_none()
            )
            if record:
                record.data = None
                record.datetime_deleted = datetime.now(timezone.utc)
                test_db.session.add(record)
        test_db.session.commit()

        # POST to the same container with a new ID
        new_entity_id = str(uuid4())
        new_data = {
            "@id": f"{namespace}/{new_entity_id}",
            "type": "Object",
            "name": "Replacement Resource",
        }

        response = client_ldpapi.post(
            f"{namespace}/object/",
            json=new_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201

        # Check container pagination
        container_response = client_ldpapi.get(f"{namespace}/object/")
        assert container_response.status_code == 200
        container_data = container_response.get_json()
        assert "total" in container_data
        assert container_data["total"] > 0

    def test_post_to_deleted_record_preserves_activity_stream(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """Test that activity stream is updated when POST to container.

        Should create a new Activity for the new resource.
        """
        from flaskapp.models.activity import Activity

        # Create a record via POST
        entity_id = str(uuid4())
        original_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Original",
        }

        post_response = client_ldpapi.post(
            f"{namespace}/object/",
            json=original_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert post_response.status_code == 201

        # Delete the record
        record = (
            test_db.session.query(Record).filter_by(entity_id=entity_id).one_or_none()
        )
        if record:
            record.data = None
            record.datetime_deleted = datetime.now(timezone.utc)
            test_db.session.add(record)
            test_db.session.commit()

            # POST again to the same container
            new_data = {
                "@id": f"{namespace}/{entity_id}",
                "type": "Object",
                "name": "New Resource",
            }

            response = client_ldpapi.post(
                f"{namespace}/object/",
                json=new_data,
                content_type="application/ld+json",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

            assert response.status_code == 201

        # Verify Activity was created
        activities = test_db.session.query(Activity).all()
        assert len(activities) > 0


class TestPutEndpoint:
    """Tests for Issue 2: PUT mechanism for creating/updating records."""

    def test_put_with_valid_data_creates_new_record(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT with valid JSON, valid JSON-LD, and matching ID should create new record.

        Expected: 201 Created
        """
        entity_id = str(uuid4())
        valid_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "New Resource via PUT",
            "description": "Created using PUT method",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=valid_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201
        assert "Location" in response.headers

        # Verify record was created
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == entity_id)
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data is not None
        assert new_record.data.get("name") == "New Resource via PUT"

    def test_put_with_valid_data_updates_existing_record(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT with valid data to existing record should update it.

        Expected: 200 OK
        """
        # Create an existing record via POST
        entity_id = str(uuid4())
        original_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Original Name",
        }

        post_response = client_ldpapi.post(
            f"{namespace}/object/",
            json=original_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert post_response.status_code == 201

        # Now PUT to update
        updated_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Updated Name",
        }

        put_response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=updated_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert put_response.status_code == 200

        # Verify update
        updated_record = (
            test_db.session.query(Record).filter_by(entity_id=entity_id).one_or_none()
        )
        assert updated_record is not None
        assert updated_record.data.get("name") == "Updated Name"

    def test_put_with_invalid_json_returns_error(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT with invalid JSON should return error.

        Expected: 422
        """
        entity_id = str(uuid4())

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            data="not valid json {{{",
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 422

    def test_put_with_mismatched_id_returns_error(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT with ID that doesn't match destination URI should return error.

        Expected: 422
        """
        entity_id = str(uuid4())
        data_with_wrong_id = {
            "@id": f"{namespace}/wrong/entity/id",
            "type": "Object",
            "name": "Test",
        }

        response = client_ldpapi.put(
            f"{namespace}/{entity_id}",
            json=data_with_wrong_id,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 422

    def test_put_to_deleted_record_reactivates(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT to a deleted record path should reactivate it.

        The deleted record should be reactivated with new data.
        Expected: 200 OK (since record exists, even if deleted)
        """
        # Create a record via POST
        entity_id = str(uuid4())
        original_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Original",
        }

        post_response = client_ldpapi.post(
            f"{namespace}/object/",
            json=original_data,
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert post_response.status_code == 201

        # Delete the record
        record = (
            test_db.session.query(Record).filter_by(entity_id=entity_id).one_or_none()
        )
        if record:
            record.data = None
            record.datetime_deleted = datetime.now(timezone.utc)
            test_db.session.add(record)
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
                test_db.session.query(Record)
                .filter_by(entity_id=entity_id)
                .one_or_none()
            )
            assert reactivated_record is not None
            assert reactivated_record.data is not None
            assert reactivated_record.datetime_deleted is None
            assert reactivated_record.data.get("name") == "Reactivated"

    def test_put_returns_correct_headers(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
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

    def test_put_with_id_field_instead_of_at_id(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT should accept 'id' field as well as '@id'."""
        entity_id = str(uuid4())
        data_with_id_field = {
            "id": f"{namespace}/{entity_id}",
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
            test_db.session.query(Record).filter_by(entity_id=entity_id).one_or_none()
        )
        assert new_record is not None
        assert new_record.data.get("name") == "Test with id field"

    def test_put_activity_stream_updated(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT should create/update Activity in activity stream."""
        from flaskapp.models.activity import Activity

        # Create an existing record
        entity_id = str(uuid4())
        original_data = {
            "@id": f"{namespace}/{entity_id}",
            "type": "Object",
            "name": "Original",
        }

        post_response = client_ldpapi.post(
            f"{namespace}/object/",
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

    def test_put_with_duplicate_id_returns_conflict(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
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
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
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
