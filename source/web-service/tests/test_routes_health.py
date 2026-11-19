class TestHealthRoute:
    def test_liveness_ok(self, client, namespace, test_db):
        response = client.get(f"/{namespace}/health")
        assert response.status_code == 200
        assert response.json["status"] == "okay"

    def test_readiness_ok(self, client, namespace, test_db):
        response = client.get(f"/{namespace}/health/readiness")
        assert response.status_code == 200
        assert response.json["status"] == "okay"

    def test_auth_health_deprec_ok(self, client, namespace, test_db, auth_token):
        response = client.get(
            f"/{namespace}/authhealth",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert response.json["status"] == "okay"

    def test_auth_health_ok(self, client, namespace, test_db, auth_token):
        response = client.get(
            f"/{namespace}/health/readiness/withauth",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200
        assert response.json["status"] == "okay"

    def test_rdf_health_deprec_ok(self, client, namespace, test_db, auth_token):
        response = client.get(f"/{namespace}/rdfhealth")
        assert response.status_code == 200
        assert response.json["status"] == "okay"

    def test_rdf_health_ok(self, client, namespace, test_db, auth_token):
        response = client.get(f"/{namespace}/health/readiness/rdf")
        assert response.status_code == 200
        assert response.json["status"] == "okay"

    def test_health_db_down(self, client, namespace, test_db):
        test_db.drop_all()
        response = client.get(f"/{namespace}/health/readiness")
        assert response.status_code == 503
