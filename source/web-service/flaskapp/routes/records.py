from flask import Blueprint, current_app

from app.utilities import camelCasedStringFromHyphenatedString
from flaskapp.models import Record
from flaskapp.utilities import error_response, validate_namespace

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

        # TODO: This is spec-compliant, but the time is not actually GMT.
        response.headers["Last-Modified"] = record.datetime_updated.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
    else:
        response = error_response(
            (404, "Unable to obtain matching record from database!")
        )

    return response
