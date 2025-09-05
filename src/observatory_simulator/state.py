import os
import threading
from collections import defaultdict
from typing import Any

from pydantic import BaseModel

from .config import Config

# Load configuration
CONFIG = Config(os.environ.get("ASTRA_SIMULATORS_CONFIG", "config.yaml"))
config = CONFIG.get()


# --- Pydantic Models for API Responses ---
class AlpacaResponse(BaseModel):
    ClientTransactionID: int = 0
    ServerTransactionID: int = 0
    ErrorNumber: int = 0
    ErrorMessage: str = ""


class BoolResponse(AlpacaResponse):
    Value: bool


class IntResponse(AlpacaResponse):
    Value: int


class DoubleResponse(AlpacaResponse):
    Value: float


class StringResponse(AlpacaResponse):
    Value: str


class StringArrayResponse(AlpacaResponse):
    Value: list[str]


class IntArrayResponse(AlpacaResponse):
    Value: list[int]


class DoubleArrayResponse(AlpacaResponse):
    Value: list[float]


class ImageArrayResponse(AlpacaResponse):
    Value: list[list[int]]


class DeviceStateResponse(AlpacaResponse):
    Value: dict[str, Any]


# ASCOM Enums
class CameraStates:
    IDLE = 0
    WAITING = 1
    EXPOSING = 2
    READING = 3
    DOWNLOAD = 4
    ERROR = 5


class SensorTypes:
    MONOCHROME = 0
    COLOR = 1
    RGGB = 2
    CMYG = 3
    CMYG2 = 4
    LRGB = 5


class PierSide:
    UNKNOWN = -1
    EAST = 0
    WEST = 1


class GuideDirections:
    NORTH = 0
    SOUTH = 1
    EAST = 2
    WEST = 3


class ShutterState:
    OPEN = 0
    CLOSED = 1
    OPENING = 2
    CLOSING = 3
    ERROR = 4


class CoverStatus:
    NOT_PRESENT = 0
    CLOSED = 1
    MOVING = 2
    OPEN = 3
    UNKNOWN = 4
    ERROR = 5


class CalibratorStatus:
    NOT_PRESENT = 0
    OFF = 1
    NOT_READY = 2
    READY = 3
    UNKNOWN = 4
    ERROR = 5


class AlignmentModes:
    ALT_AZ = 0
    POLAR = 1
    GERMAN_POLAR = 2


class EquatorialCoordinateType:
    OTHER = 0
    TOPOCENTRIC = 1
    J2000 = 2
    J2050 = 3
    B1950 = 4


class DriveRates:
    SIDEREAL = 0
    LUNAR = 1
    SOLAR = 2
    KING = 3


class TelescopeAxes:
    PRIMARY = 0
    SECONDARY = 1
    TERTIARY = 2


# --- State Classes ---
class CameraState(BaseModel):
    camera_state: int = CameraStates.IDLE
    connected: bool = False
    image_ready: bool = False
    exposure_start_time: str | None = None
    exposure_duration: float = 0.0
    image_data: list[list[int]] | None = None
    light: bool = True
    # Binning and subframe - these will be overridden by config
    binx: int = 1
    biny: int = 1
    numx: int = 1024  # Will be set from cameraxsize in config
    numy: int = 1024  # Will be set from cameraysize in config
    startx: int = 0
    starty: int = 0
    # Temperature control - config will override
    ccdtemperature: float = 20.0
    setccdtemperature: float = 20.0
    cooleron: bool = False
    coolerpower: float = 0.0
    # Gain and offset - config will override
    gain: int = 1
    offset: int = 100
    # Readout mode - config will override
    readoutmode: int = 0
    fastreadout: bool = False
    # Pulse guiding
    ispulseguiding: bool = False
    # Progress
    percentcompleted: int = 0


class TelescopeState(BaseModel):
    connected: bool = False
    # Position - config will override these
    rightascension: float = 0.0
    declination: float = 0.0
    altitude: float = 0.0
    azimuth: float = 0.0
    targetrightascension: float = 0.0
    targetdeclination: float = 0.0
    tracking: bool = False
    slewing: bool = False
    athome: bool = False
    atpark: bool = False
    sideofpier: int = PierSide.UNKNOWN
    ispulseguiding: bool = False
    # Site information - config will override
    sitelatitude: float = 0.0
    sitelongitude: float = 0.0
    siteelevation: float = 0.0
    # Tracking rates
    rightascensionrate: float = 0.0
    declinationrate: float = 0.0
    trackingrate: int = DriveRates.SIDEREAL
    # Guide rates
    guideraterightascension: float = 0.0
    guideratedeclination: float = 0.0
    # Settings - config will override
    doesrefraction: bool = True
    slewsettletime: float = 0.0
    # UTC date
    utcdate: str | None = None


class DomeState(BaseModel):
    connected: bool = False
    # Config will override these
    altitude: float = 0.0
    azimuth: float = 0.0
    athome: bool = False
    atpark: bool = False
    slewing: bool = False
    shutterstatus: int = ShutterState.CLOSED
    slaved: bool = False


class FocuserState(BaseModel):
    connected: bool = False
    # Config will override these
    position: int = 0
    ismoving: bool = False
    tempcomp: bool = False
    temperature: float = 20.0


class FilterWheelState(BaseModel):
    connected: bool = False
    position: int = 0  # Config will override


class RotatorState(BaseModel):
    connected: bool = False
    # Config will override these
    position: float = 0.0
    mechanicalposition: float = 0.0
    targetposition: float = 0.0
    ismoving: bool = False
    reverse: bool = False


class SafetyMonitorState(BaseModel):
    connected: bool = False
    issafe: bool = True  # Config will override


class SwitchState(BaseModel):
    connected: bool = False
    switches: dict[int, dict[str, Any]] = {}  # Config will override


class ObservingConditionsState(BaseModel):
    connected: bool = False
    # Config will override all these values
    averageperiod: float = 0.0
    cloudcover: float = 0.0
    dewpoint: float = 0.0
    humidity: float = 0.0
    pressure: float = 0.0
    rainrate: float = 0.0
    skybrightness: float = 0.0
    skyquality: float = 0.0
    skytemperature: float = 0.0
    starfwhm: float = 0.0
    temperature: float = 0.0
    winddirection: float = 0.0
    windgust: float = 0.0
    windspeed: float = 0.0


class CoverCalibratorState(BaseModel):
    connected: bool = False
    # Config will override these
    brightness: int = 0
    calibratorchanging: bool = False
    calibratorstate: int = CalibratorStatus.NOT_PRESENT
    covermoving: bool = False
    coverstate: int = CoverStatus.CLOSED


# Global state management
_state = defaultdict(lambda: defaultdict(dict))
_server_transaction_id = 0
_state_lock = threading.Lock()


def get_server_transaction_id() -> int:
    global _server_transaction_id
    with _state_lock:
        _server_transaction_id += 1
        return _server_transaction_id


def _create_default_state(device_type: str, device_number: int) -> dict[str, Any]:
    """Create default state for a device, incorporating configuration values"""
    config_data = get_device_config(device_type, device_number)

    # Start with minimal base state
    if device_type == "camera":
        state = CameraState().model_dump()
        # Handle the special case where config uses 'cameraxsize'/'cameraysize'
        # but state uses 'numx'/'numy'
        if "cameraxsize" in config_data:
            state["numx"] = config_data["cameraxsize"]
        if "cameraysize" in config_data:
            state["numy"] = config_data["cameraysize"]
    elif device_type == "telescope":
        state = TelescopeState().model_dump()
    elif device_type == "dome":
        state = DomeState().model_dump()
    elif device_type == "focuser":
        state = FocuserState().model_dump()
    elif device_type == "filterwheel":
        state = FilterWheelState().model_dump()
    elif device_type == "rotator":
        state = RotatorState().model_dump()
    elif device_type == "safetymonitor":
        state = SafetyMonitorState().model_dump()
    elif device_type == "switch":
        state = SwitchState().model_dump()
    elif device_type == "observingconditions":
        state = ObservingConditionsState().model_dump()
    elif device_type == "covercalibrator":
        state = CoverCalibratorState().model_dump()
    else:
        state = {"connected": False}

    # Apply ALL configuration values, overriding defaults
    state.update(config_data)
    return state


def get_device_state(device_type: str, device_number: int) -> dict[str, Any]:
    with _state_lock:
        if not _state[device_type][device_number]:
            # Initialize device state with configuration
            _state[device_type][device_number] = _create_default_state(device_type, device_number)

        return _state[device_type][device_number].copy()


def update_device_state(device_type: str, device_number: int, new_state: dict[str, Any]):
    with _state_lock:
        if device_type not in _state or device_number not in _state[device_type]:
            # Initialize if not exists
            _state[device_type][device_number] = _create_default_state(device_type, device_number)

        _state[device_type][device_number].update(new_state)


def get_device_config(device_type: str, device_number: int) -> dict[str, Any]:
    """Get device configuration from config.yaml"""
    return config.get("devices", {}).get(device_type, {}).get(device_number, {})


def validate_device_exists(device_type: str, device_number: int) -> bool:
    """Check if device exists in configuration"""
    return device_number in config.get("devices", {}).get(device_type, {})


def reload_config() -> None:
    """Reload configuration from file (useful for development)"""
    global config
    config = CONFIG.reload()
    # Clear existing state so it will be re-initialized with new config
    global _state
    with _state_lock:
        _state.clear()


def get_all_configured_devices() -> dict[str, list[int]]:
    """Get all device types and numbers that are configured"""
    devices = {}
    for device_type, device_configs in config.get("devices", {}).items():
        devices[device_type] = list(device_configs.keys())
    return devices
