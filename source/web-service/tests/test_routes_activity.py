import os
import json
import re

import pytest

from flaskapp.utilities import generate_url
from flaskapp.models.activity import Activity
from flaskapp.utilities import format_datetime
from datetime import datetime


@pytest.fixture(scope="module")
def base_url():
    return os.getenv("LOD_BASE_URL")


class TestBaseRoute:
    def test_typical_functonality(self, client, sample_data, current_app):
        current_app.config["AS_DESC"] = "desc"
        url = "/museum/collection/activity-stream"
        response = client.get(url)
        payload = json.loads(response.data)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "LOD Gateway" in response.headers["Server"]
        assert payload["type"] == "OrderedCollection"
        assert payload["summary"] == "desc"
        assert url in payload["id"]
        assert f"{url}/page/1" in payload["first"]["id"]

    def test_default_namespace(self, client, current_app, sample_data):
        current_app.config["DEFAULT_URL_NAMESPACE"] = "ns"
        response = client.get("/ns/activity-stream")
        payload = json.loads(response.data)
        assert response.status_code == 200
        assert "/ns/activity-stream" in payload["id"]
        assert "/ns/activity-stream" in payload["first"]["id"]

    def test_item_count(self, client, sample_activity):
        response = client.get(f"/ns/activity-stream")

        assert json.loads(response.data)["totalItems"] == 0
        assert "first" not in json.loads(response.data).keys()
        assert "last" not in json.loads(response.data).keys()

        sample_activity(1)
        response = client.get(f"/ns/activity-stream")
        assert json.loads(response.data)["totalItems"] == 1

    def test_pagination(self, client, current_app, sample_activity):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get(f"/ns/activity-stream")
        assert "page/2" in json.loads(response.data)["last"]["id"]

    def test_pagination_with_missing_records(
        self, client, current_app, sample_activity, test_db
    ):
        current_app.config["ITEMS_PER_PAGE"] = 2
        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)

        test_db.session.delete(a1)
        test_db.session.delete(a2)
        test_db.session.commit()

        response = client.get(f"/ns/activity-stream")
        assert json.loads(response.data)["totalItems"] == 1
        assert "page/2" in json.loads(response.data)["last"]["id"]


class TestPageRoute:
    def test_typical_functionality(self, client, sample_data):
        url = "/museum/collection/activity-stream/page/1"
        response = client.get(url)
        payload = json.loads(response.data)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "LOD Gateway" in response.headers["Server"]
        assert payload["type"] == "OrderedCollectionPage"
        assert re.search("/activity-stream$", payload["partOf"]["id"])
        assert re.search(f"{url}$", payload["id"])

    def test_object_creation(self, client, sample_data):
        url = "/museum/collection/activity-stream/page/1"
        response = client.get(url)
        payload = json.loads(response.data)
        assert len(payload["orderedItems"]) == 1
        assert sample_data["activity"].uuid in payload["orderedItems"][0]["id"]

    def test_default_namespace(self, client, current_app, sample_data):
        current_app.config["DEFAULT_URL_NAMESPACE"] = "ns"
        response = client.get("/ns/activity-stream/page/1")
        payload = json.loads(response.data)
        assert response.status_code == 200
        assert "/ns/activity-stream" in payload["id"]

    def test_next_one_page(self, client, current_app, sample_activity):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        response = client.get("/ns/activity-stream/page/1")
        payload = json.loads(response.data)
        assert "next" not in payload.keys()

    def test_next_two_pages(self, client, current_app, sample_activity):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get("/ns/activity-stream/page/1")
        payload = json.loads(response.data)
        assert "next" in payload.keys()
        assert payload["next"]["type"] == "OrderedCollectionPage"
        assert re.search("page/2$", payload["next"]["id"])

    def test_next_last_page(self, client, current_app, sample_activity):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get("/ns/activity-stream/page/2")
        payload = json.loads(response.data)
        assert "next" not in payload.keys()

    def test_prev_one_page(self, client, current_app, sample_activity):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        response = client.get("/ns/activity-stream/page/1")
        payload = json.loads(response.data)
        assert "prev" not in payload.keys()

    def test_prev_two_pages(self, client, current_app, sample_activity):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get("/ns/activity-stream/page/2")
        payload = json.loads(response.data)
        assert "prev" in payload.keys()
        assert payload["prev"]["type"] == "OrderedCollectionPage"
        assert re.search("page/1$", payload["prev"]["id"])

    def test_prev_first_page(self, client, current_app, sample_activity):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get("/ns/activity-stream/page/1")
        payload = json.loads(response.data)
        assert "prev" not in payload.keys()

    def test_item_ordering(self, client, current_app, sample_activity):
        current_app.config["ITEMS_PER_PAGE"] = 2
        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)
        response = json.loads(client.get("/ns/activity-stream/page/1").data)
        response2 = json.loads(client.get("/ns/activity-stream/page/2").data)

        assert a1.record.id == 1
        assert a2.record.id == 2
        assert a3.record.id == 3

        assert len(response["orderedItems"]) == 2
        assert len(response2["orderedItems"]) == 1

        assert a1.record.uuid in response["orderedItems"][0]["object"]["id"]
        assert a2.record.uuid in response["orderedItems"][1]["object"]["id"]
        assert a3.record.uuid in response2["orderedItems"][0]["object"]["id"]

    def test_id_offset(self, client, current_app, sample_activity, test_db):
        current_app.config["ITEMS_PER_PAGE"] = 2

        a0 = sample_activity(0)
        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)

        test_db.session.delete(a0)
        test_db.session.commit()

        response = json.loads(client.get("/ns/activity-stream/page/1").data)
        response2 = json.loads(client.get("/ns/activity-stream/page/2").data)

        assert len(response["orderedItems"]) == 1
        assert len(response2["orderedItems"]) == 2

        assert a1.record.uuid in response["orderedItems"][0]["object"]["id"]
        assert a2.record.uuid in response2["orderedItems"][0]["object"]["id"]
        assert a3.record.uuid in response2["orderedItems"][1]["object"]["id"]

    def test_id_missing(self, client, current_app, sample_activity, test_db):
        current_app.config["ITEMS_PER_PAGE"] = 2

        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)
        a4 = sample_activity(4)
        a5 = sample_activity(5)

        test_db.session.delete(a3)
        test_db.session.commit()

        response = json.loads(client.get("/ns/activity-stream/page/1").data)
        response2 = json.loads(client.get("/ns/activity-stream/page/2").data)
        response3 = json.loads(client.get("/ns/activity-stream/page/3").data)

        assert len(response["orderedItems"]) == 2
        assert len(response2["orderedItems"]) == 1
        assert len(response3["orderedItems"]) == 1

        assert a1.record.uuid in response["orderedItems"][0]["object"]["id"]
        assert a2.record.uuid in response["orderedItems"][1]["object"]["id"]
        assert a4.record.uuid in response2["orderedItems"][0]["object"]["id"]
        assert a5.record.uuid in response3["orderedItems"][0]["object"]["id"]

    def test_all_page_ids_missing(self, client, current_app, sample_activity, test_db):
        current_app.config["ITEMS_PER_PAGE"] = 2

        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)
        a4 = sample_activity(4)
        a5 = sample_activity(5)

        test_db.session.delete(a3)
        test_db.session.delete(a4)
        test_db.session.commit()

        response = json.loads(client.get("/ns/activity-stream/page/1").data)
        response2 = json.loads(client.get("/ns/activity-stream/page/2").data)
        response3 = json.loads(client.get("/ns/activity-stream/page/3").data)

        assert len(response["orderedItems"]) == 2
        assert len(response2["orderedItems"]) == 0
        assert len(response3["orderedItems"]) == 1

        assert a1.record.uuid in response["orderedItems"][0]["object"]["id"]
        assert a2.record.uuid in response["orderedItems"][1]["object"]["id"]
        assert a5.record.uuid in response3["orderedItems"][0]["object"]["id"]

    def test_all_first_page_ids_missing(
        self, client, current_app, sample_activity, test_db
    ):
        current_app.config["ITEMS_PER_PAGE"] = 2

        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)
        a4 = sample_activity(4)
        a5 = sample_activity(5)

        test_db.session.delete(a1)
        test_db.session.delete(a2)
        test_db.session.commit()

        response = json.loads(client.get("/ns/activity-stream/page/1").data)
        response2 = json.loads(client.get("/ns/activity-stream/page/2").data)
        response3 = json.loads(client.get("/ns/activity-stream/page/3").data)

        assert len(response["orderedItems"]) == 0
        assert len(response2["orderedItems"]) == 2
        assert len(response3["orderedItems"]) == 1

        assert a3.record.uuid in response2["orderedItems"][0]["object"]["id"]
        assert a4.record.uuid in response2["orderedItems"][1]["object"]["id"]
        assert a5.record.uuid in response3["orderedItems"][0]["object"]["id"]

    def test_out_of_bounds_page(self, client, sample_data):
        url = "/museum/collection/activity-stream/page/99999"
        response = client.get(url)
        assert response.status_code == 404

    def test_no_records(self, client, test_db):
        url = "/museum/collection/activity-stream/page/1"
        response = client.get(url)
        assert response.status_code == 404

    def test_page_zero(self, client, test_db):
        url = "/museum/collection/activity-stream/page/0"
        response = client.get(url)
        assert response.status_code == 404

    def test_format_datetime(self):
        dt = datetime.fromisoformat("2019-12-04T15:36:12-08:00")
        assert format_datetime(dt) == "2019-12-04T15:36:12-08:00"
        assert format_datetime(None) == None
        assert format_datetime(123) == None
        assert format_datetime("abc") == None


class TestItemRoute:
    def test_typical_functionality(self, client, sample_data):
        activity = sample_data["activity"]
        url = f"/museum/collection/activity-stream/{activity.uuid}"
        response = client.get(url)
        payload = json.loads(response.data)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "LOD Gateway" in response.headers["Server"]
        assert payload["type"] == "Create"

    def test_invalid_url(self, client, sample_data):
        activity = sample_data["activity"]
        url = f"/museum/collection/activity-stream/not_a_record"
        response = client.get(url)
        assert response.status_code == 404

    def test_default_namespace(self, client, current_app, sample_data):
        current_app.config["DEFAULT_URL_NAMESPACE"] = "ns"
        activity = sample_data["activity"]
        url = f"/ns/activity-stream/{activity.uuid}"
        response = client.get(url)
        payload = json.loads(response.data)
        assert response.status_code == 200
        assert "/ns/activity-stream" in payload["id"]


class TestGenerateURL:
    def test_without_params(self, base_url):
        assert generate_url() == f"{base_url}/activity-stream"

    def test_with_namespace(self, base_url):
        url = generate_url(namespace="namespace")
        assert url == f"{base_url}/namespace/activity-stream"

    def test_with_blank_namespace(self, base_url):
        url = generate_url(namespace="")
        assert url == f"{base_url}/activity-stream"

    def test_with_base(self, base_url):
        url = generate_url(base=True)
        assert url == f"{base_url}"

    def test_with_base_and_namepace(self, base_url):
        url = generate_url(base=True, namespace="namespace")
        assert url == f"{base_url}/namespace"

    def test_with_sub(self, base_url):
        url = generate_url(sub=["a", "b"])
        assert url == f"{base_url}/activity-stream/a/b"

    def test_with_everything(self, base_url):
        url = generate_url(base=True, namespace="namespace", sub=["a", "b"])
        assert url == f"{base_url}/namespace/a/b"

    # These ones do not function the way I would have expected.
    @pytest.mark.xfail
    def test_with_non_string_namespace(self, base_url):
        url = generate_url(namespace=5000)
        assert url == f"{base_url}/5000/activity-stream"
