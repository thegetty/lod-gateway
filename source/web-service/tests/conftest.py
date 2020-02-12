from datetime import datetime
from uuid import uuid4

import pytest

from flaskapp import create_app
from flaskapp.models import db
from flaskapp.models.activity import Activity
from flaskapp.models.record import Record


@pytest.fixture
def app():
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
            uuid=str(uuid4()),
            datetime_created=datetime(2019, 11, 22, 13, 2, 53, 0),
            datetime_updated=datetime(2019, 12, 18, 11, 22, 7, 0),
            namespace="museum/collection",
            entity="Object",
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
            datetime_created=datetime(2019, 11, 22, 13, 2, 53, 0),
            namespace="museum/collection",
            entity="Object",
            record_id=record_id,
            event="Create",
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
