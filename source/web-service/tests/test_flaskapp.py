"""Tests for app config: id/RDF id prefixes, FULL_RDF_ID_PREFIX override, FULL_BASE_GRAPH."""

from flaskapp import create_app


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


class TestRDFIdPrefixConfig:
    """FULL_RDF_ID_PREFIX env var: override, fallback, and trailing-slash handling."""

    def test_full_rdf_id_prefix_set(self, monkeypatch):
        monkeypatch.setenv("FULL_RDF_ID_PREFIX", "https://g.example/graph")
        app = create_app()
        assert app.config["RDFidPrefix"] == "https://g.example/graph"
        # display prefix unaffected by the override
        # (CI runs with APPLICATION_NAMESPACE="ns", overriding .env.example)
        assert app.config["idPrefix"] == "http://localhost:5100/ns"

    def test_full_rdf_id_prefix_unset_falls_back(self, monkeypatch):
        monkeypatch.delenv("FULL_RDF_ID_PREFIX", raising=False)
        app = create_app()
        # BASE_URL + RDF_NAMESPACE (which equals APPLICATION_NAMESPACE="ns" in CI)
        assert app.config["RDFidPrefix"] == "http://localhost:5100/ns"
        assert app.config["idPrefix"] == "http://localhost:5100/ns"

    def test_full_rdf_id_prefix_empty_falls_back(self, monkeypatch):
        monkeypatch.setenv("FULL_RDF_ID_PREFIX", "")
        app = create_app()
        assert app.config["RDFidPrefix"] == "http://localhost:5100/ns"

    def test_trailing_slashes_stripped(self, monkeypatch):
        # BASE_URL trailing slash (no namespace) must be stripped from idPrefix;
        # FULL_RDF_ID_PREFIX trailing slash must be stripped from RDFidPrefix
        monkeypatch.setenv("BASE_URL", "http://localhost:5100/")
        monkeypatch.setenv("APPLICATION_NAMESPACE", "")
        monkeypatch.setenv("FULL_RDF_ID_PREFIX", "https://g.example/graph/")
        app = create_app()
        assert app.config["idPrefix"] == "http://localhost:5100"
        assert app.config["RDFidPrefix"] == "https://g.example/graph"

    def test_full_base_graph_derives_from_rdfid_prefix(self, monkeypatch):
        # isolate: avoid the real base_graph_filter writing a record to the shared test DB
        monkeypatch.setattr("flaskapp.base_graph_filter", lambda *a, **k: set())
        monkeypatch.setenv("FULL_RDF_ID_PREFIX", "https://g.example/graph")
        monkeypatch.setenv("RDF_BASE_GRAPH", "basegraph")
        app = create_app()
        assert app.config["FULL_BASE_GRAPH"] == "https://g.example/graph/basegraph"

    def test_full_base_graph_fallback_derivation(self, monkeypatch):
        # isolate: avoid the real base_graph_filter writing a record to the shared test DB
        monkeypatch.setattr("flaskapp.base_graph_filter", lambda *a, **k: set())
        monkeypatch.delenv("FULL_RDF_ID_PREFIX", raising=False)
        monkeypatch.setenv("RDF_BASE_GRAPH", "basegraph")
        app = create_app()
        # BASE_URL + RDF_NAMESPACE (which equals APPLICATION_NAMESPACE="ns" in CI)
        assert app.config["FULL_BASE_GRAPH"] == "http://localhost:5100/ns/basegraph"
