import json

# Timing requests
import time

# For retry jitter
from random import random

import requests

from flask import Blueprint, current_app, request, abort, jsonify
from sqlalchemy import exc

from flaskapp.models import db

# Storage methods for DB and graph store
from flaskapp.storage_utilities.record import (
    validate_record_set,
    get_record,
    record_delete,
    record_create,
    record_update,
    process_activity,
)
from flaskapp.storage_utilities.graph import (
    graph_check_endpoint,
    graph_delete,
    graph_replace,
    graph_expand,
    revert_triplestore_if_possible,
    inflate_relative_uris,
    RetryAfterError,
)
from flaskapp.errors import (
    status_nt,
    status_data_missing,
    status_graphstore_error,
    status_db_save_error,
    status_GET_not_allowed,
    status_ok,
    construct_error_response,
)
from flaskapp.utilities import (
    Event,
    checksum_json,
    authenticate_bearer,
)
from flaskapp.base_graph_utils import base_graph_filter


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
    status = authenticate_bearer(request, current_app)
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
    ids_to_refresh = []

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
                    # Suppress the base graph from the activity-stream
                    if id != current_app.config["RDF_BASE_GRAPH"]:
                        process_activity(prim_key, crud_event)
                    elif current_app.config["TESTMODE_BASEGRAPH"] is True:
                        current_app.logger.warning(
                            "Base graph changed. TESTMODE_BASEGRAPH is on, so reloading base graph filter. Test instance MUST BE single worker!"
                        )
                        # refresh the base graph for this instance
                        current_app.config["RDF_FILTER_SET"] = base_graph_filter(
                            current_app.config["RDF_BASE_GRAPH"],
                            current_app.config["FULL_BASE_GRAPH"],
                        )
                        current_app.logger.info(
                            f"Current Base graph filter: {list(current_app.config['RDF_FILTER_SET'])}"
                        )
                    else:
                        current_app.logger.warning(
                            "Base graph changed. Note this event will not be added to the activitystream."
                        )

                    # add pair of IDs to result dict
                    result_dict[id] = (
                        f'{current_app.config["NAMESPACE"]}/{id}'
                        if current_app.config["NAMESPACE"]
                        else f"{id}"
                    )

                    # add the list index to the list of updates to process through the graph store
                    idx_to_process_further.append(idx)

                elif crud_event == Event.Refresh:
                    # add the list index to the list of updates to process through the graph store
                    ids_to_refresh.append(id)
                    # This will be overwritten with a status if RDF Processing occurs later.
                    result_dict[id] = "rdf_processing_is_off"
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
        if current_app.config["PROCESS_RDF"] is True:
            current_app.logger.debug(
                "PROCESS_RDF is true - process records as valid JSON-LD"
            )
            if idx_to_process_further:
                graphstore_result = process_graphstore_record_set(
                    [record_list[x] for x in idx_to_process_further],
                    query_endpoint=query_endpoint,
                    update_endpoint=update_endpoint,
                )

                # if RDF process fails, roll back and return graph store specific error
                if graphstore_result is not True:
                    current_app.logger.error(
                        "Error occurred processing JSON-LD. Rolling back."
                    )
                    db.session.rollback()

                    # Failure happened when expanding the graphs?
                    if isinstance(graphstore_result, status_nt):
                        return graphstore_result

                    # graphstore_result should contain a list of graphs successfully updated that need to be rolled back
                    # Given that this failure should only happen if an out of band error has occurred (Neptune overloaded)
                    # the attempt to rollback these graphs may also not be successful.
                    current_app.logger.error(
                        f"Attempting to revert {graphstore_result}"
                    )
                    revert_triplestore_if_possible(graphstore_result)

                    # This should be treated as a server error
                    return status_nt(
                        500,
                        "Triplestore Update Error",
                        "A failure happened when trying to update the triplestore. Check logs for details.",
                    )

            # Only handle refresh requests if the PROCESS_RDF is enabled
            if ids_to_refresh:
                results = revert_triplestore_if_possible(ids_to_refresh)
                result_dict.update(results)

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

    id = data.get("id") or data.get("@id")

    if not id:
        return status_nt(
            400,
            "Request Error",
            "A failure happened when trying to get the root id for the JSON document. "
            "It must have a value for either the 'id' or '@id' at the top level.",
        )

    is_delete_request = "_delete" in data.keys() and data["_delete"] in [
        "true",
        "True",
        True,
    ]

    if "_refresh" in data.keys() and data["_refresh"] in [
        "true",
        "True",
        True,
    ]:
        # The graph refresh step will load the current data and determine whether to
        # delete or update the graphstore.
        return (None, id, Event.Refresh)

    # Find if Record with this 'id' exists
    db_rec = get_record(id)

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
        # Is ingest attempting to overwrite an existing container?
        if "container" in db_rec:
            # Container exists in position that record wants to be ingested to
            # --> Bad entity ID
            return (None, id, Event.ContainerConflict)

        # extract the record reference:
        db_rec = db_rec["record"]

        chksum = checksum_json(data)
        if chksum == db_rec.checksum:
            current_app.logger.info(
                f"Data uploaded for {id} is identical to the record already uploaded based on checksum. Ignoring."
            )
            return (None, id, None)

        # get primary key of existing record
        prim_key = db_rec.id

        # delete - only if db record is not a stub record
        if is_delete_request is True:
            if db_rec.data is None and db_rec.checksum is None:
                # stub record
                return (None, id, Event.Delete)
            record_delete(db_rec, data)
            return (prim_key, id, Event.Delete)

        # update
        else:
            record_update(db_rec, data)
            return (prim_key, id, Event.Update)


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
        except RetryAfterError as e:
            # wait the requested time * the retry number (backoff) + a random 0.0->1.0s duration for jitter
            retry_time = (e.waittime * retries) + random()
            current_app.logger.warning(
                f"Triplestore service temporarily unavailable - pausing for {retry_time:0.2f} before retrying. Attempt {retries}"
            )
            time.sleep(retry_time)
        except requests.exceptions.ConnectionError:
            retry_time = retries * random()
            current_app.logger.warning(
                f"ConnectionError hit. Pausing for {retry_time:0.2f}. Attempt {retries}."
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

        records_to_delete = []
        serialized_nt_cache = {}

        idmap = {}

        proc = None  # jsonld.JsonLdProcessor()

        # expand all graphs, and collect list of graph_uris for deletion
        for record in record_list:
            data = json.loads(record)
            # Store the relative 'id' URL before the recursive URL prefixing is performed
            id_attr = "@id" if "@id" in data else "id"
            id = data[id_attr]

            # Assemble the record 'id' attribute base URL prefix
            data = inflate_relative_uris(data=data, id_attr=id_attr)

            # Store the absolute 'id' URL after the recursive URL prefixing is performed
            graph_uri = data[id_attr]

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
    except requests.exceptions.ConnectionError:
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
