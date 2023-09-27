from email.utils import formatdate

from flask import Blueprint, current_app, abort, request, jsonify, url_for
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import defer, load_only

from flaskapp.models import db
from flaskapp.models.record import Record, Version
from flaskapp.utilities import format_datetime, requested_linkformat
from flaskapp.errors import (
    construct_error_response,
    status_record_not_found,
)

# Create a new "sparql" route blueprint
timegate = Blueprint("timegate", __name__)


def json_to_linkformat(d):
    lf = [f"<{d['uri']}>"]
    lf += [f'{k}="{v}"' for k, v in d.items() if k not in ["uri"]]
    return ";".join(lf)


@timegate.route("/-tm-/<path:entity_id>")
def get_timemap(entity_id):
    # Get the timemap for the given entity_id, if one exists
    idPrefix = current_app.config["BASE_URL"]
    mementoformat = current_app.config["MEMENTO_PREFERRED_FORMAT"]
    current_app.logger.info(f"Looking up timemap for entity {entity_id}")
    record = (
        Record.query.filter(Record.entity_id == entity_id)
        .options(load_only("entity_id", "id", "datetime_updated"))
        .limit(1)
        .first()
    )

    # if there is no record, return 404
    if record is None:
        response = construct_error_response(status_record_not_found)
        return abort(response)

    # Memento URI-R:
    uri_r = f"{idPrefix}{ url_for('records.entity_record', entity_id=entity_id) }"

    # This URI-T
    uri_t = f"{idPrefix}{ url_for('timegate.get_timemap', entity_id=entity_id) }"

    # Timemap formatting
    # no browser understands link-format, and it's a pain of a format. A JSON-encoded version is
    # offered for ease of use.

    # If Accept: application/json or application/link-format (https://datatracker.ietf.org/doc/html/rfc6690#section-2)
    # Default can be set using the "MEMENTO_PREFERRED_FORMAT" environment variable.
    # MUST URI-T as rel "timemap"
    # MUST URI-R as rel "original"
    # and MUST each URI-M (Version)
    timemap = []
    timemap.append(
        {
            "uri": uri_t,
            "rel": "self",
            "until": formatdate(
                timeval=record.datetime_updated.timestamp(),
                localtime=False,
                usegmt=True,
            ),
        }
    )
    timemap.append({"uri": uri_r, "rel": "original timegate"})

    versions = (
        db.session.query(Version)
        .options(load_only("record_id", "entity_id", "datetime_updated"))
        .filter(Version.record_id == record.id)
        .order_by(Version.datetime_updated.desc())
        .all()
    )

    num_versions = len(versions)
    if num_versions == 1:
        # spec doesn't really talk about how to format in this case
        timemap.append(
            {
                "uri": f"{idPrefix}{ url_for('records.entity_version', entity_id=versions[0].entity_id) }",
                "datetime": formatdate(
                    timeval=versions[0].datetime_updated.timestamp(),
                    localtime=False,
                    usegmt=True,
                ),
                "rel": "first last memento",
            }
        )
    elif num_versions > 1:
        for idx, version in enumerate(versions):
            mm = {
                "uri": f"{idPrefix}{ url_for('records.entity_version', entity_id=version.entity_id) }",
                "datetime": formatdate(
                    timeval=version.datetime_updated.timestamp(),
                    localtime=False,
                    usegmt=True,
                ),
                "rel": "memento",
            }
            if idx == 0:
                # Should be an ordered list from the DB, last as newest
                mm["rel"] = "last memento"
            elif num_versions - idx == 1:
                # last in list will be the oldest - 'first' is the correct type
                mm["rel"] = "first memento"
                # mark timemap with until datetime
                timemap[0]["from"] = formatdate(
                    timeval=version.datetime_updated.timestamp(),
                    localtime=False,
                    usegmt=True,
                )
            timemap.append(mm)

    # Response format? config['MEMENTO_PREFERRED_FORMAT'] for the default
    requested_fmt = requested_linkformat(request, mementoformat)
    current_app.logger.debug(
        f"Accept: {request.headers.get('accept')}, pref: {mementoformat}, tm format decision: {requested_fmt}"
    )
    if requested_fmt == "application/json":
        return jsonify(timemap), 200
    else:
        lf = " , \n".join([json_to_linkformat(x) for x in timemap])
        response = current_app.make_response(lf)
        response.content_type = "application/link-format;charset=utf-8"
        response.mimetype = "application/link-format"
        response.status_code = 200
        response.content_encoding = "utf-8"
        response.content_location = uri_t
        response.location = uri_t
        return response
