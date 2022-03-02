import json

from flask import current_app
from flaskapp.routes.ingest import process_graphstore_record_set
from flaskapp.errors import status_nt


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
            f"/{namespace}/ingest", headers={"Authorization": "Bearer " + auth_token}
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
        assert b"JSON Record Parse/Validation Error" in response.data

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
        assert b"JSON Record Parse/Validation Error" in response.data

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
    def test_ingest_single(self, client_no_rdf, namespace, auth_token, test_db_no_rdf):
        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {"id": "object/12345", "name": "John", "age": 31, "city": "New York"}
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert b"object/12345" in response.data

    def test_ingest_multiple(
        self, client_no_rdf, namespace, auth_token, test_db_no_rdf
    ):
        response = client_no_rdf.post(
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

    def test_ingest_same_data_twice(
        self, client_no_rdf, namespace, auth_token, test_db_no_rdf
    ):
        data = {"id": "person/12345", "name": "John", "age": 31, "city": "New York"}
        # load one record:
        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert b"person/12345" in response.data

        # Do it again - should get a 200, but nothing in response.
        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        data_resp = response.get_json()
        assert data_resp["person/12345"] == "null"

    def test_ingest_new_versions(
        self, client_no_rdf, namespace, auth_token, test_db_no_rdf
    ):
        data = {"id": "person/12345", "name": "John", "age": 31, "city": "New York"}

        # Make sure that the versioning flag is set
        assert current_app.config["KEEP_LAST_VERSION"] is True

        # load one record:
        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        data["new property"] = "new data"

        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        response = client_no_rdf.get(
            f"/{namespace}/person/12345",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert "X-Previous-Version" in response.headers
        assert "X-Is-Old-Version" in response.headers

        old_version = client_no_rdf.get(
            f"/{namespace}/{response.headers['X-Previous-Version']}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert old_version.status_code == 200

    def test_ingest_test_old_version_deletion(
        self, client_no_rdf, namespace, auth_token, test_db_no_rdf
    ):
        data = {"id": "person/12345", "name": "John", "age": 31, "city": "New York"}

        # Make sure that the versioning flag is set
        assert current_app.config["KEEP_LAST_VERSION"] is True

        # load one record:
        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        data["new property"] = "new data"

        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        response = client_no_rdf.get(
            f"/{namespace}/person/12345",
            headers={"Authorization": "Bearer " + auth_token},
        )
        old_version_id = response.headers["X-Previous-Version"]

        data["new property"] = "newer data"

        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        response = client_no_rdf.get(
            f"/{namespace}/person/12345",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert response.headers["X-Previous-Version"] != old_version_id

        old_version = client_no_rdf.get(
            f"/{namespace}/{old_version_id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert old_version.status_code == 404

    def test_ingest_test_direct_delete_on_old_version(
        self, client_no_rdf, namespace, auth_token, test_db_no_rdf
    ):
        data = {"id": "person/123456", "name": "John", "age": 31, "city": "New York"}

        # Make sure that the versioning flag is set
        assert current_app.config["KEEP_LAST_VERSION"] is True

        # load one record:
        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        data["new property"] = "new data"

        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        response = client_no_rdf.get(
            f"/{namespace}/person/123456",
            headers={"Authorization": "Bearer " + auth_token},
        )
        old_version_id = response.headers["X-Previous-Version"]

        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps({"id": old_version_id, "_delete": "true"}),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        response = client_no_rdf.get(
            f"/{namespace}/person/123456",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert response.headers["X-Previous-Version"] == "None"

        old_version = client_no_rdf.get(
            f"/{namespace}/{old_version_id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert old_version.status_code == 404

    def test_ingest_test_update_null_on_old_version(
        self, client_no_rdf, namespace, auth_token, test_db_no_rdf
    ):
        data = {"id": "person/123456", "name": "John", "age": 31, "city": "New York"}

        # Make sure that the versioning flag is set
        assert current_app.config["KEEP_LAST_VERSION"] is True

        # load one record:
        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        data["new property"] = "new data"

        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(data),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

        response = client_no_rdf.get(
            f"/{namespace}/person/123456",
            headers={"Authorization": "Bearer " + auth_token},
        )
        old_version_id = response.headers["X-Previous-Version"]

        # update old version:
        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps({"id": old_version_id, "some": "garbage"}),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert response.get_json()[old_version_id] == "null"


class TestGraphStoreConnection:
    def test_graphstore_connection_good(self, client, namespace, auth_token):
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
        asserted = process_graphstore_record_set(
            records,
            query_endpoint.replace("http://", "mock-pass://"),
            update_endpoint.replace("http://", "mock-pass://"),
        )
        assert asserted == True

    def test_graphstore_zero_triples(self, client, namespace, auth_token):
        query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
        update_endpoint = current_app.config["SPARQL_UPDATE_ENDPOINT"]
        records = [
            json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "https://data.getty.edu/museum/collection/object/12345",
                }
            )
        ]

        asserted = process_graphstore_record_set(
            records,
            query_endpoint.replace("http://", "mock-pass://"),
            update_endpoint.replace("http://", "mock-pass://"),
        )

        assert isinstance(asserted, status_nt)
        assert asserted.code == 422

    def test_graphstore_connection_fail(self, client, namespace, auth_token):
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
        asserted = process_graphstore_record_set(
            records,
            query_endpoint.replace("http://", "mock-fail://"),
            update_endpoint.replace("http://", "mock-fail://"),
        )
        assert asserted and asserted.code == 500


class TestNewJSONLDIngest:
    def test_ingest_single_jsonld(self, client, namespace, auth_token, test_db):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "object/12345",
                    "type": "HumanMadeObject",
                    "_label": "Irises",
                }
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert b"object/12345" in response.data

    def test_ingest_multiple_jsonld(self, client, namespace, auth_token, test_db):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "object/12345",
                    "type": "HumanMadeObject",
                    "_label": "Irises",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "object/12346",
                    "type": "HumanMadeObject",
                    "_label": "New Object",
                }
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert b"object/12345" in response.data

    def test_deletion_failure(self, client, namespace, auth_token, test_db):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps({"id": "urn:failure_upon_deletion", "_delete": True}),
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 500
        assert b"failure happened" in response.data

    def test_batch_deletion_rollback(self, client, namespace, auth_token, test_db):
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "object/12345",
                    "type": "HumanMadeObject",
                    "_label": "Irises",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "object/12346",
                    "type": "HumanMadeObject",
                    "_label": "New Object",
                }
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # Make sure record exists
        response = client.get(f"/{namespace}/object/12345")
        assert response.status_code == 200

        # Now attempt to delete the 12345 item, and then a failure one and check to see
        # if the 12345 exists after the post and that the revert attempt worked.
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps({"id": "object/12345", "_delete": True})
            + "\n"
            + json.dumps({"id": "urn:failure_upon_deletion", "_delete": True}),
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 500
        assert b"failure happened" in response.data

        # Make sure record still exists
        response = client.get(f"/{namespace}/object/12345")
        assert response.status_code == 200

        assert "LOD Gateway" in response.headers["Server"]
        assert "Irises" in response.text
