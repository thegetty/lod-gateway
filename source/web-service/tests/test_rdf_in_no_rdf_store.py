import json

from flaskapp.models import db
from flaskapp.models.record import Record


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


class TestIngestRDFinL1Success:
    def test_ingest_wcontext_and_retrieve(
        self, client_no_rdf, namespace, auth_token, test_db_no_rdf
    ):
        response = client_no_rdf.post(
            f"/{namespace}/ingest",
            data=json.dumps(
                {
                    "@context": "https://fakecontext.org/should/not/be/loaded",
                    "id": "object/12345_context",
                    "name": "John",
                    "age": 31,
                    "city": "New York",
                }
            ),
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert b"object/12345" in response.data

        assert _assert_data_in_db("object/12345_context", name="John", age=31)

        response = client_no_rdf.get(f"/{namespace}/object/12345_context")
        assert response.status_code == 200
        assert "LOD Gateway" in response.headers["Server"]

        data = json.loads(response.data)
        assert "@context" in data
