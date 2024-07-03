import math

from flask import Blueprint, current_app, abort, request, redirect, jsonify, url_for
from sqlalchemy.orm import joinedload, defer
from sqlalchemy.sql.functions import coalesce, max
from sqlalchemy import func

# date parsing
import dateparser

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
activity = Blueprint("activity", __name__)


@activity.route("/activity-stream/skip-to-datetime")
@activity.route("/activity-stream/skip-to-datetime/<string:target_datetime>")
def redirect_to_page_using_datetime(target_datetime=None):
    if "datetime" in request.args:
        target_datetime = request.args["datetime"]

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


@activity.route("/activity-stream")
def activity_stream_collection():
    """Generate the root OrderedCollection for the stream

    TODO: This does not currently filter against namespaces for the count. Should it?

    Returns:
        Response: A JSON-encoded OrderedCollection
    """

    count = db.session.query(func.count(Activity.id)).scalar()
    total_pages = str(compute_total_pages())

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


# Abort if 'pagenum' is not integer
@activity.route("/activity-stream/page/<string:pagenum>")
def activity_stream_wrong_page_format(pagenum):
    response = construct_error_response(status_pagenum_not_integer)
    return abort(response)


@activity.route("/activity-stream/page/<int:pagenum>")
def activity_stream_page(pagenum):
    """Generate an OrderedCollectionPage of Activity Stream items.

    Args:
        pagenum (Integer): The page to generate

    Returns:
        TYPE: Response: a JSON-encoded OrderedCollectionPage
    """

    limit = current_app.config["ITEMS_PER_PAGE"]
    offset = (pagenum - 1) * limit
    total_pages = compute_total_pages()

    if pagenum == 0 or pagenum > total_pages:
        response = construct_error_response(status_page_not_found)
        return abort(response)

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
        Activity.query.options(
            joinedload(Activity.record, innerjoin=True), defer("record.data")
        )
        .filter(Activity.id > offset, Activity.id <= offset + limit)
        .order_by("id")
    )

    items = [generate_item(a) for a in activities]
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
        .one_or_none()
    )

    if not activity:
        response = construct_error_response(status_record_not_found)
        return abort(response)

    data = generate_item(activity)

    return current_app.make_response(data)


def compute_total_pages():
    limit = current_app.config["ITEMS_PER_PAGE"]
    # Quick count
    last = db.session.query(coalesce(max(Activity.id), 0).label("num")).one()
    return math.ceil(last.num / limit)


def generate_url(sub=[], base=False):
    """Create a URL string from relevant fragments

    Args:
        sub (list, optional): A list of additional URL parts
        base (bool, optional): Should the "activity-stream" part be added?

    Returns:
        String: The generated URL string
    """
    base_url = current_app.config["BASE_URL"]
    namespace = current_app.config["NAMESPACE"]

    if base:
        as_prefix = None
    else:
        as_prefix = "activity-stream"

    parts = [base_url, namespace, as_prefix, "/".join(sub)]
    parts = [item for item in parts if item]
    return "/".join(parts)


def generate_item(activity):
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
        "endTime": format_datetime(activity.datetime_created),
        "object": {
            "id": generate_url(base=True, sub=[str(activity.record.entity_id)]),
            "type": activity.record.entity_type,
        },
    }
