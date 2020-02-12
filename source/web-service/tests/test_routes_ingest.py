import pytest

from flaskapp.models import db
from flaskapp.models.record import Record

from datetime import datetime, timezone
from uuid import uuid4


class TestIngestRoute:
    def test_ingest_GET_not_allowed(self, client, namespace):
        response = client.get(f"/{namespace}/ingest")
        assert response.status_code == 405

    def test_ingest_auth_token_wrong(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest", headers={"Authorization": "wrong token"}
        )
        assert response.status_code == 401

    def test_ingest_auth_token_missing(self, client, namespace):
        response = client.post(f"/{namespace}/ingest")
        assert response.status_code == 401

    def test_ingest_POST(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest", headers={"Authorization": auth_token},
        )
        assert response.status_code == 422
        assert b"No input data found" in response.data
