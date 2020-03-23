import json

from flask import current_app
from flaskapp.routes.sparql import execute_query


class TestSparqlErrors:
    def test_sparql_auth_token_wrong(self, client, namespace):
        response = client.post(
            f"/{namespace}/sparql", headers={"Authorization": "Bearer WrongToken"}
        )
        assert response.status_code == 401

    def test_sparql_auth_token_missing(self, client, namespace):
        response = client.post(f"/{namespace}/sparql")
        assert response.status_code == 401

    def test_sparql_query_missing(self, client, namespace, auth_token):
        response = client.post(
            f"/{namespace}/sparql", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == 400
        assert b"No query parameter included" in response.data

    def test_sparql_update_not_permitted(self, client, namespace, auth_token):
        response = client.get(
            f"/{namespace}/sparql" + "?update=DROP+GRAPH+<person/12345>",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 400
        assert b"SPARQL update is not permitted" in response.data


class TestSparqlSuccess:
    def test_sparql_get(self, client, namespace, auth_token, test_db):
        response = client.get(
            f"/{namespace}/sparql" + "?query=SELECT+*+%7B%3Fs+%3Fp+%3Fo%7D+LIMIT+1",
            headers={
                "Authorization": "Bearer " + auth_token,
                "Accept": "application/json",
            },
        )
        assert response.status_code == 200
        assert b"results" in response.data

    def test_sparql_post(self, client, namespace, auth_token, test_db):
        response = client.post(
            f"/{namespace}/sparql",
            data={"query": "SELECT * {?s ?p ?o} LIMIT 1"},
            headers={
                "Authorization": "Bearer " + auth_token,
                "Accept": "application/json",
            },
        )
        assert response.status_code == 200
        assert b"results" in response.data

    def test_sparql_options(self, client, namespace, auth_token, test_db):
        response = client.options(f"/{namespace}/sparql")
        assert response.status_code == 200
        assert "GET" in response.headers["Allow"]
        assert "POST" in response.headers["Allow"]
        assert "OPTIONS" in response.headers["Allow"]
        assert "DELETE" not in response.headers["Allow"]


class TestNeptuneConnection:
    def test_neptune_connection_good(self, client, namespace, auth_token):
        endpoint = current_app.config["NEPTUNE_ENDPOINT"]
        query = "SELECT * {?s ?p ?o} LIMIT 1"
        accept_header = "*/*"
        response = execute_query(
            query, accept_header, endpoint.replace("http://", "mock-pass://")
        )
        assert b"results" in response

    def test_neptune_connection_fail(self, client, namespace, auth_token):
        endpoint = current_app.config["NEPTUNE_ENDPOINT"]
        query = "SELECT * {?s ?p ?o} LIMIT 1"
        accept_header = "*/*"
        asserted = execute_query(
            query, accept_header, endpoint.replace("http://", "mock-fail://")
        )
        assert asserted and asserted.code == 500
