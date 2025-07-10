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
    construct_error_response,
)

from flaskapp.utilities import execute_sparql_query_post, execute_sparql_query

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
        st = time.perf_counter()
        res = execute_sparql_query_post(
            # The request.form key-value pairs are combined with the query key-value
            # pair to ensure the query string is always sent to execute_sparql_query_post()
            # whether provided via request.args, request.form, or request.data:
            dict(request.form, query=query),
            accept_header,
            query_endpoint,
        )
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
        res = execute_sparql_query(query, accept_header, query_endpoint)

        current_app.logger.debug(
            f"Remote SPARQL GET query executed in {time.perf_counter() - st:.2f}s"
        )
    if isinstance(res, status_nt):
        response = construct_error_response(res)
        return abort(response)
    else:
        return Response(res, direct_passthrough=True, content_type=accept_header)
