from datetime import datetime

import pytest

from flaskapp import create_app
from flaskapp.models import db, Records


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
def client(app):

    testing_client = app.test_client()

    ctx = app.app_context()
    ctx.push()
    yield testing_client  # this is where the testing happens!
    ctx.pop()


@pytest.fixture
def sample_data(current_app):
    if current_app.config["ENV"] == "production":
        pytest.exit("Do not run tests that blow away the database in production.")
    db.drop_all()
    db.create_all()
    test_record = Records(
        uuid="0e5e1a63-40ac-41a7-b055-e62ba173fa87",
        datetime_created=datetime(2019, 11, 22, 13, 2, 53, 0),
        datetime_updated=datetime(2019, 11, 22, 13, 2, 53, 0),
        namespace="museum/collection",
        entity="Object",
        data={"example": "data"},
    )
    db.session.add(test_record)
    db.session.commit()
    return test_record
