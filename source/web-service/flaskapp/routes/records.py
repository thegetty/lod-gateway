from datetime import datetime, timezone

from flask import Blueprint, current_app

from flaskapp.models.record import Record
from flaskapp.utilities import camel_case


# Create a new "records" route blueprint
records = Blueprint("records", __name__)


@records.route("/<string:entity>/<string:UUID>")
def entity_record(entity, UUID):
    """Generate a page for a cached record

    Args:
        namespace (String): The namespace of record
        entity (String): The entity type
        UUID (String): The identifier for the record

    Returns:
        Response: The JSON-encoded record
    """

    record = (
        Record.query.filter(Record.uuid == UUID)
        .filter(Record.entity == camel_case(entity))
        .first()
    )

    if record and record.data:
        response = current_app.make_response(record.data)

        if record.datetime_updated:  # Use 'datetime_updated' for updated records...
            last_modified = record.datetime_updated
        else:  # Or use 'datetime_created' for newly created records...
            last_modified = record.datetime_created

        # Adjust the timezone to UTC equivalent to GMT so that the date is correctly serialized
        response.headers["Last-Modified"] = last_modified.astimezone(
            timezone.utc
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")
        return response
    else:
        return current_app.make_response(
            ("Unable to obtain matching record from database!", 404)
        )
