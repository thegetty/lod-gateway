import json
import re

from flaskapp.models import db
from flaskapp.models.record import Record
from flask import current_app
from flaskapp.routes.ingest import process_graphstore_record_set, process_record_set
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
        assert b"ID Missing" in response.data

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
        assert b"ID Missing" in response.data

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


def _assert_data_in_db(record_id, **kwargs):
    if obj := Record.query.filter_by(entity_id=record_id).one_or_none():
        print("Found record, now testing keyword arguments")
        for k, v in kwargs.items():
            if obj.data[k] != v:
                print(f"In key '{k}' - should be {v}, found {obj.data[k]} instead")
                return False
        return True
    else:
        # Couldn't find record
        print("Could not find record 'record_id'")
        return False


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

        assert _assert_data_in_db("object/12345", name="John", age="31")

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
        assert (
            "Vary" in response.headers and "accept-datetime" in response.headers["Vary"]
        )
        assert "Link" in response.headers

        p = re.compile(r".*<(.*)>.*")

        m = p.match(response.headers["Link"])
        assert m is not None

        uri = m.groups()[0]

        timemap = client_no_rdf.get(
            uri,
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert timemap.status_code == 200


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
        # Trying to issue a SPARQL Update to delete he 'failure_upon_deletion' object id
        # will result in the mock service responding with a Server Error to simulate the
        # triplestore going down mid-request.

        # As the LOD Gateway can never guess why the triplestore service dies (could be
        # temporary, could be a misconfiguration, could be -ro for some reason, etc), the
        # LOD instance should respond with a Server Error itself to communicate this service issue.
        # The client should assume that state may have changed, but reattempting their request when
        # the service is back online should result in a consistent state.
        query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
        update_endpoint = current_app.config["SPARQL_UPDATE_ENDPOINT"]

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "urn:failure_upon_deletion",
                    "type": "HumanMadeObject",
                    "_label": "DELETE ME",
                }
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # Make sure record exists
        response = client.get(f"/{namespace}/urn:failure_upon_deletion")
        assert response.status_code == 200

        response = process_record_set(
            [json.dumps({"id": "urn:failure_upon_deletion", "_delete": "true"})],
            query_endpoint.replace("http://", "mock-pass://"),
            update_endpoint.replace("http://", "mock-pass://"),
        )
        assert isinstance(response, status_nt)
        assert response.code == 500
        assert "failure happened" in response.detail

    def test_batch_deletion_rollback(self, client, namespace, auth_token, test_db):
        # This simulates a triplestore failure as part of a batch request.
        # The service should make best efforts to revert, but this should always be
        # treated as untrusted (as with all out-of-band failures).
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
            )
            + "\n"
            + json.dumps(
                {
                    "@context": "https://linked.art/ns/v1/linked-art.json",
                    "id": "urn:failure_upon_deletion",
                    "type": "HumanMadeObject",
                    "_label": "DELETE ME",
                }
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # Make sure record exists
        response = client.get(f"/{namespace}/object/12345")
        assert response.status_code == 200

        # Now attempt to delete the 12345 item, and then a failure one and check to see
        # if the 12345 exists after the post and that the revert attempt worked.
        query_endpoint = current_app.config["SPARQL_QUERY_ENDPOINT"]
        update_endpoint = current_app.config["SPARQL_UPDATE_ENDPOINT"]

        response = process_record_set(
            [
                json.dumps({"id": "object/12345", "_delete": "true"}),
                json.dumps({"id": "urn:failure_upon_deletion", "_delete": "true"}),
            ],
            query_endpoint.replace("http://", "mock-pass://"),
            update_endpoint.replace("http://", "mock-pass://"),
        )

        assert isinstance(response, status_nt)
        assert response.code == 500
        assert "failure happened" in response.detail

        # Make sure record still exists
        response = client.get(f"/{namespace}/object/12345")
        assert response.status_code == 200

        assert "LOD Gateway" in response.headers["Server"]
        assert b"Irises" in response.data
