import json

from flask import Blueprint, request, abort

from flaskapp.IngestClasses import IngestRecord


# Create a new "ingest" route blueprint
ingest = Blueprint("ingest", __name__)


@ingest.route("/ingest", methods=["GET"])
def ingest_get():
    """ Process 'GET' request
        Do not allow 'GET' on this route. Handle it here,
        otherwise it will go to 'records' route, producing misleading 404 error     

    """
    return abort(405)


@ingest.route("/ingest", methods=["POST"])
def ingest_post():

    # Get json record list by splitting lines
    json_string_list = request.data.splitlines()

    # Validate all records
    result = validate_ingest_record_set(json_string_list)

    # For now return a string if success
    if result == True:
        return "success"
    else:
        return abort(result.code)


def validate_ingest_record_set(json_string_list):
    for json_str in json_string_list:
        ingest_rec = IngestRecord(json_str)
        status = ingest_rec.validate()
        if status != IngestRecord.status_ok:
            return status

    else:
        return True
