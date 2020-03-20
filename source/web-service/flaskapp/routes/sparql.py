import json
import requests

from flask import Blueprint, current_app, request, abort, jsonify

from flaskapp.errors import status_nt, status_neptune_error, construct_error_response

# Create a new "sparql" route blueprint
sparql = Blueprint("sparql", __name__)

# ### ROUTES ###
@sparql.route("/sparql", methods=["GET", "POST"])
def query_entrypoint():
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
        current_app.logger.info(accept_header)

    neptune_endpoint = current_app.config["NEPTUNE_ENDPOINT"]
    try:
        res = execute_query(query, accept_header, neptune_endpoint)
        return res
    except requests.exceptions.ConnectionError as e:
        response = construct_error_response(status_neptune_error)
        return status_neptune_error


def execute_query(query, accept_header, neptune_endpoint):
    res = requests.post(
        neptune_endpoint, data={"query": query}, headers={"Accept": accept_header}
    )
    return res.content
