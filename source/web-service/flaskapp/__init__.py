import sys
from datetime import datetime
import os
import psutil
import logging

from flask import Flask, Response

from app.di import DI
from app.database import Database
from flaskapp.routes.activity import activity
from flaskapp.routes.records import records
from flaskapp.models import db

# initialize the dependency injector
di = DI()

database = Database(shared=False)
if database:
    di.set("database", database)
else:
    raise RuntimeError("The database handler could not be initialized!")


def create_app():
    app = Flask(__name__)

    # Setup global configuration
    app.config["DEFAULT_URL_NAMESPACE"] = os.environ["LOD_DEFAULT_URL_NAMESPACE"]
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Set the debug level
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=os.getenv("DEBUG_LEVEL", logging.INFO))

    with app.app_context():

        app.register_blueprint(activity)
        app.register_blueprint(records)

        # Index Route
        @app.route("/")
        def welcome():
            now = datetime.now().strftime("%H:%M:%S on %Y-%m-%d")
            body = f"Welcome to the Getty's Linked Open Data Gateway Service at {now}"
            return Response(body, status=200)

        @app.after_request
        def afterRequest(response):
            if logger.isEnabledFor(logging.DEBUG):
                response = _add_debug_to_headers(response)
            return response

        return app


def _add_debug_to_headers(response):
    """Include process information within the response header.

    If there is an error obtaining information, the failure is logged
    and the response is returned without modification.

    Args:
        response: The flash response object

    Returns:
        the flask response object with an X-Process-Information header
        containing debug information
    """

    logger.debug(f"response.headers = {response.headers}")

    database = DI.get("database")
    if not database:
        logger.error("No database connection could be established!")
        return response

    information = database.information()
    if not isinstance(information, dict):
        logger.error("No database information could be obtained!")
        return response

    process = psutil.Process()
    if not process:
        logger.error("No process information instance could be obtained!")
        return response

    information["process"] = {
        "id": os.getpid(),
        "memory": {
            "info": process.memory_full_info(),
            "used": process.memory_full_info().uss,
        },
    }

    logger.debug(information)

    if os.getenv("WEB_DEBUG_HEADER", "NO") == "YES":
        # Obtain the headers
        headers = response.headers
        if not headers:
            logger.error("No response headers could be obtained!")
            return response

        headers["X-Process-Information"] = json.dumps(information)

        # Adjust the headers
        response.headers = headers
    return response
