import sys
import datetime
import json
import hashlib

# Import the utility functions (commandOptions, get, has, put, debug, repeater, etc)
from app.utilities import *

# Import the dependency injector
from app.di import DI

# Import the database service handler
from app.database import Database

# Import the data model
from app.model import *

# Import the Flask web framework
from flask import Flask, Blueprint, Response

# Create a new "records" route blueprint
records = Blueprint("records", __name__)


@records.route("/<string:entity>/<string:UUID>")
def obtainRecordWithDefaultNamespace(entity, UUID):
    debug(
        "obtainRecordWithDefaultNamespace(entity: %s; uuid: %s) called..."
        % (entity, UUID),
        level=1,
    )

    defaultNamespace = os.getenv("LOD_DEFAULT_URL_NAMESPACE", None)
    if isinstance(defaultNamespace, str) and len(defaultNamespace) > 0:
        response = obtainRecord(defaultNamespace, entity, UUID)
    else:
        response = Response(
            status=404,
            headers={
                **{
                    "X-Error": "Unable to obtain matching record from database as no namespace has been defined!"
                },
                **headers,
            },
        )

    return response


@records.route("/<path:namespace>/<string:entity>/<string:UUID>")
def obtainRecord(namespace, entity, UUID):
    debug(
        "obtainRecord(namespace: %s, entity: %s; uuid: %s) called..."
        % (namespace, entity, UUID),
        level=1,
    )

    # return sprintf("You requested Namespace: %s for Entity: %s with UUID: %s" % (namespace, entity, UUID))

    # Define our default headers to add to the response
    headers = {"Server": "MART/1.0", "Access-Control-Allow-Origin": "*"}

    database = DI.get("database")
    if database:
        connection = database.connect(autocommit=True)
        if connection:
            DI.set("connection", connection)
        else:
            return Response(
                status=500,
                headers={
                    **{"X-Error": "Unable to establish a database connection!"},
                    **headers,
                },
            )
    else:
        return Response(
            status=500,
            headers={
                **{"X-Error": "Unable to obtain the database handler!"},
                **headers,
            },
        )

    response = None

    if entity:
        _entity = camelCasedStringFromHyphenatedString(entity)

        debug("Will now perform lookup for %s with UUID: %s" % (_entity, UUID), level=2)

        record = Record.findFirst(
            "namespace = :namespace: AND entity = :entity: AND uuid = :uuid:",
            bind={"namespace": namespace, "entity": _entity, "uuid": UUID},
        )
        if record:
            debug(record, level=3)

            if isinstance(record.counter, int):
                record.counter += 1
            else:
                record.counter = 1

            record.update(quietly=True)

            if record.data and len(record.data) >= 0:
                # response = sprintf("Found record in the database with ID: %d of type %s" % (record.id, type(record.data)))

                body = json.dumps(
                    record.data, sort_keys=False, indent=4, ensure_ascii=False
                )
                if isinstance(body, str) and len(body) > 0:
                    body = body.encode("utf-8")

                    headers = {**{"Date": record.datetime_published}, **headers}

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
                        headers=headers,
                    )
                else:
                    debug(
                        "The result.data could not be serialized to JSON!", error=True
                    )

                    response = Response(
                        status=404,
                        headers={
                            **{
                                "X-Error": "The result.data could not be serialized to JSON!"
                            },
                            **headers,
                        },
                    )
            else:
                debug("The result.data attribute is empty!", error=True)

                response = Response(
                    status=404,
                    headers={
                        **{"X-Error": "The result.data attribute is empty!"},
                        **headers,
                    },
                )
        else:
            debug("Unable to obtain matching record from database!", error=True)

            response = Response(
                status=404,
                headers={
                    **{"X-Error": "Unable to obtain matching record from database!"},
                    **headers,
                },
            )
    else:
        debug("No valid entity type name was specified!", error=True)

        response = Response(
            "Bad Request",
            status=400,
            headers={
                **{"X-Error": "No valid entity type name was specified!"},
                **headers,
            },
        )

    database.disconnect(connection=connection)

    return response
