import json

import re
import requests
from unittest.mock import patch, Mock


# Mock the SPARQL response to link queries:
mock_response = Mock()
mock_response.status_code = 200
mock_response.content = b'@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .\n@prefix crm:   <http://www.cidoc-crm.org/cidoc-crm/> .\n@prefix dc:    <http://purl.org/dc/elements/1.1/> .\n\n<http://localhost:5100/document/1>\n        dc:description  "test1" ;\n        dc:title        "test1" ;\n        dc:type         "Subject Heading - Topical" ;\n        dc:type         <https://data.getty.edu/local/thesaurus/aspace-subject-topical> .\n'
mock_response.headers = {"Content-Type": "text/turtle; charset=utf-8"}


def mock_requests(method, url, *args, **kwargs):
    if url == "http://localhost:3030/ds/sparql":
        return mock_response
    raise ValueError(f"Unexpected URL: {url}")


def parse_link_header(header_value):
    """
    Parses a Link header into a list of dictionaries with error handling.
    Each dictionary contains the URL and its associated parameters.
    Not the best parsing but it should do for tests.
    """
    links = []
    if not header_value:
        return links

    parts = header_value.split(",")

    for part in parts:
        try:
            section = part.strip().split(";")
            url = section[0].strip()
            if not url.startswith("<") or not url.endswith(">"):
                continue
            url = url[1:-1]

            params = {}
            for param in section[1:]:
                if "=" in param:
                    key, value = param.strip().split("=", 1)
                    params[key.strip()] = value.strip('"')
            links.append({"url": url, **params})
        except Exception:
            continue

    return links


def test_link_header_contains_expected_formatlinks(
    namespace, client, auth_token, test_db, linguisticobject
):
    # guarantee that there is the test dublincore profile:
    response = client.post(
        f"/{namespace}/ingest",
        data=json.dumps(linguisticobject("test document", "document/1")),
        headers={"Authorization": "Bearer " + auth_token},
    )
    assert response.status_code == 200
    assert b"document/1" in response.data

    response = client.get("/document/1")
    assert "Link" in response.headers

    parsed_links = parse_link_header(response.headers["Link"])

    expected_links = [
        {
            "url": "http://localhost:5100/museum/collection/document/1?_mediatype=application/ld%2Bjson",
            "rel": "canonical",
        },
        {
            "url": "http://localhost:5100/museum/collection/document/1?_mediatype=text/turtle&_profile=urn:getty:dublincore",
            "rel": "alternate",
        },
    ]

    for expected in expected_links:
        match_found = any(
            link["url"] == expected["url"] and link.get("rel") == expected["rel"]
            for link in parsed_links
        )
        assert match_found, f"Expected link not found: {expected}"


def test_profiled_resource_link_headers(
    namespace, client, auth_token, test_db, linguisticobject
):
    # guarantee that there is the test dublincore profile:
    response = client.post(
        f"/{namespace}/ingest",
        data=json.dumps(linguisticobject("test document 2", "document/2")),
        headers={"Authorization": "Bearer " + auth_token},
    )
    assert response.status_code == 200
    assert b"document/2" in response.data

    response = client.get(
        "/document/2?_mediatype=text/turtle&_profile=urn:getty:dublincore"
    )
    assert "Link" in response.headers

    parsed_links = parse_link_header(response.headers["Link"])

    expected_links = [
        {
            "url": "http://localhost:5100/museum/collection/document/2?_mediatype=application/ld%2Bjson",
            "rel": "canonical",
        },
        {"url": "urn:getty:dublincore", "rel": "profile"},
    ]

    for expected in expected_links:
        match_found = any(
            link["url"] == expected["url"] and link.get("rel") == expected["rel"]
            for link in parsed_links
        )
        assert match_found, f"Expected link not found: {expected}"
