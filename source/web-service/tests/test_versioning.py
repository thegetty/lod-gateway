import json
import re
import uuid

from flask import current_app
from flaskapp.routes.ingest import process_graphstore_record_set, process_record_set


class TestVersioning:
    def test_timemap_in_link_header(self, client, namespace, sample_data, test_db):
        response = client.get(f"/{namespace}/{sample_data['record'].entity_id}")

        assert response.status_code == 200

        headers = response.headers

        assert "accept-datetime" in headers.get("Vary")
        assert "timemap" in headers["Link"]

        link = response.headers["Link"]

        p = re.compile(r".*<([^>]*)>\s*;.*rel=\"([^\"]*)\"")

        for line in link.split(" , "):
            m = p.match(line)

            assert m is not None
            print(m.groups())
            uri, rel = m.groups()

            if "timemap" in rel:
                assert uri.endswith(
                    f"{namespace}/-tm-/{sample_data['record'].entity_id}"
                )
            if "original" in rel:
                assert uri.endswith(f"{namespace}/{sample_data['record'].entity_id}")

    def test_multiple_versions_in_timemap_json(
        self, client, namespace, auth_token, linguisticobject, test_db
    ):
        identifier = str(uuid.uuid4())

        foo_jsonld = linguisticobject("Subject name Foo", identifier)
        bar_jsonld = linguisticobject("Subject name Bar (replaces Foo)", identifier)

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(foo_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200
        assert identifier in response.data.decode("utf-8")

        # make new versions:
        for _ in range(2):
            response = client.post(
                f"/{namespace}/ingest",
                data=json.dumps(bar_jsonld),
                headers={"Authorization": "Bearer " + auth_token},
            )

            response = client.post(
                f"/{namespace}/ingest",
                data=json.dumps(foo_jsonld),
                headers={"Authorization": "Bearer " + auth_token},
            )

        # Timemap should be at this URL. Get the JSON version
        response = client.get(
            f"/{namespace}/-tm-/{identifier}", headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        timemap = response.get_json()

        # timemap, Original (current) and 4 versions (timemap, foo, bar, foo, bar, foo)
        assert len(timemap) > 5

    def test_timemap_in_link_format(
        self, client, namespace, auth_token, linguisticobject, test_db
    ):
        identifier = str(uuid.uuid4())

        foo_jsonld = linguisticobject("Subject name Foo", identifier)

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(foo_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200
        assert identifier in response.data.decode("utf-8")

        # Timemap should be at this URL. Get the JSON version
        response = client.get(
            f"/{namespace}/-tm-/{identifier}",
            headers={"Accept": "application/link-format"},
        )

        assert response.status_code == 200

        # Even though there are no 'versions' the timemap should include the timemap and the original
        lines = response.data.decode("utf-8").split(" , ")

        p = re.compile(r".*<([^>]*)>\s*;.*rel=\"([^\"]*)\"")

        rels = ["original timegate", "self"]
        for line in lines:
            if line.strip() != "":
                print("LINE:  '" + line + "'")
                m = p.match(line.strip())

                assert m is not None
                uri, rel = m.groups()

                if rel in rels:
                    rels.remove(rel)

                if rel == "original timegate":
                    assert uri.endswith(f"{namespace}/{identifier}")
                elif rel == "self":
                    assert uri.endswith(f"{namespace}/-tm-/{identifier}")

        assert len(rels) == 0

    def test_getting_version_is_authenticated(
        self, client, namespace, auth_token, linguisticobject, test_db
    ):
        identifier = str(uuid.uuid4())

        foo_jsonld = linguisticobject("Subject name Foo", identifier)
        bar_jsonld = linguisticobject("Subject name Bar (replaces Foo)", identifier)

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(foo_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # new version
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(bar_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # Timemap should be at this URL. Get the JSON version
        response = client.get(
            f"/{namespace}/-tm-/{identifier}", headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        timemap = response.get_json()

        firstmemento = None
        for item in timemap:
            if item["rel"].endswith("first last memento"):
                firstmemento = item

        assert firstmemento is not None

        assert "-VERSION-" in firstmemento["uri"]

        # get client version
        client_uri = f"{namespace}/{firstmemento['uri'].split(namespace+'/')[-1]}"

        # check if it requires authentication
        response = client.get(client_uri)
        assert response.status_code == 401

        response = client.get(
            client_uri, headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert response.json["content"] == foo_jsonld["content"]

    def test_deleting_a_version(
        self, client, namespace, auth_token, linguisticobject, test_db
    ):
        identifier = str(uuid.uuid4())

        foo_jsonld = linguisticobject("Subject name Foo", identifier)
        bar_jsonld = linguisticobject("Subject name Bar (replaces Foo)", identifier)

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(foo_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # new version
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(bar_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # Timemap should be at this URL. Get the JSON version
        response = client.get(
            f"/{namespace}/-tm-/{identifier}", headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        timemap = response.get_json()

        firstmemento = None
        for item in timemap:
            if item["rel"].endswith("first last memento"):
                firstmemento = item

        assert firstmemento is not None

        response = client.delete(
            f"/{namespace}/-VERSION-/{item['uri'].split('-VERSION-/')[-1]}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200

    def test_deleting_a_version_with_no_auth(
        self, client, namespace, auth_token, linguisticobject, test_db
    ):
        identifier = str(uuid.uuid4())

        foo_jsonld = linguisticobject("Subject name Foo", identifier)
        bar_jsonld = linguisticobject("Subject name Bar (replaces Foo)", identifier)

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(foo_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # new version
        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(bar_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        # Timemap should be at this URL. Get the JSON version
        response = client.get(
            f"/{namespace}/-tm-/{identifier}", headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        timemap = response.get_json()

        firstmemento = None
        for item in timemap:
            if item["rel"].endswith("first last memento"):
                firstmemento = item

        assert firstmemento is not None

        response = client.delete(
            f"/{namespace}/-VERSION-/{item['uri'].split('-VERSION-/')[-1]}",
        )

        assert response.status_code == 401
