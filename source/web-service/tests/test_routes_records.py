import json

from flaskapp.models import db
from flaskapp.models.record import Record
from flaskapp.utilities import format_datetime, checksum_json
from flaskapp.utilities import containerRecursiveCallback, idPrefixer

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

    def test_prefix_record_ids_recursive(
        self, sample_data_with_ids, client, namespace, current_app
    ):
        current_app.config["PREFIX_RECORD_IDS"] = "RECURSIVE"

        response = client.get(
            f"/{namespace}/{sample_data_with_ids['record'].entity_id}"
        )

        # Assemble the record 'id' attribute base URL prefix
        idPrefix = (
            current_app.config["BASE_URL"] + "/" + current_app.config["NAMESPACE"]
        )

        # For this test case, we prefix any record "id" field that requires it
        # so here we perform the same prefixing call as the records endpoint
        # where the recursive flag is set to True, and then compare the results
        data = containerRecursiveCallback(
            data=sample_data_with_ids["record"].data,
            attr="id",
            callback=idPrefixer,
            prefix=idPrefix,
            recursive=True,
        )

        assert response.status_code == 200
        assert "LOD Gateway" in response.headers["Server"]
        assert json.loads(response.data) == data

    def test_prefix_record_ids_top(
        self, sample_data_with_ids, client, namespace, current_app
    ):
        current_app.config["PREFIX_RECORD_IDS"] = "TOP"

        response = client.get(
            f"/{namespace}/{sample_data_with_ids['record'].entity_id}"
        )

        # Assemble the record 'id' attribute base URL prefix
        idPrefix = (
            current_app.config["BASE_URL"] + "/" + current_app.config["NAMESPACE"]
        )

        # For this test case, we only prefix the top-level record "id" field
        # so here we perform the same prefixing call as the records endpoint
        # where the recursive flag is set to False, and then compare the results
        data = containerRecursiveCallback(
            data=sample_data_with_ids["record"].data,
            attr="id",
            callback=idPrefixer,
            prefix=idPrefix,
            recursive=False,
        )

        assert response.status_code == 200
        assert "LOD Gateway" in response.headers["Server"]
        assert json.loads(response.data) == data

    def test_prefix_record_ids_none(
        self, sample_data_with_ids, client, namespace, current_app
    ):
        current_app.config["PREFIX_RECORD_IDS"] = "NONE"

        response = client.get(
            f"/{namespace}/{sample_data_with_ids['record'].entity_id}"
        )

        # For this test case, we do not prefix any record "id" fields
        # so we compare the same record data as-is with the client data
        data = sample_data_with_ids["record"].data

        assert response.status_code == 200
        assert "LOD Gateway" in response.headers["Server"]
        assert json.loads(response.data) == data
