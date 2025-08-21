class TestFlaskApp:
    def test_home_page_redirect_to_dashboard(self, sample_data, client, namespace):
        response = client.get(f"/{namespace}/", headers={"Accept": "text/html"})
        assert response.status_code == 302
        response = client.get(
            f"/{namespace}/", headers={"Accept": "application/ld+json"}
        )
        assert response.status_code == 302

    def test_home_page_redirect_to_dashboard_ldpapi(
        self, sample_data, client_ldpapi, namespace
    ):
        response = client_ldpapi.get(f"/{namespace}/", headers={"Accept": "text/html"})
        assert response.status_code == 302
        response = client_ldpapi.get(
            f"/{namespace}/", headers={"Accept": "application/ld+json"}
        )
        # Should resolve and HTTP 303 redirect to the first page of the container
        assert response.status_code == 303

    def test_dashboard(self, sample_data, client, namespace):
        response = client.get(f"/{namespace}/dashboard")
        assert response.status_code == 200
        assert b"LOD Gateway" in response.data

    def test_cors_response(self, client, namespace):
        response = client.options(f"/{namespace}/")
        assert response.headers.get("Access-Control-Allow-Origin") == "*"

    def test_cors_on_get(self, sample_data, client, namespace):
        response = client.get(f"/{namespace}/")
        assert response.headers.get("Access-Control-Allow-Origin") == "*"

    def test_custom_headers_on_get(self, sample_data, client, namespace):
        response = client.get(f"/{namespace}/")
        assert "LOD Gateway" in response.headers.get("Server")
