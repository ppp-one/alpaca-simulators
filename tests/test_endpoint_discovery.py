"""
Tests for endpoint discovery.

Discovery must not read app.routes: FastAPI changed how include_router stores
sub-routes, so a walk over app.routes finds nothing on newer versions and the
test interface renders an empty page.
"""

from fastapi.testclient import TestClient

from alpaca_simulators.endpoint_discovery import (
    discover_device_endpoints,
    get_action_endpoints,
)
from alpaca_simulators.main import DISCOVERY_ROUTERS, ROUTERS, app

client = TestClient(app)

EXPECTED_DEVICE_TYPES = {
    "camera",
    "covercalibrator",
    "dome",
    "filterwheel",
    "focuser",
    "observingconditions",
    "rotator",
    "safetymonitor",
    "switch",
    "telescope",
}


class TestDiscovery:
    def test_every_router_is_registered(self):
        """Both lists come from ROUTERS, so registration and discovery agree."""
        assert len(DISCOVERY_ROUTERS) == len(ROUTERS)
        assert [router for router, _ in DISCOVERY_ROUTERS] == [router for router, _, _ in ROUTERS]

    def test_all_device_types_are_found(self):
        endpoints = discover_device_endpoints(DISCOVERY_ROUTERS)
        # The common router contributes the generic "{device_type}" key.
        assert set(endpoints) == EXPECTED_DEVICE_TYPES | {"{device_type}"}

    def test_device_has_get_and_put_endpoints(self):
        endpoints = discover_device_endpoints(DISCOVERY_ROUTERS)
        camera = endpoints["camera"]
        assert "cameraxsize" in camera["GET"]
        assert "startexposure" in camera["PUT"]
        assert "startexposure" in get_action_endpoints("camera", endpoints)

    def test_api_endpoints_route_is_not_empty(self):
        response = client.get("/api/endpoints")
        assert response.status_code == 200
        discovered = response.json()["discovered_endpoints"]
        assert EXPECTED_DEVICE_TYPES <= set(discovered)

    def test_test_interface_renders_endpoints(self):
        response = client.get("/test_interface")
        assert response.status_code == 200
        assert "const endpoints = {};" not in response.text
        for device_type in EXPECTED_DEVICE_TYPES:
            assert f'"{device_type}"' in response.text
