import json
import re
import uuid

from flask import current_app


class TestVersioning:
    def test_timemap_in_link_header(self, client, namespace, sample_data):
        response = client.get(f"/{namespace}/{sample_data['record'].entity_id}")

        assert response.status_code == 200

        headers = response.headers

        assert "Memento-Datetime" in headers
        assert "timemap" in headers["Link"]

        link = response.headers["Link"]
        p = re.compile(r".*<(.*)>.*")
        m = p.match(link)

        assert m is not None
        assert m.groups()[0].endswith(f"{namespace}/-tm-/{identifier}")

    def test_multiple_versions_in_timemap_json(
        self, client, namespace, auth_token, linguisticobject
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
        assert identifier in response.data

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
        self, client, namespace, auth_token, linguisticobject
    ):
        identifier = str(uuid.uuid4())

        foo_jsonld = linguisticobject("Subject name Foo", identifier)

        response = client.post(
            f"/{namespace}/ingest",
            data=json.dumps(foo_jsonld),
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200
        assert identifier in response.data

        # Timemap should be at this URL. Get the JSON version
        response = client.get(
            f"/{namespace}/-tm-/{identifier}",
            headers={"Accept": "application/link-format"},
        )

        assert response.status_code == 200

        # Even though there are no 'versions' the timemap should include the timemap and the original
        lines = response.text.split(",")

        p = re.compile(r".*<(.*)>\s*;.*rel=\"([^\"]*)\"")

        rels = ["original", "self"]
        for line in lines:
            if line.strip() != "":
                m = p.match(line.strip())

                assert m is not None
                uri, rel = m.groups()

                if rel in rels:
                    rels.remove(rel)

                if rel == "original":
                    assert uri.endswith(f"{namespace}/{identifier}")
                elif rel == "self":
                    assert uri.endswith(f"{namespace}/-tm-/{identifier}")
                else:
                    assert rel == "rel not understood."

        assert len(rels) == 0
