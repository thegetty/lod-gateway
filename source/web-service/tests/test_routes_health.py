class TestHealthRoute:
    def test_health_ok(self, client, namespace, test_db):
        response = client.get(f"/{namespace}/health")
        assert response.status_code == 200

    def test_auth_health_ok(self, client, namespace, test_db, auth_token):
        response = client.get(
            f"/{namespace}/authhealth",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 200

    def test_health_db_down(self, client, namespace, test_db):
        test_db.drop_all()
        response = client.get(f"/{namespace}/health")
        assert response.status_code == 500
        assert b"Data Base Error" in response.data
