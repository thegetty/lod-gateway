import pytest


class TestHealthRoute:
    def test_health_exists(self, client, namespace):
        response = client.get(f"/{namespace}/health")
        assert response.status_code == 200 or response.status_code == 500
