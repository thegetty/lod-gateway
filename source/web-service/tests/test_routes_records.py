import json

import pytest

from flaskapp.models import db, Records


class TestObtainRecord:
    def test_typical_functionality(self, sample_data, client):
        response = client.get(f"/museum/collection/object/{sample_data['record'].uuid}")
        assert response.status_code == 200
        assert json.loads(response.data) == sample_data["record"].data

    def test_missing_record(self, sample_data, client):
        response = client.get("/museum/collection/object/no-record")
        assert response.status_code == 404

    def test_empty_data_field(self, sample_data, client):
        test_record = Records.query.get(1)
        test_record.data = None
        db.session.add(test_record)
        db.session.commit()
        response = client.get(f"/museum/collection/object/{sample_data['record'].uuid}")
        assert response.status_code == 404

    def test_default_namespace(self, sample_data, client, current_app):
        current_app.config["DEFAULT_URL_NAMESPACE"] = "museum/collection"
        response = client.get(f"/object/{sample_data['record'].uuid}")
        assert response.status_code == 200
        assert json.loads(response.data) == sample_data["record"].data

    def test_last_modified(self, sample_data, client):
        response = client.get(f"/museum/collection/object/{sample_data['record'].uuid}")
        last_modified = sample_data["record"].datetime_updated.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        assert response.headers["Last-Modified"] == last_modified
