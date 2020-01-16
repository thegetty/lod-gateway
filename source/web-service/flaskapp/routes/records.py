from datetime import datetime, timezone

from flask import Blueprint, current_app

from flaskapp.models import Record
from flaskapp.utilities import (
    error_response,
    validate_namespace,
    camelCasedStringFromHyphenatedString,
)


# Create a new "records" route blueprint
records = Blueprint("records", __name__)


@records.route("/<string:entity>/<string:UUID>", defaults={"namespace": None})
@records.route("/<path:namespace>/<string:entity>/<string:UUID>")
def entity_record(namespace, entity, UUID):
    """Generate a page for a cached record

    Args:
        namespace (String): The namespace of record
        entity (String): The entity type
        UUID (String): The identifier for the record

    Returns:
        Response: The JSON-encoded record
    """
    namespace = validate_namespace(namespace)

    record = (
        Record.query.filter(Record.uuid == UUID)
        .filter(Record.namespace == namespace)
        .filter(Record.entity == camelCasedStringFromHyphenatedString(entity))
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
    else:
        response = error_response(
            (404, "Unable to obtain matching record from database!")
        )

    return response
