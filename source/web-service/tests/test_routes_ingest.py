import json

import pytest

from flaskapp.models import db
from flaskapp.models.record import Record

from datetime import datetime, timezone
from uuid import uuid4


class TestIngestRoute:
    def test_ingest_GET_not_allowed(self, client, current_app):
        response = client.get("/ns/ingest")
        assert response.status_code == 405

    def test_ingest_POST(self, client, current_app):
        response = client.post("/ns/ingest")
        assert response.status_code == 200
