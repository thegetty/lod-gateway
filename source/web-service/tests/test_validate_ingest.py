import pytest
import json


class TestIngestValidate:
    def test_ingest_validate_single(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data=json.dumps(
                {"id": "object/12345", "name": "John", "age": 31, "city": "New York"}
            ),
        )
        assert response.status_code == 200

    def test_ingest_validate_single_bad_syntax(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data='{"id": "object/12345", "name": "John" "age": 31, "city": "New York"}',
        )
        assert response.status_code == 422
        assert b"Could not parse JSON record" in response.data

    def test_ingest_validate_single_no_id(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data=json.dumps(
                {"ic": "object/12345", "name": "John", "age": 31, "city": "New York"}
            ),
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found"

    def test_ingest_validate_single_wrong_id_format(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data=json.dumps(
                {"id": "12345", "name": "John", "age": 31, "city": "New York"}
            ),
        )
        assert response.status_code == 422
        assert b"Wrong ID format" in response.data

    def test_ingest_validate_multiple(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data='{"id": "person/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "group/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 200

    def test_ingest_validate_multiple_bad_syntax(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John" "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 422
        assert b"Could not parse JSON record" in response.data

    def test_ingest_validate_multiple_no_id(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"ic": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found" in response.data

    def test_ingest_validate_multiple_wrong_id_format(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 422
        assert b"Wrong ID format" in response.data
