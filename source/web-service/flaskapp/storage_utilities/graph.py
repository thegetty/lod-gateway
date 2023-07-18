import requests
import json
import time
import re

from flask import current_app, request, abort, jsonify

from flaskapp.storage_utilities.record import get_record
from flaskapp.utilities import (
    Event,
    containerRecursiveCallback,
    idPrefixer,
    full_stack_trace,
    is_quads,
    quads_to_triples,
    graph_filter,
)

import rdflib

from pyld import jsonld
from pyld.jsonld import JsonLdError

from flaskapp.base_graph_utils import base_graph_filter
from flaskapp.graph_prefix_bindings import get_bound_graph


# RDF processing
class RetryAfterError(Exception):
    def __init__(
        self,
        waittime,
        message="Upstream is having temporary issues - retry later suggested.",
    ):
        self.waittime = waittime
        self.message = message
        super().__init__(self.message)


def inflate_relative_uris(data, id_attr="id"):
    idPrefix = (
        current_app.config["BASE_URL"] + "/" + current_app.config["NAMESPACE_FOR_RDF"]
    )

    return containerRecursiveCallback(
        data=data, attr=id_attr, callback=idPrefixer, prefix=idPrefix
    )


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


def graph_expand(data, proc=None):
    json_ld_cxt = None
    json_ld_id = None
    json_ld_type = None

    if isinstance(data, dict):
        id_attr = "id"
        if "@context" in data:
            json_ld_cxt = data["@context"]
        if "id" in data:
            json_ld_id = data["id"]
        if "@id" in data:
            json_ld_id = data["@id"]
            id_attr = "@id"
        if "type" in data:
            json_ld_type = data["type"]

    # time the expansion
    tictoc = time.perf_counter()

    # PyLD expansion? or RDFLIB?
    if current_app.config["USE_PYLD_REFORMAT"] is True:
        current_app.logger.info(f"{json_ld_id} - expanding using PyLD")
        try:
            if proc is None:
                proc = jsonld.JsonLdProcessor()

            current_app.logger.debug(
                f"{json_ld_id} - PyLD parsing START at timecode {time.perf_counter() - tictoc}"
            )
            serialized_nt = proc.to_rdf(
                data,
                {
                    "format": "application/n-quads",
                    "documentLoader": current_app.config["RDF_DOCLOADER"],
                },
            )

            current_app.logger.debug(
                f"{json_ld_id} - PyLD parsing END at timecode {time.perf_counter() - tictoc}"
            )
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
            f"Graph {data[id_attr]} expanded in {time.perf_counter() - tictoc:05f}s"
        )
        return serialized_nt
    else:
        current_app.logger.info(f"{json_ld_id} - expanding using PyLD")
        current_app.logger.debug(
            f"{json_ld_id} - RDFLIB parsing START at timecode {time.perf_counter() - tictoc}"
        )
        g = get_bound_graph(identifier=json_ld_id)
        g.parse(data=json.dumps(data), format="json-ld")
        current_app.logger.debug(
            f"{json_ld_id} - RDFLIB parsing END, START serialization at timecode {time.perf_counter() - tictoc}"
        )
        if len(g) == 0:
            current_app.logger.error(
                f"No suitable quads or triples were parsed from the supplied JSON-LD. Is {json_ld_id} actually JSON-LD?"
            )
            return False
        return g.serialize(format="nquads")


def graph_replace(graph_name, serialized_nt, update_endpoint):
    # This will replace the named graph with only the triples supplied

    # Quads supplied instead?
    serialized_nt = quads_to_triples(serialized_nt)

    # Update the RDF filter set ['RDF_FILTER_SET'] after success (only if this is the base graph)?
    update_filterset = False

    # Filter base graph triples out?
    if graph_name != current_app.config["FULL_BASE_GRAPH"]:
        if current_app.config["RDF_FILTER_SET"] is not None:
            current_app.logger.debug(
                f"Filtering base triples ({len(current_app.config['RDF_FILTER_SET'])}) from graph n-triples"
            )
            serialized_nt = graph_filter(
                serialized_nt, current_app.config["RDF_FILTER_SET"]
            )
        else:
            current_app.logger.warning(
                f"Base graph is set to '{current_app.config['RDF_BASE_GRAPH']}', but no triples are in its graph?"
            )
    else:
        # This graph has the same name as the selected base graph - update the filter set if successful
        update_filterset = True

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

    current_app.logger.debug(
        f"Size of graph replace statement: {len(replace_stmt)} characters"
    )
    tictoc = time.perf_counter()
    res = requests.post(update_endpoint, data={"update": replace_stmt})
    if res.status_code == 200:
        current_app.logger.info(
            f"Graph {graph_name} replaced in {time.perf_counter() - tictoc:05f}s"
        )
        if update_filterset is True:
            current_app.logger.info(
                f"Base graph has been updated - updating the base graph filter set to match."
            )
            current_app.config["RDF_FILTER_SET"] = base_graph_filter(
                current_app.config["RDF_BASE_GRAPH"],
                current_app.config["FULL_BASE_GRAPH"],
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
        raise RetryAfterError(delay_time)
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
            raise RetryAfterError(delay_time)
        else:
            current_app.logger.error(f"Graph delete error code: {res.status_code}")
            current_app.logger.error(f"Graph delete error: {res.text}")
            return False
    else:
        current_app.logger.error(
            f"graph_delete was passed graph_name=None - not doing anything"
        )
        return False


def revert_triplestore_if_possible(list_of_relative_ids):
    """This method loads the requested ids from the DB and attempts to refresh the triplestore with the expanded triples.

    If there is a DB error on update or create, this function will also be called in an attempt to revert the triplestore to match the
    DB records. Note that this should not be trusted, as the DB is already in an error state but it is due dilligence in case of an error.

    """
    query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
    update_endpoint = current_app.config["SPARQL_UPDATE_ENDPOINT"]

    proc = None
    results = {}

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
                results[relative_id] = "deleted"
            except (requests.exceptions.ConnectionError, RetryAfterError) as e:
                current_app.logger.error(
                    f"REVERT: Rollback failure - couldn't revert {relative_id} to a deleted state in the triplestore"
                )
                results[relative_id] = "connection_error"
        else:
            # expand, skip if zero triples or fail, and reassert
            try:
                current_app.logger.warning(
                    f"REVERT: Attempting to expand and reinsert {relative_id} into the triplestore."
                )
                # Recursively prefix each 'id' attribute that currently lacks a http(s)://<baseURL>/<namespace> prefix
                id_attr = "@id" if "@id" in record.data else "id"
                data = inflate_relative_uris(data=record.data, id_attr=id_attr)

                nt = graph_expand(data, proc=proc)
                if nt is False:
                    current_app.logger.warning(
                        f"REVERT: Attempted to revert {relative_id} to DB version, JSON-LD failed to expand. Skipping."
                    )
                    results[relative_id] = "graph_expansion_error"
                else:
                    graph_replace(data[id_attr], nt, update_endpoint)
                    current_app.logger.warning(
                        f"REVERT: Reasserted {relative_id} in triplestore to match DB state (graph - {data[id_attr]})"
                    )
                    results[relative_id] = "refreshed"
            except (requests.exceptions.ConnectionError, RetryAfterError) as e:
                current_app.logger.error(
                    f"REVERT: Rollback failure - couldn't revert {relative_id} to match the DB"
                )
                results[relative_id] = "connection_error"

    return results


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
