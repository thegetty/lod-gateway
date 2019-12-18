import json

import pytest

from flaskapp.models import db, Record

from datetime import datetime, timezone
from uuid import uuid4

class TestObtainRecord:
    def test_typical_functionality(self, sample_data, client):
        response = client.get(f"/museum/collection/object/{sample_data['record'].uuid}")
        assert response.status_code == 200
        assert "LOD Gateway" in response.headers["Server"]
        assert json.loads(response.data) == sample_data["record"].data

    def test_missing_record(self, sample_data, client):
        response = client.get("/museum/collection/object/no-record")
        assert response.status_code == 404

    def test_empty_data_field(self, sample_data, client):
        test_record = Record.query.get(1)
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

        last_modified = (
            sample_data["record"]
            .datetime_updated.astimezone(timezone.utc)
            .strftime("%a, %d %b %Y %H:%M:%S GMT")
        )

        assert response.headers["Last-Modified"] == last_modified

    def test_last_modified_created(self, sample_data, client):
        record = Record(
            uuid=str(uuid4()),
            datetime_created=datetime(2019, 11, 22, 13, 2, 53, 0),
            datetime_updated=None,
            namespace="museum/collection",
            entity="Object",
            data={"example": "data"},
        )

        db.session.add(record)
        db.session.commit()

        response = client.get(
            f"/museum/collection/object/{record.uuid}"
        )

        # here we use the sample "record" created above which lacks a populated datetime_updated attribute,
        # thus the logic in ./flaskapp/routes/records.py will use the datetime_created for Last-Modified
        last_modified = (
            record
            .datetime_created.astimezone(timezone.utc)
            .strftime("%a, %d %b %Y %H:%M:%S GMT")
        )

        assert response.headers["Last-Modified"] == last_modified
