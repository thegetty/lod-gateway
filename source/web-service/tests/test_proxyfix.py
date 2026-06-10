import os
import pytest
from flask import url_for
from flaskapp import create_app


@pytest.fixture
def make_client():
    def _make_client(enable_proxy):
        os.environ["WERKZEUG_PROXY_FIX"] = "true" if enable_proxy else "false"
        os.environ["WERKZEUG_X_PREFIX"] = "0"
        os.environ["WERKZEUG_X_FOR"] = "1"
        os.environ["WERKZEUG_X_HOST"] = "1"

        # import the Blueprint *before* app initialization
        from flaskapp.routes.home_page import home_page

        # inject the route directly into the blueprint just for the test
        @home_page.route("/dynamic-test-route")
        def dynamic_test_route():
            # For blueprints, url_for requires the 'blueprint_name.view_name' syntax
            return {"url": url_for("home_page.dynamic_test_route", _external=True)}

        # 3. Initialize the app
        app = create_app()
        return app, app.test_client()

    yield _make_client
    os.environ.pop("WERKZEUG_PROXY_FIX", None)


def test_proxy_fix_enabled(make_client):
    app, client = make_client(enable_proxy=True)

    namespace = app.config["NAMESPACE"]

    response = client.get(
        f"/{namespace}/dynamic-test-route",
        headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "example.com"},
    )

    assert response.json["url"] == f"https://example.com{namespace}/dynamic-test-route"


def test_proxy_fix_disabled(make_client):
    app, client = make_client(enable_proxy=False)

    namespace = app.config["NAMESPACE"]

    response = client.get(
        f"/{namespace}/dynamic-test-route",
        headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "example.com"},
    )

    # Throws away the HTTPS PROTO header and redirects to HTTP:
    assert response.json["url"].startswith("http://")

    # Throws away the HOST header too.
    assert "example.com" not in response.json["url"]
