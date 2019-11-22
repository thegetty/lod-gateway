import os

import pytest

from flaskapp.routes.activity import _generateURL, generateActivityStreamItem
from app.model import Activity, Record


@pytest.fixture(scope="module")
def base_url():
    return os.getenv("LOD_BASE_URL")


@pytest.fixture
def activity():
    activity = Activity()
    activity.id = 2
    activity.uuid = "8ed7abf6-b201-46f0-a2e4-3cc3a8512b1e"
    activity.event = "Update"
    activity.datetime_created = "2019-01-01 12:00:00+0000"
    activity.datetime_updated = "2019-07-04 12:00:00+0000"
    activity.datetime_published = "2019-12-25 12:00:00+0000"

    return activity


@pytest.fixture
def record():
    record = Record()
    record.id = 1
    record.uuid = "2d4ae6a5-e77c-4c67-bc14-b1c6829c0f42"
    record.entity = "Person"
    record.namespace = "ns"

    return record


@pytest.fixture
def sample_item():
    return {
        "id": "http://localhost:5100/activity-stream/8ed7abf6-b201-46f0-a2e4-3cc3a8512b1e",
        "type": "Update",
        "actor": None,
        "object": {
            "id": "http://localhost:5100/ns/person/2d4ae6a5-e77c-4c67-bc14-b1c6829c0f42",
            "type": "Person",
        },
        "created": "2019-01-01T12:00:00+00:00",
        "updated": "2019-07-04T12:00:00+00:00",
        "published": "2019-12-25T12:00:00+00:00",
    }


class TestGenerateActivityStreamItem:
    def test_typical_functionality(self, activity, record, sample_item):

        item = generateActivityStreamItem(activity, record=record)
        assert item == sample_item

    def test_namespace(self, activity, record):
        item = generateActivityStreamItem(activity, namespace="ns", record=record)
        assert "/ns/" in item["id"]
        assert "/ns/" in item["object"]["id"]

    # Date tests
    def test_creation_only(self, activity, record):
        activity.datetime_updated = None
        activity.datetime_published = None
        item = generateActivityStreamItem(activity, record=record)
        assert item["updated"] == item["created"]
        assert item["published"] == item["created"]

    def test_no_publication_date(self, activity, record):
        activity.datetime_published = None
        item = generateActivityStreamItem(activity, record=record)
        assert item["published"] == item["updated"]

    # Error state testing
    def test_invalid_date(self, activity, record):
        activity.datetime_published = "Banana"
        with pytest.raises(ValueError):
            item = generateActivityStreamItem(activity, record=record)

    def test_missing_record(self, activity, record):
        item = generateActivityStreamItem(activity, record=None)
        assert item["object"] == None

    def test_missing_activity(self, activity, record):
        item = generateActivityStreamItem(None, record=record)
        assert item == None


class TestGenerateURL:
    def test_without_params(self, base_url):
        assert _generateURL() == f"{base_url}/activity-stream"

    def test_with_namespace(self, base_url):
        url = _generateURL(namespace="namespace")
        assert url == f"{base_url}/namespace/activity-stream"

    def test_with_blank_namespace(self, base_url):
        url = _generateURL(namespace="")
        assert url == f"{base_url}/activity-stream"

    def test_with_base(self, base_url):
        url = _generateURL(base=True)
        assert url == f"{base_url}"

    def test_with_entity(self, base_url):
        url = _generateURL(entity="entity")
        assert url == f"{base_url}/activity-stream/entity"

    def test_with_base_and_namepace(self, base_url):
        url = _generateURL(base=True, namespace="namespace")
        assert url == f"{base_url}/namespace"

    def test_with_sub(self, base_url):
        url = _generateURL(sub=["a", "b"])
        assert url == f"{base_url}/activity-stream/a/b"

    def test_with_entity_and_sub(self, base_url):
        url = _generateURL(entity="entity", sub=["a", "b"])
        assert url == f"{base_url}/activity-stream/entity/a/b"

    def test_with_entity_namspace_sub(self, base_url):
        url = _generateURL(entity="entity", namespace="namespace", sub=["a", "b"])
        assert url == f"{base_url}/namespace/activity-stream/entity/a/b"

    def test_with_everything(self, base_url):
        url = _generateURL(
            base=True, entity="entity", namespace="namespace", sub=["a", "b"]
        )
        assert url == f"{base_url}/namespace/entity/a/b"

    # These ones do not function the way I would have expected.
    @pytest.mark.xfail
    def test_with_non_string_namespace(self, base_url):
        url = _generateURL(namespace=5000)
        assert url == f"{base_url}/5000/activity-stream"

    @pytest.mark.xfail
    def test_with_non_string_entity(self, base_url):
        url = _generateURL(entity=5000)
        assert url == f"{base_url}/activity-stream/5000"

    @pytest.mark.xfail
    def test_with_blank_entity(self, base_url):
        with pytest.raises(ValueError):
            url = _generateURL(entity="")
