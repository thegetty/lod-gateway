import json
import re

from flask import current_app
from flaskapp.routes.ingest import process_graphstore_record_set, process_record_set
from flaskapp.errors import status_nt


class TestVersioning:
    def test_timemap_in_link_header(self, client, namespace, sample_data):
        response = client.get(f"/{namespace}/{sample_data['record'].entity_id}")

        assert response.status_code == 200

        headers = response.headers

        assert "Memento-Datetime" in headers
        assert "timemap" in headers['Link']
