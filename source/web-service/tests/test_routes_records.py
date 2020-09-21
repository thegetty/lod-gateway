import json

from flaskapp.models import db
from flaskapp.models.record import Record
from flaskapp.utilities import format_datetime, checksum_json

from datetime import datetime, timezone
from uuid import uuid4


class TestObtainRecord:
    def test_typical_functionality(self, sample_data, client, namespace):
        response = client.get(f"/{namespace}/{sample_data['record'].entity_id}")
        assert response.status_code == 200
        assert "LOD Gateway" in response.headers["Server"]
        assert json.loads(response.data) == sample_data["record"].data

    def test_missing_record(self, sample_data, client, namespace):
        response = client.get(f"/{namespace}/object/no-record")
        assert response.status_code == 404

    def test_empty_data_field(self, sample_data, client, namespace):
        test_record = Record.query.get(1)
        test_record.data = None
        db.session.add(test_record)
        db.session.commit()
        response = client.get(f"/{namespace}/{sample_data['record'].entity_id}")
        assert response.status_code == 404

    def test_last_modified(self, sample_data, client, namespace):
        response = client.get(f"/{namespace}/{sample_data['record'].entity_id}")
        last_modified = format_datetime(sample_data["record"].datetime_updated)
        assert response.headers["Last-Modified"] == last_modified

    def test_last_modified_created(self, sample_data, client, namespace):
        record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime(2019, 11, 22, 13, 2, 53, 0),
            datetime_updated=datetime(2019, 11, 22, 13, 2, 53, 0),
            data={"example": "data"},
            checksum=checksum_json({"example": "data"}),
        )

        db.session.add(record)
        db.session.commit()

        response = client.get(f"/{namespace}/{record.entity_id}")

        last_modified = format_datetime(record.datetime_updated)
        assert response.headers["Last-Modified"] == last_modified

    def test_etag_304(self, sample_data, client, namespace):
        checksum_value = checksum_json({"example": "data"})

        record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime(2019, 11, 22, 13, 2, 53, 0),
            datetime_updated=datetime(2019, 11, 22, 13, 2, 53, 0),
            data={"example": "data"},
            checksum=checksum_value,
        )

        db.session.add(record)
        db.session.commit()

        response = client.get(
            f"/{namespace}/{record.entity_id}",
            headers={"If-None-Match": checksum_value},
        )
        assert response.status_code == 304

    def test_etag_200_without_match(self, sample_data, client, namespace):
        checksum_value = checksum_json({"example": "data"})

        record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime(2019, 11, 22, 13, 2, 53, 0),
            datetime_updated=datetime(2019, 11, 22, 13, 2, 53, 0),
            data={"example": "data"},
            checksum=checksum_value,
        )

        db.session.add(record)
        db.session.commit()

        response = client.get(
            f"/{namespace}/{record.entity_id}",
            headers={"If-None-Match": "something that wont match"},
        )
        assert response.status_code == 200
