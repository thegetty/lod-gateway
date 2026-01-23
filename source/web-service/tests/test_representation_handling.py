import pytest
from flaskapp.storage_utilities.representation import Representation
from flaskapp.errors import ResourceValidationError


@pytest.fixture
def server_root():
    return "http://example.org/"


@pytest.fixture
def relative_container():
    return "base/"


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
    return {"@context": {"@base": "http://example.org/base/"}, "@id": "resource/789"}


@pytest.fixture
def jsonld_with_context_and_absolute_id():
    return {
        "@context": {"@base": "http://example.org/base/"},
        "@id": "http://external.org/resource/789",
    }


def test_validate_jsonld_valid_id(valid_jsonld_with_id):
    assert Representation._validate_jsonld(valid_jsonld_with_id) is True


def test_validate_jsonld_valid_at_id(valid_jsonld_with_at_id):
    assert Representation._validate_jsonld(valid_jsonld_with_at_id) is True


def test_validate_jsonld_missing_id(invalid_jsonld_missing_id):
    assert Representation._validate_jsonld(invalid_jsonld_missing_id) is False


def test_validate_jsonld_empty_id(invalid_jsonld_empty_id):
    assert Representation._validate_jsonld(invalid_jsonld_empty_id) is False


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
    with pytest.raises(ResourceValidationError):
        r.json_ld = invalid_jsonld_missing_id


def test_jsonld_with_context_and_base(
    server_root, relative_container, jsonld_with_context_and_base
):
    r = Representation(server_root=server_root, relative_container=relative_container)
    r.json_ld = jsonld_with_context_and_base
    assert r.json_ld["@context"]["@base"] == "http://example.org/base/"


def test_jsonld_with_absolute_id_and_base_raises(
    server_root, relative_container, jsonld_with_context_and_absolute_id
):
    r = Representation(server_root=server_root, relative_container=relative_container)
    with pytest.raises(ResourceValidationError):
        r.json_ld = jsonld_with_context_and_absolute_id
        print(r.json_ld)
