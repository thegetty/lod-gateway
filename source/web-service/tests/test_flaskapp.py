def test_home_page(client, namespace):
    response = client.get(f"/{namespace}/")
    assert response.status_code == 200
    assert b"Welcome to the Getty's Linked Open Data Gateway Service" in response.data


def test_cors_response(client, namespace):
    response = client.options(f"/{namespace}/")
    assert response.headers.get("Access-Control-Allow-Origin") == "*"


def test_cors_on_get(client, namespace):
    response = client.get(f"/{namespace}/")
    assert response.headers.get("Access-Control-Allow-Origin") == "*"


def test_custom_headers_on_get(client, namespace):
    response = client.get(f"/{namespace}/")
    assert "LOD Gateway" in response.headers.get("Server")
