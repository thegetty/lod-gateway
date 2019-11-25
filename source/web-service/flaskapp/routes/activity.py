import math

from flask import Blueprint, current_app

from flaskapp.models import Activities
from flaskapp.utilities import (
    error_response,
    generate_url,
    validate_namespace,
    DEFAULT_HEADERS,
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

    count = Activities.query.count()
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

    return current_app.make_response((data, 200, DEFAULT_HEADERS))


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
    offset = (pagenum - 1) * limit
    count = Activities.query.count()
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

    activities = Activities.query.order_by("id").limit(limit).offset(offset)
    items = [_generate_item(namespace, a) for a in activities]
    data["orderedItems"] = items

    return current_app.make_response((data, 200, DEFAULT_HEADERS))


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

    activity = Activities.query.filter(Activities.uuid == uuid).first()
    if not activity:
        return error_response((404, "Could not find ActivityStream record"))

    data = _generate_item(namespace, activity)

    return current_app.make_response((data, 200, DEFAULT_HEADERS))


def _generate_item(namespace, activity):
    """Generate the ActivityStream Create record

    Args:
        namespace (String): The namespace of the application
        activity (Activities): The Activities record to generate

    Returns:
        Dict: The generated data structure
    """
    return {
        "id": generate_url(namespace=namespace, sub=[str(activity.uuid)]),
        "type": activity.event,
        "created": activity.datetime_created.strftime("%Y-%m-%dT%H:%M:%S:%z"),
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
