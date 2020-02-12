from flask import Blueprint, current_app, abort

from flaskapp.models import db

from flaskapp.routes.ingest import status_nt, construct_error_response


# Create a new "health_check" route blueprint
healthcheck = Blueprint("health_check", __name__)


@healthcheck.route("/healthcheck", methods=["GET"])
def healthcheck_get():
    if healthcheck_db():
        return "OK"
    else:
        status_db_error = status_nt(
            503, "Data Base Error", "DB connection cannot be established"
        )
        response = construct_error_response(status_db_error)
        return abort(response)


def healthcheck_db():
    try:
        db.session.execute("SELECT 1")
        return True
    except:
        return False
