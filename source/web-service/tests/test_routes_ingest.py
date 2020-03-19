import json
import pytest
import re
import requests
import urllib.parse

from flask import current_app
from flaskapp.routes.ingest import process_neptune_record_set


@pytest.fixture()
def requests_mocker(requests_mock):
    """The `requests_mocker()` method supports mocking requests to Neptune, which is inaccessible
    from within CircleCI. The `requests_mocker()` method provides support for mocking successful
    HTTP requests to Neptune, and providing appropriate responses for the limited set of queries
    performed by the /ingest endpoint's `process_neptune_record_set()` method, as well as support
    for generating failed requests to mimic networking issues or connection time-outs."""

    def mocker_text_callback(request, context):
        if request.path_url == "/status":
            context.status_code = 200
            return json.dumps({
                "status": "healthy",
            })
        elif request.path_url == "/sparql":
            sparql = None

            if request.body.startswith("query=") or request.body.startswith("update="):
                params = urllib.parse.parse_qsl(request.body)
                if params:
                    for param in params:
                        if param[0] == "query" or param[0] == "update":
                            sparql = param[1]
                            break

            if sparql:
                if sparql.startswith("SELECT"):
                    context.status_code = 200
                    return json.dumps({
                        "results": {
                            "bindings": [
                                {
                                    "count": {
                                        "value": 0,
                                    }
                                }
                            ],
                        },
                    })
                elif sparql.startswith("INSERT DATA"):
                    context.status_code = 200
                    return None
                elif sparql.startswith("DROP GRAPH"):
                    context.status_code = 200
                    return None

        context.status_code = 400
        return None

    # Configure the good mock handlers; these rely on the `mocker_text_callback()` method defined above
    neptune = current_app.config["NEPTUNE_ENDPOINT"]
    pattern = re.compile(neptune.replace("http://", "mock-pass://").replace("/sparql", "/(.*)"))

    requests_mock.head(pattern, text=mocker_text_callback)
    requests_mock.get(pattern, text=mocker_text_callback)
    requests_mock.post(pattern, text=mocker_text_callback)

    # Configure the fail mock handlers; these rely on the mocker to throw the configured exception
    neptune = current_app.config["NEPTUNE_ENDPOINT"]
    pattern = re.compile(neptune.replace("http://", "mock-fail://").replace("/sparql", "/(.*)"))

    requests_mock.head(pattern, exc=requests.exceptions.ConnectionError)
    requests_mock.get(pattern, exc=requests.exceptions.ConnectionError)
    requests_mock.post(pattern, exc=requests.exceptions.ConnectionError)

    yield requests_mock


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
    def test_neptune_connection_good(self, client, namespace, auth_token, requests_mocker):
       endpoint = current_app.config["NEPTUNE_ENDPOINT"]
       records  = [json.dumps({"id": "object/12345", "type": "HumanMadeObject", "_label": "Irises"})]
       asserted = process_neptune_record_set(records, endpoint.replace("http://", "mock-pass://"))
       assert asserted == True

    def test_neptune_connection_fail(self, client, namespace, auth_token, requests_mocker):
       endpoint = current_app.config["NEPTUNE_ENDPOINT"]
       records  = [json.dumps({"id": "object/12345", "type": "HumanMadeObject", "_label": "Irises"})]
       asserted = process_neptune_record_set(records, endpoint.replace("http://", "mock-fail://"))
       assert (asserted and asserted.code == 500)

