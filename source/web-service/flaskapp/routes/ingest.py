from flask import Blueprint, current_app, request, Response, abort
from flaskapp.utilities import validate_namespace


# Create a new "ingest" route blueprint
ingest = Blueprint("ingest", __name__)


@ingest.route("/<path:namespace>/ingest", methods=["GET"])
def ingest_get(namespace):
    """ Process 'GET' request
        Do not allow 'GET' on this route. Handle it here,
        otherwise it will go to 'records' route, producing misleading 404 error     

    """
    return abort(405)


@ingest.route("/<path:namespace>/ingest", methods=["POST"])
def ingest_post(namespace):

    namespace = validate_namespace(namespace)

    result = request.data
    return result
