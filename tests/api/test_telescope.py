import pytest
from fastapi.testclient import TestClient

from alpaca_simulators.main import app
from alpaca_simulators.state import (
    Rate,
    TelescopeAxes,
    get_device_state,
    reload_config,
    update_device_state,
)


@pytest.fixture()
def setup_telescope_state():
    """Setup telescope device state before each test"""
    update_device_state(
        "telescope",
        0,
        {
            f"axis{TelescopeAxes.PRIMARY}rates": Rate(Maximum=10.0, Minimum=0.0),
            f"axis{TelescopeAxes.SECONDARY}rates": Rate(Maximum=5.0, Minimum=1.0),
            f"axis{TelescopeAxes.TERTIARY}rates": Rate(Maximum=2.0, Minimum=0.5),
        },
    )
    yield get_device_state("telescope", 0)
    reload_config()


client = TestClient(app)

base_api_path = "/api/v1/telescope"


class TestTelescope:
    """Tests for telescope endpoints"""

    def test_get_axisrates_primary_axis(self, setup_telescope_state):
        """Test getting axis rates for primary axis"""
        transaction_id = 123
        response = client.get(
            f"{base_api_path}/0/axisrates",
            params={"Axis": TelescopeAxes.PRIMARY, "ClientTransactionID": transaction_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Value" in data
        assert isinstance(data["Value"], list)
        assert data["Value"] == [setup_telescope_state.get("axis0rates").model_dump()]
        assert data["ClientTransactionID"] == transaction_id
        assert "ServerTransactionID" in data

    def test_get_axisrates_secondary_axis(self, setup_telescope_state):
        """Test getting axis rates for secondary axis"""
        transaction_id = 456
        response = client.get(
            f"{base_api_path}/0/axisrates",
            params={"Axis": TelescopeAxes.SECONDARY, "ClientTransactionID": transaction_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["Value"] == [setup_telescope_state.get("axis1rates").model_dump()]
        assert data["ClientTransactionID"] == transaction_id

    def test_get_axisrates_tertiary_axis(self, setup_telescope_state):
        """Test getting axis rates for tertiary axis"""
        response = client.get(
            f"{base_api_path}/0/axisrates", params={"Axis": TelescopeAxes.TERTIARY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["Value"] == [setup_telescope_state.get("axis2rates").model_dump()]

    def test_get_axisrates_invalid_axis(self):
        """Test getting axis rates with invalid axis value"""
        transaction_id = 789
        response = client.get(
            f"{base_api_path}/0/axisrates",
            params={"Axis": 99, "ClientTransactionID": transaction_id},
        )
        assert response.status_code == 200  # Alpaca returns 200 for errors
        data = response.json()
        assert data["ErrorNumber"] == 0x402
        assert "Invalid axis" in data["ErrorMessage"]
        assert data["ClientTransactionID"] == transaction_id

    def test_get_axisrates_missing_axis_parameter(self):
        """Test that Axis parameter is required"""
        response = client.get(f"{base_api_path}/0/axisrates")
        assert response.status_code == 422  # FastAPI validation error

    def test_get_axisrates_default_client_transaction_id(self, setup_telescope_state):
        """Test that ClientTransactionID defaults to 0 when not provided"""
        response = client.get(
            f"{base_api_path}/0/axisrates", params={"Axis": TelescopeAxes.PRIMARY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ClientTransactionID"] == 0

    def test_get_axisrates_invalid_device_number(self):
        """Test with non-existent device number"""
        response = client.get(
            f"{base_api_path}/99/axisrates", params={"Axis": TelescopeAxes.PRIMARY}
        )
        assert response.status_code == 200  # Alpaca returns 200 for errors
        data = response.json()
        assert "ErrorNumber" in data
        assert data["ErrorNumber"] != 0

    def test_get_axisrates_negative_device_number(self):
        """Test with negative device number (should fail validation)"""
        response = client.get(
            f"{base_api_path}/-1/axisrates", params={"Axis": TelescopeAxes.PRIMARY}
        )
        assert response.status_code == 422  # FastAPI validation error

    def test_get_axisates_returns_default_on_missing_state(self):
        """Test that default rates are returned if state is missing"""
        update_device_state("telescope", 0, {f"axis{TelescopeAxes.PRIMARY}rates": None})
        response = client.get(
            f"{base_api_path}/0/axisrates",
            params={"Axis": TelescopeAxes.PRIMARY, "ClientTransactionID": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["Value"] == [{"Maximum": 1.0, "Minimum": 0.0}]  # Default rates
