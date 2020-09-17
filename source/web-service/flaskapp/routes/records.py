from datetime import datetime, timezone

from flask import Blueprint, current_app, abort, request

from flaskapp.models.record import Record
from flaskapp.utilities import format_datetime, containerRecursiveCallback, idPrefixer
from flaskapp.errors import construct_error_response, status_record_not_found


# Create a new "records" route blueprint
records = Blueprint("records", __name__)


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
            return ("", 304, headers)

        # If the etag(s) did not match, then the record is not cached or known to the client
        # and should be sent:

        # Assemble the record 'id' attribute base URL prefix
        idPrefix = (
            current_app.config["BASE_URL"] + "/" + current_app.config["NAMESPACE"]
        )

        # Recursively prefix each 'id' attribute that currently lacks a http(s):// prefix
        data = containerRecursiveCallback(
            data=record.data, attr="id", callback=idPrefixer, prefix=idPrefix
        )

        response = current_app.make_response(data)
        response.headers["Last-Modified"] = format_datetime(record.datetime_updated)
        response.headers["ETag"] = record.checksum
        return response
    else:
        response = construct_error_response(status_record_not_found)
        return abort(response)
