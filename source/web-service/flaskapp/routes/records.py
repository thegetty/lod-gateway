import click
import math

from datetime import datetime, timezone
from flask import Blueprint, current_app, abort, request
from sqlalchemy.exc import IntegrityError

from flaskapp.models import db
from flaskapp.models.record import Record
from flaskapp.models.activity import Activity
from flaskapp.utilities import format_datetime, containerRecursiveCallback, idPrefixer
from flaskapp.errors import (
    construct_error_response,
    status_record_not_found,
    status_page_not_found,
)
from flaskapp.utilities import checksum_json

# Create a new "records" route blueprint
records = Blueprint("records", __name__)


@records.cli.command("checksum")
@click.argument("extent")
def create_checksums(extent):
    # Flask CLI command to generate checksums for the records in the system
    # `flask records checksum null`
    extent = extent.lower()
    if extent not in ["null"]:
        print(
            f"Option must be 'null' to checksum just those Record rows without a checksum."
        )
        return
    print("Migration will now checksum records - may take some time")
    try:
        completed = 0
        while Record.query.filter(Record.checksum == None).first() is not None:
            for idx, record in enumerate(
                Record.query.filter(Record.checksum == None).limit(100).all()
            ):
                checksum = checksum_json(record.data)
                record.checksum = checksum
                db.session.add(record)
            db.session.commit()
            completed += idx + 1
            print(f"Record count: {completed} complete")
        db.session.commit()
    except IntegrityError as e:
        current_app.logger.error(f"IntegrityError hit while creating checksums: {e}")
        print(f"IntegrityError! {e}")
        db.session.rollback()


@records.route("/<path:entity_id>")
def entity_record(entity_id):

    record = Record.query.filter(Record.entity_id == entity_id).one_or_none()

    # if data == None, the record was deleted
    if record and record.data:
        current_app.logger.debug(request.if_none_match)
        if record.checksum in request.if_none_match:
            # Client has supplied etags of the resources it has cached for this URI
            # If the current checksum for this record matches, send back an empty response
            # using HTTP 304 Not Modified, with the etag and last modified date in the headers
            headers = {
                "Last-Modified": format_datetime(record.datetime_updated),
                "ETag": record.checksum,
            }

            if current_app.config["KEEP_LAST_VERSION"] is True:
                headers["X-Previous-Version"] = record.previous_version
                headers["X-Is-Old-Version"] = record.is_old_version
            return ("", 304, headers)

        # If the etag(s) did not match, then the record is not cached or known to the client
        # and should be sent:

        # Assemble the record 'id' attribute base URL prefix
        idPrefix = (
            current_app.config["BASE_URL"] + "/" + current_app.config["NAMESPACE"]
        )

        # Recursively prefix each 'id' attribute that currently lacks a http(s):// prefix
        prefixRecordIDs = current_app.config["PREFIX_RECORD_IDS"]
        if (
            prefixRecordIDs == "NONE"
        ):  # when "NONE", record "id" field prefixing is not enabled
            data = record.data  # so pass back the record data as-is to the client
        else:  # otherwise, record "id" field prefixing is enabled, as configured
            recursive = (
                False if prefixRecordIDs == "TOP" else True
            )  # recursive by default

            data = containerRecursiveCallback(
                data=record.data,
                attr="id",
                callback=idPrefixer,
                prefix=idPrefix,
                recursive=recursive,
            )

        response = current_app.make_response(data)
        response.headers["Content-Type"] = "application/json;charset=UTF-8"
        response.headers["Last-Modified"] = format_datetime(record.datetime_updated)
        response.headers["ETag"] = record.checksum
        if current_app.config["KEEP_LAST_VERSION"] is True:
            response.headers["X-Previous-Version"] = record.previous_version
            response.headers["X-Is-Old-Version"] = record.is_old_version
        return response
    else:
        response = construct_error_response(status_record_not_found)
        return abort(response)


### Activity Stream of the record ###


@records.route("/<path:entity_id>/activity-stream")
def entity_record_activity_stream(entity_id):
    count = get_record_activities_count(entity_id)
    limit = current_app.config["ITEMS_PER_PAGE"]
    total_pages = str(math.ceil(count / limit))

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "summary": current_app.config["AS_DESC"],
        "type": "OrderedCollection",
        "id": url_record(entity_id),
        "totalItems": count,
    }

    data["first"] = {
        "id": url_record(entity_id, 1),
        "type": "OrderedCollectionPage",
    }
    data["last"] = {
        "id": url_record(entity_id, total_pages),
        "type": "OrderedCollectionPage",
    }

    return current_app.make_response(data)


@records.route("/<path:entity_id>/activity-stream/page/<string:pagenum>")
def record_activity_stream_page(entity_id, pagenum):
    activities = get_record_activities(entity_id)
    count = len(activities)
    pagenum = int(pagenum)
    limit = current_app.config["ITEMS_PER_PAGE"]
    offset = (pagenum - 1) * limit
    total_pages = math.ceil(count / limit)
    stop = min(offset + limit, count)
    activities_curr_page = activities[offset:stop]

    if pagenum == 0 or pagenum > total_pages:
        response = construct_error_response(status_page_not_found)
        return abort(response)

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollectionPage",
        "id": url_record(entity_id, pagenum),
        "partOf": {"id": url_record(entity_id), "type": "OrderedCollection"},
    }

    if pagenum < total_pages:
        data["next"] = {
            "id": url_record(entity_id, pagenum + 1),
            "type": "OrderedCollectionPage",
        }

    if pagenum > 1:
        data["prev"] = {
            "id": url_record(entity_id, pagenum - 1),
            "type": "OrderedCollectionPage",
        }

    items = [generate_item(a) for a in activities_curr_page]
    data["orderedItems"] = items

    return current_app.make_response(data)


# Auxiliary functions


def url_base(entity_id=None):
    base_url = current_app.config["BASE_URL"]
    namespace = current_app.config["NAMESPACE"]
    url = base_url + "/" + namespace
    if entity_id:
        url = url + "/" + entity_id
    return url


def url_record(entity_id, page=None):
    url = url_base() + "/" + entity_id + "/activity-stream"
    if page:
        url = url + "/page/" + str(page)
    return url


def url_activity(id):
    return url_base() + "/activity-stream/" + id


def generate_item(activity):
    return {
        "id": url_activity(activity.uuid),
        "type": activity.event,
        "created": format_datetime(activity.datetime_created),
        "object": {
            "id": url_base(activity.record.entity_id),
            "type": activity.record.entity_type,
        },
    }


def get_record_activities(entity_id):
    return (
        (
            Activity.query.join(Record)
            .filter(Activity.record_id == Record.id)
            .filter(Record.entity_id == entity_id)
        )
        .order_by(Activity.id)
        .all()
    )


def get_record_activities_count(entity_id):
    return (
        Activity.query.join(Record)
        .filter(Activity.record_id == Record.id)
        .filter(Record.entity_id == entity_id)
    ).count()
