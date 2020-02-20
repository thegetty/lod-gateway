import pytest
import json


class TestIngestValidate:
    # def test_ingest_validate_single(self, client, namespace, auth_token):
    #     response = client.post(
    #         f"/{namespace}/ingest",
    #         data=json.dumps(
    #             {"id": "object/12345", "name": "John", "age": 31, "city": "New York"}
    #         ),
    #         headers={"Authorization": "Bearer " + auth_token},
    #     )
    #     assert response.status_code == 200

    def test_ingest_validate_single_bad_syntax(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "COMMA IS MISSING AFTER THIS" "age": 31, "city": "New York"}',
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"Could not parse JSON record" in response.data

    def test_ingest_validate_single_no_id(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {"NO_ID": "object/12345", "name": "John", "age": 31, "city": "New York"}
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found"

    def test_ingest_validate_single_id_empty(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {"id": "     ", "name": "John", "age": 31, "city": "New York"}
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found" in response.data

    # def test_ingest_validate_multiple(self, client, namespace, auth_token):
    #     response = client.post(
    #         f"/{namespace}/ingest",
    #         data='{"id": "person/12345", "name": "John", "age": 31, "city": "New York"}'
    #         + "\n"
    #         + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
    #         + "\n"
    #         + '{"id": "group/12345", "name": "John", "age": 31, "city": "New York"}'
    #         + "\n",
    #         headers={"Authorization": "Bearer " + auth_token},
    #     )
    #     assert response.status_code == 200

    def test_ingest_validate_multiple_bad_syntax(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "COMMA IS MISSING AFTER THIS" "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"Could not parse JSON record" in response.data

    def test_ingest_validate_multiple_no_id(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"NO_ID": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found" in response.data

    def test_ingest_validate_multiple_id_empty(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "     ", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found" in response.data

    def test_ingest_validate_error_response(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "     ", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
            headers={"Authorization": "Bearer " + auth_token},
        )
        # check for correct 'error json'
        assert json.loads(response.data)

        # validate 'error json' details
        data = json.loads(response.data)
        assert data["errors"]
        assert data["errors"][0]["status"] == 422
        assert data["errors"][0]["source"]["line number"] == 3
        assert data["errors"][0]["title"] == "ID Missing"
        assert data["errors"][0]["detail"] == "ID for the JSON record not found"
