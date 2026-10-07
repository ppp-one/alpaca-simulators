import asyncio
import math
from datetime import datetime, timezone

import cabaret
import numpy as np
import pytest
from fastapi.testclient import TestClient

from alpaca_simulators.api import camera
from alpaca_simulators.config import Config
from alpaca_simulators.main import app
from alpaca_simulators.state import (
    CameraStates,
    get_device_state,
    reload_config,
    update_device_state,
)

client = TestClient(app)

RA = 10.0  # hours
DEC = 20.0  # degrees
RATE = 2.0  # arcsec/s


@pytest.fixture()
def generate_image_calls(monkeypatch):
    """Replace cabaret's image generation and record the arguments it gets."""
    calls = []

    def fake_generate_image(self, **kwargs):
        calls.append(kwargs)
        return np.zeros((2, 2), dtype=np.uint16)

    monkeypatch.setattr(cabaret.Observatory, "generate_image", fake_generate_image)
    camera.image_cache.clear()
    Config().load().update({"pointing_error_ra": 0.0, "pointing_error_dec": 0.0})
    update_device_state(
        "telescope",
        0,
        {
            "rightascension": RA,
            "declination": DEC,
            "tracking": True,
            "rightascensionrate": 0.0,
            "declinationrate": 0.0,
            "moveaxis_primary_rate": 0.0,
            "moveaxis_secondary_rate": 0.0,
        },
    )
    yield calls
    camera.image_cache.clear()
    reload_config()


def _expose(bad_tracking: bool, seconds_since_slew: float | None) -> dict:
    Config().load().update({"bad_tracking": bad_tracking, "bad_tracking_rate": RATE})
    last_slew_time = None
    if seconds_since_slew is not None:
        last_slew_time = datetime.now(timezone.utc).timestamp() - seconds_since_slew
    update_device_state("telescope", 0, {"last_slew_time": last_slew_time})

    asyncio.run(camera.exposure_task(0, 0.0, True))

    assert get_device_state("camera", 0)["camera_state"] == CameraStates.IDLE
    return get_device_state("camera", 0)


class TestBadTracking:
    def test_slew_and_sync_record_last_slew_time(self):
        before = datetime.now(timezone.utc).timestamp()
        update_device_state("telescope", 0, {"atpark": False, "last_slew_time": None})

        response = client.put(
            "/api/v1/telescope/0/slewtocoordinates",
            data={"RightAscension": RA, "Declination": DEC},
        )
        assert response.status_code == 200
        slew_time = get_device_state("telescope", 0)["last_slew_time"]
        assert slew_time >= before

        response = client.put(
            "/api/v1/telescope/0/synctocoordinates",
            data={"RightAscension": RA, "Declination": DEC},
        )
        assert response.status_code == 200
        assert get_device_state("telescope", 0)["last_slew_time"] >= slew_time
        reload_config()

    def test_off_gives_no_drift(self, generate_image_calls):
        _expose(bad_tracking=False, seconds_since_slew=100.0)

        kwargs = generate_image_calls[0]
        assert kwargs["ra"] == pytest.approx(RA / 24 * 360)
        assert kwargs["dec"] == pytest.approx(DEC)
        assert kwargs["tracking_ra_rate"] == pytest.approx(0.0)
        assert kwargs["tracking_dec_rate"] == pytest.approx(0.0)

    def test_on_shifts_frame_by_drift_since_slew(self, generate_image_calls):
        _expose(bad_tracking=True, seconds_since_slew=100.0)

        drift_deg = 100.0 * RATE / 3600
        kwargs = generate_image_calls[0]
        # RA drift is in coordinate space: 1 RA-hour = 15 degrees.
        assert kwargs["ra"] == pytest.approx(RA / 24 * 360 + drift_deg, abs=1e-4)
        assert kwargs["dec"] == pytest.approx(DEC + drift_deg, abs=1e-4)

    def test_on_trails_stars_during_exposure(self, generate_image_calls):
        _expose(bad_tracking=True, seconds_since_slew=100.0)

        dec = DEC + 100.0 * RATE / 3600
        kwargs = generate_image_calls[0]
        assert kwargs["tracking_ra_rate"] == pytest.approx(RATE * math.cos(math.radians(dec)))
        assert kwargs["tracking_dec_rate"] == pytest.approx(RATE)

    def test_on_without_slew_time_trails_but_does_not_shift(self, generate_image_calls):
        _expose(bad_tracking=True, seconds_since_slew=None)

        kwargs = generate_image_calls[0]
        assert kwargs["ra"] == pytest.approx(RA / 24 * 360)
        assert kwargs["dec"] == pytest.approx(DEC)
        assert kwargs["tracking_dec_rate"] == pytest.approx(RATE)
