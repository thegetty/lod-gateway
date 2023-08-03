import logging
import logging.config
from os import environ, getenv
from flaskapp.logging_configuration import get_logging_config
import json

from datetime import datetime, timedelta
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
from flaskapp.base_graph_utils import base_graph_filter, document_loader


# For JSON access logs:
from pythonjsonlogger.jsonlogger import JsonFormatter, merge_record_extra


class GunicornLogFormatter(JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        """
        This method allows us to inject gunicorn's args as fields for the formatter
        """
        super(GunicornLogFormatter, self).add_fields(log_record, record, message_dict)
        for field in self._required_fields:
            if field in self.rename_fields:
                log_record[self.rename_fields[field]] = record.args.get(field)
            else:
                log_record[field] = record.args.get(field)


# top-level logging configuration should provide the basic configuration for any logger Flask sets in the
# create_app step (and in other modules).
LOG_LEVEL = getenv("DEBUG_LEVEL", "INFO")
ENABLE_JSON = getenv("JSON_LOGGING", "true").lower() == "true"
ENABLE_ACCESS_JSON = getenv("ACCESS_JSON_LOGGING", "true").lower() == "true"
logging.config.dictConfig(
    get_logging_config(LOG_LEVEL, json=ENABLE_JSON, json_access=ENABLE_ACCESS_JSON)
)


def create_app():
    app = Flask(__name__)

    app.config["DEBUG_LEVEL"] = getenv("DEBUG_LEVEL", "INFO")
    app.config["FLASK_ENV"] = getenv("FLASK_ENV", "production")

    app.logger.info(f"LOD Gateway logging at level {app.config['DEBUG_LEVEL']}")

    CORS(app, send_wildcard=True)
    # Setup global configuration
    app.config["AUTH_TOKEN"] = environ["AUTHORIZATION_TOKEN"]
    app.config["VERSION_AUTH"] = environ.get("VERSIONING_AUTHENTICATION", "True")
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

    # SPARQL endpoints only apply if LOD Gateway is configured to process input into RDF triples
    app.config["RDF_BASE_GRAPH"] = None
    app.config["FULL_BASE_GRAPH"] = None
    app.config["RDF_FILTER_SET"] = None
    app.config["USE_PYLD_REFORMAT"] = True
    app.config["PROCESS_RDF"] = False
    if environ.get("PROCESS_RDF", "False").lower() == "true":
        app.config["PROCESS_RDF"] = True
        app.logger.info(f"RDF Processing functionality is enabled.")
        app.config["SPARQL_QUERY_ENDPOINT"] = environ["SPARQL_QUERY_ENDPOINT"]
        app.config["SPARQL_UPDATE_ENDPOINT"] = environ["SPARQL_UPDATE_ENDPOINT"]

        # Testing mode for basegraph?
        app.config["TESTMODE_BASEGRAPH"] = (
            environ.get("TESTMODE_BASEGRAPH", "False").lower() == "true"
        )

        app.config["USE_PYLD_REFORMAT"] = (
            environ.get("USE_PYLD_REFORMAT", "true").lower() == "true"
        )

        app.logger.info(
            "Using PyLD for parsing/reserialization"
            if app.config["USE_PYLD_REFORMAT"]
            else "Using RDFLib for parsing/reserialization"
        )

        # set up a default RDF context cache?
        doccache_default_expiry = int(environ.get("RDF_CONTEXT_CACHE_EXPIRES", 30))
        app.config["RDF_DOCLOADER"] = document_loader(
            docCache={}, cache_expires=doccache_default_expiry
        )

        # Preload the cache?
        # See the base_graph_utils.document_loader for what structure to use for the cache object
        # What should be in the environment variable is a JSON-encoded string, eg:
        # >>> print(json.dumps(docCache))
        # and copy and paste the result into the field.
        if doccache_json := environ.get("RDF_CONTEXT_CACHE"):
            try:
                doc_cache = json.loads(doccache_json)
                app.config["RDF_DOCLOADER"] = document_loader(
                    docCache=doc_cache, cache_expires=doccache_default_expiry
                )
            except json.decoder.JSONDecodeError as e:
                app.logger.error(
                    f"The data in ENV: 'RDF_CONTEXT_CACHE' is not JSON! Will not load presets."
                )
    else:
        app.logger.info(f"RDF Processing functionality is disabled.")

    # Setting the limit on number of records returned due to a glob browse request
    try:
        app.config["BROWSE_PAGE_SIZE"] = int(environ.get("BROWSE_PAGE_SIZE", 200))
    except (ValueError, TypeError) as e:
        app.config["BROWSE_PAGE_SIZE"] = 200

    # PATCH_UPDATE_THRESHOLD
    app.config["PATCH_UPDATE_THRESHOLD"] = None
    if patch_threshold := environ.get("PATCH_UPDATE_THRESHOLD"):
        try:
            patch_threshold = int(patch_threshold)
            app.config["PATCH_UPDATE_THRESHOLD"] = timedelta(minutes=patch_threshold)
        except TypeError.ValueError as e:
            app.logger.warning(
                f"Value in the PATCH_UPDATE_THRESHOLD env var was not understood as a number"
            )

    app.logger.info(
        f"RDF GRAPH PATCH enabled, edit threshold is set to a duration of {app.config['PATCH_UPDATE_THRESHOLD']}"
        if app.config["PATCH_UPDATE_THRESHOLD"]
        else "RDF GRAPH PATCH is disabled"
    )

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

    app.config["LINK_HEADER_PREV_VERSION"] = False
    if environ.get("LINK_HEADER_PREV_VERSION", "False").lower() == "true":
        app.config["LINK_HEADER_PREV_VERSION"] = True

    app.logger.info(
        "Versioning enabled"
        if app.config["KEEP_LAST_VERSION"]
        else "Versioning is disabled"
    )

    app.config["SUBADDRESSING"] = False
    if environ.get("SUBADDRESSING", "False").lower() == "true":
        app.config["SUBADDRESSING"] = True
        app.config["SUBADDRESSING_MAX_PARTS"] = 4
        app.config["SUBADDRESSING_MIN_PARTS"] = 1

        if environ.get("SUBADDRESSING_MAX_PARTS") is not None:
            try:
                app.config["SUBADDRESSING_MAX_PARTS"] = int(
                    environ.get("SUBADDRESSING_MAX_PARTS")
                )
            except (ValueError, TypeError) as e:
                app.logger.error(
                    f"Value for SUBADDRESSING_MAX_PARTS could not be interpreted as an integer. Ignoring."
                )
        if environ.get("SUBADDRESSING_MIN_PARTS") is not None:
            try:
                app.config["SUBADDRESSING_MIN_PARTS"] = int(
                    environ.get("SUBADDRESSING_MIN_PARTS")
                )
            except (ValueError, TypeError) as e:
                app.logger.error(
                    f"Value for SUBADDRESSING_MIN_PARTS could not be interpreted as an integer. Ignoring."
                )

    app.logger.info(
        f"Subaddressing enabled - search depth up to (app.config['SUBADDRESSING_MAX_PARTS']"
        if app.config["SUBADDRESSING"]
        else "Subaddressing disabled"
    )

    if app.config["FLASK_ENV"].lower() == "development":
        app.config["SQLALCHEMY_ECHO"] = True

    db.init_app(app)
    compress = Compress()
    if app.config["FLASK_GZIP_COMPRESSION"].lower() == "true":
        compress.init_app(app)
    migrate = Migrate(app, db)

    if environ.get("LOCAL_THESAURUS_URL", None) is not None:
        app.config["LOCAL_THESAURUS_URL"] = environ["LOCAL_THESAURUS_URL"]
        local_thesaurus.populate_db(app.app_context())

    with app.app_context():
        ns = app.config["NAMESPACE"]

        # Needs the app context and the db to be initialized:
        if basegraph := environ.get("RDF_BASE_GRAPH"):
            app.config["RDF_BASE_GRAPH"] = basegraph
            app.config[
                "FULL_BASE_GRAPH"
            ] = f'{app.config["BASE_URL"]}/{app.config["NAMESPACE_FOR_RDF"]}/{basegraph}'

            app.config["RDF_FILTER_SET"] = base_graph_filter(
                app.config["RDF_BASE_GRAPH"], app.config["FULL_BASE_GRAPH"]
            )

        app.config["SERVER_CAPABILITIES"] = (
            ", ".join(
                [
                    f"{txt}: '{app.config[k]}'"
                    for k, txt in [
                        ("PROCESS_RDF", "JSON-LD"),
                        ("FULL_BASE_GRAPH", "Base Graph"),
                        ("SUBADDRESSING", "Subaddressing"),
                        ("KEEP_LAST_VERSION", "Versioning"),
                        ("PATCH_UPDATE_THRESHOLD", "RDF Graph PATCH"),
                    ]
                    if app.config.get(k)
                ]
            )
            or ""
        )

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
            response.headers["Server"] = "LOD Gateway/2.3.0"
            response.headers["X-LODGATEWAY-CAPABILITIES"] = app.config[
                "SERVER_CAPABILITIES"
            ]

            # Cache-control
            response.headers["Cache-Control"] = "no-cache"

            return response

        return app
