import json
import httpx

# timing
import time

from flask import (
    Blueprint,
    current_app,
    request,
    abort,
    jsonify,
    Response,
    make_response,
)

from flaskapp.errors import (
    status_nt,
    status_graphstore_error,
    construct_error_response,
    status_ok,
)
from flaskapp.routes.ingest import authenticate_bearer

# Create a new "sparql" route blueprint
sparql = Blueprint("sparql", __name__)


# ### ROUTES ###
@sparql.route("/sparql", methods=["GET", "POST"])
async def query_entrypoint():
    if current_app.config["PROCESS_RDF"] is not True:
        response = construct_error_response(
            status_nt(
                501,
                "Not Implemented",
                "Application is not enabled for SPARQL operations",
            )
        )
        return abort(response)

    if "update" in request.args or request.form.get("update") is not None:
        response = construct_error_response(
            status_nt(400, "Bad Request", "SPARQL update is not permitted")
        )
        return abort(response)

    query = None
    if "query" in request.args:
        query = request.args["query"]
    else:
        query = request.form.get("query")

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

    accept_header = None
    if "Accept" in request.args:
        accept_header = request.args["Accept"]
    else:
        accept_header = request.form.get("Accept")

    if accept_header is None:
        accept_header = request.headers.get("Accept")

    query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
    if request.method == "POST":
        res = await execute_query_post(request.form, accept_header, query_endpoint)
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
        res = await execute_query(query, accept_header, query_endpoint)
    if isinstance(res, status_nt):
        response = construct_error_response(res)
        return abort(response)
    else:
        return Response(res, direct_passthrough=True, content_type=accept_header)


async def execute_query(query, accept_header, query_endpoint):
    try:
        st = time.perf_counter()
        async with httpx.AsyncClient(follow_redirects=True) as client:
            res = await client.post(
                query_endpoint, data={"query": query}, headers={"Accept": accept_header}
            )
            current_app.logger.info(
                f"Remote SPARQL query executed in {time.perf_counter() - st:.2f}s"
            )
            res.raise_for_status()
            return res.content
    except httpx.HTTPError as e:
        response = status_nt(e.status_code, type(e).__name__, str(e))
        return response
    except httpx.ConnectionError as e:
        return status_graphstore_error


async def execute_query_post(data, accept_header, query_endpoint):
    try:
        st = time.perf_counter()
        async with httpx.AsyncClient(follow_redirects=True) as client:
            res = await client.post(
                query_endpoint, data=data, headers={"Accept": accept_header}
            )

            current_app.logger.info(
                f"Remote SPARQL query executed in {time.perf_counter() - st:.2f}s"
            )
            res.raise_for_status()
            return res
    except httpx.HTTPError as e:
        response = status_nt(e.status_code, type(e).__name__, str(e))
        return response
    except httpx.ConnectionError as e:
        return status_graphstore_error
