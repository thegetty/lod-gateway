import json

from flask import current_app
from flaskapp.routes.ingest import process_neptune_record_set


class TestIngestErrors:
    def test_ingest_GET_not_allowed(self, client, namespace):
        response = client.get(f"/{namespace}/ingest")
        assert response.status_code == 405

    def test_ingest_auth_token_wrong(self, client, namespace):
        response = client.post(
            f"/{namespace}/ingest", headers={"Authorization": "Bearer WrongToken"}
        )
        assert response.status_code == 401

    def test_ingest_auth_token_missing(self, client, namespace):
        response = client.post(f"/{namespace}/ingest")
        assert response.status_code == 401

    def test_ingest_data_missing(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest", headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"No input data found" in response.data

    def test_ingest_single_bad_syntax(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "COMMA IS MISSING AFTER THIS" "age": 31, "city": "New York"}',
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"Could not parse JSON record" in response.data

    def test_ingest_single_id_missing(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {"NO_ID": "object/12345", "name": "John", "age": 31, "city": "New York"}
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found"

    def test_ingest_single_id_empty(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {"id": "     ", "name": "John", "age": 31, "city": "New York"}
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
        assert b"ID for the JSON record not found" in response.data

    def test_ingest_multiple_bad_syntax(self, client, namespace, auth_token):
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

    def test_ingest_multiple_id_missing(self, client, namespace, auth_token):
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

    def test_ingest_multiple_id_empty(self, client, namespace, auth_token):
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

    def test_ingest_error_response_json(self, client, namespace, auth_token):
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

    def test_ingest_bad_auth_header_error_response(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}\n',
            headers={"Authorization": "BadAuthorizationHeader"},
        )
        # check for correct 'error json'
        assert json.loads(response.data)

        # validate 'error json' details
        data = response.json
        assert data["errors"]
        assert data["errors"][0]["status"] == 400
        assert data["errors"][0]["title"] == "Bad Authorization Header"
        assert (
            data["errors"][0]["detail"] == "Syntax of Authorization header is invalid"
        )


class TestIngestSuccess:
    def test_ingest_single(self, client, namespace, auth_token, test_db):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {"id": "object/12345", "name": "John", "age": 31, "city": "New York"}
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert b"object/12345" in response.data

    def test_ingest_multiple(self, client, namespace, auth_token, test_db):
        response = client.post(
            f"/{namespace}/ingest",
            data='{"id": "person/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "object/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n"
            + '{"id": "group/12345", "name": "John", "age": 31, "city": "New York"}'
            + "\n",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert b"group/12345" in response.data


class TestNeptuneConnection:
    def test_neptune_connection_good(self, client, namespace, auth_token):
        query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
        update_endpoint = current_app.config["SPARQL_UPDATE_ENDPOINT"]
        records = [
            json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "https://data.getty.edu/museum/collection/object/12345",
                    "type": "HumanMadeObject",
                    "_label": "Irises",
                }
            )
        ]
        asserted = process_neptune_record_set(
            records,
            query_endpoint.replace("http://", "mock-pass://"),
            update_endpoint.replace("http://", "mock-pass://"),
        )
        assert asserted == True

    def test_neptune_connection_fail(self, client, namespace, auth_token):
        query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
        update_endpoint = current_app.config["SPARQL_UPDATE_ENDPOINT"]
        records = [
            json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "https://data.getty.edu/museum/collection/object/12345",
                    "type": "HumanMadeObject",
                    "_label": "Irises",
                }
            )
        ]
        asserted = process_neptune_record_set(
            records,
            query_endpoint.replace("http://", "mock-fail://"),
            update_endpoint.replace("http://", "mock-fail://"),
        )
        assert asserted and asserted.code == 500
