from fastapi.testclient import TestClient

from alpaca_simulators.main import app

client = TestClient(app)


def test_unknown_api_route_is_400_plain_text():
    response = client.get("/api/v1/telescope/0/nosuchmethod")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/plain")
    assert "/api/v1/telescope/0/nosuchmethod" in response.text


def test_unknown_non_api_route_stays_404():
    response = client.get("/nosuchpage")
    assert response.status_code == 404


def test_missing_parameter_is_400_plain_text():
    response = client.get("/api/v1/telescope/0/axisrates")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/plain")
    assert "Axis" in response.text


def test_malformed_parameter_is_400_plain_text():
    response = client.get("/api/v1/telescope/0/axisrates", params={"Axis": "x"})
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/plain")
    assert "Axis" in response.text


def test_method_not_allowed_passes_through():
    response = client.delete("/api/v1/telescope/0/connected")
    assert response.status_code == 405
    assert "allow" in response.headers
