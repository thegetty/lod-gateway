"""
Tests for LDP POST to deleted records and PUT mechanism endpoints.

This test file covers:
1. Issue 1: POST to container paths that match deleted records
2. Issue 2: PUT mechanism for creating/updating records with full validation
"""

import json

import pytest
from uuid import uuid4

import urllib.parse as urlparse

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

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
    content_type: str = JSONLD_CT,
):
    """POST with auth, using helpers from test_ldp_api.py."""
    headers = {"Content-Type": content_type, "Authorization": "Bearer " + auth_token}
    if slug:
        headers["Slug"] = slug

    if not (
        container_url.startswith(f"/{namespace}/")
        or container_url.startswith(f"{namespace}/")
    ):
        container_url = f"/{namespace}/{container_url}"

    container_url = container_url.rstrip("/") + "/"

    response = client_ldpapi.post(container_url, data=json.dumps(body), headers=headers)

    return response


def _put_jsonld(
    namespace,
    client_ldpapi,
    auth_token,
    url: str,
    body: dict,
    slug: str = None,
    content_type: str = JSONLD_CT,
):
    """PUT with auth, using helpers from test_ldp_api.py."""
    headers = {"Content-Type": content_type, "Authorization": "Bearer " + auth_token}
    if slug:
        headers["Slug"] = slug

    if not (url.startswith(f"/{namespace}/") or url.startswith(f"{namespace}/")):
        url = f"/{namespace}/{url}"

    response = client_ldpapi.put(url, data=json.dumps(body), headers=headers)

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


def parse_link_header(h: str) -> list:
    """Parse RFC8288 Link header into a list of dicts: {"url": ..., "rel": ...}.

    (Copied from test_ldp_api.py to keep this file self-contained.)
    """
    links = []
    if not h:
        return links
    parts = [p.strip() for p in h.split(",") if p.strip()]
    for p in parts:
        if not p.startswith("<"):
            continue
        url_end = p.find(">")
        url = p[1:url_end]
        params_str = p[url_end + 1 :].strip().lstrip(";").strip()
        params = {}
        for kv in [x.strip() for x in params_str.split(";") if x.strip()]:
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k.strip()] = v.strip().strip('"')
        links.append({"url": url, **params})
    return links


def _page_base(data: dict) -> str:
    """Extract @base from a container page response @context (str, dict, or list)."""
    context = data.get("@context")
    if isinstance(context, dict):
        return context.get("@base", "") or ""
    if isinstance(context, list):
        for block in context:
            if isinstance(block, dict) and block.get("@base"):
                return block["@base"]
    return ""


def container_member_ids(namespace, client_ldpapi, container_url: str) -> set:
    """Enumerate ALL members of a container via the LDP REST API.

    GETs the container (following the 303 to page 1), collects the ldp:contains
    @ids, then follows rel="next" Link headers until exhausted, unioning members
    across pages (items are unique per page). Member identifiers are returned
    relative to the page @base, e.g. 'object/foo' (a record) or
    'object/new-sub-container/' (a container). A non-200 response (e.g. 404)
    yields an empty set.
    """
    url = container_url
    if url.startswith("http"):
        url = to_relative(url)
    if not (url.startswith(f"/{namespace}/") or url.startswith(f"{namespace}/")):
        url = f"/{namespace}/{container_url}"
    url = url.rstrip("/") + "/"

    members = set()
    pages = 0
    while url and pages < 1000:
        r = client_ldpapi.get(url, follow_redirects=True, headers={"Accept": JSONLD_CT})
        if r.status_code != 200:
            return members
        pages += 1
        data = r.get_json() or {}
        base = _page_base(data)

        for item in data.get("ldp:contains", []) or []:
            if isinstance(item, dict) and (mid := item.get("@id")):
                if base and mid.startswith(base):
                    mid = mid[len(base) :]
                members.add(mid.lstrip("/"))

        nexts = [
            link["url"]
            for link in parse_link_header(r.headers.get("Link", ""))
            if link.get("rel") == "next"
        ]
        url = to_relative(nexts[0]) if nexts else None
    return members


def is_container_member(
    namespace, client_ldpapi, container_url: str, identifier: str
) -> bool:
    """True if `identifier` (e.g. 'object/foo' or 'object/foo/') is a member
    of the container, per the LDP REST API container membership."""
    members = container_member_ids(namespace, client_ldpapi, container_url)
    return identifier.lstrip("/") in members


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

        assert is_container_member(
            namespace, client_ldpapi, "object/", f"object/{entity_id}"
        ), "Recreated record is not listed as a member of the container."

        # Verify new record was created via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, f"object/{entity_id}"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        record_data = get_response.get_json()
        assert record_data is not None
        assert record_data.get("dcterms:title") == "Fixed"

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

        # Nothing was created or overwritten: the original remains the member,
        # and its data is unchanged.
        assert is_container_member(
            namespace, client_ldpapi, "object/", f"object/{entity_id}"
        ), "Original record should remain a container member after a rejected POST."
        get_after = client_ldpapi.get(
            to_abs(namespace, f"object/{entity_id}"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_after.status_code == 200
        assert get_after.get_json().get("dcterms:title") == "Original"

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", f"object/{entity_id}"
        ), "Newly created record is not listed as a member of the container."

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", f"object/{new_entity_id}"
        ), "Recreated record is not listed as a member of the container."

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

        assert not is_container_member(
            namespace, client_ldpapi, "object/", f"object/{entity_id}"
        ), "Deleted record should no longer be a container member."

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", f"object/{entity_id}"
        ), "Recreated record is not listed as a member of the container."

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", "object/foo"
        ), "Created record is not listed as a member of the container."

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", "object/bar"
        ), "Created record is not listed as a member of the container."

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

        returned_data = response.get_json()

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", "object/bar"
        ), "Created record is not listed as a member of the container."

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", "object/baz"
        ), "Created record is not listed as a member of the container."

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", "object/foobar"
        ), "Created record is not listed as a member of the container."

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

        assert not is_container_member(
            namespace, client_ldpapi, "object/", "object/foo"
        ), "A rejected PUT must not create a record or container membership."

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

        assert not is_container_member(
            namespace, client_ldpapi, "object/", "object/foo"
        ), "A PUT with invalid JSON must not create a record or container membership."

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", f"object/{entity_id}"
        ), "Updated record must remain a member of the container."

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

        assert is_container_member(
            namespace, client_ldpapi, "object/", "object/test-headers"
        ), "Created record is not listed as a member of the container."

    def test_put_autocreates_parent_containers(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT to a deep path auto-creates the intermediate containers.

        With LDP_AUTOCREATE_CONTAINERS=True, PUT to object/foo/bar/resource
        must ensure each subpath container exists (/object/, /object/foo/,
        /object/foo/bar/), and the resource must be a member of its parent
        container. Each subpath becomes a container, and the membership chain
        links them: object/ -> object/foo/ -> object/foo/bar/ -> resource.
        Expected: 201 Created
        """
        valid_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": "object/foo/bar/resource",
            "type": "Object",
            "dcterms:title": "Deeply nested resource",
        }

        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/foo/bar/resource",
            valid_data,
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        assert response.headers["Location"].endswith("object/foo/bar/resource")

        # Each intermediate subpath exists and is an ldp:BasicContainer
        for container in ("object/foo/", "object/foo/bar/"):
            g, _ = get_graph(namespace, client_ldpapi, container)
            assert (
                URIRef(to_abs(namespace, container)),
                RDF.type,
                LDP.BasicContainer,
            ) in g, f"Auto-created container {container} is not an ldp:BasicContainer."

        # Membership chain through the auto-created containers
        assert is_container_member(
            namespace, client_ldpapi, "object/", "object/foo/"
        ), "Auto-created container object/foo/ is not a member of object/."
        assert is_container_member(
            namespace, client_ldpapi, "object/foo/", "object/foo/bar/"
        ), "Auto-created container object/foo/bar/ is not a member of object/foo/."
        assert is_container_member(
            namespace, client_ldpapi, "object/foo/bar/", "object/foo/bar/resource"
        ), "Created resource is not a member of its parent container."

        # Verify the resource via GET
        get_response = client_ldpapi.get(
            to_abs(namespace, "object/foo/bar/resource"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        assert get_response.get_json().get("dcterms:title") == "Deeply nested resource"


class TestKeyVariantAndRebaseRegression:
    """Regression tests for the key-variant preservation and slug rebase fixes.

    Covers TC-1, TC-2 (FR-1 variant preservation), TC-3 (FR-3 + D1), TC-4
    (FR-3 + D2), TC-5 (FR-4), TC-6 (FR-2 PUT id injection), TC-9 (422 fence).
    """

    # --- TC-1: POST with @-variant keys ---
    def test_post_at_variant_preserved(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-1 (FR-1): upload with @id/@type keys must come back with @id/@type
        keys only - no mirrored or plain-variant keys at the top level, in the
        201 response or the subsequent GET."""
        body = {
            "@id": "1234",
            "@type": "http://schema.org/Annotation",
            "first": {"@id": "page"},
        }
        response = _post_jsonld(
            namespace, client_ldpapi, auth_token, "object/", body, slug="1234"
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["@id"] == "object/1234"
        assert data["@type"] == "http://schema.org/Annotation"
        assert "at_type" not in data
        assert "type" not in data
        assert "at_id" not in data
        assert "id" not in data

        # GET on the Location returns the same key form
        get_r = client_ldpapi.get(
            to_abs(namespace, "object/1234"),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_r.status_code == 200
        g = get_r.get_json()
        assert "@id" in g and "@type" in g
        assert "at_type" not in g and "type" not in g
        assert "at_id" not in g and "id" not in g

    # --- TC-2: POST with plain-variant keys ---
    def test_post_plain_variant_preserved(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-2 (FR-1): upload with id/type keys must come back with id/type
        keys only - none of @id/@type/at_id/at_type at the top level.

        The inline @vocab context is only there so the plain-key document
        expands to a non-empty RDF graph (a gateway-wide requirement, see
        graph_expand); without it a plain-key document has no triples at all.
        """
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "5678",
            "type": "http://schema.org/Annotation",
            "first": {"id": "page"},
        }
        response = _post_jsonld(
            namespace, client_ldpapi, auth_token, "object/", body, slug="5678"
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == "object/5678"
        assert data["type"] == "http://schema.org/Annotation"
        assert "@id" not in data
        assert "@type" not in data
        assert "at_id" not in data
        assert "at_type" not in data

    # --- TC-3: slug rebases bare/fragment relative ids under container/slug (D1) ---
    def test_post_slug_rebases_nested_relative_ids(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-3 (FR-3 + D1): with a Slug header, bare relative ids and
        fragment-only ids in the document resolve under container/slug."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "s1",
            "type": "http://schema.org/Annotation",
            "first": {"id": "page"},
            "second": {"id": "annotation/1"},
            "frag": {"id": "#frag"},
        }
        response = _post_jsonld(
            namespace, client_ldpapi, auth_token, "object/", body, slug="s1"
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == "object/s1"
        assert data["first"]["id"] == "object/s1/page"
        assert data["second"]["id"] == "object/s1/annotation/1"
        assert data["frag"]["id"] == "object/s1#frag"

    # --- TC-4: slug moves already-container-prefixed ids under the slug (D2) ---
    def test_post_slug_moves_container_prefixed_ids(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-4 (FR-3 + D2): ids already container-prefixed are moved under
        container/slug when a Slug header is present."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "s2",
            "type": "http://schema.org/Annotation",
            "a": {"id": "object/a"},
            "b": {"id": "object/b"},
        }
        response = _post_jsonld(
            namespace, client_ldpapi, auth_token, "object/", body, slug="s2"
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["a"]["id"] == "object/s2/a"
        assert data["b"]["id"] == "object/s2/b"

    # --- TC-5: slug leaves foreign-host absolute URIs untouched (FR-4) ---
    def test_post_slug_leaves_absolute_uris_untouched(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-5 (FR-4): an id with a URI scheme on a different host is never
        rewritten, even with a Slug header."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "s3",
            "type": "http://schema.org/Annotation",
            "foreign": {"id": "http://other.host/z?x=1#f"},
        }
        response = _post_jsonld(
            namespace, client_ldpapi, auth_token, "object/", body, slug="s3"
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["foreign"]["id"] == "http://other.host/z?x=1#f"

    # --- TC-6: PUT missing-id detection and injection (FR-2) ---
    def test_put_missing_id_injects_destination_uri(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-6 case 1: PUT body with no id key at all -> destination URI
        injected under '@id' (the default id_attr). The PUT response
        re-serializes ids in absolute (prefixed) form."""
        body = {"@type": "http://schema.org/Thing"}
        response = _put_jsonld(
            namespace, client_ldpapi, auth_token, "object/newres", body
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["@id"] == to_abs(namespace, "object/newres")
        assert "id" not in data
        assert "at_id" not in data

    def test_put_empty_id_injects_destination_uri(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-6 case 2: PUT body with an empty id -> destination URI injected
        under 'id'. Pre-fix this 422'd with 'ID Mismatch' (object/ vs
        object/newres2) - the regression anchor. The inline @vocab context
        is only there so the plain-key document expands to a non-empty graph."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "",
            "type": "http://schema.org/Thing",
        }
        response = _put_jsonld(
            namespace, client_ldpapi, auth_token, "object/newres2", body
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == to_abs(namespace, "object/newres2")
        assert "@id" not in data
        assert "at_id" not in data

    def test_put_slug_empty_id_injects_destination_uri(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-6 case 3: PUT with a Slug header and empty id -> destination
        URI object/snew injected under 'id'. Per D5 the Slug header is not
        honored on PUT: here the slug happens to match the destination leaf,
        so the observable result is unchanged (the slug is simply ignored)."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "",
            "type": "http://schema.org/Thing",
        }
        response = _put_jsonld(
            namespace, client_ldpapi, auth_token, "object/snew", body, slug="snew"
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == to_abs(namespace, "object/snew")
        assert "@id" not in data
        assert "at_id" not in data

    def test_put_slug_header_ignored(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """D5: PUT ignores the Slug header - the URL path is the sole target.
        A mismatched slug must not rebase ids under the slug root and must
        not inject the slug path: destination URI injected, nested relative
        ids rebased under the destination container, not the slug root."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "",
            "type": "http://schema.org/Thing",
            "member": {"id": "nested/1"},
        }
        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/slugtest",
            body,
            slug="mismatched",
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == to_abs(namespace, "object/slugtest")
        assert "mismatched" not in data["id"]
        assert data["member"]["id"] == to_abs(namespace, "object/nested/1")
        assert "@id" not in data
        assert "at_id" not in data

    def test_put_invalid_id_injects_destination_uri(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-6 case 4: PUT body whose id is present but fails validid
        (contains a space) is treated as missing and the destination URI is
        injected under 'id'. This 201 is pinned behavior, not a defect."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "has space!",
            "type": "http://schema.org/Thing",
        }
        response = _put_jsonld(
            namespace, client_ldpapi, auth_token, "object/badid", body
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == to_abs(namespace, "object/badid")
        assert "@id" not in data
        assert "at_id" not in data

    # --- TC-9: 422 fence - docs missing both type and @type still rejected ---
    def test_post_missing_type_rejected(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-9: POST a body with no type and no @type -> 422 from
        framework-side PlainBody validation (behavior preserved by the
        raw-body switch)."""
        body = {"@id": "1"}
        response = _post_jsonld(namespace, client_ldpapi, auth_token, "object/", body)
        assert response.status_code == 422

    def test_put_missing_type_rejected(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """TC-9: PUT a body with no type and no @type -> 422 from
        framework-side PlainBody validation."""
        body = {"@id": "notype"}
        response = _put_jsonld(
            namespace, client_ldpapi, auth_token, "object/notype", body
        )
        assert response.status_code == 422


class TestJsonMimetypeAcceptance:
    """Step 14: parse_representation accepts any JSON media type (request.is_json),
    not just application/ld+json, matching the framework-side body validation.
    A request with a JSON Content-Type the framework already accepts must not
    422 at the view layer."""

    def test_post_accepts_application_json(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        body = {"@id": "cttest", "@type": "http://schema.org/Thing"}
        response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            body,
            content_type="application/json",
        )
        assert response.status_code == 201, response.text

    def test_put_accepts_application_json(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        body = {"@id": "object/cttest2", "@type": "http://schema.org/Thing"}
        response = _put_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/cttest2",
            body,
            content_type="application/json",
        )
        assert response.status_code == 201, response.text

    def test_post_accepts_json_suffix_mimetype(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        body = {"@id": "cttest3", "@type": "http://schema.org/Thing"}
        response = _post_jsonld(
            namespace,
            client_ldpapi,
            auth_token,
            "object/",
            body,
            content_type="application/geo+json",
        )
        assert response.status_code == 201, response.text


class TestPutContainer:
    """Tests for PUT container creation and update.

    PUT to a container path (ending with /) with a payload that declares itself
    as an ldp:BasicContainer should create or update that container.
    """

    def _basic_container_body(self, title, description=None):
        """Build a minimal ldp:BasicContainer JSON-LD body."""
        body = {
            "@context": {
                "ldp": "http://www.w3.org/ns/ldp#",
                "dcterms": str(DCTERMS),
            },
            "@type": "ldp:BasicContainer",
            "dcterms:title": title,
        }
        if description:
            body["dcterms:description"] = description
        return body

    def test_put_create_container(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT to a new container path should create an ldp:BasicContainer.

        Expected: 201 Created with container representation in response body.
        """
        container_id = "object/new-sub-container/"
        body = self._basic_container_body("My New Container", "A test container")
        body["@id"] = container_id.rstrip("/")

        response = _put_jsonld(namespace, client_ldpapi, auth_token, container_id, body)

        assert (
            response.status_code == 201
        ), f"Expected 201, got {response.status_code}. Response: {response.text}"

        # Response body should be a paginated container page
        data = response.get_json()
        assert data is not None
        assert "ldp:BasicContainer" in data.get("@type", [])
        assert data.get("dcterms:title") == "My New Container"

        # Verify the container is resolvable via GET
        get_response = client_ldpapi.get(
            to_relative(to_abs(namespace, container_id)),
            follow_redirects=True,
            headers={"Accept": JSONLD_CT},
        )
        assert get_response.status_code == 200
        container_data = get_response.get_json()
        assert "ldp:BasicContainer" in container_data.get("@type", [])
        assert container_data.get("dcterms:title") == "My New Container"

        assert is_container_member(
            namespace, client_ldpapi, "object/", "object/new-sub-container/"
        ), "Created container is not listed as a member of its parent container."

    def test_put_update_container(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT to an existing container should update dctitle/dcdescription.

        Expected: 200 OK with updated container representation.
        """
        # First create the container
        container_id = "object/updatable-container/"
        create_body = self._basic_container_body("Original Title", "Original desc")
        create_body["@id"] = container_id.rstrip("/")

        create_response = _put_jsonld(
            namespace, client_ldpapi, auth_token, container_id, create_body
        )
        assert create_response.status_code == 201

        # Now PUT to update the title and description
        update_body = self._basic_container_body("Updated Title", "Updated description")
        update_body["@id"] = container_id.rstrip("/")

        update_response = _put_jsonld(
            namespace, client_ldpapi, auth_token, container_id, update_body
        )

        assert (
            update_response.status_code == 200
        ), f"Expected 200, got {update_response.status_code}. Response: {update_response.text}"

        # Verify the update persisted
        get_response = client_ldpapi.get(
            to_relative(to_abs(namespace, container_id)),
            follow_redirects=True,
            headers={"Accept": JSONLD_CT},
        )
        assert get_response.status_code == 200
        container_data = get_response.get_json()
        assert container_data.get("dcterms:title") == "Updated Title"
        assert container_data.get("dcterms:description") == "Updated description"

        assert is_container_member(
            namespace, client_ldpapi, "object/", "object/updatable-container/"
        ), "Updated container must remain a member of its parent container."

    def test_put_fail_container_record_exists(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """PUT a container at a path where a Resource record exists should fail.

        Expected: 409 Conflict.
        """
        # First create a normal Resource record at the path
        record_id = "object/conflict-path"
        record_data = {
            "@context": [{"dcterms": str(DCTERMS), "type": "@type"}],
            "@id": record_id,
            "type": "Object",
            "dcterms:title": "I am a Resource, not a container",
        }

        post_response = _post_jsonld(
            namespace, client_ldpapi, auth_token, "object/", record_data
        )
        assert post_response.status_code == 201

        # Now try to PUT a container at the same path (with trailing slash)
        container_id = f"{record_id}/"
        container_body = self._basic_container_body("Conflict Container")
        container_body["@id"] = record_id

        response = _put_jsonld(
            namespace, client_ldpapi, auth_token, container_id, container_body
        )

        assert (
            response.status_code == 409
        ), f"Expected 409, got {response.status_code}. Response: {response.text}"

        # Verify the record is still intact
        get_response = client_ldpapi.get(
            to_abs(namespace, record_id),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert get_response.status_code == 200
        assert (
            get_response.get_json().get("dcterms:title")
            == "I am a Resource, not a container"
        )

        assert not is_container_member(
            namespace, client_ldpapi, "object/", f"{record_id}/"
        ), "A rejected container PUT must not add a container member."


class TestLocalAbsolutePaths:
    """Local absolute paths (ids starting with '/', no URI scheme) are
    host-independent references to other items in the store: the write-side
    id remapping leaves them untouched, while a local absolute path as the
    top-level id is invalid (treated as missing: a no-slug POST gets a
    generated id, a PUT gets the destination URI injected)."""

    def test_post_slug_preserves_nested_local_absolute_paths(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """User's exact example (adapted to the 'object/' fixture container):
        POST object/ with slug item1 and a nested '/absolute/path' stores the
        nested id untouched, rebasing host-relative ids under the slug root."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "aiusndiasndiandi",
            "type": "http://schema.org/Thing",
            "some_property": {"id": "/absolute/path"},
        }
        response = _post_jsonld(
            namespace, client_ldpapi, auth_token, "object/", body, slug="item1"
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == "object/item1"
        assert data["some_property"]["id"] == "/absolute/path"
        # Round-trip: the stored nested id is not rebased under object/item1
        get_response = client_ldpapi.get(
            to_abs(namespace, "object/item1"),
            follow_redirects=True,
            headers={"Accept": JSONLD_CT},
        )
        assert get_response.status_code == 200, get_response.text
        stored = get_response.get_json()["some_property"]["id"]
        assert stored.endswith("/absolute/path")
        assert stored != to_abs(namespace, "object/item1/absolute/path")

    def test_post_no_slug_top_level_absolute_path_gets_generated_id(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """A top-level local absolute path is invalid: a no-slug POST treats
        it as missing and generates an id, rather than creating the resource
        at container/absolute/path."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "type": "http://schema.org/Thing",
            "id": "/absolute/path",
        }
        response = _post_jsonld(namespace, client_ldpapi, auth_token, "object/", body)
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"].startswith("object/")
        assert data["id"] != "object/absolute/path"
        location = response.headers.get("Location", "")
        assert location == to_abs(namespace, data["id"])

    def test_put_top_level_absolute_path_injects_destination_uri(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """A top-level local absolute path is invalid: PUT treats it as
        missing and injects the destination URI (201, no 422 ID mismatch)."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "type": "http://schema.org/Thing",
            "id": "/absolute/path",
        }
        response = _put_jsonld(
            namespace, client_ldpapi, auth_token, "object/absitem", body
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == to_abs(namespace, "object/absitem")


class TestEmptyAndNullTopLevelId:
    """A null or empty top-level id takes the same pathway as a missing id:
    the destination is assigned (slug or generated id for POST, the
    destination URI for PUT) and the id/@id key form is retained."""

    def test_post_empty_id_with_slug_assigned_to_slug(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """POST object/ with Slug: 4321 and a top-level id of '': the slug
        value is assigned under the same 'id' key (not rewritten to '@id'),
        and nested relative ids rebase under container/slug."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "",
            "type": "http://schema.org/Thing",
            "member": {"id": "note/1"},
        }
        response = _post_jsonld(
            namespace, client_ldpapi, auth_token, "object/", body, slug="4321"
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == "object/4321"
        assert "@id" not in data
        assert data["member"]["id"] == "object/4321/note/1"

    def test_post_null_id_with_slug_assigned_to_slug(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """A top-level id of null (JSON null) is mapped to '' before
        validation and takes the same pathway as the empty string."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": None,
            "type": "http://schema.org/Thing",
            "member": {"id": "note/1"},
        }
        response = _post_jsonld(
            namespace, client_ldpapi, auth_token, "object/", body, slug="4321"
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == "object/4321"
        assert "@id" not in data
        assert data["member"]["id"] == "object/4321/note/1"

    def test_post_empty_id_no_slug_generated(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """A no-slug POST with an empty top-level id must not mask the miss:
        the record is created at a generated id under the container, not at
        the container's own path."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": "",
            "type": "http://schema.org/Thing",
        }
        response = _post_jsonld(namespace, client_ldpapi, auth_token, "object/", body)
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"].startswith("object/")
        assert data["id"] != "object/"
        assert "@id" not in data

    def test_post_null_id_no_slug_generated(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": None,
            "type": "http://schema.org/Thing",
        }
        response = _post_jsonld(namespace, client_ldpapi, auth_token, "object/", body)
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"].startswith("object/")
        assert data["id"] != "object/"
        assert "@id" not in data

    def test_put_null_id_injects_destination_uri(
        self, namespace, client_ldpapi, ldp_fixture_app, auth_token
    ):
        """A PUT with a top-level id of null treats it as missing and injects
        the destination URI under the same 'id' key (201, no 422)."""
        body = {
            "@context": {"@vocab": "https://schema.org/"},
            "id": None,
            "type": "http://schema.org/Thing",
            "member": {"id": "note/1"},
        }
        response = _put_jsonld(
            namespace, client_ldpapi, auth_token, "object/nonnull", body
        )
        assert response.status_code == 201, response.text
        data = response.get_json()
        assert data["id"] == to_abs(namespace, "object/nonnull")
        assert "@id" not in data
