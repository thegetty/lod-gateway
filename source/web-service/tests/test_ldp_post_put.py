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

# Reuse helpers from test_ldp_api.py
BASE_URL = "http://localhost:5100/"
JSONLD_CT = "application/ld+json"


def _make_payload(base: dict) -> dict:
    """Add @context to payload for PyLD RDF conversion."""
    return {
        "@context": {"dcterms": str(DCTERMS), "type": "@type"},
        **base,
    }


def to_abs(namespace, url: str) -> str:
    import urllib.parse as urlparse

    base = BASE_URL
    if namespace:
        base = urlparse.urljoin(BASE_URL, namespace).rstrip("/") + "/"
    return urlparse.urljoin(base, url.lstrip("/"))


def to_relative(url: str) -> str:
    rel = url.split(BASE_URL, 1)[-1]
    return rel


def _post_jsonld(
    namespace,
    client_ldpapi,
    auth_token,
    container_url: str,
    body: dict,
    slug: str = None,
):
    """POST with auth, using helpers from test_ldp_api.py."""
    import urllib.parse as urlparse

    headers = {"Content-Type": JSONLD_CT, "Authorization": "Bearer " + auth_token}
    if slug:
        headers["Slug"] = slug

    if not (
        container_url.startswith(f"/{namespace}/")
        or container_url.startswith(f"{namespace}/")
    ):
        container_url = f"/{namespace}/{container_url}"

    container_url = container_url.rstrip("/") + "/"

    response = client_ldpapi.post(container_url, json=body, headers=headers)

    return response


def _put_jsonld(namespace, client_ldpapi, auth_token, url: str, body: dict):
    """PUT with auth, using helpers from test_ldp_api.py."""
    import urllib.parse as urlparse

    headers = {"Content-Type": JSONLD_CT, "Authorization": "Bearer " + auth_token}

    if not (url.startswith(f"/{namespace}/") or url.startswith(f"{namespace}/")):
        url = f"/{namespace}/{url}"

    response = client_ldpapi.put(url, json=body, headers=headers)

    return response


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
            "@context": {"dcterms": str(DCTERMS), "type": "@type"},
            "@id": entity_id,
            "type": "Object",
            "name": "Original",
        }

        # Create record via POST to container
        post_response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            original_data,
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
        new_data = _make_payload({
            "@id": entity_id,
            "type": "Object",
            "name": "New Resource",
            "description": "This should replace the deleted record",
        })

        response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            new_data,
        )

        # Should succeed with 201 Created
        assert (
            response.status_code == 201
        ), f"Expected 201, got {response.status_code}. Response data: {response), f"Expected 201, got {response.status_code}. Response data: {response.data}" = _make_payload({
        ), f"Expected 201, got {response.status_code}. Response data: {response    assert "Location" in response.headers
        ), f"Expected 201, got {response.status_code}. Response data: {response    assert "application/ld+json" in response.headers.get("Content-Type", "")

        ), f"Expected 201, got {response.status_code}. Response data: {response    # Verify new record was created
        ), f"Expected 201, got {response.status_code}. Response data: {response    new_record = (
        ), f"Expected 201, got {response.status_code}. Response data: {response    test_db.session.query(Record)
        ), f"Expected 201, got {response.status_code}. Response data: {response    .filter(Record.entity_id == entity_id)
        ), f"Expected 201, got {response.status_code}. Response data: {response    .one_or_none()
        ), f"Expected 201, got {response.status_code}. Response data: {response    )
        ), f"Expected 201, got {response.status_code}. Response data: {response    assert new_record is not None
        ), f"Expected 201, got {response.status_code}. Response data: {response    assert new_record.data is not None
        ), f"Expected 201, got {response.status_code}. Response data: {response    assert new_record.datetime_deleted is None
        ), f"Expected 201, got {response.status_code}. Response data: {response    assert new_record.data.get("name") == "New Resource"

        ), f"Expected 201, got {response.status_code}. Response data: {response    def test_post_to_active_record_fails_with_409(
        ), f"Expected 201, got {response.status_code}. Response data: {response    self, namespace, client_ldpapi, ldp_fixture_app, auth_token
        ), f"Expected 201, got {response.status_code}. Response data: {response    ):
        ), f"Expected 201, got {response.status_code}. Response data: {response    """POST to a container where an active record with the same ID exists should fail with 409 Conflict.

        ), f"Expected 201, got {response.status_code}. Response data: {response    This ensures we don't accidentally overwrite active records.
        ), f"Expected 201, got {response.status_code}. Response data: {response    Expected: 409 Conflict
        ), f"Expected 201, got {response.status_code}. Response data: {response    """
        ), f"Expected 201, got {response.status_code}. Response data: {response    # Create an active record via POST
        ), f"Expected 201, got {response.status_code}. Response data: {response    entity_id = str(uuid4())
        ), f"Expected 201, got {response.status_code}. Response data: {response    original_data = {
        ), f"Expected 201, got {response.status_code}. Response data: {response})
            "@id": entity_id,
            "type": "Object",
            "name": "Original",
        }

        post_response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            original_data,
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
                "@id": entity_id,
                "type": "Object",
                "name": "Duplicate",
            }

            response = _post_jsonld(
                namespace,
                client_ldpapi,
                auth_token,
                "object/",
                new_data,
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
        new_dnew_data = _make_payload({
        new_d})
            "@id": entity_id,
            "type": "Object",
            "name": "Brand New Resource",
        }

        response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            new_data,
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
                "@id": eid,
                "type": "Object",
                "name": f"Resource {eid[:8]}",
            }
            response = _post_jsonld(
                namespace,
                client_ldpapi,
                auth_token,
                "object/",
                data,
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
            "@id": new_entity_id,
            "type": "Object",
            "name": "Replacement Resource",
        }

        response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            new_data,
        )

        assert response.status_code == 201

        # Check container pagination
        container_url = to_abs(namespace, "object/")
        container_response = client_ldpapi.get(
            to_relative(container_url),
            headers={"Accept": JSONLD_CT},
        )
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
            "@id": entity_id,
            "type": "Object",
            "name": "Original",
        }

        post_response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            original_data,
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
                "@id": entity_id,
                "type": "Object",
                "name": "New Resource",
            }

            response = _post_jsonld(
                namespace,
                client_ldpapi,
                auth_token,
                "object/",
                new_data,
            )

            assert response.status_code == 201

        # Verify Activity was created
        activities = test_db.session.query(Activity).all()
        assert len(activities) > 0


class TestPutEndpoint:
    """Tests for Issue 2: PUT mechanism for creating/updating records.

    The fundamental rule of PUT is: if 'id' or '@id' is present at the top level of
    the JSON-LD, it MUST match the destination URI. Rebasing accommodates variations,
    but the underlying idea is the same for ALL PUT REST APIs.
    """

    def test_put_with_correct_id_field(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT /ns/object/foo with 'id': 'object/foo' at top level.

        The 'id' field must match the destination URI.
        Expected: 201 Created
        """
        valid_data = {
            "id": "object/foo",
            "type": "Object",
            "name": "Resource with correct id",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/foo",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        assert "Location" in response.headers

        # Verify record was created
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == "object/foo")
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data is not None
        assert new_record.data.get("name") == "Resource with correct id"

    def test_put_with_correct_at_id_field(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT /ns/object/bar with '@id': 'object/bar' at top level.

        The '@id' field must match the destination URI.
        Expected: 201 Created
        """
        valid_data = {
            "@id": "object/bar",
            "type": "Object",
            "name": "Resource with correct @id",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/bar",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        # Verify record was created
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == "object/bar")
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data.get("name") == "Resource with correct @id"

    def test_put_with_remappable_relative_id(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT /ns/object/bar with 'id': 'bar' at top level.

        The relative 'id' should be remapped to match the destination URI.
        Expected: 201 Created
        """
        valid_data = {
            "id": "bar",
            "type": "Object",
            "name": "Resource with remappable relative id",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/bar",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        # Verify record was created with correct entity_id
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == "object/bar")
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data.get("name") == "Resource with remappable relative id"

    def test_put_with_remappable_relative_at_id(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT /ns/object/baz with '@id': 'baz' at top level.

        The relative '@id' should be remapped to match the destination URI.
        Expected: 201 Created
        """
        valid_data = {
            "@id": "baz",
            "type": "Object",
            "name": "Resource with remappable relative @id",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/baz",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        # Verify record was created with correct entity_id
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == "object/baz")
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data.get("name") == "Resource with remappable relative @id"

    def test_put_without_id_injects_destination_uri(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT /ns/object/foobar without top-level 'id' or '@id'.

        The destination URI should be injected as '@id': 'foobar'.
        Expected: 201 Created
        """
        valid_data = {
            "type": "Object",
            "name": "Resource without id",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/foobar",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        # Verify record was created with correct entity_id
        new_record = (
            test_db.session.query(Record)
            .filter(Record.entity_id == "object/foobar")
            .one_or_none()
        )
        assert new_record is not None
        assert new_record.data.get("name") == "Resource without id"
        # Verify the injected @id
        assert "@id" in new_record.data or "id" in new_record.data

    def test_put_with_mismatched_id_returns_error(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT with ID that doesn't match destination URI should return error.

        Expected: 422
        """
        data_with_wrong_id = {
            "@id": "wrong/entity/id",
            "type": "Object",
            "name": "Test",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/foo",
            data_with_wrong_id,
        )

        assert response.status_code == 422

    def test_put_with_invalid_json_returns_error(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT with invalid JSON should return error.

        Expected: 422
        """
        url = to_abs(namespace, "object/foo")
        response = client_ldpapi.put(
            to_relative(url),
            data="not valid json {{{",
            content_type="application/ld+json",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 422

    def test_put_with_valid_data_updates_existing_record(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT with valid data to existing record should update it.

        Expected: 200 OK
        """
        # Create an existing record via POST
        entity_id = str(uuid4())
        original_data = {
            "@id": entity_id,
            "type": "Object",
            "name": "Original Name",
        }

        post_response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            original_data,
        )
        assert post_response.status_code == 201

        # Now PUT to update
        updated_data = {
            "@id": entity_id,
            "type": "Object",
            "name": "Updated Name",
        }

        put_response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            entity_id,
            updated_data,
        )

        assert put_response.status_code == 200

        # Verify update
        updated_record = (
            test_db.session.query(Record).filter_by(entity_id=entity_id).one_or_none()
        )
        assert updated_record is not None
        assert updated_record.data.get("name") == "Updated Name"

    def test_put_returns_correct_headers(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT should return correct HTTP headers.

        Expected: Location, Content-Type headers
        """
        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/test-headers",
            {"@id": "object/test-headers", "type": "Object", "name": "Test"},
        )

        assert response.status_code == 201
        assert "Location" in response.headers
        assert "Content-Type" in response.headers
        assert "application/ld+json" in response.headers["Content-Type"]
