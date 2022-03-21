import math

from flask import Blueprint, current_app, abort, url_for, request, jsonify
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
    status_ok,
)

# authentication function from ingest. This really should be changed at some point to a
# better library like JWT
from flaskapp.routes.ingest import authenticate_bearer

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


# by id
@activity_entity.route("/activity-stream/id/<path:entity_id>", methods=["GET", "HEAD"])
def activity_stream_entity_id_collection(entity_id):
    if get_count_for_id(entity_id) == 0:
        response = construct_error_response(status_record_not_found)
        return abort(response)

    data = create_activity_collection_for_id(entity_id)
    return current_app.make_response(data)


@activity_entity.route("/activity-stream/id/<path:entity_id>", methods=["POST"])
def truncate_activity_stream_of_entity_id(entity_id):
    # Authentication. If fails, abort with 401
    status = authenticate_bearer(request)
    if status != status_ok:
        response = construct_error_response(status)
        return abort(response)

    count = get_count_for_id(entity_id)
    # Are there events for this ID?
    if count == 0:
        response = construct_error_response(status_record_not_found)
        return abort(response)

    # How many events to keep
    keep_latest_events = request.values.get("keep")
    try:
        keep_latest_events = int(keep_latest_events)
    except (ValueError, TypeError) as e:
        current_app.logger.error(f"'keep' parameter was not an integer.")
        keep_latest_events = None

    if keep_latest_events is None or keep_latest_events < 1:
        return (
            jsonify(
                {
                    "error": {
                        "message": (
                            "To truncate an entity's activity-stream, the parameter 'keep' "
                            "must be provided and set equal to the number of events to keep for "
                            "the entity and must not be less than 1"
                        )
                    }
                }
            ),
            400,
        )

    # Should we keep the oldest event?
    keep_oldest_event = request.values.get("keep_oldest_event")
    end_of_truncate = None
    if keep_oldest_event is not None and keep_oldest_event.lower() == "true":
        end_of_truncate = -1

    # A valid keep number was passed but is it at least as big as the
    # total number of events for this entity?
    # Adjust if the oldest event is being kept.
    if keep_latest_events >= (count + (end_of_truncate or 0)):
        return jsonify({"number_of_events_removed": 0}), 200

    # should have a valid number of items to remove from the activitystream.
    # There is a way to do this 'cleverly' with multiple subquerys, and other
    # things, but there won't be that many events per resource so we can
    # process it client-side.

    # Get the list of events, sorted by id but DESCENDING
    # Should be from newest to oldest event.
    activity_list = (
        Activity.query.filter(Activity.record.has(entity_id=entity_id))
        .order_by(Activity.id.desc())
        .all()
    )

    deleted = 0
    # python slice will pull all the list into memory
    # should be fine, given the above note.
    for a in activity_list[keep_latest_events:end_of_truncate]:
        db.session.delete(a)
        deleted += 1

    current_app.logger.warning(
        f"Truncating {entity_id} activity-stream to most recent {keep_latest_events} event(s)"
    )
    try:
        db.session.commit()
        return jsonify({"number_of_events_removed": deleted}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"SQLAlchemyError! {e}")
        raise e


@activity_entity.route(
    "/activity-stream/id/<path:entity_id>/page/<string:pagenum>",
    methods=["GET", "HEAD"],
)
def activity_stream_entity_id_page(entity_id, pagenum):
    data = create_page_data_for_entity(pagenum, entity_id)
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


def create_activity_collection_for_id(entity_id):
    count = get_count_for_id(entity_id)
    limit = current_app.config["ITEMS_PER_PAGE"]
    total_pages = str(math.ceil(count / limit))

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "summary": current_app.config["AS_DESC"],
        "type": "OrderedCollection",
        "id": current_app.config["BASE_URL"]
        + url_for(
            "activity_entity.activity_stream_entity_id_collection", entity_id=entity_id,
        ),
        "totalItems": count,
    }

    if count:
        data["first"] = {
            "id": current_app.config["BASE_URL"]
            + url_for(
                "activity_entity.activity_stream_entity_id_page",
                pagenum=1,
                entity_id=entity_id,
            ),
            "type": "OrderedCollectionPage",
        }
        data["last"] = {
            "id": current_app.config["BASE_URL"]
            + url_for(
                "activity_entity.activity_stream_entity_id_page",
                pagenum=total_pages,
                entity_id=entity_id,
            ),
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


def create_page_data_for_entity(pagenum, entity_id):
    pagenum = int(pagenum)
    limit = current_app.config["ITEMS_PER_PAGE"]
    offset = (pagenum - 1) * limit
    count = get_count_for_id(entity_id)
    total_pages = math.ceil(count / limit)

    if pagenum == 0 or pagenum > total_pages:
        response = construct_error_response(status_page_not_found)
        return abort(response)

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollectionPage",
        "id": current_app.config["BASE_URL"]
        + url_for(
            "activity_entity.activity_stream_entity_id_page",
            pagenum=pagenum,
            entity_id=entity_id,
        ),
        "partOf": {
            "id": current_app.config["BASE_URL"]
            + url_for(
                "activity_entity.activity_stream_entity_id_collection",
                entity_id=entity_id,
            ),
            "type": "OrderedCollection",
        },
    }

    if pagenum < total_pages:
        data["next"] = {
            "id": current_app.config["BASE_URL"]
            + url_for(
                "activity_entity.activity_stream_entity_id_page",
                pagenum=pagenum + 1,
                entity_id=entity_id,
            ),
            "type": "OrderedCollectionPage",
        }

    if pagenum > 1:
        data["prev"] = {
            "id": current_app.config["BASE_URL"]
            + url_for(
                "activity_entity.activity_stream_entity_id_page",
                pagenum=pagenum - 1,
                entity_id=entity_id,
            ),
            "type": "OrderedCollectionPage",
        }

    activities = get_entity_id_activities(entity_id, offset, limit)

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
        result.append(v.entity_type.lower())
    return result


def get_count(entity_type):
    count = (
        Activity.query.with_entities(Activity.id)
        .join(Record)
        .filter(func.lower(Record.entity_type) == entity_type)
    ).count()

    return count


def get_count_for_id(entity_id):
    count = (
        Activity.query.with_entities(Activity.id)
        .join(Record)
        .filter(Record.entity_id == entity_id)
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


def get_entity_id_activities(entity_id, offset, limit):
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
            .filter(Record.entity_id == entity_id)
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
