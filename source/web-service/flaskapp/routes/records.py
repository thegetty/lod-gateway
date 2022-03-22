import click
import math

# RFC1128 dates, yuck
import dateparser
from email.utils import formatdate

from datetime import datetime, timezone
from flask import Blueprint, current_app, abort, request, jsonify, url_for, redirect
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import load_only
from sqlalchemy import func

from flaskapp.models import db
from flaskapp.models.record import Record, Version
from flaskapp.models.activity import Activity
from flaskapp.utilities import format_datetime, containerRecursiveCallback, idPrefixer
from flaskapp.errors import (
    construct_error_response,
    status_record_not_found,
    status_page_not_found,
    status_ok,
)
from flaskapp.utilities import checksum_json

# authentication function from ingest. This really should be changed at some point to a
# better library like JWT
from flaskapp.routes.ingest import authenticate_bearer


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


def _quick_count(query):
    count_q = query.statement.with_only_columns([func.count()]).order_by(None)
    count = query.session.execute(count_q).scalar()
    return count


@records.route("/<path:entity_id>")
def entity_record(entity_id):
    """GET the record that exactly matches the entity_id, or if the entity_id ends with a '*', treat it as a wildcard
    search for items in the LOD Gateway"""

    # idPrefix will be used by either the API route returning the record, or the route listing matches
    hostPrefix = current_app.config["BASE_URL"]
    idPrefix = hostPrefix + "/" + current_app.config["NAMESPACE"]
    if entity_id.endswith("*"):
        # Instead of responding with a single record, find and list the responses that match the 'glob' in the request
        # load_only - we only care about three columns.
        records = (
            Record.query.options(
                load_only(
                    Record.entity_id,
                    Record.entity_type,
                    Record.datetime_updated,
                    Record.datetime_deleted,
                )
            )
            .filter(Record.datetime_deleted == None)
            .filter(Record.entity_id.like(entity_id[:-1] + "%"))
        )
        # Pagination - GET URL parameter 'page'
        page = 1
        if "page" in request.args:
            try:
                page = int(request.args["page"])
            except (ValueError, TypeError) as e:
                current_app.logger.error(f"Bad value supplied for 'page' parameter.")

        # BROWSE_PAGE_SIZE - optional app config value
        page_size = 200
        try:
            page_size = int(current_app.config["BROWSE_PAGE_SIZE"])
        except (ValueError, TypeError, KeyError) as e:
            current_app.logger.warning(
                f"Bad value supplied for BROWSE_PAGE_SIZE environment var."
            )

        # Use SQLAlchemy's inbuilt pagination routine
        page_request = records.paginate(page=page, per_page=page_size)

        # Do a quick count based on the query. Might not be that much quicker than .count() with the load_only
        # option above, but this way is the quickest method for doing a count.
        total = _quick_count(records)

        # Return the URL, the entity type and the datetime_updated
        # (Maybe sort by the date?)
        items = [
            {
                "id": f"{idPrefix}/{item.entity_id}",
                "type": item.entity_type,
                "datetime_updated": item.datetime_updated,
            }
            for item in page_request.items
        ]

        r_json = {
            "items": items,
            "total": total,
            "first": f"{idPrefix}/{entity_id}?page=1",
        }

        # Pagination will be in the usual "first", "prev", "next" pattern
        if page_request.has_next is True:
            r_json["next"] = f"{idPrefix}/{entity_id}?page={page+1}"
            r_json["last"] = f"{idPrefix}/{entity_id}?page={math.ceil(total/page_size)}"
        if page > 1:
            r_json["prev"] = f"{idPrefix}/{entity_id}?page={page-1}"

        return jsonify(r_json)
    else:
        record = Record.query.filter(Record.entity_id == entity_id).one_or_none()
        current_app.logger.info(f"Looking up resource {entity_id}")

        if record is None:
            # no record, not even a stub:
            response = construct_error_response(status_record_not_found)
            return abort(response)

        prev = None
        if record is not None and len(record.versions) > 0:

            # Ordered in reverse chronological order.
            prev = record.versions[0]

        link_headers = basic_link_headers = (
            f'<{hostPrefix}{ url_for("timegate.get_timemap", entity_id=record.entity_id) }>; rel="timemap"; type="application/link-format" , '
            + f'<{hostPrefix}{ url_for("timegate.get_timemap", entity_id=record.entity_id) }>; rel="timemap"; type="application/json" , '
            + f'<{hostPrefix}{ url_for("records.entity_record", entity_id=record.entity_id) }>; rel="original timegate" '
        )

        if prev is not None:
            link_headers = (
                basic_link_headers
                + f', <{hostPrefix}{ url_for("records.entity_version", entity_id=prev.entity_id) }>; rel="prev"'
            )

        # Is the client trying to negotiate for an earlier version through Accept-Datetime
        if (
            record is not None
            and current_app.config["KEEP_LAST_VERSION"] is True
            and "accept-datetime" in request.headers
        ):
            # parse date and try to find a matching version, 302 redirect
            desired_datetime = dateparser.parse(request.headers["accept-datetime"])

            # Valid datetime and asking for a datetime older than the current version?
            if desired_datetime is not None and not (
                desired_datetime >= record.datetime_updated
            ):
                desired_version = (
                    db.session.query(Version)
                    .filter(Version.record == record)
                    .filter(Version.datetime_updated <= desired_datetime)
                    .order_by(Version.datetime_updated.desc())
                    .limit(1)
                    .one_or_none()
                )
                if desired_version is None:
                    # Return oldest version URL
                    desired_version = record.versions[-1]

                # found an version predating the version asked for
                # 302 Redirect to that version.
                response = redirect(
                    url_for(
                        "records.entity_version", entity_id=desired_version.entity_id,
                    ),
                    code=302,
                )
                response.headers["Link"] = basic_link_headers
                response.headers["Vary"] = "accept-datetime"

                return response

        # Otherwise, supply the current record.
        if record and record.data:
            current_app.logger.debug(request.if_none_match)
            if record.checksum in request.if_none_match:
                # Client has supplied etags of the resources it has cached for this URI
                # If the current checksum for this record matches, send back an empty response
                # using HTTP 304 Not Modified, with the etag and last modified date in the headers
                headers = {
                    "Last-Modified": format_datetime(record.datetime_updated),
                    "ETag": f'"{record.checksum}"',
                }

                if current_app.config["KEEP_LAST_VERSION"] is True:
                    # Timemap and prev (optional) link
                    headers["Link"] = link_headers
                    headers["Vary"] = "accept-datetime"
                return ("", 304, headers)

            # If the etag(s) did not match, then the record is not cached or known to the client
            # and should be sent:

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
            response.headers["ETag"] = f'"{record.checksum}"'
            if current_app.config["KEEP_LAST_VERSION"] is True:
                # Timemap
                response.headers["Link"] = link_headers
                response.headers["Vary"] = "accept-datetime"
            return response
        elif record and record.data is None:
            # Record existed but has been deleted.
            response = construct_error_response(status_record_not_found)
            if current_app.config["KEEP_LAST_VERSION"] is True:
                response.headers["Link"] = link_headers
                response.headers["Vary"] = "accept-datetime"
            return abort(response)
        else:
            response = construct_error_response(status_record_not_found)
            return abort(response)


# old version of a record
@records.route("/-VERSION-/<path:entity_id>", methods=["GET", "HEAD"])
def entity_version(entity_id):
    # Authentication. If fails, abort with 401
    status = authenticate_bearer(request)
    if status != status_ok:
        response = construct_error_response(status)
        return abort(response)

    if current_app.config["KEEP_LAST_VERSION"] is True:
        """GET the version that exactly matches the id supplied"""

        # idPrefix will be used by either the API route returning the record, or the route listing matches
        hostPrefix = current_app.config["BASE_URL"]
        idPrefix = hostPrefix + "/" + current_app.config["NAMESPACE"]

        version = Version.query.filter(Version.entity_id == entity_id).one_or_none()

        if version is not None:
            # There is a record of a version of a resource here. The record is available through version.record
            current_app.logger.debug(
                "Version -- If-None-Match header: " + str(request.if_none_match)
            )
            if version.checksum in request.if_none_match:
                # Client has supplied etags of the resources it has cached for this URI
                # If the current checksum for this record matches, send back an empty response
                # using HTTP 304 Not Modified, with the etag and last modified date in the headers
                headers = {
                    "Last-Modified": format_datetime(version.datetime_updated),
                    "ETag": f'"{version.checksum}"',
                }

                headers["Memento-Datetime"] = formatdate(
                    timeval=version.datetime_updated.timestamp(),
                    localtime=False,
                    usegmt=True,
                )
                # TODO update URI when TIME MAP API is in place.
                headers["Link"] = " , ".join(
                    [
                        f'<{idPrefix}/{version.record.entity_id}>; rel="original timegate"',
                        f'<{hostPrefix}{ url_for("timegate.get_timemap", entity_id=version.record.entity_id) }> ; rel="timemap"',
                    ]
                )
                return ("", 304, headers)

            # If the etag(s) did not match, then the record is not cached or known to the client
            # and should be sent:

            # Recursively prefix each 'id' attribute that currently lacks a http(s):// prefix
            data = version.data
            if data is not None:
                prefixRecordIDs = current_app.config["PREFIX_RECORD_IDS"]
                if (
                    prefixRecordIDs != "NONE"
                ):  # when "NONE", record "id" field prefixing is not enabled
                    # otherwise, record "id" field prefixing is enabled, as configured
                    recursive = (
                        False if prefixRecordIDs == "TOP" else True
                    )  # recursive by default

                    data = containerRecursiveCallback(
                        data=data,
                        attr="id",
                        callback=idPrefixer,
                        prefix=idPrefix,
                        recursive=recursive,
                    )

            response = current_app.make_response(data or "")
            response.headers["Content-Type"] = "application/json;charset=UTF-8"
            response.headers["Last-Modified"] = format_datetime(
                version.datetime_updated
            )
            response.headers["Memento-Datetime"] = formatdate(
                timeval=version.datetime_updated.timestamp(),
                localtime=False,
                usegmt=True,
            )
            response.headers["ETag"] = f'"{version.checksum}"'
            response.headers["Link"] = " , ".join(
                [
                    f'<{idPrefix}/{version.record.entity_id}>; rel="original timegate"',
                    f'<{hostPrefix}{ url_for("timegate.get_timemap", entity_id=version.record.entity_id) }> ; rel="timemap"',
                ]
            )
            if data is None:
                response.status_code = 404
            return response
        else:
            response = construct_error_response(status_record_not_found)
            return abort(response)
    else:
        response = construct_error_response(
            status_nt(405, "Method not Allowed", "Versioning has been disabled.")
        )
        return response


# old version of a record
@records.route("/-VERSION-/<path:entity_id>", methods=["DELETE"])
def delete_entity_version(entity_id):
    # Authentication. If fails, abort with 401
    status = authenticate_bearer(request)
    if status != status_ok:
        response = construct_error_response(status)
        return abort(response)

    if current_app.config["KEEP_LAST_VERSION"] is True:
        """GET the version that exactly matches the id supplied"""

        # idPrefix will be used by either the API route returning the record, or the route listing matches
        hostPrefix = current_app.config["BASE_URL"]
        idPrefix = hostPrefix + "/" + current_app.config["NAMESPACE"]

        version = Version.query.filter(Version.entity_id == entity_id).one_or_none()

        if version is None:
            response = construct_error_response(status_record_not_found)
            return abort(response)

        try:
            current_app.logger.warning(
                f"Deleting version '-VERSION-/{entity_id}' as requested."
            )
            db.session.delete(version)
            db.session.commit()
            return jsonify({"message": f"-VERSION-/{entity_id} deleted."}), 200
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Hit an error attempting to delete -VERSION-/{entity_id}"
            )
            current_app.logger.error(e)
            response = construct_error_response(status_db_error)
            return abort(response)


### Activity Stream of the record ###


@records.route("/<path:entity_id>/activity-stream", methods=["GET", "HEAD"])
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

    data["first"] = {"id": url_record(entity_id, 1), "type": "OrderedCollectionPage"}
    data["last"] = {
        "id": url_record(entity_id, total_pages),
        "type": "OrderedCollectionPage",
    }

    return current_app.make_response(data)


@records.route("/<path:entity_id>/activity-stream", methods=["POST"])
def truncate_activity_stream_of_entity_id(entity_id):
    # Authentication. If fails, abort with 401
    status = authenticate_bearer(request)
    if status != status_ok:
        response = construct_error_response(status)
        return abort(response)

    count = get_record_activities_count(entity_id)
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


@records.route("/<path:entity_id>/activity-stream/page/<string:pagenum>")
def record_activity_stream_page(entity_id, pagenum):
    count = get_record_activities_count(entity_id)
    pagenum = int(pagenum)
    limit = current_app.config["ITEMS_PER_PAGE"]
    offset = (pagenum - 1) * limit
    total_pages = math.ceil(count / limit)
    activities = get_record_activities(entity_id, offset, limit)

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

    items = [generate_item(a) for a in activities]
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
        "endTime": format_datetime(activity.datetime_created),
        "object": {"id": url_base(activity.entity_id), "type": activity.entity_type},
    }


def get_record_activities(entity_id, offset, limit):
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


def get_record_activities_count(entity_id):
    return (Activity.query.join(Record).filter(Record.entity_id == entity_id)).count()
