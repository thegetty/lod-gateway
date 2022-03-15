from email.utils import formatdate

from flask import Blueprint, current_app, abort, request, jsonify, url_for
from sqlalchemy.exc import IntegrityError

from flaskapp.models import db
from flaskapp.models.record import Record, Version
from flaskapp.utilities import format_datetime
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
    current_app.logger.info(f"Looking up timemap for entity {entity_id}")
    record = Record.query.filter(Record.entity_id == entity_id).one_or_none()

    # if there is no record, return 404
    if record is None:
        response = construct_error_response(status_record_not_found)
        return abort(response)

    # Memento URI-R:
    uri_r = f"{idPrefix}{ url_for('records.entity_record', entity_id=entity_id) }"

    # This URI-T
    uri_t = f"{idPrefix}{ url_for('timegate.get_timemap', entity_id=entity_id) }"

    # Timemap
    # If Accept: application/link-format -> application/link-format https://www.ietf.org/rfc/rfc5988.txt
    # Otherwise: application/json
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
    timemap.append({"uri": uri_r, "rel": "original"})

    num_versions = len(record.versions)
    if num_versions == 1:
        # spec doesn't really talk about how to format in this case
        timemap.append(
            {
                "uri": f"{idPrefix}{ url_for('records.entity_version', entity_id=record.versions[0].entity_id) }",
                "datetime": formatdate(
                    timeval=record.versions[0].datetime_updated.timestamp(),
                    localtime=False,
                    usegmt=True,
                ),
                "rel": "first last memento",
            }
        )
    elif num_versions > 1:
        for idx, version in enumerate(record.versions):
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
                # Should be an ordered list from the DB, first as newest
                mm["rel"] = "first memento"
            elif num_versions - idx == 1:
                mm["rel"] = "last memento"
                # mark timemap with until datetime
                timemap[0]["from"] = format_datetime(version.datetime_updated)
            timemap.append(mm)

    # Accept?
    if "application/link-format" in request.headers.get("Accept", "application/json"):
        lf = ",\n".join([json_to_linkformat(x) for x in timemap])
        response = current_app.make_response(lf)
        response.content_type = "applcation/link-format"
        response.content_encoding = "utf-8"
        return response
    else:
        return jsonify(timemap), 200
