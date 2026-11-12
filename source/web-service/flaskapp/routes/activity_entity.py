import math

from flask_openapi3 import APIBlueprint
from flask import current_app, abort
from sqlalchemy import func

from flaskapp.models import db
from flaskapp.models.activity import Activity
from flaskapp.models.record import Record
from flaskapp.utilities import max_utc_datetime
from flaskapp.errors import (
    construct_error_response,
    status_record_not_found,
    status_page_not_found,
)
from flaskapp.openapi import activity_tag
from flaskapp.openapi_models import (
    EntityTypePath,
    EntityTypePagenumPath,
    _strip_openapi_kwargs,
)

from flaskapp.activity_streams import (
    as_response,
    build_collection,
    build_event_item,
    build_page,
    type_page_url,
    type_stream_url,
)

# Create a new "activity" route blueprint
activity_entity = APIBlueprint("activity_entity", __name__)
_strip_openapi_kwargs(activity_entity)

# Make the list of entity types global to populate it only once
lod_entity_types = []


### Activity Stream Entity Routes ###


@activity_entity.get(
    "/activity-stream/type/<string:entity_type>",
    tags=[activity_tag],
    summary="Activity Stream by entity type",
    responses={
        200: {"description": "Filtered activity collection"},
        304: {"description": "Not modified"},
        404: {"description": "Entity type not found"},
    },
)
@activity_entity.get("/activity-stream/type/<string:entity_type>")
def activity_stream_entity_collection(path: EntityTypePath):
    """Generate the root OrderedCollection for a type-filtered stream.

    Returns:
        Response: A JSON-encoded OrderedCollection with the AS 2.0 media
        type, an ETag and a Last-Modified (RFC 9110 revalidation).
    """
    entity_type = path.entity_type
    entity_type = entity_type.lower()
    global lod_entity_types
    if len(lod_entity_types) == 0:
        lod_entity_types = get_distinct_entity_types()
    if entity_type not in lod_entity_types:
        response = construct_error_response(status_record_not_found)
        return abort(response)

    data = create_activity_collection(entity_type)
    return data


@activity_entity.get(
    "/activity-stream/type/<string:entity_type>/page/<int:pagenum>",
    tags=[activity_tag],
    summary="Activity Stream by type, paginated",
    path=EntityTypePagenumPath,
    responses={
        200: {"description": "Paginated activity items"},
        304: {"description": "Not modified"},
        404: {"description": "Not found"},
    },
)
@activity_entity.get("/activity-stream/type/<string:entity_type>/page/<string:pagenum>")
def activity_stream_entity_page(path: EntityTypePagenumPath):
    entity_type = path.entity_type.lower()
    data = create_page_data(path.pagenum, entity_type)
    return data


### Functions ###


def create_activity_collection(entity_type):
    """Build the type collection and return it with its validators."""
    limit = current_app.config["ITEMS_PER_PAGE"]
    count, max_dt = (
        db.session.query(
            func.count(Activity.id),
            func.max(Activity.datetime_created),
        )
        .join(Record)
        .filter(func.lower(Record.entity_type) == entity_type)
        .one()
    )
    total_pages = math.ceil(count / limit)
    page_url_fn = lambda page: type_page_url(page, entity_type)
    data = build_collection(
        type_stream_url(entity_type), count, total_pages, page_url_fn
    )
    return as_response(data, max_dt)


def create_page_data(pagenum, entity_type):
    """Build a type stream page and return it with its validators."""
    pagenum = int(pagenum)
    limit = current_app.config["ITEMS_PER_PAGE"]
    offset = (pagenum - 1) * limit
    count = get_count(entity_type)
    total_pages = math.ceil(count / limit)

    if pagenum == 0 or pagenum > total_pages:
        response = construct_error_response(status_page_not_found)
        return abort(response)

    # Type streams page with standard OFFSET/LIMIT over a count (not the
    # global stream's pk-window), per the service's paging policy.
    rows = get_entity_activities(entity_type, offset, limit)
    items = [
        build_event_item(
            "type", a.uuid, a.event, a.datetime_created, a.entity_id, a.entity_type
        )
        for a in rows
    ]
    # Last-Modified covers this page's items only.
    last_modified = max_utc_datetime(a.datetime_created for a in rows)

    page_url_fn = lambda page: type_page_url(page, entity_type)
    data = build_page(
        pagenum,
        total_pages,
        type_page_url(pagenum, entity_type),
        type_stream_url(entity_type),
        page_url_fn,
        items,
    )

    return as_response(data, last_modified)


def get_distinct_entity_types():
    val = Record.query.distinct(Record.entity_type).all()
    result = []
    for v in val:
        if v.entity_type:
            result.append(v.entity_type.lower())
    return result


def get_count(entity_type):
    count = (
        Activity.query.with_entities(Activity.id)
        .join(Record)
        .filter(func.lower(Record.entity_type) == entity_type)
    ).count()

    return count


def get_entity_activities(entity_type, offset, limit):
    activities = (
        (
            Activity.query.with_entities(
                Activity.uuid,
                Activity.event,
                Activity.datetime_created,
                Record.entity_id,
                Record.entity_type,
            )
            .join(Record)
            .filter(func.lower(Record.entity_type) == entity_type)
        )
        .order_by(Activity.id)
        .limit(limit)
        .offset(offset)
    )

    return activities
