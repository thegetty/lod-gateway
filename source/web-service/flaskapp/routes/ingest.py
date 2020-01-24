from flask import Blueprint, request, abort


# Create a new "ingest" route blueprint
ingest = Blueprint("ingest", __name__)


@ingest.route("/ingest", methods=["GET"])
def ingest_get():
    """ Process 'GET' request
        Do not allow 'GET' on this route. Handle it here,
        otherwise it will go to 'records' route, producing misleading 404 error     

    """
    return abort(405)


@ingest.route("/ingest", methods=["POST"])
def ingest_post():

    result = request.data
    return result
