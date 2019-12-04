import sys
from datetime import datetime
import os
import psutil
import logging

from flask import Flask, Response
from flask_cors import CORS

from flaskapp.routes.activity import activity
from flaskapp.routes.records import records
from flaskapp.models import db


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Setup global configuration
    app.config["DEFAULT_URL_NAMESPACE"] = os.environ["LOD_DEFAULT_URL_NAMESPACE"]
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_SORT_KEYS"] = False
    app.config["ITEMS_PER_PAGE"] = 100
    app.config["AS_DESC"] = os.environ["LOD_AS_DESC"]

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
        def add_header(response):
            response.headers["Server"] = "LOD Gateway/0.2"
            return response

        return app
