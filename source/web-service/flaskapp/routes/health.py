from flask import Blueprint, current_app, abort

from flaskapp.models import db
from flaskapp.routes import ingest
from flaskapp.errors import (
    status_db_error,
    construct_error_response,
    status_graphstore_error,
)

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


def health_db():
    try:
        db.session.execute("select id from records limit 1")
        return True
    except:
        return False


def health_graphstore(query_endpoint):
    return ingest.graph_check_endpoint(query_endpoint)
