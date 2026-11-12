import math

from flask_openapi3 import APIBlueprint
from flask import current_app, abort, redirect, jsonify, url_for
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import coalesce
from sqlalchemy import func

# date parsing
import dateparser

from flaskapp.models import db
from flaskapp.models.activity import Activity
from flaskapp.models.record import Record
from flaskapp.utilities import max_utc_datetime
from flaskapp.errors import (
    construct_error_response,
    status_record_not_found,
    status_pagenum_not_integer,
    status_page_not_found,
)
from flaskapp.openapi import activity_tag
from flaskapp.openapi_models import (
    TargetDatetimePath,
    OptionalTargetDatetimeQuery,
    PagenumPath,
    UuidPath,
    _strip_openapi_kwargs,
)

from flaskapp.activity_streams import (
    as_response,
    build_collection,
    build_event_item,
    build_page,
    stream_page_url,
    stream_url,
)

# Create a new "activity" route blueprint
activity = APIBlueprint("activity", __name__)
_strip_openapi_kwargs(activity)


# GET param method:
@activity.get(
    "/activity-stream/skip-to-datetime",
    tags=[activity_tag],
    summary="Skip to activity page by datetime",
    responses={
        200: {"description": "Redirect or results"},
        400: {"description": "Bad datetime"},
        404: {"description": "No activity found for date"},
    },
)
def get_param_redirect_to_page(query: OptionalTargetDatetimeQuery):
    return _redirect_to_page_using_datetime(query.datetime)


@activity.get(
    "/activity-stream/skip-to-datetime/<string:target_datetime>",
    tags=[activity_tag],
    summary="Skip to activity page by datetime",
    responses={
        200: {"description": "Redirect or results"},
        400: {"description": "Bad datetime"},
        404: {"description": "No activity found for date"},
    },
)
def path_datetime_redirect_to_page(path: TargetDatetimePath):
    return _redirect_to_page_using_datetime(path.target_datetime)


def _redirect_to_page_using_datetime(target_datetime=None):
    if not target_datetime:
        # response - bad request
        return (
            jsonify({"errors": [{"error": "Datetime was not specified."}]}),
            400,
        )

    try:
        datetime_obj = dateparser.parse(
            target_datetime,
            settings={"RETURN_AS_TIMEZONE_AWARE": True},
        )
        if datetime_obj is None:
            # response - bad request, unparsable date
            return (
                jsonify({"errors": [{"error": "Datetime was not understood"}]}),
                400,
            )
    except (ValueError, TypeError) as e:
        current_app.logger.debug(
            f"There was an error decoding the date provided: '{target_datetime}' - {e}"
        )
        return (
            jsonify({"errors": [{"error": "Datetime was not understood"}]}),
            400,
        )

    # Try to find the closest Activity id to suggested date
    # The datetime is not indexed at the moment but could be eventually. This
    # initial query will be slow until then!
    if closest_log := (
        Activity.query.filter(Activity.datetime_created >= datetime_obj)
        .order_by(Activity.id)
        .first()
    ):
        limit = current_app.config["ITEMS_PER_PAGE"]
        page = (closest_log.id // limit) + 1
        current_app.logger.debug(
            f"Redirecting to page {page} for Activity.id {closest_log.id} due to "
            f"datetime {target_datetime} - parsed as {datetime_obj}"
        )
        return redirect(url_for("activity.activity_stream_page", pagenum=page))
    else:
        return (
            jsonify(
                {
                    "errors": [
                        {
                            "error": f"No Activity entries found newer than specified date: '{target_datetime}'."
                        }
                    ]
                }
            ),
            404,
        )


@activity.get(
    "/activity-stream",
    tags=[activity_tag],
    summary="Activity Stream root",
    responses={
        200: {"description": "Activity Stream collection"},
        304: {"description": "Not modified"},
    },
)
@activity.get("/activity-stream/")
def activity_stream_collection():
    """Generate the root OrderedCollection for the stream

    Returns:
        Response: A JSON-encoded OrderedCollection with the AS 2.0 media
        type, an ETag and a Last-Modified (RFC 9110 revalidation).
    """

    limit = current_app.config["ITEMS_PER_PAGE"]
    count, max_id, max_dt = (
        db.session.query(
            func.count(Activity.id),
            coalesce(func.max(Activity.id), 0),
            func.max(Activity.datetime_created),
        ).one()
    )
    # PK-window pagination: page N covers the id window
    # ((N-1)*size, N*size], so the page count derives from the highest id,
    # not from the row count (deletions leave gaps, not fewer pages).
    total_pages = math.ceil(max_id / limit)
    data = build_collection(stream_url(), count, total_pages, stream_page_url)
    return as_response(data, max_dt)


@activity.get(
    "/activity-stream/page/<int:pagenum>",
    tags=[activity_tag],
    summary="Activity Stream page",
    responses={
        200: {"description": "Paginated activity items"},
        304: {"description": "Not modified"},
        404: {"description": "Page out of bounds"},
    },
)
@activity.get("/activity-stream/page/<int:pagenum>")
def activity_stream_page(path: PagenumPath):
    """Generate an OrderedCollectionPage of Activity Stream items.

    Args:
        pagenum (Integer): The page to generate

    Returns:
        TYPE: Response: a JSON-encoded OrderedCollectionPage


    The items are fetched by primary-key window (not OFFSET/LIMIT): the
    window bounds are index-scanned, which is far faster than an offset
    scan. Deleted ids inside a window leave a short page; the page count
    derives from the highest id, so a windowed page is always in bounds.
    """

    pagenum = None
    if path and path.pagenum:
        pagenum = path.pagenum

    if not pagenum:
        pagenum = 1

    limit = current_app.config["ITEMS_PER_PAGE"]
    offset = (pagenum - 1) * limit
    max_id = db.session.query(coalesce(func.max(Activity.id), 0)).scalar()
    total_pages = math.ceil(max_id / limit)

    if pagenum == 0 or pagenum > total_pages:
        response = construct_error_response(status_page_not_found)
        return abort(response)

    rows = (
        Activity.query.with_entities(
            Activity.uuid,
            Activity.event,
            Activity.datetime_created,
            Record.entity_id,
            Record.entity_type,
        )
        .join(Record)
        .filter(Activity.id > offset, Activity.id <= offset + limit)
        .order_by(Activity.id)
    )
    items = [
        build_event_item(
            "global", r.uuid, r.event, r.datetime_created, r.entity_id, r.entity_type
        )
        for r in rows
    ]
    # Last-Modified covers this page's items only, so activity on other
    # pages of the stream does not invalidate this representation's cache.
    last_modified = max_utc_datetime(r.datetime_created for r in rows)

    data = build_page(
        pagenum, total_pages, stream_page_url(pagenum), stream_url(), stream_page_url, items
    )

    return as_response(data, last_modified)


@activity.get(
    "/activity-stream/<string:uuid>",
    tags=[activity_tag],
    summary="Activity Stream item",
    responses={
        200: {"description": "Activity item"},
        304: {"description": "Not modified"},
        404: {"description": "Not found"},
    },
)
@activity.get("/activity-stream/<string:uuid>")
def activity_stream_item(path: UuidPath):
    """Generate an ActivityStreams Create Response

    Args:
        uuid (String): The ID of the ActivityStream Create entity

    Returns:
        Response:  a JSON-encoded Create entity
    """

    activity = (
        Activity.query.options(joinedload(Activity.record, innerjoin=True))
        .filter(Activity.uuid == path.uuid)
        .one_or_none()
    )

    if not activity:
        response = construct_error_response(status_record_not_found)
        return abort(response)

    data = build_event_item(
        "global",
        activity.uuid,
        activity.event,
        activity.datetime_created,
        activity.record.entity_id,
        activity.record.entity_type,
        standalone=True,
    )

    return as_response(data, activity.datetime_created)
