"""
Tests for LDP POST to deleted records and PUT mechanism endpoints.

This test file covers:
1. Issue 1: POST to container paths that match deleted records
2. Issue 2: PUT mechanism for creating/updating records with full validation
"""

import pytest
from uuid import uuid4

import urllib.parse as urlparse

from rdflib import Graph, Namespace, URIRef

# LDP & common namespaces
LDP = Namespace("http://www.w3.org/ns/ldp#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

BASE_URL = "http://localhost:5100/"
JSONLD_CT = "application/ld+json"


def delete_resource(namespace, client_ldpapi, auth_token, url: str):
    """DELETE with auth."""
    if not (url.startswith(f"/{namespace}/") or url.startswith(f"{namespace}/")):
        url = f"/{namespace}/{url}"

    # delete resources, not containers here
    url = url.rstrip("/")

    response = client_ldpapi.delete(
        url,
        headers={"Authorization": "Bearer " + auth_token},
    )
    print(response.text, response.headers, response.status_code)
    assert response.status_code == 200
    return response


def create_basic_text_annotation(target, text_content, mimeformat="text/plain"):
    return {
        "@context": "https://www.w3.org/ns/anno.jsonld",
        "type": "Annotation",
        "body": {
            "type": "TextualBody",
            "value": text_content,
            "format": mimeformat,
        },
        "target": target,
    }


def to_abs(namespace, url: str) -> str:
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
    headers = {"Content-Type": JSONLD_CT, "Authorization": "Bearer " + auth_token}

    if not (url.startswith(f"/{namespace}/") or url.startswith(f"{namespace}/")):
        url = f"/{namespace}/{url}"

    response = client_ldpapi.put(url, json=body, headers=headers)

    return response


def get_graph(namespace, client_ldpapi, url: str) -> Graph:
    """GET URL with Accept: application/ld+json and parse into RDFLib graph."""
    # Make relative if necessary
    if url.startswith("http"):
        url = to_relative(url)

    # add namespace if not present
    if not (url.startswith(f"/{namespace}/") or url.startswith(f"{namespace}/")):
        url = f"/{namespace}/{url}"

    r = client_ldpapi.get(url, follow_redirects=True, headers={"Accept": JSONLD_CT})
    assert r.status_code == 200
    assert JSONLD_CT in r.headers.get(
        "Content-Type", ""
    ), f"Expected Content-Type {JSONLD_CT}, got {r.headers.get('Content-Type')}"
    g = Graph()
    g.parse(data=r.text, format="json-ld")
    return g, r  # return response for header checks, too


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
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": entity_id,
            "type": "Object",
            "dcterms:title": "Original",
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

        # Check resource is part of graph:
        created_res = post_response.headers["Location"]
        created_ref = URIRef(created_res)
        url = to_abs(namespace, "object/")
        c_subj = URIRef(url)
        g_after_post, _ = get_graph(namespace, client_ldpapi, "object/")

        assert (
            c_subj,
            LDP.contains,
            created_ref,
        ) in g_after_post, (
            "BasicContainer did not add ldp:contains for the newly created resource."
        )

        # Delete the record using the DELETE endpoint
        delete_response = delete_resource(
            namespace, client_ldpapi, auth_token, f"object/{entity_id}"
        )
        assert delete_response.status_code == 200

        g_after_delete, _ = get_graph(namespace, client_ldpapi, "object/")

        assert (
            c_subj,
            LDP.contains,
            created_ref,
        ) not in g_after_delete, (
            "BasicContainer did not remove ldp:contains for the newly deleted resource."
        )

        # POST to the same container again with new data
        new_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": entity_id,
            "type": "Object",
            "dcterms:title": "Fixed",
        }

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
        ), f"Expected 201, got {response.status_code}. Response data: {response.data}"
        assert "Location" in response.headers
        assert "application/ld+json" in response.headers.get("Content-Type", "")

        g_after_second_post, _ = get_graph(namespace, client_ldpapi, "object/")

        assert (
            c_subj,
            LDP.contains,
            created_ref,
        ) in g_after_second_post, "BasicContainer did not re-add ldp:contains."

        # Verify new record was created via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, f"object/{entity_id}"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        record_data = get_response.get_json()
        assert record_data is not None
        assert record_data.get("dcterms:title") == "New Resource"

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
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": entity_id,
            "type": "Object",
            "dcterms:title": "Original",
        }

        post_response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            original_data,
        )
        assert post_response.status_code == 201

        # Verify record is active via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, f"object/{entity_id}"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        record_data = get_response.get_json()
        assert record_data.get("dcterms:title") == "Original"

        # POST to the same container again with same ID (should fail with 409)
        new_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": entity_id,
            "type": "Object",
            "dcterms:title": "Duplicate",
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
        new_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": entity_id,
            "type": "Object",
            "dcterms:title": "Brand New Resource",
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

        # Verify record was created via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, f"object/{entity_id}"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        record_data = get_response.get_json()
        assert record_data.get("dcterms:title") == "Brand New Resource"

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
                "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
                "@id": eid,
                "type": "Object",
                "dcterms:title": "One of many",
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
            delete_response = delete_resource(
                namespace, client_ldpapi, auth_token, f"object/{eid}"
            )
            assert delete_response.status_code == 200

        # POST to the same container with a new ID
        new_entity_id = str(uuid4())
        new_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": new_entity_id,
            "type": "Object",
            "dcterms:title": "Entirely new data",
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
            follow_redirects=True,
        )
        assert container_response.status_code == 200
        container_data = container_response.get_json()
        assert "totalItems" in container_data
        assert container_data["totalItems"] > 0

    def test_post_to_deleted_record_preserves_activity_stream(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """Test that activity stream is updated when POST to container.

        Should create a new Activity for the new resource.
        """
        # Create a record via POST
        entity_id = str(uuid4())
        original_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": entity_id,
            "type": "Object",
            "dcterms:title": "post to deleted record",
        }

        post_response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            original_data,
        )
        assert post_response.status_code == 201

        # Get activity stream count after first POST (404 means totalItems == 0)
        activity_before = client_ldpapi.get(
            to_abs(namespace, f"object/{entity_id}/activity-stream"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        if activity_before.status_code == 200:
            count_before = activity_before.get_json().get("totalItems", 0)
        else:
            count_before = 0

        # Delete the record
        delete_response = delete_resource(
            namespace, client_ldpapi, auth_token, f"object/{entity_id}"
        )
        assert delete_response.status_code == 200

        # POST again to the same container
        new_data = {
            "@id": entity_id,
            "type": "Object",
            "dcterms:title": "New Resource",
        }

        response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            new_data,
        )

        assert response.status_code == 201

        # Verify activity stream grew (new activity entries created)
        activity_after = client_ldpapi.get(
            to_abs(namespace, f"object/{entity_id}/activity-stream"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert activity_after.status_code == 200
        count_after = activity_after.get_json().get("totalItems", 0)
        assert count_after > count_before


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
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "id": "object/foo",
            "type": "Object",
            "dcterms:title": "Resource with correct id",
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

        # Verify record was created via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, "object/foo"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        assert (
            get_response.get_json().get("dcterms:title") == "Resource with correct id"
        )

    def test_put_with_correct_at_id_field(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT /ns/object/bar with '@id': 'object/bar' at top level.

        The '@id' field must match the destination URI.
        Expected: 201 Created
        """
        valid_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": "object/bar",
            "type": "Object",
            "dcterms:title": "Resource with correct @id",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/bar",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        # Verify record was created via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, "object/bar"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        assert (
            get_response.get_json().get("dcterms:title") == "Resource with correct @id"
        )

    def test_put_with_remappable_relative_id(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT /ns/object/bar with 'id': 'bar' at top level.

        The relative 'id' should be remapped to match the destination URI.
        Expected: 201 Created
        """

        valid_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "type": "Object",
            "dcterms:title": "Resource with remappable relative id",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/bar",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        returned_data = response.json()

        assert (
            returned_data.get("dcterms:title") == "Resource with remappable relative id"
        )
        assert "@id" in returned_data

        # Verify record was created with correct entity_id via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, "object/bar"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        assert (
            get_response.get_json().get("dcterms:title")
            == "Resource with remappable relative id"
        )

    def test_put_with_remappable_relative_at_id(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT /ns/object/baz with '@id': 'baz' at top level.

        The relative '@id' should be remapped to match the destination URI.
        Expected: 201 Created
        """
        valid_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": "baz",
            "type": "Object",
            "dcterms:title": "Resource with remappable relative id",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/baz",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        # Verify record was created with correct entity_id via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, "object/baz"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        assert (
            get_response.get_json().get("dcterms:title")
            == "Resource with remappable relative id"
        )

    def test_put_without_id_injects_destination_uri(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT /ns/object/foobar without top-level 'id' or '@id'.

        The destination URI should be injected as '@id': 'foobar'.
        Expected: 201 Created
        """
        valid_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "type": "Object",
            "dcterms:title": "Resource without id",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/foobar",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        # Verify record was created with correct entity_id via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, "object/foobar"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        record_data = get_response.get_json()
        assert record_data.get("dcterms:title") == "Resource without id"
        # Verify the injected @id
        assert "@id" in record_data or "id" in record_data

    def test_put_with_mismatched_id_returns_error(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT with ID that doesn't match destination URI should return error.

        Expected: 422
        """
        data_with_wrong_id = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "type": "Object",
            "@id": "wrong/entity/id",
            "dcterms:title": "Test",
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
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": entity_id,
            "type": "Object",
            "dcterms:title": "Original Name",
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
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": entity_id,
            "type": "Object",
            "dcterms:title": "UPDATED Name",
        }

        put_response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            f"object/{entity_id}",
            updated_data,
        )

        assert put_response.status_code == 200

        # Verify update via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, f"object/{entity_id}"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        assert get_response.get_json().get("dcterms:title") == "UPDATED Name"

    def test_put_returns_correct_headers(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT should return correct HTTP headers.

        Expected: Location, Content-Type headers
        """

        headers_test_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": "object/test-headers",
            "type": "Object",
            "dcterms:title": "Test",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/test-headers",
            headers_test_data,
        )

        assert response.status_code == 201
        assert "Location" in response.headers
        assert "Content-Type" in response.headers
        assert "application/ld+json" in response.headers["Content-Type"]
