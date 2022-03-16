import logging
import logging.config
from os import environ, getenv
from flaskapp.logging_configuration import get_logging_config

from datetime import datetime
import sqlite3

from flask import Flask, Response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_compress import Compress

from flask.logging import default_handler

from flaskapp.routes.activity import activity
from flaskapp.routes.activity_entity import activity_entity
from flaskapp.routes.records import records
from flaskapp.routes.ingest import ingest
from flaskapp.routes.health import health
from flaskapp.routes.sparql import sparql
from flaskapp.routes.yasgui import yasgui
from flaskapp.routes.timegate import timegate
from flaskapp.models import db
from flaskapp.models.activity import Activity
from flaskapp.models.record import Record
from flaskapp import local_thesaurus


# top-level logging configuration should provide the basic configuration for any logger Flask sets in the
# create_app step (and in other modules).
LOG_LEVEL = getenv("DEBUG_LEVEL", "INFO")
logging.config.dictConfig(get_logging_config(LOG_LEVEL))


def create_app():
    app = Flask(__name__)

    app.config["DEBUG_LEVEL"] = getenv("DEBUG_LEVEL", "INFO")

    app.logger.info(f"LOD Gateway logging INFO at level {app.config['DEBUG_LEVEL']}")

    CORS(app, send_wildcard=True)
    # Setup global configuration
    app.config["AUTH_TOKEN"] = environ["AUTHORIZATION_TOKEN"]
    app.config["BASE_URL"] = environ["BASE_URL"]
    app.config["NAMESPACE"] = environ["APPLICATION_NAMESPACE"]
    app.config["NAMESPACE_FOR_RDF"] = environ.get(
        "RDF_NAMESPACE", app.config["NAMESPACE"]
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = environ["DATABASE"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_SORT_KEYS"] = False
    app.config["ITEMS_PER_PAGE"] = 100
    app.config["AS_DESC"] = environ["LOD_AS_DESC"]
    app.config["PROCESS_RDF"] = environ["PROCESS_RDF"]

    # Setting the limit on number of records returned due to a glob browse request
    try:
        app.config["BROWSE_PAGE_SIZE"] = int(environ.get("BROWSE_PAGE_SIZE", 200))
    except (ValueError, TypeError) as e:
        app.config["BROWSE_PAGE_SIZE"] = 200

    # SPARQL endpoints only apply if LOD Gateway is configured to process input into RDF triples
    if app.config["PROCESS_RDF"].lower() == "true":
        app.config["SPARQL_QUERY_ENDPOINT"] = environ["SPARQL_QUERY_ENDPOINT"]
        app.config["SPARQL_UPDATE_ENDPOINT"] = environ["SPARQL_UPDATE_ENDPOINT"]
    app.config["JSON_AS_ASCII"] = False
    app.config["FLASK_GZIP_COMPRESSION"] = environ["FLASK_GZIP_COMPRESSION"]
    app.config["PREFIX_RECORD_IDS"] = getenv("PREFIX_RECORD_IDS", default="RECURSIVE")

    # KEEP_LAST_VERSION turns on functionality to keep a previous copy of an upload, and to connect it
    # to the new version by way of the new entitiy_id being stored. This copy is stored in a different
    # table and has different API endpoints to access it. The versioning API is based on Memento, with
    # fixed URIs for past versions, and provides TimeMap and TimeGate functionality.

    app.config["KEEP_LAST_VERSION"] = False
    if environ.get("KEEP_LAST_VERSION", "False").lower() == "true":
        app.config["KEEP_LAST_VERSION"] = True

    if environ.get("KEEP_VERSIONS_AFTER_DELETION", "False").lower() == "true":
        app.config["KEEP_VERSIONS_AFTER_DELETION"] = True

    if app.env == "development":
        app.config["SQLALCHEMY_ECHO"] = True

    db.init_app(app)
    compress = Compress()
    if app.config["FLASK_GZIP_COMPRESSION"].lower() == "true":
        compress.init_app(app)
    migrate = Migrate(app, db)

    if app.config["NAMESPACE"] == "local/thesaurus":
        app.config["LOCAL_THESAURUS_URL"] = environ["LOCAL_THESAURUS_URL"]
        local_thesaurus.populate_db(app.app_context())

    with app.app_context():

        ns = app.config["NAMESPACE"]

        app.register_blueprint(activity, url_prefix=f"/{ns}")
        app.register_blueprint(activity_entity, url_prefix=f"/{ns}")
        app.register_blueprint(records, url_prefix=f"/{ns}")
        app.register_blueprint(ingest, url_prefix=f"/{ns}")
        app.register_blueprint(sparql, url_prefix=f"/{ns}")
        app.register_blueprint(yasgui, url_prefix=f"/{ns}")
        app.register_blueprint(timegate, url_prefix=f"/{ns}")
        app.register_blueprint(health, url_prefix=f"/{ns}")

        # Index Route
        @app.route(f"/{ns}/")
        def welcome():
            now = datetime.now().strftime("%H:%M:%S on %Y-%m-%d")
            body = f"Welcome to the Getty's Linked Open Data Gateway Service at {now}"
            return app.make_response(body)

        @app.after_request
        def add_header(response):
            response.headers["Server"] = "LOD Gateway/2.0.0"
            return response

        return app
