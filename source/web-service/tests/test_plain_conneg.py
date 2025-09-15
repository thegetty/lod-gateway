import pytest
class TestObtainRDFRecord:
    def test_prefix_record_and_accept_json(
        self, sample_idprefixdata, client, namespace, current_app
    ):
        current_app.config["PREFIX_RECORD_IDS"] = "RECURSIVE"
        response = client.get(
            f"/{namespace}/{sample_idprefixdata.entity_id}",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
      
    def test_prefix_record_and_accept_jsonld(
        self, sample_idprefixdata, client, namespace, current_app
    ):
        current_app.config["PREFIX_RECORD_IDS"] = "RECURSIVE"
        response = client.get(
            f"/{namespace}/{sample_idprefixdata.entity_id}",
            headers={"Accept": "application/ld+json"},
        )
        assert response.status_code == 200
