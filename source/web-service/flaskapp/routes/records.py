import click

from datetime import datetime, timezone
from flask import Blueprint, current_app, abort, request
from sqlalchemy.exc import IntegrityError

from flaskapp.models import db
from flaskapp.models.record import Record
from flaskapp.utilities import format_datetime, containerRecursiveCallback, idPrefixer
from flaskapp.errors import construct_error_response, status_record_not_found
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
        data = containerRecursiveCallback(
            data=record.data, attr="id", callback=idPrefixer, prefix=idPrefix
        )

        response = current_app.make_response(data)
        response.headers["Last-Modified"] = format_datetime(record.datetime_updated)
        response.headers["ETag"] = record.checksum
        if current_app.config["KEEP_LAST_VERSION"] is True:
            response.headers["X-Previous-Version"] = record.previous_version
            response.headers["X-Is-Old-Version"] = record.is_old_version
        return response
    else:
        response = construct_error_response(status_record_not_found)
        return abort(response)
