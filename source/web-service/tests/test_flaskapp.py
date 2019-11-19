import os
import tempfile

import pytest

from flaskapp import create_app


@pytest.fixture
def app():
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):

    testing_client = app.test_client()

    ctx = app.app_context()
    ctx.push()
    yield testing_client  # this is where the testing happens!
    ctx.pop()


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to the Getty's Linked Open Data Gateway Service" in response.data
