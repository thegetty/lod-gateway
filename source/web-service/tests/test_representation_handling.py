import pytest
from flaskapp.storage_utilities.representation import Representation
from flaskapp.errors import ResourceValidationError


@pytest.fixture
def server_root():
    return "http://example.org/base/"


@pytest.fixture
def relative_container():
    return "resource"


@pytest.fixture
def valid_jsonld_with_id():
    return {"id": "resource/123"}


@pytest.fixture
def valid_jsonld_with_at_id():
    return {"@id": "resource/456"}


@pytest.fixture
def invalid_jsonld_missing_id():
    return {"name": "No ID here"}


@pytest.fixture
def invalid_jsonld_empty_id():
    return {"id": "   "}


@pytest.fixture
def jsonld_with_context_and_base():
    return {
        "@context": {"@base": "http://example.org/base/"},
        "@id": "resource/789",
        "part_of": {"@id": "resource/789/collection"},
        "linked_to": {"@id": "resource/900/collection"},
    }


@pytest.fixture
def jsonld_with_absolute_uris():
    return {
        "@id": "http://example.org/base/resource/789",
        "part_of": {"@id": "http://example.org/base/resource/789/collection"},
    }


@pytest.fixture
def jsonld_with_context_and_absolute_id():
    return {
        "@context": {"@base": "http://example.org/base/"},
        "@id": "http://external.org/resource/789",
    }


@pytest.fixture
def jsonld_basic_container_fqdn_dctermstitle():
    return {
        "@context": {
            "@base": "http://example.org/base/",
            "ldp": "http://www.w3.org/ns/ldp#",
        },
        "@type": ["ldp:BasicContainer", "ldp:Resource"],
        "http://purl.org/dc/terms/title": "Test Container",
    }


@pytest.fixture
def jsonld_basic_container_prefix_dctermstitle():
    return {
        "@context": {
            "@base": "http://example.org/base/",
            "ldp": "http://www.w3.org/ns/ldp#",
            "dc": "http://purl.org/dc/terms/",
        },
        "@type": ["ldp:BasicContainer", "ldp:Resource"],
        "dc:title": "Test Container",
        "dc:description": "Test Description",
    }


def test_validate_jsonld_valid_id(valid_jsonld_with_id):
    assert Representation._validate_jsonld(valid_jsonld_with_id) is True


def test_validate_jsonld_valid_at_id(valid_jsonld_with_at_id):
    assert Representation._validate_jsonld(valid_jsonld_with_at_id) is True


def test_validate_jsonld_missing_id(invalid_jsonld_missing_id):
    assert (
        Representation._validate_jsonld(invalid_jsonld_missing_id) is True
    )  # valid JSON-LD

    assert Representation._has_top_level_id(invalid_jsonld_missing_id) is False


def test_validate_jsonld_empty_id(invalid_jsonld_empty_id):
    assert Representation._validate_jsonld(invalid_jsonld_empty_id) is True
    assert Representation._has_top_level_id(invalid_jsonld_empty_id) is False


def test_jsonld_setter_valid_jsonld_sets_context(
    server_root, relative_container, valid_jsonld_with_id
):
    r = Representation(server_root=server_root, relative_container=relative_container)
    r.json_ld = valid_jsonld_with_id
    assert r.json_ld["@context"]["@base"] == "http://example.org/base/"


def test_jsonld_setter_invalid_jsonld_raises(
    server_root, relative_container, invalid_jsonld_missing_id
):
    r = Representation(server_root=server_root, relative_container=relative_container)
    r.json_ld = invalid_jsonld_missing_id
    assert r.has_top_level_id() is False


def test_jsonld_with_context_and_base(
    server_root, relative_container, jsonld_with_context_and_base
):
    r = Representation(server_root=server_root, relative_container=relative_container)
    r.json_ld = jsonld_with_context_and_base
    assert r.json_ld["@context"]["@base"] == "http://example.org/base/"
    # the id should be unchanged
    assert r.json_ld["@id"] == "resource/789"


def test_jsonld_with_absolute_uris(
    server_root, relative_container, jsonld_with_absolute_uris
):
    r = Representation(server_root=server_root, relative_container=relative_container)
    r.json_ld = jsonld_with_absolute_uris
    assert r.json_ld["@context"]["@base"] == "http://example.org/base/"
    # the ids should be rebased:
    assert r.json_ld["@id"] == "resource/789"
    assert r.json_ld["part_of"]["@id"] == "resource/789/collection"


def test_jsonld_with_absolute_id_and_base_raises(
    server_root, relative_container, jsonld_with_context_and_absolute_id
):
    r = Representation(server_root=server_root, relative_container=relative_container)
    r.json_ld = jsonld_with_context_and_absolute_id
    print(r.json_ld)
    assert (
        r.json_ld["@id"] == "http://external.org/resource/789"
    )  # the external.org is not the base


def test_jsonld_with_slug_and_slug_changes(
    server_root, relative_container, jsonld_with_context_and_base
):
    r = Representation(
        server_root=server_root, relative_container=relative_container, slug="test-slug"
    )
    r.json_ld = jsonld_with_context_and_base
    print(r.json_ld)

    assert r.json_ld["@id"] == "resource/test-slug"
    assert r.json_ld["part_of"]["@id"] == "resource/test-slug/collection"


# Containers


def test_jsonld_container(
    server_root, relative_container, jsonld_basic_container_fqdn_dctermstitle
):
    r = Representation(
        server_root=server_root,
        relative_container=relative_container,
        slug="annotations",
    )
    r.json_ld = jsonld_basic_container_fqdn_dctermstitle
    print(r.json_ld)

    assert r.is_basic_container is True
    assert r.json_ld["@id"] == "resource/annotations"
    assert r.title == "Test Container"
    assert r.description == ""


def test_jsonld_container_prefixed_dcterms(
    server_root, relative_container, jsonld_basic_container_prefix_dctermstitle
):
    r = Representation(
        server_root=server_root,
        relative_container=relative_container,
        slug="annotations",
    )
    r.json_ld = jsonld_basic_container_prefix_dctermstitle
    print(r.json_ld)

    assert r.is_basic_container is True
    assert r.json_ld["@id"] == "resource/annotations"
    assert r.title == "Test Container"
    assert r.description == "Test Description"


# -- null / empty top-level id handling -----------------------------------
# A null or empty top-level id takes the same pathway as a missing id: it is
# treated as missing (not an error), the id/@id key form is retained, and the
# destination is assigned (slug or generated id for POST, destination URI for
# PUT). A null top-level id is mapped to "" before validation because pyld
# rejects a null @id as "must be a string".


class TestNullAndEmptyTopLevelId:
    @pytest.mark.parametrize("value", [None, "", "   ", 42, 3.14, ["x"]])
    def test_unusable_top_level_id_is_missing_not_crash(self, value):
        # Must return False (treated as missing), never raise.
        assert Representation._has_top_level_id({"id": value}) is False
        assert Representation._has_top_level_id({"@id": value}) is False

    def test_valid_top_level_id_returned(self):
        assert Representation._has_top_level_id({"id": "leaf"}) == "leaf"
        assert Representation._has_top_level_id({"@id": "items/1"}) == "items/1"

    def test_null_id_maps_to_empty_and_accepted(self, server_root, relative_container):
        r = Representation(
            server_root=server_root, relative_container=relative_container
        )
        # A null top-level id no longer raises; it is mapped to "".
        r.json_ld = {"id": None}
        assert r.json_ld["id"] == "resource/"
        assert "@id" not in r.json_ld
        # The raw upload is what detection runs against, and it reads as missing.
        assert r.has_original_top_level_id() is False

    def test_null_at_id_maps_to_empty_and_accepted(
        self, server_root, relative_container
    ):
        r = Representation(
            server_root=server_root, relative_container=relative_container
        )
        r.json_ld = {"@id": None}
        assert r.json_ld["@id"] == "resource/"
        assert "id" not in r.json_ld
        assert r.has_original_top_level_id() is False

    def test_null_id_with_slug_retains_key_form(self, server_root, relative_container):
        r = Representation(
            server_root=server_root, relative_container=relative_container, slug="4321"
        )
        r.json_ld = {"id": None, "referred_to_by": {"id": "note/1"}}
        assert r.json_ld["id"] == "resource/4321"
        assert "@id" not in r.json_ld
        assert r.json_ld["referred_to_by"]["id"] == "resource/4321/note/1"

    def test_null_at_id_with_slug_retains_key_form(
        self, server_root, relative_container
    ):
        r = Representation(
            server_root=server_root, relative_container=relative_container, slug="4321"
        )
        r.json_ld = {"@id": None, "referred_to_by": {"id": "note/1"}}
        assert r.json_ld["@id"] == "resource/4321"
        assert "id" not in r.json_ld

    def test_empty_id_with_slug_retains_key_form(self, server_root, relative_container):
        # "" and null take the same pathway.
        r = Representation(
            server_root=server_root, relative_container=relative_container, slug="4321"
        )
        r.json_ld = {"id": "", "referred_to_by": {"id": "note/1"}}
        assert r.json_ld["id"] == "resource/4321"
        assert "@id" not in r.json_ld

    def test_mapping_is_top_level_only(self, server_root, relative_container):
        # Only the top-level id is mapped to "". A nested id is left exactly
        # as uploaded (a nested null is not legal JSON-LD under contexts that
        # treat id as an @id alias, and pyld rejects it there; under other
        # contexts pyld drops the null object. Either way the setter does not
        # touch it).
        r = Representation(
            server_root=server_root, relative_container=relative_container
        )
        r.json_ld = {"id": "resource/123", "part_of": {"id": None}}
        assert r.json_ld["id"] == "resource/123"
        assert r.json_ld["part_of"]["id"] is None
