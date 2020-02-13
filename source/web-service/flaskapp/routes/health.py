from flask import Blueprint, current_app, abort

from flaskapp.models import db

from flaskapp.routes.ingest import status_nt, construct_error_response


# Create a new "health_check" route blueprint
health = Blueprint("health", __name__)


@health.route("/health", methods=["GET"])
def healthcheck_get():
    if health_db():
        return "OK"
    else:
        status_db_error = status_nt(
            500, "Data Base Error", "DB connection cannot be established"
        )
        response = construct_error_response(status_db_error)
        return abort(response)


def health_db():
    try:
        db.session.execute("SELECT 1")
        return True
    except:
        return False
