import json
import hashlib

from flask import Flask, Blueprint, Response

from app.di import DI
from app.utilities import camelCasedStringFromHyphenatedString
from app.database import Database
from app.model import Record


# Create a new "records" route blueprint
records = Blueprint("records", __name__)

DEFAULT_HEADERS = {"Server": "MART/1.0", "Access-Control-Allow-Origin": "*"}


@records.route("/<string:entity>/<string:UUID>")
def obtainRecordWithDefaultNamespace(entity, UUID):

    defaultNamespace = os.getenv("LOD_DEFAULT_URL_NAMESPACE", None)
    if isinstance(defaultNamespace, str) and len(defaultNamespace) > 0:
        return obtainRecord(defaultNamespace, entity, UUID)
    else:
        return _errorResponse((500, "Unable to obtain the database handler!"))


@records.route("/<path:namespace>/<string:entity>/<string:UUID>")
def obtainRecord(namespace, entity, UUID):

    # Define our default headers to add to the response
    error = None

    database = DI.get("database")
    if database:
        connection = database.connect(autocommit=True)
        if connection:
            DI.set("connection", connection)
        else:
            error = (500, "Unable to establish a database connection!")
    else:
        error = (500, "Unable to obtain the database handler!")

    if error:
        return _errorResponse(error)

    response = None

    if entity:
        _entity = camelCasedStringFromHyphenatedString(entity)

        record = Record.findFirst(
            "namespace = :namespace: AND entity = :entity: AND uuid = :uuid:",
            bind={"namespace": namespace, "entity": _entity, "uuid": UUID},
        )
        if record:
            _updateCounter(record)

            if record.data and len(record.data) >= 0:

                body = json.dumps(
                    record.data, sort_keys=False, indent=4, ensure_ascii=False
                )
                if isinstance(body, str) and len(body) > 0:
                    body = body.encode("utf-8")

                    headers = {**{"Date": record.datetime_published}, **DEFAULT_HEADERS}

                    hasher = hashlib.sha1()
                    hasher.update(body)
                    hash = hasher.hexdigest()

                    if hash:
                        headers["E-Tag"] = hash

                    # see https://werkzeug.palletsprojects.com/en/0.15.x/wrappers/
                    response = Response(
                        body,
                        status=200,
                        content_type="application/ld+json;charset=UTF-8",
                        headers=DEFAULT_HEADERS,
                    )
                else:
                    error = (404, "The result.data could not be serialized to JSON!")
            else:
                error = (404, "The result.data attribute is empty!")
        else:
            error = (404, "Unable to obtain matching record from database!")
    else:
        error = (400, "No valid entity type name was specified!")

    database.disconnect(connection=connection)

    if error:
        return _errorResponse(error)

    return response


def _errorResponse(error):
    return Response(
        error[1], status=error[0], headers={**{"X-Error": error[1]}, **DEFAULT_HEADERS}
    )


def _updateCounter(record):
    if isinstance(record.counter, int):
        record.counter += 1
    else:
        record.counter = 1
    record.update(quietly=True)
