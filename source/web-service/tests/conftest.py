import json
import pytest
import os
import re
import requests
import urllib.parse

from datetime import datetime
from uuid import uuid4

from flaskapp import create_app
from flaskapp.models import db
from flaskapp.models.activity import Activity
from flaskapp.models.record import Record
from flaskapp.utilities import Event


@pytest.fixture
def app(mocker):
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def app_no_rdf(mocker):
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    flask_app.config["PROCESS_RDF"] = "False"
    flask_app.config["SPARQL_QUERY_ENDPOINT"] = None
    flask_app.config["SPARQL_UPDATE_ENDPOINT"] = None

    yield flask_app


@pytest.fixture
def current_app(app):
    with app.app_context():
        yield app


@pytest.fixture
def current_app_no_rdf(app_no_rdf):
    with app_no_rdf.app_context():
        yield app_no_rdf


@pytest.fixture
def auth_token(current_app):
    yield current_app.config["AUTH_TOKEN"]


@pytest.fixture
def namespace(current_app):
    yield current_app.config["NAMESPACE"]


@pytest.fixture
def base_url(current_app, namespace):
    b_url = current_app.config["BASE_URL"]
    return f"{b_url}/{namespace}"


@pytest.fixture
def client(app):

    testing_client = app.test_client()

    ctx = app.app_context()
    ctx.push()
    yield testing_client  # this is where the testing happens!
    ctx.pop()


@pytest.fixture
def client_no_rdf(app_no_rdf):

    testing_client = app_no_rdf.test_client()

    ctx = app_no_rdf.app_context()
    ctx.push()
    yield testing_client  # this is where the testing happens!
    ctx.pop()


@pytest.fixture
def test_db(current_app):
    # `SQLALCHEMY_DATABASE_URI` maps to the `DATABASE` environment variable through Flask's create_app() setup
    if ".amazonaws.com" in current_app.config["SQLALCHEMY_DATABASE_URI"]:
        pytest.exit(
            ">>> WARNING – Cannot run the PyTest suite as the `DATABASE` environment variable currently references an AWS-hosted database, which will be *DESTROYED* by running the test suite! <<<"
        )
    db.drop_all()
    db.create_all()
    return db


@pytest.fixture
def test_db_no_rdf(current_app_no_rdf):
    # `SQLALCHEMY_DATABASE_URI` maps to the `DATABASE` environment variable through Flask's create_app() setup
    if ".amazonaws.com" in current_app_no_rdf.config["SQLALCHEMY_DATABASE_URI"]:
        pytest.exit(
            ">>> WARNING – Cannot run the PyTest suite as the `DATABASE` environment variable currently references an AWS-hosted database, which will be *DESTROYED* by running the test suite! <<<"
        )
    db.drop_all()
    db.create_all()
    return db


@pytest.fixture
def sample_record(test_db):
    def _sample_record():
        record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            datetime_updated=datetime(2019, 12, 18, 11, 22, 7),
            data={"example": "data"},
        )
        test_db.session.add(record)
        test_db.session.commit()
        return record

    return _sample_record


@pytest.fixture
def sample_activity(test_db, sample_record):
    def _sample_activity(record_id):

        if not Record.query.get(record_id):
            record = sample_record()
            record_id = record.id

        activity = Activity(
            uuid=str(uuid4()),
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            record_id=record_id,
            event=Event.Create.name,
        )
        test_db.session.add(activity)
        test_db.session.commit()
        return activity

    return _sample_activity


@pytest.fixture
def sample_data(sample_record, sample_activity):
    record = sample_record()
    activity = sample_activity(record.id)
    return {"record": record, "activity": activity}


@pytest.fixture
def sample_record_with_ids(test_db):
    def _sample_record():
        record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            datetime_updated=datetime(2019, 12, 18, 11, 22, 7),
            data={
                "id": "object/123",
                "example": "data",
                "nested": [
                    {
                        "id": "object/456",
                    },
                    {
                        "id": "object/789",
                    },
                ],
            },
        )
        test_db.session.add(record)
        test_db.session.commit()
        return record

    return _sample_record


@pytest.fixture
def linguisticobject():
    def _generator(name, id):
        return {
            "@context": "https://linked.art/ns/v1/linked-art.json",
            "id": id,
            "content": name,
            "classified_as": [
                {
                    "id": "https://data.getty.edu/local/thesaurus/aspace-subject-topical",
                    "type": "Type",
                    "_label": "Subject Heading - Topical",
                }
            ],
        }

    return _generator


@pytest.fixture
def sample_jsonldrecord_with_id(test_db, linguisticobject):
    def _sample_record(name, id):
        record = Record(
            entity_id=id,
            entity_type="LinguisticObject",
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            datetime_updated=datetime(2019, 12, 18, 11, 22, 7),
            data=linguisticobject(name, id),
        )
        test_db.session.add(record)
        test_db.session.commit()
        return record

    return _sample_record


@pytest.fixture
def sample_activity_with_ids(test_db, sample_record_with_ids):
    def _sample_activity(record_id):

        if not Record.query.get(record_id):
            record = sample_record_with_ids()
            record_id = record.id

        activity = Activity(
            uuid=str(uuid4()),
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            record_id=record_id,
            event=Event.Create.name,
        )
        test_db.session.add(activity)
        test_db.session.commit()
        return activity

    return _sample_activity


@pytest.fixture
def sample_data_with_ids(sample_record_with_ids, sample_activity_with_ids):
    record = sample_record_with_ids()
    activity = sample_activity_with_ids(record.id)
    return {"record": record, "activity": activity}


@pytest.fixture(autouse=True)
def requests_mocker(requests_mock):
    """The `requests_mocker()` method supports mocking requests to the graph store, which is inaccessible
    from within CircleCI. The `requests_mocker()` method provides support for mocking successful
    HTTP requests to the graph store, and providing appropriate responses for the limited set of queries
    performed by the /ingest endpoint's `process_graphstore_record_set()` method, as well as support
    for generating failed requests to mimic networking issues or connection time-outs."""

    def mocker_text_callback(request, context):
        print(request.url, request.path_url)

        if request.path_url.endswith("/status"):
            context.status_code = 200
            return json.dumps(
                {
                    "status": "healthy",
                }
            )
        elif request.path_url.endswith("/sparql") or request.path_url.endswith(
            "/update"
        ):  # TODO: this is not portable
            sparql = None

            if request.body.startswith("query=") or request.body.startswith("update="):
                params = urllib.parse.parse_qsl(request.body)
                if params:
                    for param in params:
                        if param[0] == "query" or param[0] == "update":
                            sparql = param[1]
                            break

            if sparql:
                if sparql.startswith("SELECT"):
                    context.status_code = 200
                    return json.dumps(
                        {
                            "results": {
                                "bindings": [
                                    {
                                        "count": {
                                            "value": 0,
                                        }
                                    }
                                ],
                            },
                        }
                    )
                elif sparql.startswith("INSERT DATA"):
                    context.status_code = 200
                    return None
                elif sparql.startswith("DELETE {GRAPH <"):
                    if "failure_uri_503" in sparql:
                        context.status_code = 503
                        context.headers["Retry-After"] = 5
                    else:
                        # Graph replace SPARQL update
                        context.status_code = 200
                    return None
                elif sparql.startswith("DROP SILENT GRAPH"):
                    context.status_code = 200
                    return None
                elif sparql.startswith("DROP GRAPH"):
                    if "failure_upon_deletion" in sparql:
                        context.status_code = 500
                    else:
                        context.status_code = 200
                    return None
        else:
            print(f"*** unhandled mock request: {request.path_url}")

        context.status_code = 400
        return None

    query_endpoint = os.getenv("SPARQL_QUERY_ENDPOINT")
    update_endpoint = os.getenv("SPARQL_UPDATE_ENDPOINT")

    # Configure the default mock handlers; these rely on the `mocker_text_callback()` method defined above
    query_pattern = re.compile(query_endpoint.replace("/sparql", "/(.*)"))
    update_pattern = re.compile(
        update_endpoint.replace("/update", "/(.*)")
    )  # TODO: this is not portable

    for pattern in (query_pattern, update_pattern):
        requests_mock.options(pattern, text=mocker_text_callback)
        requests_mock.head(pattern, text=mocker_text_callback)
        requests_mock.get(pattern, text=mocker_text_callback)
        requests_mock.post(pattern, text=mocker_text_callback)

    # Configure the good mock handlers; these rely on the `mocker_text_callback()` method defined above
    query_pattern = re.compile(
        query_endpoint.replace("http://", "mock-pass://").replace("/sparql", "/(.*)")
    )
    update_pattern = re.compile(
        update_endpoint.replace("http://", "mock-pass://").replace(
            "/update", "/(.*)"
        )  # TODO: this is not portable
    )

    for pattern in (query_pattern, update_pattern):
        requests_mock.options(pattern, text=mocker_text_callback)
        requests_mock.head(pattern, text=mocker_text_callback)
        requests_mock.get(pattern, text=mocker_text_callback)
        requests_mock.post(pattern, text=mocker_text_callback)

    # Configure the fail mock handlers; these rely on the mocker to throw the configured exception
    query_pattern = re.compile(
        query_endpoint.replace("http://", "mock-fail://").replace("/sparql", "/(.*)")
    )
    update_pattern = re.compile(
        update_endpoint.replace("http://", "mock-fail://").replace(
            "/update", "/(.*)"
        )  # TODO: this is not portable
    )

    for pattern in (query_pattern, update_pattern):
        requests_mock.options(pattern, exc=requests.exceptions.ConnectionError)
        requests_mock.head(pattern, exc=requests.exceptions.ConnectionError)
        requests_mock.get(pattern, exc=requests.exceptions.ConnectionError)
        requests_mock.post(pattern, exc=requests.exceptions.ConnectionError)

    # Allow all other non-matched URL patterns to be routed to real HTTP requests
    pattern = re.compile("http(s)://(.*)")
    requests_mock.options(pattern, real_http=True)
    requests_mock.head(pattern, real_http=True)
    requests_mock.get(pattern, real_http=True)
    requests_mock.post(pattern, real_http=True)
    requests_mock.put(pattern, real_http=True)
    requests_mock.patch(pattern, real_http=True)
    requests_mock.delete(pattern, real_http=True)

    yield requests_mock
