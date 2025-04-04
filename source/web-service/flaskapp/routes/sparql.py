import requests

# timing
import time

from flask import (
    Blueprint,
    current_app,
    request,
    abort,
    Response,
    make_response,
)

from flaskapp.errors import (
    status_nt,
    status_graphstore_error,
    construct_error_response,
)

# Create a new "sparql" route blueprint
sparql = Blueprint("sparql", __name__)


# ### ROUTES ###
@sparql.route("/sparql", methods=["GET", "POST"])
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
        res = execute_query_post(
            # The request.form key-value pairs are combined with the query key-value
            # pair to ensure the query string is always sent to execute_query_post()
            # whether provided via request.args, request.form, or request.data:
            dict(request.form, query=query),
            accept_header,
            query_endpoint,
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
        res = execute_query(query, accept_header, query_endpoint)

    if isinstance(res, status_nt):
        response = construct_error_response(res)
        return abort(response)
    else:
        return Response(res, direct_passthrough=True, content_type=accept_header)


def execute_query(query: str, accept_header: str, query_endpoint: str):
    try:
        st = time.perf_counter()

        res = requests.post(
            query_endpoint, data={"query": query}, headers={"Accept": accept_header}
        )

        current_app.logger.info(
            f"Remote SPARQL query executed in {time.perf_counter() - st:.2f}s"
        )

        res.raise_for_status()

        return res.content
    except requests.exceptions.HTTPError as e:
        response = status_nt(res.status_code, type(e).__name__, str(res.content))
        return response
    except requests.exceptions.ConnectionError:
        return status_graphstore_error


def execute_query_post(data: dict, accept_header: str, query_endpoint: str):
    try:
        st = time.perf_counter()

        res = requests.post(
            query_endpoint, data=data, headers={"Accept": accept_header}
        )

        current_app.logger.info(
            f"Remote SPARQL query executed in {time.perf_counter() - st:.2f}s"
        )

        res.raise_for_status()

        return res
    except requests.exceptions.HTTPError as e:
        response = status_nt(res.status_code, type(e).__name__, str(res.content))
        return response
    except requests.exceptions.ConnectionError:
        return status_graphstore_error
