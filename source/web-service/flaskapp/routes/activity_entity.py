import math

from flask import Blueprint, current_app, abort
from sqlalchemy.orm import joinedload, load_only, defer
from sqlalchemy.sql.functions import coalesce, max
from sqlalchemy import desc, func

from flaskapp.models import db
from flaskapp.models.activity import Activity
from flaskapp.models.record import Record
from flaskapp.utilities import format_datetime
from flaskapp.errors import (
    construct_error_response,
    status_record_not_found,
    status_pagenum_not_integer,
    status_page_not_found,
)


# Create a new "activity" route blueprint
activity_entity = Blueprint("activity_entity", __name__)

# Make the list of entity types global to populate it only once
lod_entity_types = []


### Activity Stream Entity Routes ###


@activity_entity.route("/activity-stream/type/<string:entity_type>")
def activity_stream_entity_collection(entity_type):
    entity_type = entity_type.lower()
    global lod_entity_types
    if len(lod_entity_types) == 0:
        lod_entity_types = get_distinct_entity_types()
    if entity_type not in lod_entity_types:
        response = construct_error_response(status_record_not_found)
        return abort(response)

    data = create_activity_collection(entity_type)
    return current_app.make_response(data)


@activity_entity.route(
    "/activity-stream/type/<string:entity_type>/page/<string:pagenum>"
)
def activity_stream_entity_page(entity_type, pagenum):
    entity_type = entity_type.lower()
    data = create_page_data(pagenum, entity_type)
    return current_app.make_response(data)


### Functions ###


def create_activity_collection(entity_type):
    count = get_count(entity_type)
    limit = current_app.config["ITEMS_PER_PAGE"]
    total_pages = str(math.ceil(count / limit))

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "summary": current_app.config["AS_DESC"],
        "type": "OrderedCollection",
        "id": url_activity(entity_type),
        "totalItems": count,
    }

    if count:
        data["first"] = {
            "id": url_page(1, entity_type),
            "type": "OrderedCollectionPage",
        }
        data["last"] = {
            "id": url_page(total_pages, entity_type),
            "type": "OrderedCollectionPage",
        }

    return data


def create_page_data(pagenum, entity_type):
    pagenum = int(pagenum)
    limit = current_app.config["ITEMS_PER_PAGE"]
    offset = (pagenum - 1) * limit
    count = get_count(entity_type)
    total_pages = math.ceil(count / limit)

    if pagenum == 0 or pagenum > total_pages:
        response = construct_error_response(status_page_not_found)
        return abort(response)

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollectionPage",
        "id": url_page(pagenum, entity_type),
        "partOf": {"id": url_activity(entity_type), "type": "OrderedCollection"},
    }

    if pagenum < total_pages:
        data["next"] = {
            "id": url_page(pagenum + 1, entity_type),
            "type": "OrderedCollectionPage",
        }

    if pagenum > 1:
        data["prev"] = {
            "id": url_page(pagenum - 1, entity_type),
            "type": "OrderedCollectionPage",
        }

    activities = get_entity_activities(entity_type, offset, limit)

    items = [generate_item(a) for a in activities]
    data["orderedItems"] = items

    return data


def url_base():
    base_url = current_app.config["BASE_URL"]
    namespace = current_app.config["NAMESPACE"]
    return base_url + "/" + namespace


def url_activity(entity_type):
    return url_base() + "/activity-stream/type/" + entity_type.lower()


def url_page(page_num, entity_type):
    return url_activity(entity_type) + "/page/" + str(page_num)


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


def generate_item(activity):
    return {
        "id": url_base() + "/activity-stream/" + str(activity.uuid),
        "type": activity.event,
        "created": format_datetime(activity.datetime_created),
        "endTime": format_datetime(activity.datetime_created),
        "object": {
            "id": url_base() + "/" + activity.entity_id,
            "type": activity.entity_type,
        },
    }
