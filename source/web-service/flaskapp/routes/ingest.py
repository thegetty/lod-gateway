import json

from flask import Blueprint, request, abort

from collections import namedtuple


# Create a new "ingest" route blueprint
ingest = Blueprint("ingest", __name__)


@ingest.route("/ingest", methods=["GET"])
def ingest_get():
    """ Process 'GET' request
        Do not allow 'GET' on this route. Handle it here,
        otherwise it will go to 'records' route, producing misleading 404 error     

    """
    return abort(status_GET_not_allowed.code, description=status_GET_not_allowed.detail)


@ingest.route("/ingest", methods=["POST"])
def ingest_post():

    # Get json record list by splitting lines
    record_list = request.data.splitlines()

    # No data in request body
    if len(record_list) == 0:
        return abort(status_data_missing.code, description=status_data_missing.detail)

    # Validate all records
    result = validate_ingest_record_set(record_list)

    # For now return a string if success and detailed error otherwise
    if result == True:
        return "success"
    else:
        return abort(
            result[0].code,
            description="Record on line " + str(result[1]) + ": " + result[0].detail,
        )


# Vallidation status named tuple. Note the same status code (e.g. '422')
# can be used for different errors
status_nt = namedtuple("name", "code detail")

status_ok = status_nt(200, "Ok")
status_wrong_syntax = status_nt(422, "Could not parse JSON record")
status_id_missing = status_nt(422, "ID for the JSON record not found")
status_data_missing = status_nt(422, "No input data found")
status_GET_not_allowed = status_nt(
    405, "For the requested URL only 'POST' method is allowed"
)


# Validation functions
def validate_ingest_record(rec):
    """
        Validate a single json record.
        Check valid json syntax plus some other params      
    """
    try:
        # if json syntax is good, validate other params
        data = json.loads(rec)

        # currently just the 'id'; in the future can be more
        # check 'id' is present in the record
        if "id" not in data.keys():
            return status_id_missing

        # return True if all validations passed, False - otherwise
        return status_ok

    except:
        # json syntax is not valid
        return status_wrong_syntax


def validate_ingest_record_set(record_list):
    """
        Validate a list of json records. 
        Break and return status if at least one record is invalid
        Return line number where the error occured
    """
    counter = 0
    for rec in record_list:
        counter += 1
        status = validate_ingest_record(rec)
        if status != status_ok:
            return (status, counter)

    else:
        return True
