import logging
from os import environ, getenv
from datetime import datetime

from flask import Flask, Response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_compress import Compress

from flaskapp.routes.activity import activity
from flaskapp.routes.records import records
from flaskapp.routes.ingest import ingest
from flaskapp.routes.health import health
from flaskapp.routes.sparql import sparql
from flaskapp.models import db
from flaskapp.models.activity import Activity
from flaskapp.models.record import Record


def create_app():
    app = Flask(__name__)
    CORS(app, send_wildcard=True)

    # Setup global configuration
    app.config["AUTH_TOKEN"] = environ["AUTHORIZATION_TOKEN"]
    app.config["BASE_URL"] = environ["LOD_BASE_URL"]
    app.config["NAMESPACE"] = environ["APPLICATION_NAMESPACE"]
    app.config["NAMESPACE_FOR_NEPTUNE"] = environ["APP_NAMESPACE_NEPTUNE"]
    app.config["SQLALCHEMY_DATABASE_URI"] = environ["DATABASE"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_SORT_KEYS"] = False
    app.config["ITEMS_PER_PAGE"] = 100
    app.config["AS_DESC"] = environ["LOD_AS_DESC"]
    app.config["PROCESS_NEPTUNE"] = environ["PROCESS_NEPTUNE"]
    app.config["NEPTUNE_ENDPOINT"] = environ["NEPTUNE_ENDPOINT"]
    app.config["JSON_AS_ASCII"] = False
    app.config["FLASK_GZIP_COMPRESSION"] = environ["FLASK_GZIP_COMPRESSION"]

    # KEEP_LAST_VERSION turns on functionality to keep a previous copy of an upload, and to connect it
    # to the new version by way of the new entitiy_id being stored in the Record.previous_version. Why 'entity_id'?
    # This enables the previous version to be accessible through the API in normal ways without impacting currently
    # established functionality.
    # When enabled, a record response will include two new headers X-Previous-Version and X-Is-Old-Version
    # If there is a previous version of the record, the X-Previous-Version will contain the entity_id for it, and
    # it will be accessible through 'http://host/NAMESPACE/entity_id' as usual.
    # When accessing an old version, the X-Is-Old-Version header will be True.
    # When a new version requested to be ingested, any previous version is deleted and replaced with the current version.
    # The uploaded version will become the current version.
    # Deleting a record will also delete any previous version stored.
    # Actions on previous versions will not be logged to the activity stream, which will only contain actions performed on
    # current versions.
    app.config["KEEP_LAST_VERSION"] = False
    if environ.get("KEEP_LAST_VERSION", "False").lower() == "true":
        app.config["KEEP_LAST_VERSION"] = True

    if app.env == "development":
        app.config["SQLALCHEMY_ECHO"] = True

    db.init_app(app)
    compress = Compress()
    if app.config["FLASK_GZIP_COMPRESSION"].lower() == "true":
        compress.init_app(app)
    migrate = Migrate(app, db)

    # Set the debug level
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=getenv("DEBUG_LEVEL", logging.INFO))

    with app.app_context():

        ns = app.config["NAMESPACE"]

        app.register_blueprint(activity, url_prefix=f"/{ns}")
        app.register_blueprint(records, url_prefix=f"/{ns}")
        app.register_blueprint(ingest, url_prefix=f"/{ns}")
        app.register_blueprint(sparql, url_prefix=f"/{ns}")
        app.register_blueprint(health, url_prefix=f"/{ns}")

        # Index Route
        @app.route(f"/{ns}/")
        def welcome():
            now = datetime.now().strftime("%H:%M:%S on %Y-%m-%d")
            body = f"Welcome to the Getty's Linked Open Data Gateway Service at {now}"
            return app.make_response(body)

        @app.after_request
        def add_header(response):
            response.headers["Server"] = "LOD Gateway/0.2"
            return response

        return app
