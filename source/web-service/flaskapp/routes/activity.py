import math

from flask import Blueprint, current_app
from sqlalchemy.orm import joinedload, load_only
from sqlalchemy.sql.functions import coalesce, max
from sqlalchemy import desc

from flaskapp.models import db
from flaskapp.models.activity import Activity
from flaskapp.utilities import (
    generate_url,
    format_datetime,
    uncamel_case,
)


# Create a new "activity" route blueprint
activity = Blueprint("activity", __name__)


@activity.route("/activity-stream")
def activity_stream_collection():
    """Generate the root OrderedCollection for the stream

    TODO: This does not currently filter against namespaces for the count. Should it?

    Returns:
        Response: A JSON-encoded OrderedCollection
    """

    count = Activity.query.count()
    total_pages = str(_compute_total_pages())

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "summary": current_app.config["AS_DESC"],
        "type": "OrderedCollection",
        "id": generate_url(),
        "totalItems": count,
    }

    if count:
        data["first"] = {
            "id": generate_url(sub=["page", "1"]),
            "type": "OrderedCollectionPage",
        }
        data["last"] = {
            "id": generate_url(sub=["page", total_pages]),
            "type": "OrderedCollectionPage",
        }

    return current_app.make_response(data)


@activity.route("/activity-stream/page/<int:pagenum>")
def activity_stream_collection_page(pagenum):
    """Generate an OrderedCollectionPage of Activity Stream items.

    Args:
        pagenum (Integer): The page to generate

    Returns:
        TYPE: Response: a JSON-encoded OrderedCollectionPage
    """

    limit = current_app.config["ITEMS_PER_PAGE"]
    offset = (pagenum - 1) * limit
    total_pages = _compute_total_pages()

    if pagenum == 0 or pagenum > total_pages:
        return current_app.make_response(("Page number out of bounds", 404))

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollectionPage",
        "id": generate_url(sub=["page", str(pagenum)]),
        "partOf": {"id": generate_url(), "type": "OrderedCollection"},
    }

    if pagenum < total_pages:
        data["next"] = {
            "id": generate_url(sub=["page", str(pagenum + 1)]),
            "type": "OrderedCollectionPage",
        }

    if pagenum > 1:
        data["prev"] = {
            "id": generate_url(sub=["page", str(pagenum - 1)]),
            "type": "OrderedCollectionPage",
        }

    activities = (
        Activity.query.options(joinedload(Activity.record, innerjoin=True))
        .filter(Activity.id > offset, Activity.id <= offset + limit)
        .order_by("id")
    )
    items = [_generate_item(a) for a in activities]
    data["orderedItems"] = items

    return current_app.make_response(data)


@activity.route("/activity-stream/<string:uuid>")
def activity_stream_item(uuid):
    """Generate an ActivityStreams Create Response

    Args:
        uuid (String): The ID of the ActivityStream Create entity

    Returns:
        Response:  a JSON-encoded Create entity
    """

    activity = (
        Activity.query.options(joinedload(Activity.record, innerjoin=True))
        .filter(Activity.uuid == uuid)
        .first()
    )
    if not activity:
        return current_app.make_response(("Could not find ActivityStream record", 404))

    data = _generate_item(activity)

    return current_app.make_response(data)


def _compute_total_pages():
    limit = current_app.config["ITEMS_PER_PAGE"]
    last = db.session.query(coalesce(max(Activity.id), 0).label("num")).first()
    return math.ceil(last.num / limit)


def _generate_item(activity):
    """Generate the ActivityStream Create record

    Args:
        activity (Activity): The Activity record to generate

    Returns:
        Dict: The generated data structure
    """
    return {
        "id": generate_url(sub=[str(activity.uuid)]),
        "type": activity.event,
        "created": format_datetime(activity.datetime_created),
        "object": _generate_object(activity.record),
    }


def _generate_object(record):
    """Generate the AS representation of a Record

    Args:
        record (Record): The object or generate

    Returns:
        Dict: The AS representation of the object, or None if the record is invalid
    """
    record_type = uncamel_case(record.entity)
    return {
        "id": generate_url(base=True, sub=[record_type, str(record.uuid)]),
        "type": record.entity,
    }
