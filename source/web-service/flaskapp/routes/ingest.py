import json
import uuid

# Timing requests
import time

# For retry jitter
from random import random

from contextlib import suppress
from datetime import datetime

import rdflib
import requests
import traceback
from pyld import jsonld
from pyld.jsonld import JsonLdError

from flask import Blueprint, current_app, request, abort, jsonify
from sqlalchemy import exc

from flaskapp.models import db
from flaskapp.models.record import Record
from flaskapp.models.activity import Activity
from flaskapp.errors import (
    status_nt,
    status_data_missing,
    status_db_error,
    status_graphstore_error,
    status_db_save_error,
    status_GET_not_allowed,
    status_id_missing,
    status_ok,
    status_bad_auth_header,
    status_wrong_auth_token,
    status_wrong_syntax,
    construct_error_response,
)
from flaskapp.utilities import (
    Event,
    containerRecursiveCallback,
    idPrefixer,
    checksum_json,
    full_stack_trace,
)


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

    current_app.logger.debug("Authentication checked - ingest POST request allowed.")

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

    # Process record set to create/update/delete in Record, Activities and graph store
    result = process_record_set(record_list)

    # The result is an error (derived from 'status_nt'). Abort with 503
    if isinstance(result, status_nt):
        response = construct_error_response(result)
        return abort(response)

    # Finished normally - return 200 and result dict
    return jsonify(result), 200


# ### CRUD FUNCTIONS ###
def process_record_set(record_list, query_endpoint=None, update_endpoint=None):
    """
    Process the record set in a loop. Wrap into 'try-except'.
    Roll back and abort with 503 if any of 3 operations:
    Record, Activity or graph store fails.

    update_endpoint and query_endpoint are used by the test suite to mock a SPARQL
    endpoint. They shouldn't be used otherwise.
    """

    #  This dict will be returned by function. key: 'id', value: 'namespace/id'
    result_dict = {}
    idx_to_process_further = []

    current_app.logger.debug(f"Processing {len(record_list)} records for updates")
    with db.session.no_autoflush:
        try:
            for idx, rec in enumerate(record_list):

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

                    # add the list index to the list of updates to process through the graph store
                    idx_to_process_further.append(idx)

                # add to result dict pair ('id': 'None') which will signify to client no operation was done
                else:
                    result_dict[id] = "null"

        # Catch only OperationalError exception (e.g. DB is down)
        except exc.OperationalError as e:
            current_app.logger.error(e)
            current_app.logger.critical(
                "Critical failure writing the updated Record to DB"
            )
            db.session.rollback()
            return status_db_save_error

        # Process graph store entries. Check the graph store flag - if not set, do not process, return 'True'
        # Note, we compare to a string 'True' or 'False' passed from .evn file, not a boolean
        graphstore_result = True
        if current_app.config["PROCESS_RDF"] == "True":
            current_app.logger.debug(
                f"PROCESS_RDF is true - process records as valid JSON-LD"
            )
            graphstore_result = process_graphstore_record_set(
                [record_list[x] for x in idx_to_process_further],
                query_endpoint=query_endpoint,
                update_endpoint=update_endpoint,
            )

            # if RDF process fails, roll back and return graph store specific error
            if graphstore_result is not True:
                current_app.logger.error(
                    f"Error occurred processing JSON-LD. Rolling back."
                )
                db.session.rollback()

                # Failure happened when expanding the graphs?
                if isinstance(graphstore_result, status_nt):
                    return graphstore_result

                # graphstore_result should contain a list of graphs successfully updated that need to be rolled back
                # Given that this failure should only happen if an out of band error has occurred (Neptune overloaded)
                # the attempt to rollback these graphs may also not be successful.
                current_app.logger.error(f"Attempting to revert {graphstore_result}")
                revert_triplestore_if_possible(graphstore_result)

                # This should be treated as a server error
                return status_nt(
                    500,
                    "Triplestore Update Error",
                    "A failure happened when trying to update the triplestore. Check logs for details.",
                )

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

    is_delete_request = "_delete" in data.keys() and data["_delete"] in [
        "true",
        "True",
        True,
    ]

    # Record with such 'id' does not exist
    if db_rec == None:

        # this is a 'delete' request for record that is not in DB
        if is_delete_request is True:
            return (None, id, Event.Delete)

        # create and return primary key for Activities
        prim_key = record_create(data)

        # 'prim_key' - primary key created by db
        # return record 'id' since it is not known to calling function
        # 'create' - return the exect CRUD operation (createed in this case)
        return (prim_key, id, Event.Create)

    # Record exists
    else:
        if current_app.config["KEEP_LAST_VERSION"] is True:
            if db_rec.is_old_version is True:
                # check to see if existing record is the same as uploaded:
                current_app.logger.warning(
                    f"Entity ID {db_rec.entity_id} ({db_rec.entity_type}) is an old version."
                )
                if not is_delete_request:
                    # Delete is allowed but not updates
                    current_app.logger.error(
                        f"Ignoring attempted update to Entity ID {db_rec.entity_id}."
                    )
                    return (None, id, None)

            chksum = checksum_json(data)
            if chksum == db_rec.checksum:
                current_app.logger.info(
                    f"Data uploaded for {id} is identical to the record already uploaded based on checksum. Ignoring."
                )
                return (None, id, None)

        # get primary key of existing record
        prim_key = db_rec.id

        # delete - only if db record is not a stub record
        if is_delete_request is True 
            if db_rec.data is None and db_rec.checksum is None:
                # stub record
                return (None, id, Event.Delete)
            record_delete(db_rec, data)
            if db_rec.is_old_version is True:
                # Don't mark deleting an old version as an event in the activity stream
                return (None, id, None)
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
    r.is_old_version = False
    r.data = input_rec
    r.checksum = checksum_json(input_rec)

    db.session.add(r)
    db.session.flush()

    # primary key of the newly created record
    return r.id


# Do not return anything. Calling function has all the info
def record_update(db_rec, input_rec):
    if current_app.config["KEEP_LAST_VERSION"] is True:
        if db_rec.is_old_version != True:
            if db_rec.previous_version is not None:
                old_version = get_record(db_rec.previous_version)
                if old_version is not None:
                    db.session.delete(old_version)

            prev_id = str(uuid.uuid4())
            prev = Record()
            prev.entity_id = prev_id
            prev.entity_type = db_rec.entity_type
            prev.datetime_created = db_rec.datetime_created
            prev.datetime_updated = db_rec.datetime_updated
            prev.data = db_rec.data
            prev.checksum = db_rec.checksum
            prev.is_old_version = True

            db.session.add(prev)

            db_rec.previous_version = prev_id
            # reassert the new version is_old... to False
            db_rec.is_old_version = False

    # Don't allow updates to old versions - this should be stopped earlier in the normal ingest flow, but if this function is
    # called through a different route this is a good safeguard.
    if db_rec.is_old_version == True:
        current_app.logger.warning(
            f"Entity ID {db_rec.entity_id} ({db_rec.entity_type}) is an old version. Updates are disabled."
        )
        return

    db_rec.datetime_updated = datetime.utcnow()
    db_rec.data = input_rec
    db_rec.checksum = checksum_json(input_rec)


# For now just delete json from 'data' column
def record_delete(db_rec, input_rec):
    if current_app.config["KEEP_LAST_VERSION"] is True:
        # Delete old version if it exists
        if db_rec.previous_version is not None:
            old_version = get_record(db_rec.previous_version)
            if old_version is not None:
                db.session.delete(old_version)
        # Is this an old version? null the previous_version of the item it refers to
        elif db_rec.is_old_version is True:
            # Remove link from
            oldv_id = db_rec.entity_id
            curr_id = db_rec.data["id"]
            current_app.logger.info(
                f"Delete requested on entity {oldv_id} that is marked as an old version."
            )
            curr_rec = get_record(curr_id)
            if curr_rec is not None and curr_rec.previous_version == oldv_id:
                current_app.logger.info(
                    f"Removing reference from entity {curr_id} that refers to this old version {oldv_id[:10]}..."
                )
                curr_rec.previous_version = None
            else:
                current_app.logger.error(
                    f"Deleting record marked as old version of {curr_id}, but current record is not linked to this."
                )

            # First add this to session for deletion
            db.session.delete(db_rec)
            return

    db_rec.data = None
    db_rec.checksum = None
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


# RDF processing
class RetryAfter(Exception):
    def __init__(
        self,
        waittime,
        message="Upstream is having temporary issues - retry later suggested.",
    ):
        self.waittime = waittime
        self.message = message
        super().__init__(self.message)


def retry_request_function(func, args, kwargs=None, retry_limit=3):
    retries = 1
    while retries <= retry_limit:
        try:
            if kwargs is not None:
                resp = func(*args, **kwargs)
            else:
                resp = func(*args)
            if isinstance(resp, bool):
                return resp
        except RetryAfter as e:
            # wait the requested time * the retry number (backoff) + a random 0.0->1.0s duration for jitter
            retry_time = (e.waittime * retries) + random()
            current_app.logger.warning(
                f"Triplestore service temporarily unavailable - pausing for {retry_time:0.2f} before retrying. Attempt {retries}"
            )
            time.sleep(retry_time)
        except requests.exceptions.ConnectionError as e:
            retry_time = retries * random()
            current_app.logger.warning(
                f"ConnectionError hit when attempting {graph_uri} upload. Pausing for {retry_time:0.2f}. Attempt {retries}."
            )
            time.sleep(retry_time)
        retries += 1
    if retries == retry_limit:
        return False


def process_graphstore_record_set(
    record_list, query_endpoint=None, update_endpoint=None
):
    """
    This function will process the same list of records indepenently.

    All graphs will be expanded by pyld to ntriples, and if any of these have errors,
    or expand to zero triples, the whole set will fail before any change is pushed to
    the triplestore.

    Once all graphs have been validated in this way, they will be pushed individually
    to the triplestore. While it would be possible to push all operations into a single request
    one of the operational issues has been that Neptune becoming resource constrained and
    failing. A concatenated request could be extremely large and there is no guarantee that
    Neptune would treat a single request as a transaction in any case. 

    An update request will be retried, if the response is an error that corresponds to a
    suspected issue with deployment (eg overloaded), but if this retry fails, then it is the
    clients responsbility to ensure the eventual consistency of the graphs supplied once the
    service has become healthy again (the LOD Gateway instance cannot accurately tell this.)

    In case of a graph update error, the db transaction will be rolled back, and the instance 
    will make an attempt to undo the graph updates that went successfully based on the JSON-LD
    stored in the DB. This process cannot be guaranteed due to the nature of the failure but an
    attempt is made out of due dilligence.

    If all operations succeded, then return 'True'.

    In case of 'delete' request, there can be 2 possibilities:
    - record exists. In this case delete and return 'True' or 'False' depending on the result
    - record does not exist. In this scenario - don't do anything and return 'True'

    Flow:
    -----

    - gather list of all graphs to be deleted
    - expand all JSON-LD for graphs to be updated
        - Fail if any do not expand without errors OR if any graph expands to zero triples
    - iterate through the graph deletion requests (with retry, backoff and jitter)
        - If any fail, return list of graphs changed to this point
    - iterate through the graph replacement requests (with retry, backoff and jitter)
        - If any fail, return list of graphs changed to this point (including successful deletions)
    - Return True if everything succeeded, or return a list of ids to be reverted in case of any failure.

    """

    try:
        if query_endpoint is None:
            query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]

        if update_endpoint is None:
            update_endpoint = current_app.config["SPARQL_UPDATE_ENDPOINT"]

        current_app.logger.debug(f"SPARQL Update using endpoint {update_endpoint}")
        current_app.logger.debug(f"SPARQL Query using endpoint {query_endpoint}")

        # check endpoint
        if graph_check_endpoint(query_endpoint) == False:
            current_app.logger.error(
                f"Query Endpoint failed to response - {query_endpoint}"
            )
            return status_graphstore_error

        graph_uri_prefix = (
            current_app.config["BASE_URL"]
            + "/"
            + current_app.config["NAMESPACE_FOR_RDF"]
            + "/"
        )

        records_to_delete = []
        serialized_nt_cache = {}

        idmap = {}

        proc = None  # jsonld.JsonLdProcessor()

        # expand all graphs, and collect list of graph_uris for deletion
        for record in record_list:
            data = json.loads(record)
            # Store the relative 'id' URL before the recursive URL prefixing is performed
            id = data["id"]

            # Assemble the record 'id' attribute base URL prefix
            idPrefix = (
                current_app.config["BASE_URL"]
                + "/"
                + current_app.config["NAMESPACE_FOR_RDF"]
            )

            # Recursively prefix each 'id' attribute that currently lacks a http(s)://<baseURL>/<namespace> prefix
            data = containerRecursiveCallback(
                data=data, attr="id", callback=idPrefixer, prefix=idPrefix
            )

            # Store the absolute 'id' URL after the recursive URL prefixing is performed
            graph_uri = data["id"]

            # retain the backwards link from graph_id to relative id for lookup ease
            idmap[graph_uri] = id

            if "_delete" in data.keys() and data["_delete"] in ["true", "True", True]:
                # ensure that all records are processed first, before actually
                # attempting anything with consequences. Build a list to delete first.
                current_app.logger.info(f"Graph {graph_uri} is marked for deletion.")
                records_to_delete.append(graph_uri)
            else:
                # Graph is to be updated/created in the triplestore index. Expand to RDF ntriples:
                serialized_nt_cache[graph_uri] = graph_expand(data, proc)

                # invalid JSON-LD?
                if (
                    isinstance(serialized_nt_cache[graph_uri], bool)
                    and serialized_nt_cache[graph_uri] == False
                ):
                    current_app.logger.error(
                        f"Graph {graph_uri} JSON-LD failed to convert to RDF."
                    )
                    return status_nt(
                        422,
                        "Graph expansion error",
                        "Could not convert JSON-LD to RDF, id " + graph_uri,
                    )

                # JSON-LD expands to nothing? (eg contents do not match context/framing or are not present.)
                if serialized_nt_cache[graph_uri] == "":
                    current_app.logger.error(
                        f"Graph {graph_uri} JSON-LD failed to convert to any RDF triples at all. Invalid."
                    )
                    return status_nt(
                        422,
                        "Graph expansion error",
                        (
                            "The JSON-LD expansion resulted in no RDF triples but RDF processing is enabled. Rejecting id "
                            + graph_uri
                        ),
                    )

    # Catch request connection errors
    except requests.exceptions.ConnectionError as e:
        return status_graphstore_error

    graph_ids_processed = []

    # Graphs expanded successfully, attempting graph replacements and deletions
    # Keep a list of successful updates in case of error.

    retry_limit = 3

    # Deletions
    for graph_uri in records_to_delete:
        resp = retry_request_function(
            graph_delete,
            [graph_uri, query_endpoint, update_endpoint],
            retry_limit=retry_limit,
        )

        if resp is True:
            graph_ids_processed.append(idmap[graph_uri])
        else:
            # All retries used up but no success
            # Need to return all successful uploads to this point to attempt rollback
            current_app.logger.error(
                f"FATAL: Retries expended when attempting {graph_uri} deletion."
            )
            if len(graph_ids_processed) > 0:
                current_app.logger.error(
                    f"{len(graph_ids_processed)} graphs in the Triplestore will need to be reverted to their previous state."
                )
            return graph_ids_processed

    # Replacements
    for graph_uri, serialized_nt in serialized_nt_cache.items():
        replace_resp = retry_request_function(
            graph_replace,
            [graph_uri, serialized_nt, update_endpoint],
            retry_limit=retry_limit,
        )

        if replace_resp is True:
            graph_ids_processed.append(idmap[graph_uri])
        else:
            # All retries used up but no success
            # Need to return all successful uploads to this point to attempt rollback
            current_app.logger.error(
                f"FATAL: Retries expended when attempting {graph_uri} replacement."
            )
            if len(graph_ids_processed) > 0:
                current_app.logger.error(
                    f"{len(graph_ids_processed)} graphs in the Triplestore will need to be reverted to their previous state."
                )
            return graph_ids_processed
    return True


def revert_triplestore_if_possible(list_of_relative_ids):
    # This method should only be called if there is some sort of failure in updating the triplestore index for a multi-resource
    # update request (more than one delete, update, or create in a single request).
    # Given that the errors that led to this situation are unknown and could be due to resource issues or other critical issues,
    # this attempt to realign the triplestore with the data in the LOD Gateway should not be trusted to have succeeded, and the client
    # MUST ensure that the resources are consistent with each other, as the LOD Gateway instance should be considered to be in a failure
    # state with respect to the triplestore. The following is just for due dilligence, and to provide log informaton for the admin to check
    # consistency.

    query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
    update_endpoint = current_app.config["SPARQL_UPDATE_ENDPOINT"]

    proc = None

    idPrefix = (
        current_app.config["BASE_URL"] + "/" + current_app.config["NAMESPACE_FOR_RDF"]
    )

    for relative_id in list_of_relative_ids:
        # get current record
        current_app.logger.warning(
            f"Attempting to revert '{relative_id}' in triplestore to DB version"
        )
        record = get_record(relative_id)
        if record is None or record.data is None:
            # this record did not exist before the bulk request
            try:
                graph_delete(relative_id, query_endpoint, update_endpoint)
                current_app.logger.warning(
                    f"REVERT: Deleted {relative_id} from triplestore to match DB state (deleted/non-existent)"
                )
            except (requests.exceptions.ConnectionError, RetryAfter) as e:
                current_app.logger.error(
                    f"REVERT: Rollback failure - couldn't revert {relative_id} to a deleted state in the triplestore"
                )
        else:
            # expand, skip if zero triples or fail, and reassert
            try:
                current_app.logger.warning(
                    f"REVERT: Attempting to expand and reinsert {relative_id} into the triplestore."
                )
                # Recursively prefix each 'id' attribute that currently lacks a http(s)://<baseURL>/<namespace> prefix
                data = containerRecursiveCallback(
                    data=record.data, attr="id", callback=idPrefixer, prefix=idPrefix
                )
                nt = graph_expand(data, proc=proc)
                if nt is False:
                    current_app.logger.warning(
                        f"REVERT: Attempted to revert {relative_id} to DB version, JSON-LD failed to expand. Skipping."
                    )
                else:
                    graph_replace(data["id"], nt, update_endpoint)
                    current_app.logger.warning(
                        f"REVERT: Reasserted {relative_id} in triplestore to match DB state (graph - {data['id']})"
                    )
            except (requests.exceptions.ConnectionError, RetryAfter) as e:
                current_app.logger.error(
                    f"REVERT: Rollback failure - couldn't revert {relative_id} to match the DB"
                )


def graph_expand(data, proc=None):
    json_ld_cxt = None
    json_ld_id = None
    json_ld_type = None

    if isinstance(data, dict):
        if "@context" in data:
            json_ld_cxt = data["@context"]
        if "id" in data:
            json_ld_id = data["id"]
        if "type" in data:
            json_ld_type = data["type"]

    # time the expansion
    tictoc = time.perf_counter()
    try:
        if isinstance(json_ld_cxt, str) and len(json_ld_cxt) > 0:
            # raise RuntimeError("Graph expansion error: No @context URL has been defined in the data for %s!" % (json_ld_id))

            # attempt to obtain the JSON-LD @context document
            resp = requests.get(json_ld_cxt)
            if not resp.status_code == 200:  # if there is a failure, report it...
                current_app.logger.error(
                    "Graph expansion error for %s (%s): Failed to obtain @context URL (%s) with HTTP status: %d"
                    % (json_ld_id, json_ld_type, json_ld_cxt, resp.status_code)
                )

        if proc is None:
            proc = jsonld.JsonLdProcessor()

        serialized_nt = proc.to_rdf(data, {"format": "application/n-quads"})
    except Exception as e:
        current_app.logger.error(
            "Graph expansion error of type '%s' for %s (%s): %s"
            % (type(e), json_ld_id, json_ld_type, str(e))
        )

        # As the call to `str(e)` above does not seem to provide detailed insight into the exception, do so manually here...
        # The `pyld` library's `JsonLdError` type (a subclass of `Exception`) defines unique properties, so we need to
        # check the instance type of `e` before attempting to access these properties, lest we cause more exceptions...
        # See https://github.com/digitalbazaar/pyld/blob/316fbc2c9e25b3cf718b4ee189012a64b91f17e7/lib/pyld/jsonld.py#L5646
        if isinstance(e, JsonLdError):
            current_app.logger.error(
                "Graph expansion error type:    %s" % (str(e.type))
            )
            current_app.logger.error(
                "Graph expansion error details: %s" % (repr(e.details))
            )
            current_app.logger.error(
                "Graph expansion error code:    %s" % (str(e.code))
            )
            current_app.logger.error(
                "Graph expansion error cause:   %s" % (str(e.cause))
            )
            current_app.logger.error(
                "Graph expansion error trace:   %s"
                % (str("".join(traceback.format_list(e.causeTrace))))
            )
        else:
            current_app.logger.error(
                "Graph expansion error stack trace:\n%s" % (full_stack_trace())
            )

        current_app.logger.error(
            "Graph expansion error current record:  %s"
            % (json.dumps(data, sort_keys=True).encode("utf-8"))
        )

        return False

    current_app.logger.info(
        f"Graph {data['id']} expanded in {time.perf_counter() - tictoc:05f}s"
    )
    return serialized_nt


def graph_exists(graph_name, query_endpoint):
    # function left here for utility
    res = requests.post(
        query_endpoint,
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


def graph_replace(graph_name, serialized_nt, update_endpoint):
    # This will replace the named graph with only the triples supplied
    replace_stmt = (
        "DROP SILENT GRAPH <"
        + graph_name
        + "> ; \n"
        + "INSERT DATA { GRAPH <"
        + graph_name
        + "> {"
        + serialized_nt
        + "} } ;"
    )
    current_app.logger.debug(replace_stmt)
    tictoc = time.perf_counter()
    res = requests.post(update_endpoint, data={"update": replace_stmt})
    if res.status_code == 200:
        current_app.logger.info(
            f"Graph {graph_name} replaced in {time.perf_counter() - tictoc:05f}s"
        )
        return True
    elif res.status_code in [502, 503, 504]:
        # a potentially temporary server error - retry
        current_app.logger.error(
            f"Error code {res.status_code} encountered - delay, then retry suggested"
        )
        delay_time = 5
        # With backoff, it will wait for approx 5s, then 10s, then 15s before retries, and then fail
        if "Retry-After" in res.headers:
            try:
                delay_time = int(res.headers["Retry-After"])
            except (ValueError, TypeError) as e:
                pass
        raise RetryAfter(delay_time)
    elif res.status_code in [411, 412, 413]:
        # request was too large or unacceptable
        current_app.logger.critical(
            f"REQUEST TOO LARGE - error {res.status_code} encountered with graph replacement {graph_name}."
        )
        current_app.logger.error(f"Response error for {graph_name} - '{res.text}'")
        return False
    else:
        # something out of flow occurred, potential data issue
        current_app.logger.critical(
            f"FATAL - error {res.status_code} encountered with graph replacement {graph_name}"
        )
        current_app.logger.error(f"Error for {graph_name} - '{res.text}'")
        return False


def graph_delete(graph_name, query_endpoint, update_endpoint):
    # Delete graph from triplestore
    tictoc = time.perf_counter()
    # drop graph
    if graph_name is not None:
        current_app.logger.info(f"Attempting to DROP GRAPH <{graph_name}>")
        res = requests.post(
            update_endpoint, data={"update": "DROP GRAPH <" + graph_name + ">"}
        )
        if res.status_code == 200:
            current_app.logger.info(
                f"Graph {graph_name} deleted in {time.perf_counter() - tictoc:05f}s"
            )
            return True
        elif res.status_code in [502, 503, 504]:
            # a potentially temporary server error - retry
            current_app.logger.error(
                f"Error code {res.status_code} encountered - delay, then retry suggested"
            )
            delay_time = 1
            if "Retry-After" in res.headers:
                try:
                    delay_time = int(res.headers["Retry-After"])
                except (ValueError, TypeError) as e:
                    pass
            raise RetryAfter(delay_time)
        else:
            current_app.logger.error(f"Graph delete error code: {res.status_code}")
            current_app.logger.error(f"Graph delete error: {res.text}")
            return False
    else:
        current_app.logger.error(
            f"graph_delete was passed graph_name=None - not doing anything"
        )
        return False


def graph_check_endpoint(query_endpoint):
    res = requests.get(query_endpoint.replace("sparql", "status"))
    try:
        res.raise_for_status()
        res_json = json.loads(res.content)
        if res_json["status"] == "healthy":
            return True
        else:
            return False
    except requests.exceptions.HTTPError as e:
        resp = e.response
        if resp.status_code == 404:
            # the endpoint we're connecting to does not have a /status
            # (perhaps it's a locally running endpoint instead of something like AWS Neptune)
            # assume its status is OK
            return True
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
        try:
            method, token = auth_header.split(maxsplit=1)
        except ValueError:
            return status_bad_auth_header

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

    except Exception as e:
        # JSON syntax is not valid
        current_app.logger.error("JSON Record Parse/Validation Error: " + str(e))
        return status_nt(422, "JSON Record Parse/Validation Error", str(e))


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


### Deprecated RDF functions:


def graph_insert(graph_name, serialized_nt, update_endpoint):
    # This will append triples to a given named graph
    insert_stmt = "INSERT DATA {GRAPH <" + graph_name + "> {" + serialized_nt + "}}"
    tictoc = time.perf_counter()
    res = requests.post(update_endpoint, data={"update": insert_stmt})
    current_app.logger.info(
        f"Graph {graph_name} inserted in {time.perf_counter() - tictoc:05f}s"
    )
    if res.status_code == 200:
        return True
    else:
        return False
