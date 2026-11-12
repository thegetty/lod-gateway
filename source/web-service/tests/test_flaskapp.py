"""Tests for app config: id/RDF id prefixes, FULL_RDF_ID_PREFIX override, FULL_BASE_GRAPH."""

import pytest

from flaskapp import create_app


class TestFlaskApp:
    def test_home_page_redirect_to_dashboard(self, sample_data, client, namespace):
        response = client.get(f"/{namespace}/", headers={"Accept": "text/html"})
        assert response.status_code == 302
        # Pins the redirect shape behind the home-page url_base repoint
        assert response.headers["Location"].endswith("/dashboard")
        response = client.get(
            f"/{namespace}/", headers={"Accept": "application/ld+json"}
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/dashboard")

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


class TestStreamConfig:
    """Activity Stream config keys set at create_app (plan step 3, FR-1 / AC-6b)."""

    def test_compress_mimetypes_registered_gzip_on(self, monkeypatch):
        monkeypatch.setenv("FLASK_GZIP_COMPRESSION", "true")
        app = create_app()
        assert "application/json" in app.config["COMPRESS_MIMETYPES"]
        assert "application/activity+json" in app.config["COMPRESS_MIMETYPES"]

    def test_compress_mimetypes_registered_gzip_off(self, monkeypatch):
        # the registration is unconditional: the key exists regardless of the
        # FLASK_GZIP_COMPRESSION switch (round-3 OQ)
        monkeypatch.setenv("FLASK_GZIP_COMPRESSION", "false")
        app = create_app()
        assert "application/json" in app.config["COMPRESS_MIMETYPES"]
        assert "application/activity+json" in app.config["COMPRESS_MIMETYPES"]

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, True),  # unset -> include by default
            ("true", True),
            ("TRUE", True),
            ("nonsense", True),  # include unless explicitly false-ish
            ("false", False),
            ("F", False),
            ("FALSE", False),
        ],
    )
    def test_actstr_include_created_flag(self, monkeypatch, value, expected):
        if value is None:
            monkeypatch.delenv("ACTSTR_INCLUDE_CREATED", raising=False)
        else:
            monkeypatch.setenv("ACTSTR_INCLUDE_CREATED", value)
        app = create_app()
        assert app.config["ACTSTR_INCLUDE_CREATED"] is expected


class TestOpenApiStreamResponses:
    """AC-10: all seven stream GET registrations include a 304 in the served schema."""

    STREAM_PATHS = [
        "/{ns}/activity-stream",
        "/{ns}/activity-stream/page/{{pagenum}}",
        "/{ns}/activity-stream/{{uuid}}",
        "/{ns}/activity-stream/type/{{entity_type}}",
        "/{ns}/activity-stream/type/{{entity_type}}/page/{{pagenum}}",
        "/{ns}/{{entity_id}}/activity-stream",
        "/{ns}/{{entity_id}}/activity-stream/page/{{pagenum}}",
    ]

    def test_all_seven_stream_gets_declare_304(self, app):
        ns = app.config["NAMESPACE"]
        spec = app.api_doc["paths"]
        for template in self.STREAM_PATHS:
            path = template.format(ns=ns)
            assert path in spec, f"missing OpenAPI registration: {path}"
            assert "get" in spec[path], f"no GET registration: {path}"
            assert "304" in spec[path]["get"].get(
                "responses", {}
            ), f"no 304 response declared: {path}"
