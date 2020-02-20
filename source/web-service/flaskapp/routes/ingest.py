import json
import uuid
from datetime import datetime

from flask import Blueprint, current_app, request, abort, jsonify

from flaskapp.models import db
from flaskapp.models.record import Record
from flaskapp.models.activity import Activity
from flaskapp.errors import (
    status_nt,
    status_data_missing,
    status_db_error,
    status_db_save_error,
    status_GET_not_allowed,
    status_id_missing,
    status_ok,
    status_wrong_auth_token,
    status_wrong_syntax,
    construct_error_response,
)


# Create a new "ingest" route blueprint
ingest = Blueprint("ingest", __name__)


# 'GET' method is forbidden. Abort with 405
@ingest.route("/ingest", methods=["GET"])
def ingest_get():
    response = construct_error_response(status_GET_not_allowed)
    return abort(response)


@ingest.route("/ingest", methods=["POST"])
def ingest_post():

    # Authentication. If fails, abort with 401
    status = authenticate_bearer(request)
    if status != status_ok:
        response = construct_error_response(status)
        return abort(response)

    # Get json record list by splitting lines
    record_list = request.data.splitlines()

    # No data in request body, abort with 422
    if len(record_list) == 0:
        response = construct_error_response(status_data_missing)
        return abort(response)

    # Validation
    validates = validate_record_set(record_list)

    # validation error
    if validates != True:

        # unpack result tuple into variables
        status, line_number = validates

        # if it is a single record, don't return line number
        if len(record_list) < 2:
            line_number = None

        # create error response object
        response = construct_error_response(status, line_number)

        # return detailed error
        return abort(response)

    # Process record set to create/update/delete in Record, Activities and Neptune
    result = process_record_set(record_list)

    # the result is an error (derived from 'status_nt'). Abort with 503
    if isinstance(result, status_nt):
        response = construct_error_response(result)
        return abort(response)

    # finished normally - return 200 and result dict
    return jsonify(result), 200


# CRUD FUNCTIONS
def process_record_set(record_list):
    """
        Process the record set in a loop. Wrap into 'try-except'. 
        Roll back and abort with 503 if any of 3 operations: 
        Record, Activity or Neptune fails.        
    """

    #  this dict will be returned by function. key: 'id', value: 'namespace/id'
    result_dict = {}

    try:
        for rec in record_list:

            # 'prim_key' - primary key (integer) returned by db. Used in Activities
            # 'id' - string ID submitted by client. Used in result dict
            # 'crud' - one of 3 operations ('create', 'update', 'delete')
            prim_key, id, crud = process_record(rec)

            # process activities based on returned Record's primary key
            process_activity(prim_key, crud)

            # add pair of IDs to result dict
            result_dict[id] = f'{current_app.config["NAMESPACE"]}/{id}'

    except BaseException as e:
        db.session.rollback()
        return status_db_save_error

    # process Neptune entries
    neptune_result = process_neptune_record_set(record_list)

    # if success, commit the whole transaction
    if neptune_result == True:
        db.session.commit()

    # if Neptune fails, roll back
    else:
        db.session.rollback()
        return status_db_save_error

    # everything went fine
    return result_dict


def process_record(input_rec):
    """
        Process a single record. Return 3 values which are not available
        in the calling function: primary key, string 'id' and operation type
        {'create', 'update' or 'delete'}

    """
    data = json.loads(input_rec)
    id = data["id"]

    # find if Record with this 'id' exists
    db_rec = get_record(id)

    # record with such 'id' does not exist. Create and return primary key for Activities
    if db_rec == None:
        prim_key = record_create(data)

        # 'prim_id' - primary 'id' created by db
        # return record 'id' since it is not known to calling function
        # 'create' - return the exect CRUD operation (createed in this case)
        return (prim_key, id, "create")

    # record exists
    else:
        # get primary key of existing record
        prim_key = db_rec.id

        # delete
        if "_delete" in data.keys() and data["_delete"] == "true":
            record_delete(db_rec, data)
            return (prim_key, id, "delete")

        # update
        else:
            record_update(db_rec, data)
            return (prim_key, id, "update")


def process_activity(prim_key, crud):
    a = Activity()
    a.uuid = uuid.uuid1()
    a.datetime_created = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    a.namespace = current_app.config["NAMESPACE"]
    a.entity = "entity"
    a.record_id = prim_key
    a.event = crud
    db.session.add(a)


def get_record(rec_id):
    result = Record.query.filter(Record.uuid == rec_id).one_or_none()
    return result


# There is no entry with this 'id'. Create a new record
def record_create(input_rec):
    r = Record()
    r.uuid = input_rec["id"]
    r.datetime_created = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    r.namespace = current_app.config["NAMESPACE"]
    r.data = input_rec
    r.entity = "Entity"

    db.session.add(r)
    db.session.flush()

    # primary key of the newly created record
    return r.id


# Do not return anything. Calling function has all the info
def record_update(db_rec, input_rec):
    db_rec.datetime_updated = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    db_rec.namespace = current_app.config["NAMESPACE"]
    db_rec.data = input_rec


# For now just delete json from 'data' column
def record_delete(db_rec, input_rec):
    db_rec.data = None

    # for now insert into 'data_updated' as there is no 'data_deleted'
    db_rec.datetime_updated = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


# Do Neptune operation.
# If fails, delete created/updated Neptune records and return False
def process_neptune_record_set(record_list):
    return True


# AUTHENTICATION FUNCTIONS
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


# VALIDATION FUNCTIONS
def validate_record(rec):
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


def validate_record_set(record_list):
    """
        Validate a list of json records. 
        Break and return status if at least one record is invalid
        Return line number where the error occured
    """
    for index, rec in enumerate(record_list, start=1):
        status = validate_record(rec)
        if status != status_ok:
            return (status, index)

    else:
        return True
