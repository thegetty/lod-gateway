import json

from flask import Blueprint, current_app, request, abort

from flaskapp.errors import (
    status_ok,
    status_data_missing,
    status_GET_not_allowed,
    status_id_missing,
    status_wrong_auth_token,
    status_wrong_syntax,
    construct_error_response,
)


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
