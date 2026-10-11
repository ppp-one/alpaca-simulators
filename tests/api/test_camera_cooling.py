import math

import pytest
from fastapi.testclient import TestClient

from alpaca_simulators.api import camera
from alpaca_simulators.main import app
from alpaca_simulators.state import reload_config, update_device_state

client = TestClient(app)

URL = "/api/v1/camera/0"


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture()
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(camera, "monotonic", fake)
    camera._cooling.clear()
    update_device_state(
        "camera",
        0,
        {
            "ccdtemperature": 20.0,
            "setccdtemperature": 20.0,
            "cooleron": False,
            "cooling_time": 0.0,
        },
    )
    yield fake
    camera._cooling.clear()
    reload_config()


def _temperature() -> float:
    return client.get(f"{URL}/ccdtemperature").json()["Value"]


def _start_cooling(target: float, seconds: float):
    update_device_state("camera", 0, {"cooling_time": seconds})
    client.put(f"{URL}/cooleron", data={"CoolerOn": "true"})
    client.put(f"{URL}/setccdtemperature", data={"SetCCDTemperature": str(target)})


def test_default_is_instant(clock):
    update_device_state("camera", 0, {"cooling_time": 0.0})
    client.put(f"{URL}/setccdtemperature", data={"SetCCDTemperature": "-10"})
    assert _temperature() == -10.0


def test_temperature_follows_exponential_curve(clock):
    _start_cooling(target=-20.0, seconds=60.0)
    assert _temperature() == pytest.approx(20.0)

    clock.now += 10
    t10 = _temperature()
    clock.now += 10
    t20 = _temperature()

    # Exponential decay: equal time steps shrink the gap by the same factor.
    assert 20.0 > t10 > t20 > -20.0
    ratio_first = (t10 - -20.0) / (20.0 - -20.0)
    ratio_second = (t20 - -20.0) / (t10 - -20.0)
    assert ratio_first == pytest.approx(ratio_second)


def test_reaches_set_point_after_cooling_time(clock):
    _start_cooling(target=-20.0, seconds=60.0)
    clock.now += 59.9
    assert _temperature() > -20.0
    clock.now += 0.2
    assert _temperature() == -20.0


def test_gap_is_within_tolerance_at_cooling_time(clock):
    _start_cooling(target=-20.0, seconds=60.0)
    clock.now += 60.0 - 1e-6
    assert abs(_temperature() - -20.0) <= camera.COOLING_TOLERANCE + 1e-3


def test_no_cooling_with_cooler_off(clock):
    update_device_state("camera", 0, {"cooling_time": 60.0})
    client.put(f"{URL}/setccdtemperature", data={"SetCCDTemperature": "-20"})
    clock.now += 30
    assert _temperature() == 20.0


def test_new_set_point_starts_from_current_temperature(clock):
    _start_cooling(target=-20.0, seconds=60.0)
    clock.now += 20
    mid = _temperature()
    client.put(f"{URL}/setccdtemperature", data={"SetCCDTemperature": "0"})
    assert _temperature() == pytest.approx(mid)
    clock.now += 60
    assert _temperature() == 0.0


def test_turning_cooler_off_holds_temperature(clock):
    _start_cooling(target=-20.0, seconds=60.0)
    clock.now += 20
    mid = _temperature()
    client.put(f"{URL}/cooleron", data={"CoolerOn": "false"})
    clock.now += 60
    assert _temperature() == pytest.approx(mid)


def test_cooler_power_falls_during_cooldown(clock):
    _start_cooling(target=-20.0, seconds=60.0)
    power = lambda: client.get(f"{URL}/coolerpower").json()["Value"]  # noqa: E731
    start = power()
    clock.now += 20
    middle = power()
    clock.now += 100
    end = power()
    assert start == pytest.approx(100.0)
    assert start > middle > end
    assert end == camera.MIN_COOLER_POWER
    assert math.isfinite(middle)


def test_stale_curve_is_dropped_after_state_reset(clock):
    _start_cooling(target=-20.0, seconds=60.0)
    clock.now += 20
    _temperature()
    # Something outside the endpoints resets the stored temperature.
    update_device_state("camera", 0, {"ccdtemperature": 5.0, "cooleron": False})
    clock.now += 10
    assert _temperature() == 5.0


def test_cache_key_depends_on_rotation_and_temperature():
    args = dict(
        ra=1, dec=2, duration=3, light=True, focus=0, sunlight=False,
        tracking_ra_rate=0, tracking_dec_rate=0, numx=4, numy=4, binx=1, biny=1,
    )  # fmt: skip
    base = camera.make_cache_key(**args, ccdtemperature=-20.0, rotation=0.0)
    assert base != camera.make_cache_key(**args, ccdtemperature=-20.0, rotation=60)
    assert base != camera.make_cache_key(**args, ccdtemperature=-10.0, rotation=0.0)
