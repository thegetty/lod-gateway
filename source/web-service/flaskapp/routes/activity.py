import math

from flask import Blueprint, current_app
from sqlalchemy.orm import joinedload, load_only

from flaskapp.models import Activity
from flaskapp.utilities import (
    error_response,
    generate_url,
    validate_namespace,
    format_datetime,
)
from app.utilities import hyphenatedStringFromCamelCasedString


# Create a new "activity" route blueprint
activity = Blueprint("activity", __name__)


@activity.route("/activity-stream", defaults={"namespace": None})
@activity.route("/<path:namespace>/activity-stream")
def activity_stream_collection(namespace):
    """Generate the root OrderedCollection for the stream

    TODO: This does not currently filter against namespaces for the count. Should it?

    Args:
        namespace (String): The namespace of the application

    Returns:
        Response: A JSON-encoded OrderedCollection
    """
    namespace = validate_namespace(namespace)

    count = Activity.query.count()
    total_pages = str(math.ceil(count / current_app.config["ITEMS_PER_PAGE"]))

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "summary": current_app.config["AS_DESC"],
        "type": "OrderedCollection",
        "id": generate_url(namespace=namespace),
        "totalItems": count,
        "first": {
            "id": generate_url(namespace=namespace, sub=["page", "1"]),
            "type": "OrderedCollectionPage",
        },
        "last": {
            "id": generate_url(namespace=namespace, sub=["page", total_pages]),
            "type": "OrderedCollectionPage",
        },
    }

    return current_app.make_response(data)


@activity.route("/activity-stream/page/<int:pagenum>", defaults={"namespace": None})
@activity.route("/<path:namespace>/activity-stream/page/<int:pagenum>")
def activity_stream_collection_page(namespace, pagenum):
    """Generate an OrderedCollectionPage of Activity Stream items.

    Args:
        namespace (String): The namespace of the application
        pagenum (Integer): The page to generate

    Returns:
        TYPE: Response: a JSON-encoded OrderedCollectionPage
    """
    namespace = validate_namespace(namespace)

    limit = current_app.config["ITEMS_PER_PAGE"]

    try:
        first_id = Activity.query.options(load_only("id")).order_by("id").first().id
    except Exception as e:
        first_id = 0

    offset = first_id - 1 + (pagenum - 1) * limit

    count = Activity.query.count()
    total_pages = math.ceil(count / limit)

    if pagenum == 0 or pagenum > total_pages:
        return error_response((404, "Page number out of bounds"))

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollectionPage",
        "id": generate_url(namespace=namespace, sub=["page", str(pagenum)]),
        "partOf": {
            "id": generate_url(namespace=namespace),
            "type": "OrderedCollection",
        },
    }

    if pagenum < total_pages:
        data["next"] = {
            "id": generate_url(namespace=namespace, sub=["page", str(pagenum + 1)]),
            "type": "OrderedCollectionPage",
        }

    if pagenum > 1:
        data["prev"] = {
            "id": generate_url(namespace=namespace, sub=["page", str(pagenum - 1)]),
            "type": "OrderedCollectionPage",
        }

    activities = (
        Activity.query.options(joinedload(Activity.record, innerjoin=True))
        .filter(Activity.id > offset, Activity.id <= offset + limit)
        .order_by("id")
    )
    items = [_generate_item(namespace, a) for a in activities]
    data["orderedItems"] = items

    return current_app.make_response(data)


@activity.route("/activity-stream/<string:uuid>", defaults={"namespace": None})
@activity.route("/<path:namespace>/activity-stream/<string:uuid>")
def activity_stream_item(namespace, uuid):
    """Generate an ActivityStreams Create Response

    Args:
        namespace (String): The namespace of the application
        uuid (String): The ID of the ActivityStream Create entity

    Returns:
        Response:  a JSON-encoded Create entity
    """
    namespace = validate_namespace(namespace)

    activity = Activity.query.filter(Activity.uuid == uuid).first()
    if not activity:
        return error_response((404, "Could not find ActivityStream record"))

    data = _generate_item(namespace, activity)

    return current_app.make_response(data)


def _generate_item(namespace, activity):
    """Generate the ActivityStream Create record

    Args:
        namespace (String): The namespace of the application
        activity (Activity): The Activity record to generate

    Returns:
        Dict: The generated data structure
    """
    return {
        "id": generate_url(namespace=namespace, sub=[str(activity.uuid)]),
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
    record_type = hyphenatedStringFromCamelCasedString(record.entity)
    return {
        "id": generate_url(
            namespace=record.namespace, base=True, sub=[record_type, str(record.uuid)]
        ),
        "type": record.entity,
    }
