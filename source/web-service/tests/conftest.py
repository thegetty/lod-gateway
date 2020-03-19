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
def current_app(app):
    with app.app_context():
        yield app


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
def test_db(current_app):
    if current_app.config["ENV"] == "production":
        pytest.exit("Do not run tests that blow away the database in production.")
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


@pytest.fixture(autouse=True)
def requests_mocker(requests_mock):
    """The `requests_mocker()` method supports mocking requests to Neptune, which is inaccessible
    from within CircleCI. The `requests_mocker()` method provides support for mocking successful
    HTTP requests to Neptune, and providing appropriate responses for the limited set of queries
    performed by the /ingest endpoint's `process_neptune_record_set()` method, as well as support
    for generating failed requests to mimic networking issues or connection time-outs."""

    def mocker_text_callback(request, context):
        print(request.url, request.path_url)

        if request.path_url == "/status":
            context.status_code = 200
            return json.dumps({"status": "healthy",})
        elif request.path_url == "/sparql":
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
                        {"results": {"bindings": [{"count": {"value": 0,}}],},}
                    )
                elif sparql.startswith("INSERT DATA"):
                    context.status_code = 200
                    return None
                elif sparql.startswith("DROP GRAPH"):
                    context.status_code = 200
                    return None

        context.status_code = 400
        return None

    neptune = os.getenv("NEPTUNE_ENDPOINT")

    # Configure the default mock handlers; these rely on the `mocker_text_callback()` method defined above
    pattern = re.compile(neptune.replace("/sparql", "/(.*)"))

    requests_mock.head(pattern, text=mocker_text_callback)
    requests_mock.get(pattern, text=mocker_text_callback)
    requests_mock.post(pattern, text=mocker_text_callback)

    # Configure the good mock handlers; these rely on the `mocker_text_callback()` method defined above
    pattern = re.compile(
        neptune.replace("http://", "mock-pass://").replace("/sparql", "/(.*)")
    )

    requests_mock.head(pattern, text=mocker_text_callback)
    requests_mock.get(pattern, text=mocker_text_callback)
    requests_mock.post(pattern, text=mocker_text_callback)

    # Configure the fail mock handlers; these rely on the mocker to throw the configured exception
    pattern = re.compile(
        neptune.replace("http://", "mock-fail://").replace("/sparql", "/(.*)")
    )

    requests_mock.head(pattern, exc=requests.exceptions.ConnectionError)
    requests_mock.get(pattern, exc=requests.exceptions.ConnectionError)
    requests_mock.post(pattern, exc=requests.exceptions.ConnectionError)

    yield requests_mock
