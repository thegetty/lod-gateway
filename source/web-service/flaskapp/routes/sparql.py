import time
import requests

from flask_openapi3 import APIBlueprint
from flask import current_app, request, abort, Response, make_response

from flaskapp.errors import (
    status_nt,
    status_ok,
    construct_error_response,
    status_graphstore_timeout,
)

from flaskapp.openapi import sparql_tag
from flaskapp.openapi_models import _strip_openapi_kwargs

from flaskapp.utilities import (
    authenticate_bearer,
    execute_sparql_query,
    execute_sparql_query_post,
)

# Create a new "sparql" route blueprint
sparql = APIBlueprint("sparql", __name__)
_strip_openapi_kwargs(sparql)


# ### ROUTES ###
@sparql.get(
    "/sparql",
    tags=[sparql_tag],
    summary="SPARQL query endpoint",
    responses={
        200: {"description": "SPARQL results"},
        400: {"description": "Bad request"},
        501: {"description": "RDF not enabled"},
        504: {"description": "Query timeout"},
    },
)
@sparql.post(
    "/sparql",
    tags=[sparql_tag],
    summary="SPARQL query endpoint",
    responses={
        200: {"description": "SPARQL results"},
        400: {"description": "Bad request"},
        501: {"description": "RDF not enabled"},
        504: {"description": "Query timeout"},
    },
)
def query_entrypoint():
    if current_app.config["PROCESS_RDF"] is not True:
        response = construct_error_response(
            status_nt(
                501,
                "Not Implemented",
                "Application is not enabled for SPARQL operations",
            )
        )
        return abort(response)

    if current_app.config["SPARQL_QUERY_AUTHENTICATION"] is True:
        # SPARQL endpoint requires authentication
        status = authenticate_bearer(request, current_app)
        if status != status_ok:
            response = construct_error_response(status)
            return abort(response)

    if "update" in request.args or request.form.get("update") is not None:
        response = construct_error_response(
            status_nt(400, "Bad Request", "SPARQL update is not permitted")
        )
        return abort(response)

    query: str = None

    if "query" in request.args:
        query = request.args["query"]
    elif "query" in request.form:
        query = request.form["query"]

    current_app.logger.debug(str(request.form))
    current_app.logger.debug(str(request.data))
    current_app.logger.debug(f"query: {query}")

    if (
        query is None
        and request.headers.get("Content-Type") == "application/sparql-query"
    ):
        query = request.data

    if query is None:
        response = construct_error_response(
            status_nt(400, "Bad Request", "No query parameter included")
        )
        return abort(response)

    accept_header: str = None

    if "Accept" in request.args:
        accept_header = request.args["Accept"]
    else:
        accept_header = request.form.get("Accept")

    if accept_header is None:
        accept_header = request.headers.get("Accept")

    query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]

    if request.method == "POST":
        st = time.perf_counter()
        try:
            res = execute_sparql_query_post(
                # The request.form key-value pairs are combined with the query key-value
                # pair to ensure the query string is always sent to execute_sparql_query_post()
                # whether provided via request.args, request.form, or request.data:
                dict(request.form, query=query),
                accept_header,
                query_endpoint,
                timeout=current_app.config["EXTERNALHTTPCALLS_TIMELIMIT"],
            )
        except requests.exceptions.Timeout:
            # SPARQL query did not return within the set timeout time
            current_app.logger.error(
                f"SPARQL POST query endpoint took longer than {current_app.config['EXTERNALHTTPCALLS_TIMELIMIT']} seconds and has timed timeout"
            )
            response = construct_error_response(status_graphstore_timeout)
            return response

        current_app.logger.info(
            f"Remote SPARQL POST query executed in {time.perf_counter() - st:.2f}s"
        )

        if isinstance(res, status_nt):
            response = construct_error_response(res)
            return abort(response)
        else:
            excluded_headers = [
                "content-encoding",
                "content-length",
                "transfer-encoding",
                "connection",
            ]

            headers = [
                (name, value)
                for (name, value) in res.headers.items()
                if name.lower() not in excluded_headers
            ]

            return make_response(res.content, res.status_code, headers)
    else:
        st = time.perf_counter()
        try:
            res = execute_sparql_query(
                query,
                accept_header,
                query_endpoint,
                timeout=current_app.config["EXTERNALHTTPCALLS_TIMELIMIT"],
            )
        except requests.exceptions.Timeout:
            # SPARQL query did not return within the set timeout time
            current_app.logger.error(
                f"SPARQL GET Query endpoint took longer than {current_app.config['EXTERNALHTTPCALLS_TIMELIMIT']} seconds and has timed timeout"
            )
            response = construct_error_response(status_graphstore_timeout)
            return response

        current_app.logger.debug(
            f"Remote SPARQL GET query executed in {time.perf_counter() - st:.2f}s"
        )
    if isinstance(res, status_nt):
        response = construct_error_response(res)
        return abort(response)
    else:
        return Response(res, direct_passthrough=True, content_type=accept_header)
