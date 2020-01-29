from flask import Blueprint, request, abort

from flaskapp.utilities import validate_ingest_record_set


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
    record_list = request.data.splitlines()

    # Validate all records
    result = validate_ingest_record_set(record_list)

    # For now return a string if success
    if result == True:
        return "success"
    else:
        return abort(422)
