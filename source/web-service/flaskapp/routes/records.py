from flask import Blueprint, current_app

from app.utilities import camelCasedStringFromHyphenatedString
from flaskapp.models import Records
from flaskapp.routes.utilities import errorResponse, DEFAULT_HEADERS

# Create a new "records" route blueprint
records = Blueprint("records", __name__)


@records.route("/<string:entity>/<string:UUID>", defaults={"namespace": None})
@records.route("/<path:namespace>/<string:entity>/<string:UUID>")
def obtainRecord(namespace, entity, UUID):

    if not namespace:
        namespace = current_app.config["DEFAULT_URL_NAMESPACE"]

    record = (
        Records.query.filter(Records.uuid == UUID)
        .filter(Records.namespace == namespace)
        .filter(Records.entity == camelCasedStringFromHyphenatedString(entity))
        .first()
    )

    if record and record.data:
        response = current_app.make_response((record.data, 200, DEFAULT_HEADERS))

        # TODO: This is spec-compliant, but the time is not actually GMT.
        response.headers["Last-Modified"] = record.datetime_updated.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
    else:
        response = errorResponse(
            (404, "Unable to obtain matching record from database!")
        )

    return response
