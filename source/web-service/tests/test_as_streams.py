"""
Unit tests for the activity-stream utility (flaskapp.activity_streams)
and format_utc_datetime (flaskapp.utilities)
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import os

import pytest

from flaskapp import create_app
from flaskapp.activity_streams import (
    ACTIVITY_JSON,
    AS_CONTEXT,
    as_response,
    build_collection,
    build_event_item,
    build_page,
    object_url,
    record_item_url,
    record_object_url,
    record_stream_url,
    stream_item_url,
    stream_page_url,
    stream_url,
    type_item_url,
    type_object_url,
    type_page_url,
    type_stream_url,
    url_base,
)
from flaskapp.utilities import format_datetime, format_utc_datetime

# naive == UTC by project convention (ingest stamps naive UTC from aware)
NAIVE = datetime(2019, 11, 22, 13, 2, 53)
# the same instant expressed in a non-UTC offset (18:32:53+05:30 == 13:02:53Z)
AWARE_0530 = datetime(
    2019, 11, 22, 18, 32, 53, tzinfo=timezone(timedelta(hours=5, minutes=30))
)


class TestFormatUtcDatetime:
    def test_naive_is_treated_as_utc(self):
        assert format_utc_datetime(NAIVE) == "2019-11-22T13:02:53Z"

    def test_aware_is_converted_to_utc(self):
        assert format_utc_datetime(AWARE_0530) == "2019-11-22T13:02:53Z"

    def test_sub_second_precision_is_floored_to_seconds(self):
        dt = NAIVE.replace(microsecond=987654)
        assert format_utc_datetime(dt) == "2019-11-22T13:02:53Z"

    def test_aware_sub_second_is_converted_then_floored(self):
        # 18:32:53.987654+05:30 is 13:02:53.987654Z -> floors to :53Z
        dt = AWARE_0530.replace(microsecond=987654)
        assert format_utc_datetime(dt) == "2019-11-22T13:02:53Z"


class TestUrlMakers:
    def test_global_family_forms(self, current_app):
        base = current_app.config["BASE_URL"]
        ns = current_app.config["NAMESPACE"]
        assert stream_url() == f"{base}/{ns}/activity-stream"
        assert stream_page_url(2) == f"{base}/{ns}/activity-stream/page/2"
        assert stream_item_url("item-1") == f"{base}/{ns}/activity-stream/item-1"
        assert object_url("ent-1") == f"{base}/{ns}/ent-1"

    def test_type_family_forms(self, current_app):
        base = current_app.config["BASE_URL"]
        ns = current_app.config["NAMESPACE"]
        assert type_stream_url("Object") == f"{base}/{ns}/activity-stream/type/object"
        assert type_page_url(2, "Object") == (
            f"{base}/{ns}/activity-stream/type/object/page/2"
        )
        assert type_item_url("item-1") == f"{base}/{ns}/activity-stream/item-1"
        assert type_object_url("ent-1") == f"{base}/{ns}/ent-1"

    def test_record_family_forms(self, current_app):
        base = current_app.config["BASE_URL"]
        ns = current_app.config["NAMESPACE"]
        assert record_stream_url("ent-1") == f"{base}/{ns}/ent-1/activity-stream"
        assert (
            record_stream_url("ent-1", 2) == f"{base}/{ns}/ent-1/activity-stream/page/2"
        )
        assert record_item_url("item-1") == f"{base}/{ns}/activity-stream/item-1"
        assert record_object_url("ent-1") == f"{base}/{ns}/ent-1"

    def test_item_and_object_urls_coincide_when_namespace_set(self, current_app):
        assert stream_item_url("i") == type_item_url("i") == record_item_url("i")
        assert object_url("e") == type_object_url("e") == record_object_url("e")

    # Pin the documented edge semantics in a no-namespace deployment. The
    # idPrefix is derived from the environment during create_app(), so the
    # deployment is built from environment inputs rather than patched config.
    def test_join_styles_diverge_without_namespace(self, monkeypatch):
        monkeypatch.setenv("BASE_URL", "http://example.com/api")
        monkeypatch.setenv("APPLICATION_NAMESPACE", "")
        flask_app = create_app()
        flask_app.config["TESTING"] = True
        with flask_app.app_context():
            # filtered join (global family): empty parts dropped -> single slash
            assert stream_url() == "http://example.com/api/activity-stream"
            assert object_url("e") == "http://example.com/api/e"
            # raw concatenation (type / record families): trailing slash is ditched
            assert url_base() == "http://example.com/api"
            assert type_item_url("i") == "http://example.com/api/activity-stream/i"
            assert record_stream_url("e") == "http://example.com/api/e/activity-stream"
            assert record_object_url("e") == "http://example.com/api/e"


class TestBuildEventItem:
    def test_shape_and_family_ids(self, current_app):
        base = current_app.config["BASE_URL"]
        ns = current_app.config["NAMESPACE"]
        for family in ("global", "type", "record"):
            item = build_event_item(
                family, "item-1", "Create", NAIVE, "ent-1", "Object"
            )
            assert item["id"] == f"{base}/{ns}/activity-stream/item-1"
            assert item["type"] == "Create"
            assert item["object"] == {"id": f"{base}/{ns}/ent-1", "type": "Object"}

    def test_created_is_legacy_rendering_endtime_is_utc(self, current_app):
        item = build_event_item("global", "item-1", "Create", NAIVE, "ent-1", "Object")
        # legacy format_datetime: naive renders with an empty offset
        assert item["created"] == "2019-11-22T13:02:53"
        assert item["created"] == format_datetime(NAIVE)
        assert item["endTime"] == "2019-11-22T13:02:53Z"

    def test_aware_input_normalizes_endtime_keeps_legacy_created(self, current_app):
        item = build_event_item(
            "global", "item-1", "Create", AWARE_0530, "ent-1", "Object"
        )
        assert item["endTime"] == "2019-11-22T13:02:53Z"
        # the legacy rendering keeps the original offset, untouched
        assert item["created"] == "2019-11-22T18:32:53+0530"

    def test_flag_off_omits_created_endtime_remains(self, current_app, monkeypatch):
        monkeypatch.setitem(current_app.config, "ACTSTR_INCLUDE_CREATED", False)
        item = build_event_item("global", "item-1", "Create", NAIVE, "ent-1", "Object")
        assert "created" not in item
        assert item["endTime"] == "2019-11-22T13:02:53Z"

    def test_standalone_adds_top_level_context(self, current_app):
        item = build_event_item(
            "record", "item-1", "Create", NAIVE, "ent-1", "Object", standalone=True
        )
        assert item["@context"] == AS_CONTEXT

    def test_page_list_item_has_no_context(self, current_app):
        item = build_event_item("global", "item-1", "Create", NAIVE, "ent-1", "Object")
        assert "@context" not in item

    def test_unknown_family_raises(self, current_app):
        with pytest.raises(ValueError):
            build_event_item("nope", "i", "Create", NAIVE, "e", "Object")


class TestBuildCollection:
    def test_populated(self, current_app):
        doc = build_collection("collection-1", 37, 4, stream_page_url)
        assert doc["@context"] == AS_CONTEXT
        assert doc["type"] == "OrderedCollection"
        assert doc["id"] == "collection-1"
        assert doc["totalItems"] == 37
        assert doc["summary"] == current_app.config["AS_DESC"]
        assert doc["first"] == {
            "id": stream_page_url(1),
            "type": "OrderedCollectionPage",
        }
        assert doc["last"] == {
            "id": stream_page_url(4),
            "type": "OrderedCollectionPage",
        }

    def test_empty_omits_first_and_last(self, current_app):
        doc = build_collection("collection-1", 0, 0, stream_page_url)
        assert doc["totalItems"] == 0
        assert "first" not in doc
        assert "last" not in doc

    def test_custom_summary(self, current_app):
        doc = build_collection("collection-1", 5, 1, stream_page_url, summary="mine")
        assert doc["summary"] == "mine"


class TestBuildPage:
    def test_middle_page(self, current_app):
        doc = build_page(
            2, 4, "page-2", "collection-1", stream_page_url, [{"id": "item-1"}]
        )
        assert doc["@context"] == AS_CONTEXT
        assert doc["type"] == "OrderedCollectionPage"
        assert doc["id"] == "page-2"
        assert doc["partOf"] == {"id": "collection-1", "type": "OrderedCollection"}
        assert doc["next"] == {
            "id": stream_page_url(3),
            "type": "OrderedCollectionPage",
        }
        assert doc["prev"] == {
            "id": stream_page_url(1),
            "type": "OrderedCollectionPage",
        }
        assert doc["orderedItems"] == [{"id": "item-1"}]

    def test_first_page_has_no_prev(self, current_app):
        doc = build_page(1, 4, "page-1", "collection-1", stream_page_url, [])
        assert "prev" not in doc
        assert doc["next"]["id"] == stream_page_url(2)

    def test_last_page_has_no_next(self, current_app):
        doc = build_page(4, 4, "page-4", "collection-1", stream_page_url, [])
        assert "next" not in doc
        assert doc["prev"]["id"] == stream_page_url(3)


class TestEtagDeterminism:
    def _page(self, current_app):
        items = [
            build_event_item("global", f"item-{n}", "Create", NAIVE, "ent-1", "Object")
            for n in range(3)
        ]
        return build_page(2, 4, "page-2", "collection-1", stream_page_url, items), NAIVE

    def test_repeated_build_yields_identical_etag_and_body(self, current_app):
        doc, lm = self._page(current_app)
        r1 = as_response(doc, lm)
        r2 = as_response(doc, lm)
        assert r1.headers["ETag"] == r2.headers["ETag"]
        assert r1.get_data() == r2.get_data()

    def test_etag_is_the_sha256_of_the_served_bytes(self, current_app):
        doc, lm = self._page(current_app)
        r = as_response(doc, lm)
        expected = hashlib.sha256(r.get_data()).hexdigest()
        assert r.headers["ETag"] == f'"{expected}"'

    def test_content_change_rotates_etag(self, current_app):
        d1 = build_collection("c", 1, 1, stream_page_url)
        d2 = build_collection("c", 2, 1, stream_page_url)
        assert as_response(d1).headers["ETag"] != as_response(d2).headers["ETag"]

    def test_collection_and_item_documents_deterministic(self, current_app):
        coll = build_collection("c", 1, 1, stream_page_url)
        item = build_event_item("type", "item-1", "Create", NAIVE, "ent-1", "Object")
        assert as_response(coll).headers["ETag"] == as_response(coll).headers["ETag"]
        assert as_response(item).headers["ETag"] == as_response(item).headers["ETag"]


class TestETagsAndMore:
    def _collection(self, current_app):
        return build_collection("collection-1", 1, 1, stream_page_url)

    def test_star_matches_any(self, current_app):
        with current_app.test_request_context(
            "/activity-stream", headers={"If-None-Match": "*"}
        ):
            r = as_response(self._collection(current_app), NAIVE)
        assert r.status_code == 304
        assert r.headers["ETag"] == "*"
        assert r.get_data() == b""
        assert "Content-Type" not in r.headers
        assert r.headers["Last-Modified"]

    def test_if_none_match_echo(self, current_app):
        with current_app.test_request_context("/activity-stream"):
            etag = as_response(self._collection(current_app)).headers["ETag"]
        with current_app.test_request_context(
            "/activity-stream", headers={"If-None-Match": etag}
        ):
            r = as_response(self._collection(current_app), NAIVE)
        assert r.status_code == 304
        assert r.headers["ETag"] == etag
        assert "Content-Type" not in r.headers

    def test_flask_compress_suffixed_etag(self, current_app):
        # flask-compress rewrites the ETag of compressed 2xx to "<hash>:<algo>";
        # the tag as sent arrives unquoted from werkzeug with the suffix intact
        with current_app.test_request_context("/activity-stream"):
            etag = as_response(self._collection(current_app)).headers["ETag"].strip('"')
        with current_app.test_request_context(
            "/activity-stream", headers={"If-None-Match": f'"{etag}:gzip"'}
        ):
            r = as_response(self._collection(current_app), NAIVE)
        assert r.status_code == 304
        assert r.headers["ETag"] == f'"{etag}:gzip"'
        assert "Content-Type" not in r.headers

    def test_if_modified_since_matches(self, current_app):
        with current_app.test_request_context("/activity-stream"):
            lm_header = as_response(self._collection(current_app), NAIVE).headers[
                "Last-Modified"
            ]
        with current_app.test_request_context(
            "/activity-stream", headers={"If-Modified-Since": lm_header}
        ):
            r = as_response(self._collection(current_app), NAIVE)
        assert r.status_code == 304
        assert r.headers["Last-Modified"] == lm_header
        assert "Content-Type" not in r.headers

    def test_sub_second_last_modified_still_304s(self, current_app):
        lm = NAIVE.replace(microsecond=987654)
        with current_app.test_request_context("/activity-stream"):
            r200 = as_response(self._collection(current_app), lm)
            lm_header = r200.headers["Last-Modified"]  # truncated to whole seconds
        with current_app.test_request_context(
            "/activity-stream", headers={"If-Modified-Since": lm_header}
        ):
            r = as_response(self._collection(current_app), lm)
        assert r.status_code == 304
        assert r.headers["Last-Modified"] == lm_header

    def test_mixed_stale_if_none_match_and_current_ims_is_200(self, current_app):
        # RFC 9110 section 13.2.2: If-Modified-Since MUST be ignored when
        # If-None-Match is present, so a stale INM must 200, not 304
        with current_app.test_request_context("/activity-stream"):
            r200 = as_response(self._collection(current_app), NAIVE)
            lm_header = r200.headers["Last-Modified"]
        with current_app.test_request_context(
            "/activity-stream",
            headers={
                "If-None-Match": '"stale-etag-value"',
                "If-Modified-Since": lm_header,
            },
        ):
            r = as_response(self._collection(current_app), NAIVE)
        assert r.status_code == 200
        assert r.headers["ETag"] == r200.headers["ETag"]
        assert r.headers["Content-Type"] == ACTIVITY_JSON

    def test_no_validators_is_200_with_all_headers(self, current_app):
        with current_app.test_request_context("/activity-stream"):
            r = as_response(self._collection(current_app), NAIVE)
        assert r.status_code == 200
        assert r.headers["Content-Type"] == ACTIVITY_JSON
        assert r.headers["ETag"].startswith('"')
        assert len(r.headers["ETag"].strip('"')) == 64  # a strong sha256 hash
        assert r.headers["Last-Modified"]

    def test_empty_document_carries_no_last_modified(self, current_app):
        empty = build_collection("collection-1", 0, 0, stream_page_url)
        with current_app.test_request_context("/activity-stream"):
            assert "Last-Modified" not in as_response(empty).headers
        with current_app.test_request_context(
            "/activity-stream", headers={"If-None-Match": "*"}
        ):
            r = as_response(empty)
        assert r.status_code == 304
        assert "Last-Modified" not in r.headers
