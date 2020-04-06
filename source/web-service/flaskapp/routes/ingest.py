import json
import uuid
from datetime import datetime

import rdflib
import requests
from pyld import jsonld

from flask import Blueprint, current_app, request, abort, jsonify
from sqlalchemy import exc

from flaskapp.models import db
from flaskapp.models.record import Record
from flaskapp.models.activity import Activity
from flaskapp.errors import (
    status_nt,
    status_data_missing,
    status_db_error,
    status_neptune_error,
    status_db_save_error,
    status_GET_not_allowed,
    status_id_missing,
    status_ok,
    status_wrong_auth_token,
    status_wrong_syntax,
    construct_error_response,
)
from flaskapp.utilities import Event, containerRecursiveCallback, idPrefixer


# Create a new "ingest" route blueprint
ingest = Blueprint("ingest", __name__)


# ### ROUTES ###
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
    record_list = request.get_data(as_text=True).splitlines()

    # No data in request body, abort with 422
    if len(record_list) == 0:
        response = construct_error_response(status_data_missing)
        return abort(response)

    # Validation
    validates = validate_record_set(record_list)

    # Validation error
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

    # The result is an error (derived from 'status_nt'). Abort with 503
    if isinstance(result, status_nt):
        response = construct_error_response(result)
        return abort(response)

    # Finished normally - return 200 and result dict
    return jsonify(result), 200


# ### CRUD FUNCTIONS ###
def process_record_set(record_list):
    """
        Process the record set in a loop. Wrap into 'try-except'.
        Roll back and abort with 503 if any of 3 operations:
        Record, Activity or Neptune fails.
    """

    #  This dict will be returned by function. key: 'id', value: 'namespace/id'
    result_dict = {}

    try:
        for rec in record_list:

            # 'prim_key' - primary key (integer) returned by db. Used in Activities
            # 'id' - string ID submitted by client. Used in result dict
            # 'crud' - one of 3 operations ('create', 'update', 'delete')
            prim_key, id, crud_event = process_record(rec)

            # some operations may not return primary key e.g. 'delete' for non-existing record
            # if primary key is valid, process 'Activities'
            if prim_key:
                process_activity(prim_key, crud_event)

                # add pair of IDs to result dict
                result_dict[id] = f'{current_app.config["NAMESPACE"]}/{id}'

            # add to result dict pair ('id': 'None') which will signify to client no operation was done
            else:
                result_dict[id] = "null"

    # Catch only OperationalError exception (e.g. DB is down)
    except exc.OperationalError as e:
        db.session.rollback()
        return status_db_save_error

    # Process Neptune entries. Check the Neptune flag - if not set, do not process, return 'True'
    # Note, we compare to a string 'True' or 'False' passed from .evn file, not a boolean
    neptune_result = True
    if current_app.config["PROCESS_NEPTUNE"] == "True":
        neptune_result = process_neptune_record_set(record_list)

    # if Neptune fails, roll back and return Neptune specific error
    if isinstance(neptune_result, status_nt):
        db.session.rollback()
        return neptune_result

    # Everything went fine - commit the transaction
    db.session.commit()
    return result_dict


def process_record(input_rec):
    """
        Process a single record. Return 3 values which are not available
        in the calling function: primary key, string 'id' and operation type
        {'create', 'update' or 'delete'}

    """
    data = json.loads(input_rec)
    id = data["id"]

    # Find if Record with this 'id' exists
    db_rec = get_record(id)

    # Record with such 'id' does not exist
    if db_rec == None:

        # this is a 'delete' request for record that is not in DB
        if "_delete" in data.keys() and data["_delete"] == "true":
            return (None, id, Event.Delete)

        # create and return primary key for Activities
        prim_key = record_create(data)

        # 'prim_key' - primary key created by db
        # return record 'id' since it is not known to calling function
        # 'create' - return the exect CRUD operation (createed in this case)
        return (prim_key, id, Event.Create)

    # Record exists
    else:
        # get primary key of existing record
        prim_key = db_rec.id

        # delete
        if "_delete" in data.keys() and data["_delete"] == "true":
            record_delete(db_rec, data)
            return (prim_key, id, Event.Delete)

        # update
        else:
            record_update(db_rec, data)
            return (prim_key, id, Event.Update)


# There is no entry with this 'id'. Create a new record
def record_create(input_rec):
    r = Record()
    r.entity_id = input_rec["id"]

    # 'entity_type' is not required, so check if exists
    if "type" in input_rec.keys():
        r.entity_type = input_rec["type"]

    r.datetime_created = datetime.utcnow()
    r.datetime_updated = r.datetime_created
    r.data = input_rec

    db.session.add(r)
    db.session.flush()

    # primary key of the newly created record
    return r.id


# Do not return anything. Calling function has all the info
def record_update(db_rec, input_rec):
    db_rec.datetime_updated = datetime.utcnow()
    db_rec.data = input_rec


# For now just delete json from 'data' column
def record_delete(db_rec, input_rec):
    db_rec.data = None
    db_rec.datetime_deleted = datetime.utcnow()


def process_activity(prim_key, crud_event):
    a = Activity()
    a.uuid = str(uuid.uuid4())
    a.datetime_created = datetime.utcnow()
    a.record_id = prim_key
    a.event = crud_event.name
    db.session.add(a)


def get_record(rec_id):
    result = Record.query.filter(Record.entity_id == rec_id).one_or_none()
    return result


# Neptune processing
def process_neptune_record_set(record_list, neptune_endpoint=None):
    """
        This function will process the same list of records indepenently.
        See specs for details.

        If one of the records fails, all inserted/updated records must be reverted:
        newly inserted records must be deleted, updated records must be reverted to
        the previous state. And Neptune specific error derived from 'status_nt'
        (see 'errors.py' for examples and how to create) must be returned.
        If it is desireable to include failing record number, then 'status_nt'
        could be created on the fly like this:

        return status_nt(500, "Title goes here", "Description including rec number goes here")

        If all operations succeded, then return 'True'.

        In case of 'delete' request, there can be 2 possibilities:
        - record exists. In this case delete and return 'True' or 'False' depending on the result
        - record does not exist. In this scenario - don't do anything and return 'True'

    """

    try:
        if neptune_endpoint == None:
            neptune_endpoint = current_app.config["NEPTUNE_ENDPOINT"]

        # check endpoint
        if graph_check_endpoint(neptune_endpoint) == False:
            return status_neptune_error

        graph_uri_prefix = (
            current_app.config["BASE_URL"]
            + "/"
            + current_app.config["NAMESPACE_FOR_NEPTUNE"]
            + "/"
        )
        graph_rollback_save = {}
        for record in record_list:
            data = json.loads(record)
            # Store the relative 'id' URL before the recursive URL prefixing is performed
            id = data["id"]

            # Assemble the record 'id' attribute base URL prefix
            idPrefix = (
                current_app.config["BASE_URL"]
                + "/"
                + current_app.config["NAMESPACE_FOR_NEPTUNE"]
            )

            # Recursively prefix each 'id' attribute that currently lacks a http(s)://<baseURL>/<namespace> prefix
            data = containerRecursiveCallback(
                data=data, attr="id", callback=idPrefixer, prefix=idPrefix,
            )

            # Store the absolute 'id' URL after the recursive URL prefixing is performed
            graph_uri = data["id"]

            if graph_exists(graph_uri, neptune_endpoint):
                graph_backup = graph_delete(graph_uri, neptune_endpoint)
                if isinstance(graph_backup, bool) and graph_backup == False:
                    graph_transaction_rollback(graph_rollback_save, neptune_endpoint)
                    return status_nt(
                        422, "Graph delete error", "Could not delete id " + id
                    )
                else:
                    graph_rollback_save[
                        graph_uri
                    ] = graph_backup  # saved as serialized n-triples
            else:
                graph_rollback_save[graph_uri] = None

            if "_delete" in data.keys() and data["_delete"] == "true":
                continue

            serialized_nt = graph_expand(data)
            if isinstance(serialized_nt, bool) and serialized_nt == False:
                graph_transaction_rollback(graph_rollback_save, neptune_endpoint)
                return status_nt(
                    422,
                    "Graph expansion error",
                    "Could not convert JSON-LD to RDF, id " + id,
                )
            insert_resp = graph_insert(graph_uri, serialized_nt, neptune_endpoint)
            if insert_resp == False:
                graph_transaction_rollback(graph_rollback_save, neptune_endpoint)
                return status_nt(500, "Graph insert error", "Could not insert id " + id)

    # Catch request connection errors
    except requests.exceptions.ConnectionError as e:
        return status_neptune_error

    # return status_nt(500, "Neptune error", "rec num 222")
    return True


def graph_expand(data):
    try:
        expanded = jsonld.expand(data)
        g = rdflib.ConjunctiveGraph()
        g.parse(data=json.dumps(expanded), format="json-ld")
        serialized_nt = g.serialize(format="nt").decode("UTF-8")
    except Exception as e:
        return False

    return serialized_nt


def graph_exists(graph_name, neptune_endpoint):
    res = requests.post(
        neptune_endpoint,
        data={
            "query": "SELECT (count(?s) as ?count) { GRAPH <"
            + graph_name
            + "> {?s ?p ?o}}"
        },
    )
    count_json = json.loads(res.content)
    if int(count_json["results"]["bindings"][0]["count"]["value"]) > 0:
        return True
    else:
        return False


def graph_insert(graph_name, serialized_nt, neptune_endpoint):
    insert_stmt = "INSERT DATA {GRAPH <" + graph_name + "> {" + serialized_nt + "}}"
    res = requests.post(neptune_endpoint, data={"update": insert_stmt})
    if res.status_code == 200:
        return True
    else:
        return False


def graph_delete(graph_name, neptune_endpoint):
    # save copy of graph in case of rollback
    res = requests.post(
        neptune_endpoint,
        data={
            "query": "CONSTRUCT{ ?s ?p ?o } WHERE { GRAPH <"
            + graph_name
            + "> {?s ?p ?o}}"
        },
        headers={"Accept": "application/n-triples"},
    )
    graph_ntriples = res.content.decode("utf-8")

    # drop graph
    res = requests.post(
        neptune_endpoint, data={"update": "DROP GRAPH <" + graph_name + ">"}
    )
    if res.status_code == 200:
        return graph_ntriples
    else:
        return False


def graph_transaction_rollback(graph_rollback_save, neptune_endpoint):
    for graph_uri in graph_rollback_save.keys():
        graph_delete(graph_uri, neptune_endpoint)
        if graph_rollback_save[graph_uri] is not None:
            graph_insert(graph_uri, graph_rollback_save[graph_uri], neptune_endpoint)


def graph_check_endpoint(neptune_endpoint):
    res = requests.get(neptune_endpoint.replace("sparql", "status"))
    res_json = json.loads(res.content)
    if res_json["status"] == "healthy":
        return True
    else:
        return False


# ### AUTHENTICATION FUNCTIONS ###
def authenticate_bearer(request):

    # For now return the same error for all failing scenarios
    error = status_wrong_auth_token

    # Get Authorization header token
    auth_header = request.headers.get("Authorization")

    # Return error if auth header is not present
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


# ### VALIDATION FUNCTIONS ###
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
