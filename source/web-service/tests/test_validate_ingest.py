import pytest
import json


class TestIngestValidate:
    def test_ingest_validate_single(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {"id": "object/12345", "name": "John", "age": 31, "city": "New York"}
            ),
        )
        assert response.status_code == 200

    def test_ingest_validate_single_bad_syntax(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "COMA IS MISSING AFTER THIS" "age": 31, "city": "New York"}',
        )
        assert response.status_code == 422
        assert b"Could not parse JSON record" in response.data

    def test_ingest_validate_single_no_id(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {"NO_ID": "object/12345", "name": "John", "age": 31, "city": "New York"}
            ),
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found"

    def test_ingest_validate_single_id_empty(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {"id": "     ", "name": "John", "age": 31, "city": "New York"}
            ),
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found" in response.data

    def test_ingest_validate_multiple(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "person/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "group/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 200

    def test_ingest_validate_multiple_bad_syntax(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "COMA IS MISSING AFTER THIS" "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 422
        assert b"Could not parse JSON record" in response.data

    def test_ingest_validate_multiple_no_id(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"NO_ID": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found" in response.data

    def test_ingest_validate_multiple_id_empty(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "     ", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found" in response.data
