"""ASCOM Alpaca DeviceState support.

Maps each device type's operational properties to their internal state keys and
builds the spec-compliant DeviceState value (an array of {Name, Value} objects
with a mandatory TimeStamp), per the ASCOM Alpaca Platform 7 specification:
https://ascom-standards.org/newdocs/focuser.html#Focuser.DeviceState
and AlpacaDeviceAPI_v1.yaml (DeviceStateResponse).
"""

from datetime import datetime, timezone
from typing import Any

# Operational DeviceState properties per ASCOM Alpaca interface, mapping the
# interface-correct (PascalCase) property Name -> the internal (lowercase) state key.
# Only operational properties are exposed via /devicestate (not metadata such as
# Name/Description/DriverInfo). A TimeStamp entry is appended by build_device_state().
# Casing follows the ASCOM interface definitions (e.g. CCDTemperature, UTCDate, SideOfPier).
DEVICE_STATE_PROPERTIES: dict[str, dict[str, str]] = {
    "focuser": {
        "IsMoving": "ismoving",
        "Position": "position",
        "Temperature": "temperature",
    },
    "camera": {
        "CameraState": "camera_state",
        "CCDTemperature": "ccdtemperature",
        "CoolerPower": "coolerpower",
        "HeatSinkTemperature": "heatsinktemperature",
        "ImageReady": "image_ready",
        "IsPulseGuiding": "ispulseguiding",
        "PercentCompleted": "percentcompleted",
    },
    "telescope": {
        "Altitude": "altitude",
        "AtHome": "athome",
        "AtPark": "atpark",
        "Azimuth": "azimuth",
        "Declination": "declination",
        "IsPulseGuiding": "ispulseguiding",
        "RightAscension": "rightascension",
        "SideOfPier": "sideofpier",
        "Slewing": "slewing",
        "Tracking": "tracking",
        "UTCDate": "utcdate",
    },
    "dome": {
        "Altitude": "altitude",
        "AtHome": "athome",
        "AtPark": "atpark",
        "Azimuth": "azimuth",
        "ShutterStatus": "shutterstatus",
        "Slewing": "slewing",
    },
    "rotator": {
        "IsMoving": "ismoving",
        "MechanicalPosition": "mechanicalposition",
        "Position": "position",
    },
    "filterwheel": {
        "Position": "position",
    },
    "safetymonitor": {
        "IsSafe": "issafe",
    },
    "observingconditions": {
        "CloudCover": "cloudcover",
        "DewPoint": "dewpoint",
        "Humidity": "humidity",
        "Pressure": "pressure",
        "RainRate": "rainrate",
        "SkyBrightness": "skybrightness",
        "SkyQuality": "skyquality",
        "SkyTemperature": "skytemperature",
        "StarFWHM": "starfwhm",
        "Temperature": "temperature",
        "WindDirection": "winddirection",
        "WindGust": "windgust",
        "WindSpeed": "windspeed",
    },
    "covercalibrator": {
        "Brightness": "brightness",
        "CalibratorState": "calibratorstate",
        "CoverState": "coverstate",
        "CalibratorChanging": "calibratorchanging",
        "CoverMoving": "covermoving",
    },
    # Switch has no operational DeviceState properties; only TimeStamp is returned.
    "switch": {},
}


def build_device_state(device_type: str, state: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the ASCOM Alpaca DeviceState value: an array of {Name, Value} objects.

    Includes only the operational properties defined for the device type (with
    interface-correct casing), skipping any whose state value is not known, and
    always appends a mandatory ISO-8601 TimeStamp entry.
    """
    items: list[dict[str, Any]] = [
        {"Name": name, "Value": state[key]}
        for name, key in DEVICE_STATE_PROPERTIES.get(device_type, {}).items()
        if key in state
    ]
    items.append({"Name": "TimeStamp", "Value": datetime.now(timezone.utc).isoformat()})

    return items
