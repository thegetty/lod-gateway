import pytest


from flaskapp.models import db
from flaskapp.models.record import Record

from datetime import datetime, timezone
from uuid import uuid4


class TestIngestRoute:
    def test_ingest_GET_not_allowed(self, client, namespace):
        response = client.get(f"/{namespace}/ingest")
        assert response.status_code == 405

    # Empty body should trigger 422 with 'no data' description
    # Non empty request body is tested in 'validate_ingest' test
    def test_ingest_POST(self, client, namespace):
        response = client.post(f"/{namespace}/ingest")
        assert response.status_code == 422
        assert b"No input data found" in response.data
