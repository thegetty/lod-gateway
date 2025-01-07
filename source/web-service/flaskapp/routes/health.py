from flask import Blueprint, current_app, abort, request

from flaskapp.models import db
from flaskapp.routes import ingest
from flaskapp.errors import (
    status_db_error,
    construct_error_response,
    status_graphstore_error,
    status_ok,
)

from flaskapp.utilities import authenticate_bearer

# Create a new "health_check" route blueprint
health = Blueprint("health", __name__)


@health.route("/health", methods=["GET"])
def healthcheck_get():
    if health_db():
        if current_app.config["PROCESS_RDF"] is True:
            query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
            if health_graphstore(query_endpoint):
                return "OK"
            else:
                response = construct_error_response(status_graphstore_error)
                return abort(response)
        else:
            return "OK"
    else:
        response = construct_error_response(status_db_error)
        return abort(response)


@health.route("/authhealth", methods=["GET"])
def authd_healthcheck_get():
    # same as the normal healthcheck, but requires authentication. This will be a cheap
    # way for a client to make sure that its authentication token is correct.

    # Authentication. If fails, abort with 401
    status = authenticate_bearer(request, current_app)
    if status != status_ok:
        response = construct_error_response(status)
        return abort(response)

    if health_db():
        if current_app.config["PROCESS_RDF"] is True:
            query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
            if health_graphstore(query_endpoint):
                return "OK"
            else:
                response = construct_error_response(status_graphstore_error)
                return abort(response)
        else:
            return "OK"
    else:
        response = construct_error_response(status_db_error)
        return abort(response)


def health_db():
    try:
        db.session.execute("select id from records limit 1")
        return True
    except Exception as e:
        print(f"Error - {e}")
        return False


def health_graphstore(query_endpoint):
    return ingest.graph_check_endpoint(query_endpoint)
