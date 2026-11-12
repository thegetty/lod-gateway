import json
import uuid
import re
import gzip

from datetime import datetime

import pytest

from flaskapp.activity_streams import (
    generate_url,
    record_item_url,
    record_stream_url,
    type_page_url,
    type_stream_url,
    url_base,
)
from flaskapp.routes import activity_entity
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
        assert response.headers["Content-Type"] == "application/activity+json"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "LOD Gateway" in response.headers["Server"]
        assert payload["type"] == "OrderedCollection"
        assert payload["summary"] == "desc"
        assert url in payload["id"]
        assert f"{url}/page/1" in payload["first"]["id"]

    def test_media_type_is_activity_json(self, client, sample_data, namespace):
        response = client.get(f"/{namespace}/activity-stream")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/activity+json"

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
        assert response.headers["Content-Type"] == "application/activity+json"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "LOD Gateway" in response.headers["Server"]
        assert payload["type"] == "OrderedCollectionPage"
        assert re.search("/activity-stream$", payload["partOf"]["id"])
        assert re.search(f"{url}$", payload["id"])

    def test_media_type_is_activity_json(self, client, sample_data, namespace):
        response = client.get(f"/{namespace}/activity-stream/page/1")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/activity+json"

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
        assert response.status_code == 422

    def test_format_datetime(self):
        dt = datetime(2019, 11, 22, 13, 2, 53)
        assert format_datetime(dt) == "2019-11-22T13:02:53"

    def test_doesnotexist_record_activity_stream(
        self, client, sample_record_with_ids, test_db, namespace
    ):
        url = f"/{namespace}/doesnotexist/activity-stream"
        response = client.get(url)
        assert response.status_code == 404


class TestItemRoute:
    def test_typical_functionality(self, client, sample_data, namespace):
        activity = sample_data["activity"]
        url = f"/{namespace}/activity-stream/{activity.uuid}"
        response = client.get(url)
        payload = json.loads(response.data)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/activity+json"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "LOD Gateway" in response.headers["Server"]
        assert payload["type"] == Event.Create.name

    def test_media_type_is_activity_json(self, client, sample_data, namespace):
        activity = sample_data["activity"]
        response = client.get(f"/{namespace}/activity-stream/{activity.uuid}")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/activity+json"

    def test_created_present_by_default(self, client, sample_data, namespace):
        activity = sample_data["activity"]
        payload = json.loads(
            client.get(f"/{namespace}/activity-stream/{activity.uuid}").data
        )
        # The legacy term keeps its existing (non-Z) rendering...
        assert payload["created"] == "2019-11-22T13:02:53"
        # ...while endTime always carries the Z designator.
        assert payload["endTime"].endswith("Z")

    def test_z_end_time(self, client, sample_data, namespace):
        activity = sample_data["activity"]
        payload = json.loads(
            client.get(f"/{namespace}/activity-stream/{activity.uuid}").data
        )
        assert payload["endTime"] == "2019-11-22T13:02:53Z"

    def test_created_omitted_when_flag_off(
        self, client, current_app, sample_data, namespace, monkeypatch
    ):
        monkeypatch.setitem(current_app.config, "ACTSTR_INCLUDE_CREATED", False)
        activity = sample_data["activity"]
        payload = json.loads(
            client.get(f"/{namespace}/activity-stream/{activity.uuid}").data
        )
        assert "created" not in payload
        assert payload["endTime"].endswith("Z")

    def test_invalid_url(self, client, sample_data, namespace):
        activity = sample_data["activity"]
        url = f"/{namespace}/activity-stream/not_a_record"
        response = client.get(url)
        assert response.status_code == 404


class TestRouteValidators:
    """ETag / Last-Modified / 304 on the global stream (AC-3..AC-5)."""

    @pytest.mark.parametrize("path", ["/activity-stream", "/activity-stream/page/1"])
    def test_etag_present_and_stable(self, client, sample_data, namespace, path):
        url = f"/{namespace}{path}"
        response = client.get(url)
        assert response.status_code == 200
        etag = response.headers.get("ETag")
        assert re.fullmatch(r'"[0-9a-f]{64}"', etag)
        assert client.get(url).headers["ETag"] == etag

    @pytest.mark.parametrize("url", ["/activity-stream", "/activity-stream/page/1"])
    def test_etag_on_root_and_page(self, client, sample_data, namespace, url):
        self.test_etag_present_and_stable(client, sample_data, namespace, url)

    @pytest.mark.parametrize("suffixed", [False, True])
    def test_if_none_match_returns_304(
        self, client, sample_data, namespace, suffixed
    ):
        url = f"/{namespace}/activity-stream"
        first = client.get(url)
        token = first.headers["ETag"]
        if suffixed:
            # The shape Flask-Compress serves for a compressed 200:
            # the strong tag with the :algorithm suffix inside the quotes.
            token = token[:-1] + ":gzip\""
        response = client.get(url, headers={"If-None-Match": token})
        assert response.status_code == 304
        assert response.data == b""
        # The client's token is echoed, suffix and all.
        assert response.headers["ETag"] == token

    @pytest.mark.parametrize("subsecond", [False, True])
    def test_if_modified_since_returns_304(
        self, client, sample_activity, test_db, namespace, subsecond
    ):
        sample_activity(1)
        # Reseal the event's stamp. With non-zero microseconds (the
        # production shape: ingest stamps datetime.now(timezone.utc)) the
        # rendered Last-Modified is the floored second, so re-sending it
        # must still 304 - the whole-second fixtures alone can never detect
        # a missing seconds-floor.
        a = Activity.query.filter(Activity.id == 1).one()
        a.datetime_created = datetime(2019, 11, 22, 13, 2, 53, 123456 if subsecond else 0)
        test_db.session.add(a)
        test_db.session.commit()

        url = f"/{namespace}/activity-stream"
        first = client.get(url)
        last_modified = first.headers["Last-Modified"]
        response = client.get(url, headers={"If-Modified-Since": last_modified})
        assert response.status_code == 304
        assert response.data == b""

    def test_gzip_304_round_trip(self, client, current_app, sample_activity, test_db, namespace):
        url = f"/{namespace}/activity-stream/page/1"
        for i in range(20):
            sample_activity(i % 5 + 1)
        first = client.get(url, headers={"Accept-Encoding": "gzip"})
        assert first.status_code == 200
        assert first.headers.get("Content-Encoding") == "gzip"
        assert first.headers["ETag"].endswith(":gzip\"")
        response = client.get(
            url, headers={"Accept-Encoding": "gzip", "If-None-Match": first.headers["ETag"]}
        )
        assert response.status_code == 304
        assert response.data == b""
        assert response.headers["ETag"] == first.headers["ETag"]

    def test_root_etag_tracks_deletion(
        self, client, sample_activity, test_db, namespace
    ):
        url = f"/{namespace}/activity-stream"
        a1 = sample_activity(1)
        a2 = sample_activity(1)
        etag_before = client.get(url).headers["ETag"]
        test_db.session.delete(a2)
        test_db.session.commit()
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers["ETag"] != etag_before


class TestDeletionDrill:
    def test_deletion_drill_global(
        self, client, current_app, sample_activity, test_db, namespace
    ):
        # Exact seed config (AC-7): page size 3, four activities pk 1-4
        # -> pages of 3 + 1.
        current_app.config["ITEMS_PER_PAGE"] = 3
        a1 = sample_activity(1)  # pk 1
        a2 = sample_activity(1)  # pk 2 (middle of page 1)
        a3 = sample_activity(2)  # pk 3
        sample_activity(2)  # pk 4

        base = f"/{namespace}/activity-stream"
        assert json.loads(client.get(base).data)["totalItems"] == 4
        etag_page1 = client.get(base + "/page/1").headers["ETag"]
        etag_page2 = client.get(base + "/page/2").headers["ETag"]

        # Delete the middle activity of page 1 (direct Activity delete).
        test_db.session.delete(a2)
        test_db.session.commit()

        page1 = client.get(base + "/page/1")
        assert page1.status_code == 200
        assert len(json.loads(page1.data)["orderedItems"]) == 2
        assert page1.headers["ETag"] != etag_page1

        page2 = client.get(base + "/page/2")
        assert page2.status_code == 200
        assert len(json.loads(page2.data)["orderedItems"]) == 1
        # The untouched page's body bytes are identical: same ETag.
        assert page2.headers["ETag"] == etag_page2

        assert json.loads(client.get(base).data)["totalItems"] == 3

        # The deleted event's single-item route 404s.
        assert client.get(base + "/" + a2.uuid).status_code == 404

    def test_page_sum_invariant(
        self, client, current_app, sample_activity, test_db, namespace
    ):
        current_app.config["ITEMS_PER_PAGE"] = 3
        base = f"/{namespace}/activity-stream"

        for i in range(10):
            sample_activity(i % 4 + 1)

        def page_sum():
            root = json.loads(client.get(base).data)
            last_page = int(root["last"]["id"].split("/")[-1])
            total = 0
            for page in range(1, last_page + 1):
                total += len(json.loads(client.get(base + f"/page/{page}").data)["orderedItems"])
            return root["totalItems"], total

        # Holds with N...
        total_items, total = page_sum()
        assert total == total_items == 10

        # ...and after deletions (a deleted activity leaves a gap in its
        # pk window; the page count derives from the highest id).
        activities = Activity.query.all()
        test_db.session.delete(activities[1])
        test_db.session.delete(activities[6])
        test_db.session.commit()

        total_items, total = page_sum()
        assert total == total_items == 8


class TestPageGzip:
    def test_gzip_encodes_body(
        self, client, current_app, sample_activity, test_db, namespace
    ):
        # A body well over Flask-Compress's COMPRESS_MIN_SIZE (500 bytes):
        # ~30 items of stream data is several kilobytes uncompressed.
        current_app.config["ITEMS_PER_PAGE"] = 100
        for i in range(30):
            sample_activity(i % 5 + 1)

        url = f"/{namespace}/activity-stream/page/1"
        plain = client.get(url)
        assert plain.headers.get("Content-Encoding") is None

        gz = client.get(url, headers={"Accept-Encoding": "gzip"})
        assert gz.status_code == 200
        assert gz.headers.get("Content-Encoding") == "gzip"
        assert gz.headers["Content-Type"] == "application/activity+json"
        assert gzip.decompress(gz.data) == plain.data


class TestActivityEntity:
    def setup_method(self):
        # Module-global type cache (populated on the first in-session GET):
        # reset so these tests are order-independent.
        activity_entity.lod_entity_types = []

    def test_url_base(self, current_app, base_url):
        assert url_base() == f"{base_url}"

    def test_url_activity(self, current_app, base_url):
        assert (
            type_stream_url("SomeEntity")
            == f"{base_url}/activity-stream/type/someentity"
        )

    def test_url_page(self, current_app, base_url):
        assert (
            type_page_url(11, "SomeEntity")
            == f"{base_url}/activity-stream/type/someentity/page/11"
        )

    def test_collection_media_type(self, client, sample_data, namespace):
        response = client.get(f"/{namespace}/activity-stream/type/object")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/activity+json"

    def test_page_media_type(self, client, sample_data, namespace):
        response = client.get(f"/{namespace}/activity-stream/type/object/page/1")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/activity+json"

    def test_created_and_z_end_time(self, client, sample_data, namespace):
        payload = json.loads(
            client.get(f"/{namespace}/activity-stream/type/object/page/1").data
        )
        item = payload["orderedItems"][0]
        assert item["created"] == "2019-11-22T13:02:53"
        assert item["endTime"] == "2019-11-22T13:02:53Z"

    def test_created_omitted_when_flag_off(
        self, client, current_app, sample_data, namespace, monkeypatch
    ):
        monkeypatch.setitem(current_app.config, "ACTSTR_INCLUDE_CREATED", False)
        payload = json.loads(
            client.get(f"/{namespace}/activity-stream/type/object/page/1").data
        )
        item = payload["orderedItems"][0]
        assert "created" not in item
        assert item["endTime"].endswith("Z")

    def test_etag_and_304(self, client, sample_data, namespace):
        url = f"/{namespace}/activity-stream/type/object"
        first = client.get(url)
        etag = first.headers.get("ETag")
        assert re.fullmatch(r'"[0-9a-f]{64}"', etag)
        response = client.get(url, headers={"If-None-Match": etag})
        assert response.status_code == 304
        assert response.data == b""
        last_modified = first.headers["Last-Modified"]
        response = client.get(url, headers={"If-Modified-Since": last_modified})
        assert response.status_code == 304


class TestActivityRecord:
    def test_url_base(self, current_app, base_url):
        assert url_base("someid") == f"{base_url}/someid"
        assert url_base() == f"{base_url}"

    def test_url_record(self, current_app, base_url):
        assert (
            record_stream_url("someentityid")
            == f"{base_url}/someentityid/activity-stream"
        )
        assert (
            record_stream_url("someentityid", 11)
            == f"{base_url}/someentityid/activity-stream/page/11"
        )

    def test_url_activity(self, current_app, base_url):
        assert (
            record_item_url("someactivityid")
            == f"{base_url}/activity-stream/someactivityid"
        )

    def test_root_media_type_etag_and_304(self, client, sample_data, namespace):
        rid = sample_data["record"].entity_id
        url = f"/{namespace}/{rid}/activity-stream"
        first = client.get(url)
        assert first.status_code == 200
        assert first.headers["Content-Type"] == "application/activity+json"
        etag = first.headers.get("ETag")
        assert re.fullmatch(r'"[0-9a-f]{64}"', etag)
        response = client.get(url, headers={"If-None-Match": etag})
        assert response.status_code == 304

    def test_page_media_type_created_and_z_end_time(
        self, client, sample_data, namespace
    ):
        rid = sample_data["record"].entity_id
        first = client.get(f"/{namespace}/{rid}/activity-stream/page/1")
        assert first.status_code == 200
        assert first.headers["Content-Type"] == "application/activity+json"
        payload = json.loads(first.data)
        item = payload["orderedItems"][0]
        assert item["created"] == "2019-11-22T13:02:53"
        assert item["endTime"] == "2019-11-22T13:02:53Z"

    def test_page_304(self, client, sample_data, namespace):
        rid = sample_data["record"].entity_id
        url = f"/{namespace}/{rid}/activity-stream/page/1"
        first = client.get(url)
        etag = first.headers.get("ETag")
        assert re.fullmatch(r'"[0-9a-f]{64}"', etag)
        response = client.get(url, headers={"If-None-Match": etag})
        assert response.status_code == 304


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
