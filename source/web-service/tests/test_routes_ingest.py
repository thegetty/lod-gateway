import json

import pytest

from flaskapp.models import db
from flaskapp.models.record import Record

from datetime import datetime, timezone
from uuid import uuid4


class TestIngestRoute:
    def test_ingest_GET_not_allowed(self, client, current_app):
        # namespace = current_app.config["DEFAULT_URL_NAMESPACE"]
        namespace = "museum/collection"
        response = client.get(namespace + "/ingest")
        assert response.status_code == 405

    def test_ingest_POST(self, client, current_app):
        # namespace = current_app.config["DEFAULT_URL_NAMESPACE"]
        namespace = "musemu/collection"
        response = client.post(namespace + "/ingest")
        assert response.status_code == 200
