import json
import uuid
import re

from datetime import datetime

from flaskapp.routes.activity import generate_url
from flaskapp.routes import activity_entity
from flaskapp.routes import records
from flaskapp.models.activity import Activity

from flaskapp.utilities import format_datetime, Event


class TestGenerateURL:
    def test_without_params(self, current_app, base_url):
        assert generate_url() == f"{base_url}/activity-stream"

    def test_with_base(self, current_app, base_url):
        url = generate_url(base=True)
        assert url == f"{base_url}"

    def test_with_sub(self, current_app, base_url):
        url = generate_url(sub=["a", "b"])
        assert url == f"{base_url}/activity-stream/a/b"

    def test_with_both(self, current_app, base_url):
        url = generate_url(base=True, sub=["a", "b"])
        assert url == f"{base_url}/a/b"


class TestBaseRoute:
    def test_typical_functonality(self, client, sample_data, current_app, namespace):
        current_app.config["AS_DESC"] = "desc"
        url = f"/{namespace}/activity-stream"
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

    def test_item_count(self, client, sample_activity, namespace):
        response = client.get(f"/{namespace}/activity-stream")

        assert json.loads(response.data)["totalItems"] == 0
        assert "first" not in json.loads(response.data).keys()
        assert "last" not in json.loads(response.data).keys()

        sample_activity(1)
        response = client.get(f"/{namespace}/activity-stream")
        assert json.loads(response.data)["totalItems"] == 1

    def test_pagination(self, client, current_app, sample_activity, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get(f"/{namespace}/activity-stream")
        assert "page/2" in json.loads(response.data)["last"]["id"]

    def test_pagination_with_missing_records(
        self, client, current_app, sample_activity, test_db, namespace
    ):
        current_app.config["ITEMS_PER_PAGE"] = 2
        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)

        test_db.session.delete(a1)
        test_db.session.delete(a2)
        test_db.session.commit()

        response = client.get(f"/{namespace}/activity-stream")
        assert json.loads(response.data)["totalItems"] == 1

        assert "page/2" in json.loads(response.data)["last"]["id"]


class TestPageRoute:
    def test_typical_functionality(self, client, sample_data, namespace):
        url = f"/{namespace}/activity-stream/page/1"
        response = client.get(url)
        payload = json.loads(response.data)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "LOD Gateway" in response.headers["Server"]
        assert payload["type"] == "OrderedCollectionPage"
        assert re.search("/activity-stream$", payload["partOf"]["id"])
        assert re.search(f"{url}$", payload["id"])

    def test_object_creation(self, client, sample_data, namespace):
        url = f"/{namespace}/activity-stream/page/1"
        response = client.get(url)
        payload = json.loads(response.data)
        assert len(payload["orderedItems"]) == 1
        assert sample_data["activity"].uuid in payload["orderedItems"][0]["id"]

    def test_next_one_page(self, client, current_app, sample_activity, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        response = client.get(f"/{namespace}/activity-stream/page/1")
        payload = json.loads(response.data)
        assert "next" not in payload.keys()

    def test_next_two_pages(self, client, current_app, sample_activity, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get(f"/{namespace}/activity-stream/page/1")
        payload = json.loads(response.data)
        assert "next" in payload.keys()
        assert payload["next"]["type"] == "OrderedCollectionPage"
        assert re.search("page/2$", payload["next"]["id"])

    def test_next_last_page(self, client, current_app, sample_activity, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get(f"/{namespace}/activity-stream/page/2")
        payload = json.loads(response.data)
        assert "next" not in payload.keys()

    def test_prev_one_page(self, client, current_app, sample_activity, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        response = client.get(f"/{namespace}/activity-stream/page/1")
        payload = json.loads(response.data)
        assert "prev" not in payload.keys()

    def test_prev_two_pages(self, client, current_app, sample_activity, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get(f"/{namespace}/activity-stream/page/2")
        payload = json.loads(response.data)
        assert "prev" in payload.keys()
        assert payload["prev"]["type"] == "OrderedCollectionPage"
        assert re.search("page/1$", payload["prev"]["id"])

    def test_prev_first_page(self, client, current_app, sample_activity, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2
        sample_activity(1)
        sample_activity(2)
        sample_activity(3)
        response = client.get(f"/{namespace}/activity-stream/page/1")
        payload = json.loads(response.data)
        assert "prev" not in payload.keys()

    def test_item_ordering(self, client, current_app, sample_activity, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2
        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)
        response = json.loads(client.get(f"/{namespace}/activity-stream/page/1").data)
        response2 = json.loads(client.get(f"/{namespace}/activity-stream/page/2").data)

        assert a1.record.id == 1
        assert a2.record.id == 2
        assert a3.record.id == 3

        assert len(response["orderedItems"]) == 2
        assert len(response2["orderedItems"]) == 1

        assert (
            f"{namespace}/{a1.record.entity_id}"
            in response["orderedItems"][0]["object"]["id"]
        )
        assert (
            f"{namespace}/{a2.record.entity_id}"
            in response["orderedItems"][1]["object"]["id"]
        )
        assert (
            f"{namespace}/{a3.record.entity_id}"
            in response2["orderedItems"][0]["object"]["id"]
        )

    def test_id_offset(self, client, current_app, sample_activity, test_db, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2

        a0 = sample_activity(0)
        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)

        test_db.session.delete(a0)
        test_db.session.commit()

        response = json.loads(client.get(f"/{namespace}/activity-stream/page/1").data)
        response2 = json.loads(client.get(f"/{namespace}/activity-stream/page/2").data)

        assert len(response["orderedItems"]) == 1
        assert len(response2["orderedItems"]) == 2

        assert (
            f"{namespace}/{a1.record.entity_id}"
            in response["orderedItems"][0]["object"]["id"]
        )
        assert (
            f"{namespace}/{a2.record.entity_id}"
            in response2["orderedItems"][0]["object"]["id"]
        )
        assert (
            f"{namespace}/{a3.record.entity_id}"
            in response2["orderedItems"][1]["object"]["id"]
        )

    def test_id_missing(self, client, current_app, sample_activity, test_db, namespace):
        current_app.config["ITEMS_PER_PAGE"] = 2

        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)
        a4 = sample_activity(4)
        a5 = sample_activity(5)

        test_db.session.delete(a3)
        test_db.session.commit()

        response = json.loads(client.get(f"/{namespace}/activity-stream/page/1").data)
        response2 = json.loads(client.get(f"/{namespace}/activity-stream/page/2").data)
        response3 = json.loads(client.get(f"/{namespace}/activity-stream/page/3").data)

        assert len(response["orderedItems"]) == 2
        assert len(response2["orderedItems"]) == 1
        assert len(response3["orderedItems"]) == 1

        # Not maintaining empty activity-stream pages now
        assert (
            f"{namespace}/{a1.record.entity_id}"
            in response["orderedItems"][0]["object"]["id"]
        )
        assert (
            f"{namespace}/{a2.record.entity_id}"
            in response["orderedItems"][1]["object"]["id"]
        )
        assert (
            f"{namespace}/{a4.record.entity_id}"
            in response2["orderedItems"][0]["object"]["id"]
        )
        assert (
            f"{namespace}/{a5.record.entity_id}"
            in response3["orderedItems"][0]["object"]["id"]
        )

    def test_all_page_ids_missing(
        self, client, current_app, sample_activity, test_db, namespace
    ):
        current_app.config["ITEMS_PER_PAGE"] = 2

        a1 = sample_activity(1)
        a2 = sample_activity(2)
        a3 = sample_activity(3)
        a4 = sample_activity(4)
        a5 = sample_activity(5)

        test_db.session.delete(a3)
        test_db.session.delete(a4)
        test_db.session.commit()

        response = json.loads(client.get(f"/{namespace}/activity-stream/page/1").data)
        response2 = json.loads(client.get(f"/{namespace}/activity-stream/page/2").data)
        response3 = json.loads(client.get(f"/{namespace}/activity-stream/page/3").data)

        # Not maintaining empty activity-stream pages now
        assert len(response["orderedItems"]) == 2
        assert len(response2["orderedItems"]) == 0
        assert len(response3["orderedItems"]) == 1

        assert (
            f"{namespace}/{a1.record.entity_id}"
            in response["orderedItems"][0]["object"]["id"]
        )
        assert (
            f"{namespace}/{a2.record.entity_id}"
            in response["orderedItems"][1]["object"]["id"]
        )
        assert (
            f"{namespace}/{a5.record.entity_id}"
            in response3["orderedItems"][0]["object"]["id"]
        )

    def test_all_first_page_ids_missing(
        self, client, current_app, sample_activity, test_db, namespace
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

        response = json.loads(client.get(f"/{namespace}/activity-stream/page/1").data)
        response2 = json.loads(client.get(f"/{namespace}/activity-stream/page/2").data)
        response3 = json.loads(client.get(f"/{namespace}/activity-stream/page/3").data)

        # Not maintaining empty activity-stream pages now
        assert len(response["orderedItems"]) == 0
        assert len(response2["orderedItems"]) == 2
        assert len(response3["orderedItems"]) == 1

        assert (
            f"{namespace}/{a3.record.entity_id}"
            in response2["orderedItems"][0]["object"]["id"]
        )
        assert (
            f"{namespace}/{a4.record.entity_id}"
            in response2["orderedItems"][1]["object"]["id"]
        )
        assert (
            f"{namespace}/{a5.record.entity_id}"
            in response3["orderedItems"][0]["object"]["id"]
        )

    def test_out_of_bounds_page(self, client, sample_data, namespace):
        url = f"/{namespace}/activity-stream/page/99999"
        response = client.get(url)
        assert response.status_code == 404

    def test_no_records(self, client, test_db, namespace):
        url = f"/{namespace}/activity-stream/page/1"
        response = client.get(url)
        assert response.status_code == 404

    def test_page_zero(self, client, test_db, namespace):
        url = f"/{namespace}/activity-stream/page/0"
        response = client.get(url)
        assert response.status_code == 404

    def test_format_datetime(self):
        dt = datetime(2019, 11, 22, 13, 2, 53)
        assert format_datetime(dt) == "2019-11-22T13:02:53"


class TestItemRoute:
    def test_typical_functionality(self, client, sample_data, namespace):
        activity = sample_data["activity"]
        url = f"/{namespace}/activity-stream/{activity.uuid}"
        response = client.get(url)
        payload = json.loads(response.data)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "LOD Gateway" in response.headers["Server"]
        assert payload["type"] == Event.Create.name

    def test_invalid_url(self, client, sample_data, namespace):
        activity = sample_data["activity"]
        url = f"/{namespace}/activity-stream/not_a_record"
        response = client.get(url)
        assert response.status_code == 404


class TestActivityEntity:
    def test_url_base(self, current_app, base_url):
        assert activity_entity.url_base() == f"{base_url}"

    def test_url_activity(self, current_app, base_url):
        assert (
            activity_entity.url_activity("someentity")
            == f"{base_url}/activity-stream/type/someentity"
        )

    def test_url_page(self, current_app, base_url):
        assert (
            activity_entity.url_page(11, "someentity")
            == f"{base_url}/activity-stream/type/someentity/page/11"
        )


class TestActivityRecord:
    def test_url_base(self, current_app, base_url):
        assert records.url_base("someid") == f"{base_url}/someid"

    def test_url_base(self, current_app, base_url):
        assert records.url_base() == f"{base_url}"

    def test_url_record(self, current_app, base_url):
        assert (
            records.url_record("someentityid")
            == f"{base_url}/someentityid/activity-stream"
        )

    def test_url_record(self, current_app, base_url):
        assert (
            records.url_record("someentityid", 11)
            == f"{base_url}/someentityid/activity-stream/page/11"
        )

    def test_url_activity(self, current_app, base_url):
        assert (
            records.url_activity("someactivityid")
            == f"{base_url}/activity-stream/someactivityid"
        )

    def test_doesnotexist_record_activity_stream(self, client, namespace):
        url = f"/{namespace}/doesnotexist/activity-stream"
        response = client.get(url)
        assert response.status_code == 404


class TestTruncateActivityStream:
    def test_truncate_entity_id_keep_oldest(
        self, client, namespace, auth_token, linguisticobject, test_db
    ):
        identifier = str(uuid.uuid4())

        foo_jsonld = linguisticobject("Subject name Foo", identifier)
        bar_jsonld = linguisticobject("Subject name Bar (replaces Foo)", identifier)

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(foo_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # make new versions:
        for _ in range(2):
            response = client.post(
                f"/{namespace}/ingest",
                data=json.dumps(bar_jsonld),
                headers={"Authorization": "Bearer " + auth_token},
            )

            response = client.post(
                f"/{namespace}/ingest",
                data=json.dumps(foo_jsonld),
                headers={"Authorization": "Bearer " + auth_token},
            )

        # Truncate to the latest single event PLUS keep the oldest
        response = client.post(
            f"/{namespace}/{identifier}/activity-stream",
            data={"keep": 1, "keep_oldest_event": True},
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200

        doc = response.get_json()

        assert "number_of_events_removed" in doc
        assert doc["number_of_events_removed"] == 3

        # Now let's retrieve that activitystream again
        response = client.get(f"/{namespace}/{identifier}/activity-stream")
        assert response.status_code == 200

        doc = response.get_json()
        assert doc["type"] == "OrderedCollection"

        assert doc["totalItems"] == 2

    def test_truncate_entity_id_dont_keep_oldest(
        self, client, namespace, auth_token, linguisticobject, test_db
    ):
        identifier = str(uuid.uuid4())

        foo_jsonld = linguisticobject("Subject name Foo", identifier)
        bar_jsonld = linguisticobject("Subject name Bar (replaces Foo)", identifier)

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(foo_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # make new versions:
        for _ in range(2):
            response = client.post(
                f"/{namespace}/ingest",
                data=json.dumps(bar_jsonld),
                headers={"Authorization": "Bearer " + auth_token},
            )

            response = client.post(
                f"/{namespace}/ingest",
                data=json.dumps(foo_jsonld),
                headers={"Authorization": "Bearer " + auth_token},
            )

        # Truncate to the latest single event and DONT keep the oldest
        response = client.post(
            f"/{namespace}/{identifier}/activity-stream",
            data={"keep": 1, "keep_oldest_event": False},
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200

        doc = response.get_json()

        assert "number_of_events_removed" in doc
        assert doc["number_of_events_removed"] == 4

        # Now let's retrieve that activitystream again
        response = client.get(f"/{namespace}/{identifier}/activity-stream")
        assert response.status_code == 200

        doc = response.get_json()
        assert doc["type"] == "OrderedCollection"

        assert doc["totalItems"] == 1

    def test_default_keep_oldest_event_as_true(
        self, client, namespace, auth_token, linguisticobject, test_db
    ):
        identifier = str(uuid.uuid4())

        foo_jsonld = linguisticobject("Subject name Foo", identifier)
        bar_jsonld = linguisticobject("Subject name Bar (replaces Foo)", identifier)

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(foo_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # make new versions:
        for _ in range(2):
            response = client.post(
                f"/{namespace}/ingest",
                data=json.dumps(bar_jsonld),
                headers={"Authorization": "Bearer " + auth_token},
            )

            response = client.post(
                f"/{namespace}/ingest",
                data=json.dumps(foo_jsonld),
                headers={"Authorization": "Bearer " + auth_token},
            )

        # Truncate to the latest single event and BY DEFAULT keep the oldest
        response = client.post(
            f"/{namespace}/{identifier}/activity-stream",
            data={"keep": 1},
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200

        doc = response.get_json()

        assert "number_of_events_removed" in doc
        assert doc["number_of_events_removed"] == 3

        # Now let's retrieve that activitystream again
        response = client.get(f"/{namespace}/{identifier}/activity-stream")
        assert response.status_code == 200

        doc = response.get_json()
        assert doc["type"] == "OrderedCollection"

        assert doc["totalItems"] == 2
