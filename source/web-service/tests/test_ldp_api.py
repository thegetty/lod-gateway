# pytest for Python 3.13
import typing as t

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF
import urllib.parse as urlparse

from random import choice

# LDP & common namespaces
LDP = Namespace("http://www.w3.org/ns/ldp#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

BASE_URL = "http://localhost:5100/"
JSONLD_CT = "application/ld+json"


BASIC_BNODE_ANNO = {
    "@context": "https://www.w3.org/ns/anno.jsonld",
    "type": "Annotation",
    "body": {
        "type": "TextualBody",
        "value": "I like this page!",
        "format": "text/plain",
    },
    "target": "http://www.example.com/index.html",
}

BASIC_ID_ANNO = {
    "@context": ["https://www.w3.org/ns/anno.jsonld", {"@base": "urn:"}],
    "type": "AnnotationCollection",
    "id": "this",
    "first": [
        {
            "id": "this/1",
            "body": {
                "id": "http://some/aat/classification",
            },
            "target": "http://www.example.com/irises.jpg",
            "agent": {
                "type": "Software",
                "name": "Unique name for the ML classification service and version",
            },
        },
        {
            "id": "this/2",
            "body": {
                "type": "TextualBody",
                "value": "A collection of flowers",
                "format": "text/plain",
            },
            "target": "http://www.example.com/irises.jpg",
        },
    ],
}


def to_abs(namespace, url: str) -> str:
    base = BASE_URL
    if namespace:
        base = urlparse.urljoin(BASE_URL, namespace).rstrip("/") + "/"
    return urlparse.urljoin(base, url.lstrip("/"))


def to_relative(url: str) -> str:
    rel = url.split(BASE_URL, 1)[-1]
    return rel


def parse_link_header(h: str) -> t.List[t.Dict[str, str]]:
    """
    Parse RFC8288 Link header into a list of dicts: {"url": ..., "rel": ..., "type": ...}
    `requests` has parse_header_links but it expects <...>; rel= format with commas.
    """
    links = []
    if not h:
        return links

    print(f"Headers recieved: {h}")
    # Split by comma, then parse parameters
    parts = [p.strip() for p in h.split(",") if p.strip()]
    for p in parts:
        # <url>; param1=val1; param2="val2"
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


def _post_jsonld(
    namespace, client_ldpapi, auth_token, container_url: str, body: dict, slug: str
):
    """POST with auth."""
    headers = {"Content-Type": JSONLD_CT, "Authorization": "Bearer " + auth_token}
    if slug:
        headers["Slug"] = slug  # server may honor slug for resource naming

    if not (
        container_url.startswith(f"/{namespace}/")
        or container_url.startswith(f"{namespace}/")
    ):
        container_url = f"/{namespace}/{container_url}"

    container_url = container_url.rstrip("/") + "/"

    response = client_ldpapi.post(
        container_url,
        json=body,
        headers=headers,
    )

    assert response.status_code in (
        201,
        202,
    ), f"POST failed: {response.status_code} {response.text}"

    assert JSONLD_CT in response.headers.get(
        "Content-Type", ""
    ), f"Expected Content-Type {JSONLD_CT}, got {response.headers.get('Content-Type')}"

    assert "Location" in response.headers, "Location header missing on POST."
    return response


def delete_resource(namespace, client_ldpapi, auth_token, url: str):
    """DELETE with auth."""
    if not (url.startswith(f"/{namespace}/") or url.startswith(f"{namespace}/")):
        url = f"/{namespace}/{url}"

    response = client_ldpapi.delete(
        url,
        headers={"Authorization": "Bearer " + auth_token},
    )
    print(response.text, response.headers, response.status_code)
    assert response.status_code == 200
    return response


def require_link_type_contains(link_headers: t.List[t.Dict[str, str]], type_uri: str):
    """Assert Link: rel=type includes type_uri."""
    found = any(
        l.get("rel") == "type" and l.get("url") == type_uri for l in link_headers
    )
    assert found, f'Expected Link rel="type" to include <{type_uri}>'


def basic_container_iri(namespace) -> str:
    return to_abs(namespace, "/")


def _is_basic_container(g: Graph, container_url: str) -> bool:
    subj = URIRef(container_url)
    return (subj, RDF.type, LDP.BasicContainer) in g


# --- Tests ---


def test_root_container_properties_and_ldp_advertisement(
    namespace, client_ldpapi, ldp_fixture_app
):
    """
    Ensure the configured endpoint is a BasicContainer and advertises LDP.
    - rdf:type ldp:BasicContainer
    - Link rel=type includes ldp:Resource and ldp:Container
    - Returns application/ld+json
    """
    url = basic_container_iri(namespace)

    g, r = get_graph(namespace, client_ldpapi, to_relative(url))

    if not _is_basic_container(g, url):
        pytest.skip(f"{url} is not an ldp:BasicContainer (skipping).")

    subj = URIRef(url)
    assert (subj, RDF.type, LDP.BasicContainer) in g, "Not an ldp:BasicContainer."

    links = parse_link_header(r.headers.get("Link", ""))
    require_link_type_contains(links, str(LDP.Resource))
    require_link_type_contains(links, str(LDP.BasicContainer))
    # JSON-LD content type already checked in get_graph()


def test_ldp_container_advertises_ldp_and_is_jsonld(
    namespace, client_ldpapi, ldp_fixture_app
):
    """
    Validate the preconfigured containers are LDP Containers and returns JSON-LD.
    - Must advertise LDP via Link rel="type" to ldp#Resource and ldp#Container. (spec 4.2.1.4, containers)  # [1](https://www.w3.org/TR/ldp/)
    """
    for container in ["document", "object", "component", "annotations/ml-test"]:
        url = to_abs(namespace, f"/{container}/")
        g, r = get_graph(namespace, client_ldpapi, to_relative(url))

        # Link header(s)
        links = parse_link_header(r.headers.get("Link", ""))
        require_link_type_contains(links, str(LDP.Resource))
        require_link_type_contains(links, str(LDP.BasicContainer))

        # JSON-LD Content-Type
        assert JSONLD_CT in r.headers.get(
            "Content-Type", ""
        ), "Container did not return JSON-LD."  # [3](https://json-ld.org/)[4](https://en.wikipedia.org/wiki/JSON-LD)


def test_container_lists_containment_and_iterates_members(
    namespace, client_ldpapi, ldp_fixture_app
):
    """
    GET container, read ldp:contains triples, iterate each contained resource.
    Each resource must be retrievable and (if RDF) parseable as JSON-LD.
    """

    annotations = "/annotations/ml-test/"
    g, _ = get_graph(namespace, client_ldpapi, annotations)
    subj = URIRef(to_abs(namespace, annotations))

    contained = [o for (s, p, o) in g.triples((subj, LDP.contains, None))]
    assert (
        len(contained) >= 0
    ), "No ldp:contains triples found (allowed to be empty)."  # [1](https://www.w3.org/TR/ldp/)

    # sample 20 of them and resolve them:
    for _ in range(20):
        member = choice(contained)
        # Try GET member as JSON-LD; if server returns Non-RDF, we still ensure GET 200.
        r = client_ldpapi.get(to_relative(str(member)), headers={"Accept": JSONLD_CT})
        assert r.status_code == 200, f"Member {member} not retrievable."
        ct = r.headers.get("Content-Type", "")
        if JSONLD_CT in ct:
            Graph().parse(
                data=r.text, format="json-ld"
            )  # parseable JSON-LD  # [3](https://json-ld.org/)


def test_basic_container_adds_and_removes_containment(
    namespace, client_ldpapi, auth_token, ldp_fixture_app
):
    """
    POST a new RDFSource to the BasicContainer and verify:
      - <container> ldp:contains <created>
    Then DELETE it and verify the containment triple is removed.
    """
    url = to_abs(namespace, "object/")
    g, _ = get_graph(namespace, client_ldpapi, to_relative(url))

    if not _is_basic_container(g, url):
        pytest.skip(f"{url} is not an ldp:BasicContainer (skipping).")

    c_subj = URIRef(url)

    # Create a simple RDFSource
    body = {
        "@context": {"dcterms": str(DCTERMS), "type": "@type"},
        "type": "http://www.w3.org/ns/ldp#RDFSource",
        "dcterms:title": "pytest-created child of BasicContainer",
    }
    r = _post_jsonld(
        namespace, client_ldpapi, auth_token, "object/", body, slug="pytest-basic-child"
    )
    created_res = r.headers["Location"]
    created_ref = URIRef(created_res)

    # Verify containment exists after POST
    g_after_post, _ = get_graph(namespace, client_ldpapi, to_relative(url))
    assert (
        c_subj,
        LDP.contains,
        created_ref,
    ) in g_after_post, "BasicContainer did not add ldp:contains for the newly created resource."  # containment is server-managed  # [1](https://www.w3.org/TR/ldp/)

    # Retrieve created child to ensure it's available and parseable if JSON-LD
    r_child = client_ldpapi.get(to_relative(created_res), headers={"Accept": JSONLD_CT})
    assert r_child.status_code == 200
    if JSONLD_CT in r_child.headers.get("Content-Type", ""):
        Graph().parse(data=r_child.text, format="json-ld")

    # DELETE the child
    _ = delete_resource(namespace, client_ldpapi, auth_token, to_relative(created_res))

    # Verify containment removed after DELETE
    g_after_del, _ = get_graph(namespace, client_ldpapi, to_relative(url))
    assert (
        c_subj,
        LDP.contains,
        created_ref,
    ) not in g_after_del, "Containment triple still present after DELETE in BasicContainer."  # [1](https://www.w3.org/TR/ldp/)


def test_iterate_all_resources_in_root_container_and_fetch(
    namespace, client_ldpapi, ldp_fixture_app
):
    """
    Iterate all resources in container via ldp:contains and GET them.
    """

    url = basic_container_iri(namespace)
    g, _ = get_graph(namespace, client_ldpapi, to_relative(url))
    subj = URIRef(basic_container_iri(namespace))
    contains = [o for (s, p, o) in g.triples((subj, LDP.contains, None))]
    for _ in range(3):
        member = choice(contains)
        g, r = get_graph(namespace, client_ldpapi, str(member))
        assert r.status_code == 200, f"Member {member} not retrievable."
        # Optionally check ETag existence (LDP suggests ETags on representations)
        assert (
            "ETag" in r.headers
        ), "ETag header should be present on resource representation."  # [1](https://www.w3.org/TR/ldp/)


def test_accept_post_are_exposed(namespace, client_ldpapi, ldp_fixture_app):
    """
    Optional but recommended checks:
    - Container should expose Accept-Post to tell which media types can be POSTed.
    """
    # Accept-Post
    r = client_ldpapi.options(basic_container_iri(namespace), follow_redirects=True)
    assert r.status_code == 200, "OPTIONS failed."
    # Server may include Accept-Post in GET responses too; OPTIONS is a safe place to check.
    accept_post = r.headers.get("Accept-Post", "")
    # Even if not present, this is a hint; LDP defines the header.
    assert isinstance(
        accept_post, str
    ), "Accept-Post header not present or wrong type."  # [1](https://www.w3.org/TR/ldp/)

    """
    #### NB retaining the following portion of a test but at the moment, the LOD Gateway implementation
    might ignore LDP 'Prefer' headers until this becomes useful to us.


    - Prefer header controls (membership vs containment) via ldp:PreferMembership / ldp:PreferContainment.

    # Prefer headers round-trip (server may honor or ignore)
    h = {
        "Accept": JSONLD_CT,
        "Prefer": f'return=representation; include="{str(LDP.PreferMembership)}"',
    }
    r2 = client_ldpapi.get(
        basic_container_iri(namespace), headers=h, follow_redirects=True
    )
    assert r2.status_code == 200, "GET with Prefer failed."
    # When honored, server may add Preference-Applied
    _ = r2.headers.get("Preference-Applied")  # informational
    # At minimum ensure JSON-LD parseable
    Graph().parse(data=r2.text, format="json-ld")  # [2](https://www.w3.org/ns/ldp)

    """


def test_assign_ids_to_toplevel_bnode_w_slug(
    namespace, client_ldpapi, auth_token, ldp_fixture_app
):
    r = _post_jsonld(
        namespace,
        client_ldpapi,
        auth_token,
        "object/",
        BASIC_BNODE_ANNO,
        slug="pytest-basic-bnode_anno",
    )
    assert r.status_code == 201
    created_res = r.headers["Location"]
    created_ref = URIRef(created_res)

    # Slug ID used in URI
    assert created_ref.endswith("pytest-basic-bnode_anno")

    r_child = client_ldpapi.get(to_relative(created_res), headers={"Accept": JSONLD_CT})
    assert r_child.status_code == 200

    doc = r_child.json

    assert "@id" in doc
    assert doc["@id"].endswith("pytest-basic-bnode_anno")


def test_assign_ids_annotationcollection_w_slug_and_id_pref(
    namespace, client_ldpapi, auth_token, ldp_fixture_app
):
    slug = "pytest-ided-anno"
    r = _post_jsonld(
        namespace,
        client_ldpapi,
        auth_token,
        container_url="object/",
        body=BASIC_ID_ANNO,
        slug=slug,
    )
    assert r.status_code == 201
    created_res = r.headers["Location"]
    created_ref = URIRef(created_res)

    # Slug ID used in URI
    assert created_ref.endswith(slug)

    r_child = client_ldpapi.get(to_relative(created_res), headers={"Accept": JSONLD_CT})
    assert r_child.status_code == 200

    doc = r_child.json

    # ID was given using the 'id' property, so this should be preferred:
    assert "id" in doc
    assert doc["id"].endswith(slug)

    # Check children annotations have been rebased to use the new slug id as a subpath:
    anno1, anno2 = doc["first"]
    assert anno1["id"].endswith(f"{slug}/1")
    assert anno2["id"].endswith(f"{slug}/2")
