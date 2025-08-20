import json


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

    response = client.get(f"/{namespace}/document/1")
    assert "Link" in response.headers

    parsed_links = parse_link_header(response.headers["Link"])

    # test output
    print(parsed_links)

    expected_links = [
        {
            "url": f"http://localhost:5100/{namespace}/document/1?_mediatype=application/ld%2Bjson",
            "rel": "canonical",
        },
        {
            "url": f"http://localhost:5100/{namespace}/document/1?_mediatype=text/turtle&_profile=urn:getty:dublincore",
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
        f"/{namespace}/document/2?_mediatype=text/turtle&_profile=urn:getty:dublincore"
    )

    assert "Link" in response.headers

    parsed_links = parse_link_header(response.headers["Link"])

    # test output
    print(parsed_links)

    expected_links = [
        {
            "url": f"http://localhost:5100/{namespace}/document/2?_mediatype=application/ld%2Bjson",
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
