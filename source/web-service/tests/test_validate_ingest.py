import pytest
import json


class TestIngestValidate:
    def test_ingest_validate_single(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data=json.dumps(
                {"id": "12345", "name": "John", "age": 31, "city": "New York"}
            ),
        )
        assert response.status_code == 200

    def test_ingest_validate_single_bad(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data='{"id": "12345", "name": "John" "age": 31, "city": "New York"}',
        )
        assert response.status_code == 422

    def test_ingest_validate_single_noID(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data=json.dumps(
                {"ic": "12345", "name": "John", "age": 31, "city": "New York"}
            ),
        )
        assert response.status_code == 422

    def test_ingest_validate_multiple(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data='{"id": "12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 200

    def test_ingest_validate_multiple_bad(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data='{"id": "12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "12345", "name": "John" "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 422

    def test_ingest_validate_multiple_noID(self, client, current_app):
        ns = current_app.config["NAMESPACE"]
        response = client.post(
            f"/{ns}/ingest",
            data='{"id": "12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"ic": "12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
        )
        assert response.status_code == 422
