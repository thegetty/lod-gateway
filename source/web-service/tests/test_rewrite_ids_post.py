import pytest

from flaskapp.storage_utilities.representation import prefix_rdf_ids


def _collect_ids(node, id_keys=("@id", "id"), skip_context=True):
    """
    Helper to collect all string values under id_keys across the structure,
    skipping @context if skip_context=True.
    """
    found = []

    if isinstance(node, dict):
        for k, v in node.items():
            if skip_context and k == "@context":
                continue
            if k in id_keys and isinstance(v, str):
                found.append(v)
            else:
                found.extend(
                    _collect_ids(v, id_keys=id_keys, skip_context=skip_context)
                )
    elif isinstance(node, list):
        for item in node:
            found.extend(_collect_ids(item, id_keys=id_keys, skip_context=skip_context))

    return found


def test_matches_provided_example():
    sample = {
        "@graph": [
            {"@id": "https://example.org/items/123"},  # Will shorten
            {"@id": "items/456"},
            {"@id": "#frag"},
            {"@id": "_:b1"},
            {"@id": "/absolute/path"},
            {"@id": "http://another.host/things?id=1#part"},  # left unchanged
        ],
        "@context": {"name": "http://schema.org/name"},  # left unchanged
    }

    out = prefix_rdf_ids(
        sample, base_id="https://example.org/", container_path="items/"
    )
    assert [n["@id"] for n in out["@graph"]] == [
        "items/123",
        "items/456",
        "items#frag",  # no extra slash before fragment
        "_:b1",  # blank node unchanged
        "items/absolute/path",  # single slash joining
        "http://another.host/things?id=1#part",
    ]

    # Ensure context is untouched
    assert out["@context"]["name"] == sample["@context"]["name"]


def test_does_not_traverse_or_alter_context():
    sample = {
        "@context": {
            "id": "http://schema.org/identifier",
            "@id": "http://schema.org/Thing",
            "sameAs": "https://example.org/keep/this/as/is",
            "nested": {"id": "http://example.org/also/untouched"},
        },
        "@id": "http://data.org/a/1",
        "id": "http://data.org/a/2",
    }

    out = prefix_rdf_ids(sample, base_id="http://data.org/", container_path="base")
    # IDs outside @context become relative with base
    assert out["@id"] == "base/a/1"
    assert out["id"] == "base/a/2"

    # Context remains exactly the same
    assert out["@context"] == sample["@context"]


def test_only_id_keys_are_modified_other_keys_unchanged():
    sample = {
        "@id": "http://example.org/a/1",
        "id": "http://example.org/a/2",
        "sameAs": "http://example.org/should-not-change",
        "seeAlso": ["http://example.org/also-not-change"],
        "nested": {"notId": "https://example.com/will-not-change-either"},
    }

    out = prefix_rdf_ids(sample, base_id="http://example.org/", container_path="base")
    assert out["@id"] == "base/a/1"
    assert out["id"] == "base/a/2"

    # These should remain exactly as-is
    assert out["sameAs"] == "http://example.org/should-not-change"
    assert out["seeAlso"] == ["http://example.org/also-not-change"]
    assert out["nested"]["notId"] == "https://example.com/will-not-change-either"


def test_custom_id_keys_supported():
    sample = {
        "identifier": "https://x.org/thing/1",
        "alt": {"identifier": "/absolute/path"},
        "@id": "http://x.org/should-not-be-touched-if-not-in_id_keys",
    }

    out = prefix_rdf_ids(
        sample,
        base_id="https://x.org/",
        container_path="items",
        id_keys=("identifier",),
    )
    assert out["identifier"] == "items/thing/1"
    assert out["alt"]["identifier"] == "items/absolute/path"

    # Not in id_keys → should stay unchanged
    assert out["@id"] == "http://x.org/should-not-be-touched-if-not-in_id_keys"


def test_blank_node_identifiers_unchanged():
    sample = {"@graph": [{"@id": "_:b1"}, {"@id": "_:myBlank"}]}
    out = prefix_rdf_ids(sample, "items/")

    assert [n["@id"] for n in out["@graph"]] == ["_:b1", "_:myBlank"]


@pytest.mark.parametrize(
    "container_path,frag_in,expected",
    [
        ("items/", "#frag", "items#frag"),
        ("items", "#frag", "items#frag"),  # no extra slash added
    ],
)
def test_fragments_preserved_and_joined_without_extra_slash(
    container_path, frag_in, expected
):
    sample = {"@id": frag_in}
    out = prefix_rdf_ids(sample, "urn:", container_path=container_path)
    assert out["@id"] == expected


def test_already_prefixed_ids_not_duplicated():
    sample = {
        "@graph": [
            {"@id": "items/123"},  # already good
            {
                "@id": "https://example.org/items/456"
            },  # also starts with base after stripping
            {"@id": "https://example.org/items/789"},
        ]
    }

    out = prefix_rdf_ids(sample, "https://example.org/", container_path="items/")
    assert [n["@id"] for n in out["@graph"]] == [
        "items/123",
        "items/456",
        "items/789",
    ]


@pytest.mark.parametrize(
    "container_path,value,expected",
    [
        ("items/", "relative/123", "items/relative/123"),
        ("items/", "/absolute/path", "items/absolute/path"),
        ("items", "/absolute/path", "items/absolute/path"),  # no double slash
        ("items", "relative/123", "items/relative/123"),
    ],
)
def test_absolute_and_relative_paths_and_no_double_slashes(
    container_path, value, expected
):
    base_id = "urn:"
    sample = {"@id": value}
    out = prefix_rdf_ids(sample, base_id, container_path=container_path)
    assert out["@id"] == expected
    assert "://" not in out["@id"]  # relative IRI


def test_non_string_id_values_left_untouched():
    sample = {
        "@graph": [
            {"@id": 42},  # non-string
            {"@id": {"nested": "value"}},  # non-string
            {"@id": ["not", "a", "string"]},  # non-string
        ]
    }

    out = prefix_rdf_ids(sample, "items/")
    # Values should carry through unchanged
    assert out["@graph"][0]["@id"] == 42
    assert out["@graph"][1]["@id"] == {"nested": "value"}
    assert out["@graph"][2]["@id"] == ["not", "a", "string"]


def test_nested_structures_traversed_but_context_not():
    sample = {
        "@id": "http://ex.org/root",
        "children": [
            {
                "@id": "http://ex.org/c1",
                "children": [{"@id": "/c1/leaf"}, {"id": "http://ex.org/c1/leaf2"}],
            },
            {"id": "http://ex.org/c2"},
        ],
        "@context": {
            "@id": "http://schema.org/Thing",  # must remain as-is
            "inner": {"id": "http://schema.org/identifier"},  # must remain
        },
    }

    out = prefix_rdf_ids(sample, "http://ex.org/", container_path="base/")
    assert out["@id"] == "base/root"
    assert out["children"][0]["@id"] == "base/c1"
    assert out["children"][0]["children"][0]["@id"] == "base/c1/leaf"
    assert out["children"][0]["children"][1]["id"] == "base/c1/leaf2"
    assert out["children"][1]["id"] == "base/c2"

    # Context untouched
    assert out["@context"]["@id"] == sample["@context"]["@id"]
    assert out["@context"]["inner"] == sample["@context"]["inner"]


@pytest.mark.parametrize("container_path", ["items/", "items"])
def test_querystring_and_fragment_preserved(container_path):
    sample = {"@id": "https://x.org/path/to?foo=1&bar=2#frag"}
    out = prefix_rdf_ids(sample, "https://x.org/", container_path=container_path)
    assert out["@id"] == "items/path/to?foo=1&bar=2#frag"


def test_default_id_keys_include_at_id_and_id():
    sample = {
        "@id": "https://foo.org/a",
        "id": "https://foo.org/b",
        "identifier": "https://foo.org/c",  # not default key → unchanged
    }
    out = prefix_rdf_ids(sample, "https://foo.org/", container_path="base/")

    assert out["@id"] == "base/a"
    assert out["id"] == "base/b"
    assert out["identifier"] == "https://foo.org/c"


def test_ids_become_relative_iris_no_scheme_no_host_after_rewrite():
    sample = {
        "@graph": [
            {"@id": "https://host/a/b"},
            {"@id": "https://host/a/b?x=1#frag"},
        ]
    }
    out = prefix_rdf_ids(sample, "https://host/", container_path="base/")

    for n in out["@graph"]:
        val = n["@id"]
        assert "://" not in val  # relative IRIs only
        assert not val.startswith("//")  # not protocol-relative
        assert val.startswith("base/")


def test_already_prefixed_when_base_has_no_trailing_slash():
    sample = {"@id": "items/999"}
    out = prefix_rdf_ids(sample, "urn:", container_path="items")
    # Should not duplicate "items"
    assert out["@id"] == "items/999"


def test_handles_ids_that_are_just_fragment_or_empty_path():
    sample = {
        "@graph": [
            {"@id": "#only-fragment"},
            {"@id": ""},  # empty string should be treated as path-like (no scheme/host)
        ]
    }
    out = prefix_rdf_ids(sample, "urn:", container_path="items/")
    assert out["@graph"][0]["@id"] == "items#only-fragment"
    # For empty string, joining should yield base without adding extra slash at end.
    # Expected behavior: "items/" + "" → "items/" or "items" depending on implementation choice.
    # We assert it starts with "items" and contains no scheme/host.
    assert out["@graph"][1]["@id"].startswith("items")
    assert "://" not in out["@graph"][1]["@id"]


def test_id_keys_inside_context_are_not_touched_even_if_present():
    sample = {
        "@context": {
            "identifier": "http://schema.org/identifier",
            "@id": "http://schema.org/Thing",
            "id": "http://schema.org/id",
        },
        "identifier": "http://example.org/will-remain-if-not-in_id_keys",
        "@id": "http://example.org/a",
    }
    out = prefix_rdf_ids(sample, "http://example.org/", container_path="base/")
    # @id outside context should be modified
    assert out["@id"] == "base/a"
    # Context is untouched
    assert out["@context"] == sample["@context"]


##### Slug handling


def test_matches_provided_example_slug():
    sample = {
        "@graph": [
            {"@id": "https://example.org/items/780"},  # Will shorten
            {"@id": "items/780/anno/456"},
            {"@id": "#frag"},  # not actually in the 'items' graph => no slug
            {"@id": "_:b1"},
            {"@id": "items/780/absolute/path"},
            {"@id": "http://another.host/things?id=1#part"},  # left unchanged
        ],
        "@id": "items/780",
        "@context": {"name": "http://schema.org/name"},  # left unchanged, no base
    }

    # resource being POSTed to /items container, with suggested slug of 'slug-id':
    out = prefix_rdf_ids(
        sample,
        base_id="https://example.org/",
        container_path="items/",
        slug="slug-id",
        id_keys=["@id"],
    )
    assert [n["@id"] for n in out["@graph"]] == [
        "items/slug-id",
        "items/slug-id/anno/456",
        "items#frag",  # no extra slash before fragment
        "_:b1",  # blank node unchanged
        "items/slug-id/absolute/path",  # single slash joining
        "http://another.host/things?id=1#part",
    ]

    assert out["@id"] == "items/slug-id"

    # Ensure context is untouched
    assert out["@context"]["name"] == sample["@context"]["name"]
