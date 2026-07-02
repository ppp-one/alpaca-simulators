from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from alpaca_simulators.main import app
from alpaca_simulators.state import reload_config, update_device_state

client = TestClient(app)


@pytest.fixture()
def reset_state():
    """Reset all in-memory device state after each test."""
    yield
    reload_config()


def _devicestate(device_type: str, device_number: int = 0, client_transaction_id: int = 42):
    response = client.get(
        f"/api/v1/{device_type}/{device_number}/devicestate",
        params={"ClientTransactionID": client_transaction_id},
    )
    assert response.status_code == 200
    return response.json()


class TestDeviceState:
    """Tests that /devicestate conforms to the ASCOM Alpaca Platform 7 spec.

    The Value field must be an array of {Name, Value} objects using
    interface-correct property names, restricted to operational properties,
    with a mandatory ISO-8601 TimeStamp entry appended.
    """

    def test_value_is_array_of_name_value_pairs(self, reset_state):
        data = _devicestate("focuser")
        assert isinstance(data["Value"], list)
        for item in data["Value"]:
            assert set(item.keys()) == {"Name", "Value"}

    def test_envelope_fields(self, reset_state):
        data = _devicestate("focuser", client_transaction_id=99)
        assert data["ClientTransactionID"] == 99
        assert "ServerTransactionID" in data
        assert data["ErrorNumber"] == 0
        assert data["ErrorMessage"] == ""

    def test_focuser_operational_properties(self, reset_state):
        data = _devicestate("focuser")
        names = [item["Name"] for item in data["Value"]]
        for expected in ("IsMoving", "Position", "Temperature", "TimeStamp"):
            assert expected in names

    def test_timestamp_present_and_iso8601(self, reset_state):
        data = _devicestate("focuser")
        timestamp = next(item["Value"] for item in data["Value"] if item["Name"] == "TimeStamp")
        # Must parse as an ISO-8601 date-time (raises ValueError otherwise).
        datetime.fromisoformat(timestamp)

    def test_metadata_excluded(self, reset_state):
        """Non-operational metadata must not appear in DeviceState."""
        data = _devicestate("focuser")
        names = {item["Name"] for item in data["Value"]}
        for metadata in ("Name", "Description", "DriverInfo", "DriverVersion", "InterfaceVersion", "Connected"):
            assert metadata not in names
        # Internal lowercase keys must not leak through either.
        for internal in ("name", "description", "driverinfo", "connected"):
            assert internal not in names

    def test_focuser_position_value(self, reset_state):
        update_device_state("focuser", 0, {"position": 12345, "ismoving": True})
        data = _devicestate("focuser")
        values = {item["Name"]: item["Value"] for item in data["Value"]}
        assert values["Position"] == 12345
        assert values["IsMoving"] is True

    def test_camera_uses_interface_casing_and_omits_image_data(self, reset_state):
        data = _devicestate("camera")
        names = {item["Name"] for item in data["Value"]}
        # Interface-correct casing, mapped from differently-named state keys.
        assert "CameraState" in names
        assert "ImageReady" in names
        assert "TimeStamp" in names
        # The full pixel array (state key "image_data") must never be exposed.
        assert "image_data" not in names
        assert "ImageData" not in names

    def test_switch_returns_only_timestamp(self, reset_state):
        data = _devicestate("switch")
        names = [item["Name"] for item in data["Value"]]
        assert names == ["TimeStamp"]

    def test_unknown_property_is_skipped(self):
        """Properties whose state value is unknown are omitted, not emitted as null."""
        from alpaca_simulators.devicestate import build_device_state

        # Focuser state missing "temperature" -> Temperature must be skipped.
        items = build_device_state("focuser", {"ismoving": False, "position": 100})
        names = [item["Name"] for item in items]
        assert "Temperature" not in names
        assert names == ["IsMoving", "Position", "TimeStamp"]
