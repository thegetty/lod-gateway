import json
import re

from collections import namedtuple

from flask import Blueprint, current_app, request, abort


# Create a new "ingest" route blueprint
ingest = Blueprint("ingest", __name__)


@ingest.route("/ingest", methods=["GET"])
def ingest_get():
    """ Process 'GET' request
        Do not allow 'GET' on this route. Handle it here,
        otherwise it will go to 'records' route, producing misleading 404 error     

    """
    response = construct_error_response(status_GET_not_allowed)
    return abort(response)


@ingest.route("/ingest", methods=["POST"])
def ingest_post():

    # Authentication
    status = authenticate_bearer(request)
    if status != status_ok:
        response = construct_error_response(status)
        return abort(response)

    # Get json record list by splitting lines
    record_list = request.data.splitlines()

    # No data in request body
    if len(record_list) == 0:
        response = construct_error_response(status_data_missing)
        return abort(response)

    # Validate all records
    result = validate_ingest_record_set(record_list)

    # For now return a string if success and detailed error otherwise
    if result == True:
        return "success"
    else:
        # unpack result tuple into variables
        status, line_number = result

        # if it is a single record, don't return line number
        if len(record_list) < 2:
            line_number = None

        # create error response object
        response = construct_error_response(status, line_number)

        # return detailed error
        return abort(response)


# Construct 'error response' object
def construct_error_response(status, line_number=None):

    err = {}
    err["status"] = status.code

    # include 'line_number' only when needed
    if line_number:
        err["source"] = {"line number": line_number}

    err["title"] = status.title
    err["detail"] = status.detail
    err = [err]
    errors = {"errors": err}

    response = current_app.response_class(
        response=json.dumps(errors), mimetype="application/json", status=status.code,
    )

    return response


# Construct 'success response' object
# Will figure params and implementation later
def construct_success_response():
    pass


# Vallidation status named tuple. Note the same status code (e.g. '422')
# can be used for different errors
status_nt = namedtuple("name", "code title detail")

status_ok = status_nt(200, "OK", "OK")
status_wrong_syntax = status_nt(422, "Invalid JSON", "Could not parse JSON record")
status_id_missing = status_nt(422, "ID Missing", "ID for the JSON record not found")
status_data_missing = status_nt(422, "Data Missing", "No input data found")
status_GET_not_allowed = status_nt(
    405, "Forbidden Method", "For the requested URL only 'POST' method is allowed"
)
status_wrong_auth_token = status_nt(
    401, "Wrong Authorization Token", "Authorization token is wrong or missing"
)

# Authentication functions
def authenticate_bearer(request):

    # for now return the same error for all failing scenarios
    error = status_wrong_auth_token

    # get Authorization header token
    auth_header = request.headers.get("Authorization")

    # return error if auth header is not present
    if not auth_header:
        return error

    else:
        # get method (Bearer) and token
        method, token = auth_header.split()

        # check the method is correct
        if method != "Bearer":
            return error

        # verify token
        elif token != current_app.config["AUTH_TOKEN"]:
            return error

    return status_ok


# Validation functions
def validate_ingest_record(rec):
    """
        Validate a single json record.
        Check valid json syntax plus some other params      
    """
    try:
        # JSON syntax is good, validate other params
        data = json.loads(rec)

        # return 'id_missing' if no 'id' present
        if "id" not in data.keys():
            return status_id_missing

        # check 'id' is not empty
        if not data["id"].strip():
            return status_id_missing

        # all validations succeeded, return OK
        return status_ok

    except:
        # JSON syntax is not valid
        return status_wrong_syntax


def validate_ingest_record_set(record_list):
    """
        Validate a list of json records. 
        Break and return status if at least one record is invalid
        Return line number where the error occured
    """
    for index, rec in enumerate(record_list, start=1):
        status = validate_ingest_record(rec)
        if status != status_ok:
            return (status, index)

    else:
        return True
