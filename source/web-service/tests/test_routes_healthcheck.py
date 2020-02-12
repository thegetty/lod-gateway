import pytest


class TestHealthcheckRoute:
    def test_healthcheck_exists(self, client, namespace):
        response = client.get(f"/{namespace}/healthcheck")
        assert response.status_code == 200 or response.status_code == 503
