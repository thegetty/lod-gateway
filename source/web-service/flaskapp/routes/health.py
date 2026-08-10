from flask_openapi3 import APIBlueprint
from flask import current_app, abort, request

from flaskapp.models import db
from flaskapp.routes import ingest
from flaskapp.errors import (
    status_db_error,
    construct_error_response,
    status_graphstore_error,
    status_ok,
)

from sqlalchemy import text

from flaskapp.utilities import authenticate_bearer
from flaskapp.openapi import health_tag

# Create a new "health_check" route blueprint
health = APIBlueprint("health", __name__)

_OPENAPI_KWARGS = frozenset(
    [
        "tags",
        "summary",
        "responses",
        "description",
        "security",
        "deprecated",
        "external_docs",
        "servers",
        "operation_id",
        "openapi_extensions",
    ]
)


_original_health_add_url_rule = health.add_url_rule


def _health_add_url_rule(*args, **kwargs):
    for key in _OPENAPI_KWARGS:
        kwargs.pop(key, None)
    _original_health_add_url_rule(*args, **kwargs)


health.add_url_rule = _health_add_url_rule


# Checks DB Connectivity ONLY
@health.get(
    "/health",
    tags=[health_tag],
    summary="Health check",
    responses={
        200: {"description": "OK"},
        503: {"description": "Database unavailable"},
    },
)
def healthcheck_get():
    if health_db():
        return "OK"
    else:
        response = construct_error_response(status_db_error)
        return abort(response)


# Checks DB Connectivity ONLY
@health.get(
    "/authhealth",
    tags=[health_tag],
    summary="Authenticated health check",
    description="Same as /health but requires a valid bearer token.",
    security=[{"bearerAuth": []}],
    responses={
        200: {"description": "OK"},
        401: {"description": "Unauthorized"},
        503: {"description": "Database unavailable"},
    },
)
def authd_healthcheck_get():
    # same as the normal healthcheck, but requires authentication. This will be a cheap
    # way for a client to make sure that its authentication token is correct.

    # Authentication. If fails, abort with 401
    status = authenticate_bearer(request, current_app)
    if status != status_ok:
        response = construct_error_response(status)
        return abort(response)

    if health_db():
        return "OK"
    else:
        response = construct_error_response(status_db_error)
        return abort(response)


# Checks DB Connectivity AND SPARQL endpoint status
@health.get(
    "/rdfhealth",
    tags=[health_tag],
    summary="RDF health check",
    description="Checks database connectivity AND (when RDF processing is enabled) the SPARQL endpoint status.",
    responses={
        200: {"description": "OK"},
        503: {"description": "Database or SPARQL endpoint unavailable"},
    },
)
def rdf_healthcheck_get():
    # same as the normal healthcheck, but also checks the RDF SPARQL endpoint access

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
        db.session.execute(text("select id from records limit 1;"))
        return True
    except Exception as e:
        current_app.logger.error(f"Error - {e}")
        return False


def health_graphstore(query_endpoint):
    return ingest.graph_check_endpoint(query_endpoint)
