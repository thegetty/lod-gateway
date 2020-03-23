import json
import requests

from flask import Blueprint, current_app, request, abort, jsonify

from flaskapp.errors import (
    status_nt,
    status_neptune_error,
    construct_error_response,
    status_ok,
)
from flaskapp.routes.ingest import authenticate_bearer

# Create a new "sparql" route blueprint
sparql = Blueprint("sparql", __name__)

# ### ROUTES ###
@sparql.route("/sparql", methods=["GET", "POST"])
def query_entrypoint():
    # Authentication. If fails, abort with 401
    status = authenticate_bearer(request)
    if status != status_ok:
        response = construct_error_response(status)
        return abort(response)

    if "update" in request.args or request.form.get("update") is not None:
        response = construct_error_response(
            status_nt(400, "Bad request", "SPARQL update is not permitted")
        )
        return abort(response)

    query = None
    if "query" in request.args:
        query = request.args["query"]
    else:
        query = request.form.get("query")

    if query is None:
        response = construct_error_response(
            status_nt(400, "Query error", "No query parameter included")
        )
        return abort(response)

    accept_header = None
    if "accept" in request.args:
        accept_header = request.args["accept"]
    else:
        accept_header = request.form.get("accept")

    if accept_header is None:
        accept_header = request.headers["Accept"]

    neptune_endpoint = current_app.config["NEPTUNE_ENDPOINT"]
    res = execute_query(query, accept_header, neptune_endpoint)
    if isinstance(res, status_nt):
        response = construct_error_response(res)
        return response
    else:
        return res


def execute_query(query, accept_header, neptune_endpoint):
    try:
        res = requests.post(
            neptune_endpoint, data={"query": query}, headers={"Accept": accept_header}
        )
        return res.content
    except requests.exceptions.ConnectionError as e:
        return status_neptune_error
