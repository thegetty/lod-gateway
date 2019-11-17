import os
import tempfile

import pytest

from flaskapp import create_app


@pytest.fixture(scope="module")
def test_client():
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    testing_client = flask_app.test_client()

    ctx = flask_app.app_context()
    ctx.push()
    yield testing_client  # this is where the testing happens!
    ctx.pop()


def test_home_page(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert b"Welcome to the Getty's Linked Open Data Gateway Service" in response.data
