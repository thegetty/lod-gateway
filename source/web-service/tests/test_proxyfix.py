import os
import pytest
from flask import Blueprint, url_for


@pytest.fixture
def make_client():
    def _make_client(app, enable_proxy):
        os.environ["WERKZEUG_PROXY_FIX"] = "true" if enable_proxy else "false"
        os.environ["WERKZEUG_X_PREFIX"] = "0"
        os.environ["WERKZEUG_X_FOR"] = "1"
        os.environ["WERKZEUG_X_HOST"] = "1"

        namespace = app.config["NAMESPACE"]

        # Now bolt on a new BL with a debug route
        test_bp = Blueprint("proxy_test_bp", __name__)

        @test_bp.route("/dynamic-test-route")
        def dynamic_test_route():
            # Targets the local test blueprint mapping
            return {"url": url_for("proxy_test_bp.dynamic_test_route", _external=True)}

        # Register the new test blueprint using your namespace
        app.register_blueprint(test_bp, url_prefix=f"/{namespace}")

        return app.test_client()

    yield _make_client
    os.environ.pop("WERKZEUG_PROXY_FIX", None)


def test_proxy_fix_enabled(app, make_client, test_db):
    client = make_client(app, enable_proxy=True)

    namespace = app.config["NAMESPACE"]

    response = client.get(
        f"/{namespace}/dynamic-test-route",
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "example.com",
        },
    )

    assert response.json["url"] == f"https://example.com/{namespace}/dynamic-test-route"

    # Make sure some other plain routes still work fine:
    response = client.get(
        f"/{namespace}/dashboard",
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "example.com",
        },
    )
    assert response.status_code == 200
    assert b"LOD Gateway" in response.data

    response = client.get(
        f"/{namespace}/health",
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "example.com",
        },
    )
    assert response.status_code == 200


def test_proxy_fix_disabled(app, make_client, test_db):
    client = make_client(app, enable_proxy=False)

    namespace = app.config["NAMESPACE"]

    response = client.get(
        f"/{namespace}/dynamic-test-route",
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "example.com",
        },
    )

    print(response.status_code)
    print(response.content)
    print(response.headers)

    # Throws away the HTTPS PROTO header and redirects to HTTP:
    assert response.json["url"].startswith("http://")

    # Throws away the HOST header too.
    assert "example.com" not in response.json["url"]
