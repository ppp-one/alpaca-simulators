import math
import threading
from datetime import datetime, timezone
from time import sleep

from fastapi import APIRouter, Form, Path, Query

from alpaca_simulators.api.common import AlpacaError, validate_device
from alpaca_simulators.state import (
    AlignmentModes,
    AlpacaResponse,
    BoolResponse,
    DoubleResponse,
    DriveRates,
    EquatorialCoordinateType,
    GuideDirections,
    IntArrayResponse,
    IntResponse,
    PierSide,
    Rate,
    RateArrayResponse,
    StringResponse,
    TelescopeAxes,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()


def _complete_pulseguide(device_number: int, delay_seconds: float) -> None:
    """Background thread: reset IsPulseGuiding after the guide duration expires."""
    sleep(delay_seconds)
    update_device_state("telescope", device_number, {"ispulseguiding": False})


def normalize_hours(hours):
    """Normalize hours to 0-24 range"""
    return hours % 24.0


def normalize_degrees(degrees):
    """Normalize degrees to -90 to +90 range for declination"""
    return max(-90.0, min(90.0, degrees))


def hours_to_degrees(hours):
    """Convert hours to degrees"""
    return hours * 15.0


def degrees_to_hours(degrees):
    """Convert degrees to hours"""
    return degrees / 15.0


def _radec_to_altaz(
    ra_hours: float,
    dec_deg: float,
    lat_deg: float,
    lon_deg: float,
    utc_timestamp: float,
) -> tuple[float, float]:
    """Convert equatorial coordinates to horizontal coordinates.

    Returns (altitude, azimuth) in degrees.
    Azimuth is measured from North through East (0–360°).
    """
    jd = utc_timestamp / 86400.0 + 2440587.5
    gmst = 18.697374558 + 24.06570982441908 * (jd - 2451545.0)
    lst = (gmst + lon_deg / 15.0) % 24.0

    ha = math.radians((lst - ra_hours) * 15.0)  # hour angle in radians
    lat = math.radians(lat_deg)
    dec = math.radians(dec_deg)

    sin_alt = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))

    az_rad = math.atan2(
        -math.cos(dec) * math.sin(ha),
        math.sin(dec) * math.cos(lat) - math.cos(dec) * math.sin(lat) * math.cos(ha),
    )
    az = math.degrees(az_rad) % 360.0

    return alt, az


def _altaz_to_radec(
    alt_deg: float,
    az_deg: float,
    lat_deg: float,
    lon_deg: float,
    utc_timestamp: float,
) -> tuple[float, float]:
    """Convert horizontal coordinates to equatorial coordinates.

    Inverse of _radec_to_altaz. Azimuth measured from North through East.
    Returns (right_ascension_hours, declination_degrees).
    """
    jd = utc_timestamp / 86400.0 + 2440587.5
    gmst = 18.697374558 + 24.06570982441908 * (jd - 2451545.0)
    lst = (gmst + lon_deg / 15.0) % 24.0

    alt = math.radians(alt_deg)
    az = math.radians(az_deg)
    lat = math.radians(lat_deg)

    sin_dec = math.sin(lat) * math.sin(alt) + math.cos(lat) * math.cos(alt) * math.cos(az)
    dec_deg = math.degrees(math.asin(max(-1.0, min(1.0, sin_dec))))

    ha_rad = math.atan2(
        -math.sin(az) * math.cos(alt),
        math.sin(alt) * math.cos(lat) - math.cos(alt) * math.sin(lat) * math.cos(az),
    )
    ra = normalize_hours(lst - math.degrees(ha_rad) / 15.0)
    return ra, dec_deg


# Sidereal rate: 24 RA-hours per sidereal day (86164.0905 s).
_SIDEREAL_RATE_RA_H_PER_S = 24.0 / 86164.0905


def compute_coordinate_rates(state: dict) -> tuple[float, float]:
    """Return the telescope's coordinate-space angular velocity as
    ``(ra_rate, dec_rate)`` in RA-hours/s and degrees/s for the current
    tracking / MoveAxis state. Active slews are not considered here.

    This is the single source of truth shared by the motion model
    (_advance_telescope_motion) and the camera's star-trail rendering, so the
    image trailing always matches how the reported coordinates move.

    Units:
      * RightAscensionRate: seconds of RA per sidereal second (÷3600 → RA-hours/s).
      * DeclinationRate: arcsec per SI second (÷3600 → degrees/s).
      * MoveAxis rates: deg/s (primary ÷15 → RA-hours/s).
    The sidereal/SI-second distinction (~0.27%) is ignored; wall-clock seconds are used.

    Tracking on: RA/Dec change only by the rate offsets. Tracking off: RA drifts at the
    sidereal rate and the offsets are ignored. MoveAxis adds in either case.
    """
    if state.get("tracking", False):
        ra_rate = state.get("rightascensionrate", 0.0) / 3600.0  # sec-of-RA/s → RA-hours/s
        dec_rate = state.get("declinationrate", 0.0) / 3600.0  # arcsec/s → degrees/s
    else:
        ra_rate = _SIDEREAL_RATE_RA_H_PER_S
        dec_rate = 0.0
    ra_rate += state.get("moveaxis_primary_rate", 0.0) / 15.0  # deg/s → RA-hours/s
    dec_rate += state.get("moveaxis_secondary_rate", 0.0)  # deg/s
    return ra_rate, dec_rate


def _advance_telescope_motion(device_number: int) -> None:
    """Advance stored telescope coordinates based on elapsed wall-clock time."""
    state = get_device_state("telescope", device_number)
    now = datetime.now(timezone.utc).timestamp()
    last_update = state.get("last_motion_update")

    if last_update is None:
        update_device_state("telescope", device_number, {"last_motion_update": now})
        return

    elapsed_seconds = now - last_update
    if elapsed_seconds <= 0:
        return

    lat = state.get("sitelatitude", 0.0)
    lon = state.get("sitelongitude", 0.0)
    slew_rate = state.get("slew_rate", 15.0)  # degrees per second

    # --- Active slew: interpolate toward the stored target at slew_rate deg/s ---

    slew_target_alt = state.get("slew_target_alt")
    slew_target_az = state.get("slew_target_az")
    slew_target_ra = state.get("slew_target_ra")
    slew_target_dec = state.get("slew_target_dec")

    if slew_target_alt is not None and slew_target_az is not None:
        # AltAz slew: drive in alt/az space, convert result to RA/Dec.
        current_alt = state.get("altitude", 0.0)
        current_az = state.get("azimuth", 0.0)

        dalt = slew_target_alt - current_alt
        daz = slew_target_az - current_az
        # Shortest angular path in azimuth.
        if daz > 180.0:
            daz -= 360.0
        elif daz < -180.0:
            daz += 360.0

        total_dist = math.sqrt(dalt**2 + daz**2)
        max_step = elapsed_seconds * slew_rate

        if total_dist <= max_step or total_dist == 0.0:
            new_alt = slew_target_alt
            new_az = slew_target_az
            slew_complete = True
        else:
            frac = max_step / total_dist
            new_alt = current_alt + frac * dalt
            new_az = (current_az + frac * daz) % 360.0
            slew_complete = False

        new_ra, new_dec = _altaz_to_radec(new_alt, new_az, lat, lon, now)

        updates: dict = {
            "altitude": new_alt,
            "azimuth": new_az,
            "rightascension": new_ra,
            "declination": new_dec,
            "last_motion_update": now,
        }
        if slew_complete:
            updates["slewing"] = False
            updates["slew_target_alt"] = None
            updates["slew_target_az"] = None
        update_device_state("telescope", device_number, updates)
        return

    if slew_target_ra is not None and slew_target_dec is not None:
        # RA/Dec slew: drive in equatorial space, convert result to alt/az.
        current_ra = state.get("rightascension", 0.0)
        current_dec = state.get("declination", 0.0)

        dra_deg = (slew_target_ra - current_ra) * 15.0
        # Shortest angular path in RA.
        if dra_deg > 180.0:
            dra_deg -= 360.0
        elif dra_deg < -180.0:
            dra_deg += 360.0
        ddec = slew_target_dec - current_dec

        total_dist = math.sqrt(dra_deg**2 + ddec**2)
        max_step = elapsed_seconds * slew_rate

        if total_dist <= max_step or total_dist == 0.0:
            new_ra = slew_target_ra
            new_dec = slew_target_dec
            slew_complete = True
        else:
            frac = max_step / total_dist
            new_ra = normalize_hours(current_ra + frac * dra_deg / 15.0)
            new_dec = normalize_degrees(current_dec + frac * ddec)
            slew_complete = False

        new_alt, new_az = _radec_to_altaz(new_ra, new_dec, lat, lon, now)

        updates = {
            "rightascension": new_ra,
            "declination": new_dec,
            "altitude": new_alt,
            "azimuth": new_az,
            "last_motion_update": now,
        }
        if slew_complete:
            updates["slewing"] = False
            updates["slew_target_ra"] = None
            updates["slew_target_dec"] = None
        update_device_state("telescope", device_number, updates)
        return

    # --- No active slew: apply normal tracking / MoveAxis rates ---

    # Coordinate-space rates (RA-hours/s, deg/s); see compute_coordinate_rates().
    ra_rate, dec_rate = compute_coordinate_rates(state)

    rightascension = normalize_hours(state.get("rightascension", 0.0) + elapsed_seconds * ra_rate)
    declination = normalize_degrees(state.get("declination", 0.0) + elapsed_seconds * dec_rate)

    altitude, azimuth = _radec_to_altaz(rightascension, declination, lat, lon, now)

    update_device_state(
        "telescope",
        device_number,
        {
            "rightascension": rightascension,
            "declination": declination,
            "altitude": altitude,
            "azimuth": azimuth,
            "last_motion_update": now,
        },
    )


_UPDATE_INTERVAL = 0.1  # seconds between background coordinate updates


def _telescope_background_loop(device_number: int) -> None:
    """Daemon thread: update telescope coordinates every _UPDATE_INTERVAL seconds."""
    while True:
        sleep(_UPDATE_INTERVAL)
        _advance_telescope_motion(device_number)


def start_background_updater(device_numbers: list[int]) -> None:
    """Start a background updater thread for each of the given telescope device numbers."""
    for device_number in device_numbers:
        threading.Thread(
            target=_telescope_background_loop,
            args=(device_number,),
            daemon=True,
        ).start()


@router.get("/telescope/{device_number}/alignmentmode", response_model=IntResponse)
def get_alignmentmode(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return IntResponse(
        Value=state.get("alignmentmode", AlignmentModes.GERMAN_POLAR),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/altitude", response_model=DoubleResponse)
def get_altitude(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")
    return DoubleResponse(
        Value=state.get("altitude", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/aperturearea", response_model=DoubleResponse)
def get_aperturearea(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    diameter = state.get("aperturediameter", 8.0)  # m
    area = math.pi * (diameter / 2) ** 2  # m²
    return DoubleResponse(
        Value=area,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/aperturediameter", response_model=DoubleResponse)
def get_aperturediameter(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("aperturediameter", 8.0),  # m
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/athome", response_model=BoolResponse)
def get_athome(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("athome", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/atpark", response_model=BoolResponse)
def get_atpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("atpark", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/azimuth", response_model=DoubleResponse)
def get_azimuth(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")
    return DoubleResponse(
        Value=state.get("azimuth", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/canfindhome", response_model=BoolResponse)
def get_canfindhome(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("canfindhome", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/canpark", response_model=BoolResponse)
def get_canpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("canpark", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/canpulseguide", response_model=BoolResponse)
def get_canpulseguide(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("canpulseguide", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/cansetdeclinationrate", response_model=BoolResponse)
def get_cansetdeclinationrate(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("cansetdeclinationrate", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/cansetguiderates", response_model=BoolResponse)
def get_cansetguiderates(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("cansetguiderates", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/cansetpark", response_model=BoolResponse)
def get_cansetpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("cansetpark", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/cansetpierside", response_model=BoolResponse)
def get_cansetpierside(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("cansetpierside", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/cansetrightascensionrate", response_model=BoolResponse)
def get_cansetrightascensionrate(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("cansetrightascensionrate", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/cansettracking", response_model=BoolResponse)
def get_cansettracking(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("cansettracking", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/canslew", response_model=BoolResponse)
def get_canslew(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("canslew", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/canslewaltaz", response_model=BoolResponse)
def get_canslewaltaz(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("canslewaltaz", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/canslewaltazasync", response_model=BoolResponse)
def get_canslewaltazasync(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("canslewaltazasync", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/canslewasync", response_model=BoolResponse)
def get_canslewasync(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("canslewasync", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/cansync", response_model=BoolResponse)
def get_cansync(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("cansync", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/cansyncaltaz", response_model=BoolResponse)
def get_cansyncaltaz(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("cansyncaltaz", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/canunpark", response_model=BoolResponse)
def get_canunpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("canunpark", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/declination", response_model=DoubleResponse)
def get_declination(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    _advance_telescope_motion(device_number)
    state = get_device_state("telescope", device_number)
    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")
    return DoubleResponse(
        Value=state.get("declination", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/declinationrate", response_model=DoubleResponse)
def get_declinationrate(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("declinationrate", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/declinationrate", response_model=AlpacaResponse)
def set_declinationrate(
    device_number: int = Path(..., ge=0),
    DeclinationRate: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    _advance_telescope_motion(device_number)
    update_device_state(
        "telescope",
        device_number,
        {
            "declinationrate": DeclinationRate,
            "last_motion_update": datetime.now(timezone.utc).timestamp(),
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/doesrefraction", response_model=BoolResponse)
def get_doesrefraction(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("doesrefraction", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/doesrefraction", response_model=AlpacaResponse)
def set_doesrefraction(
    device_number: int = Path(..., ge=0),
    DoesRefraction: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("telescope", device_number, {"doesrefraction": DoesRefraction})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/equatorialsystem", response_model=IntResponse)
def get_equatorialsystem(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return IntResponse(
        Value=state.get("equatorialsystem", EquatorialCoordinateType.TOPOCENTRIC),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/focallength", response_model=DoubleResponse)
def get_focallength(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("focallength", 1000.0),  # mm
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/guideratedeclination", response_model=DoubleResponse)
def get_guideratedeclination(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("guideratedeclination", 15.0),  # arcsec/sec
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/guideratedeclination", response_model=AlpacaResponse)
def set_guideratedeclination(
    device_number: int = Path(..., ge=0),
    GuideRateDeclination: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if GuideRateDeclination < 0:
        raise AlpacaError(0x402, "Guide rate must be positive")

    update_device_state("telescope", device_number, {"guideratedeclination": GuideRateDeclination})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/guideraterightascension", response_model=DoubleResponse)
def get_guideraterightascension(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("guideraterightascension", 15.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/guideraterightascension", response_model=AlpacaResponse)
def set_guideraterightascension(
    device_number: int = Path(..., ge=0),
    GuideRateRightAscension: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if GuideRateRightAscension < 0:
        raise AlpacaError(0x402, "Guide rate must be positive")

    update_device_state(
        "telescope", device_number, {"guideraterightascension": GuideRateRightAscension}
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/ispulseguiding", response_model=BoolResponse)
def get_ispulseguiding(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("ispulseguiding", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/rightascension", response_model=DoubleResponse)
def get_rightascension(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    _advance_telescope_motion(device_number)
    state = get_device_state("telescope", device_number)
    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")
    return DoubleResponse(
        Value=state.get("rightascension", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/rightascensionrate", response_model=DoubleResponse)
def get_rightascensionrate(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("rightascensionrate", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/rightascensionrate", response_model=AlpacaResponse)
def set_rightascensionrate(
    device_number: int = Path(..., ge=0),
    RightAscensionRate: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    _advance_telescope_motion(device_number)
    update_device_state(
        "telescope",
        device_number,
        {
            "rightascensionrate": RightAscensionRate,
            "last_motion_update": datetime.now(timezone.utc).timestamp(),
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/sideofpier", response_model=IntResponse)
def get_sideofpier(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return IntResponse(
        Value=state.get("sideofpier", PierSide.UNKNOWN),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/sideofpier", response_model=AlpacaResponse)
def set_sideofpier(
    device_number: int = Path(..., ge=0),
    SideOfPier: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if SideOfPier not in [PierSide.EAST, PierSide.WEST, PierSide.UNKNOWN]:
        raise AlpacaError(0x402, "Invalid pier side value")

    update_device_state("telescope", device_number, {"sideofpier": SideOfPier})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/siderealtime", response_model=DoubleResponse)
def get_siderealtime(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)

    # Calculate local sidereal time
    utc_now = datetime.now(timezone.utc)
    longitude = state.get("sitelongitude", 0.0)

    # Simplified calculation - in practice this would use proper astronomy formulas
    jd = utc_now.timestamp() / 86400.0 + 2440587.5  # Julian day
    gmst = 18.697374558 + 24.06570982441908 * (jd - 2451545.0)  # Greenwich Mean Sidereal Time
    lst = (gmst + longitude / 15.0) % 24.0  # Local Sidereal Time

    return DoubleResponse(
        Value=lst,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/siteelevation", response_model=DoubleResponse)
def get_siteelevation(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("siteelevation", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/siteelevation", response_model=AlpacaResponse)
def set_siteelevation(
    device_number: int = Path(..., ge=0),
    SiteElevation: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)

    if SiteElevation < -300.0 or SiteElevation > 10000.0:
        raise AlpacaError(0x401, "Site elevation must be between -300 and +10000 metres")

    update_device_state("telescope", device_number, {"siteelevation": SiteElevation})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/sitelatitude", response_model=DoubleResponse)
def get_sitelatitude(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("sitelatitude", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/sitelatitude", response_model=AlpacaResponse)
def set_sitelatitude(
    device_number: int = Path(..., ge=0),
    SiteLatitude: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)

    if SiteLatitude < -90.0 or SiteLatitude > 90.0:
        raise AlpacaError(0x401, "Latitude must be between -90 and +90 degrees")

    update_device_state("telescope", device_number, {"sitelatitude": SiteLatitude})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/sitelongitude", response_model=DoubleResponse)
def get_sitelongitude(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("sitelongitude", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/sitelongitude", response_model=AlpacaResponse)
def set_sitelongitude(
    device_number: int = Path(..., ge=0),
    SiteLongitude: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)

    if SiteLongitude < -180.0 or SiteLongitude > 180.0:
        raise AlpacaError(0x401, "Longitude must be between -180 and +180 degrees")

    update_device_state("telescope", device_number, {"sitelongitude": SiteLongitude})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/slewing", response_model=BoolResponse)
def get_slewing(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("slewing", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/slewsettletime", response_model=IntResponse)
def get_slewsettletime(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return IntResponse(
        Value=int(state.get("slewsettletime", 0)),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/slewsettletime", response_model=AlpacaResponse)
def set_slewsettletime(
    device_number: int = Path(..., ge=0),
    SlewSettleTime: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if SlewSettleTime < 0:
        raise AlpacaError(0x401, "Slew settle time cannot be negative")

    update_device_state("telescope", device_number, {"slewsettletime": SlewSettleTime})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/targetdeclination", response_model=DoubleResponse)
def get_targetdeclination(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    value = state.get("targetdeclination")
    if value is None:
        raise AlpacaError(0x402, "Target declination has not been set")
    return DoubleResponse(
        Value=value,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/targetdeclination", response_model=AlpacaResponse)
def set_targetdeclination(
    device_number: int = Path(..., ge=0),
    TargetDeclination: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if TargetDeclination < -90.0 or TargetDeclination > 90.0:
        raise AlpacaError(0x401, "Declination must be between -90 and +90 degrees")

    update_device_state("telescope", device_number, {"targetdeclination": TargetDeclination})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/targetrightascension", response_model=DoubleResponse)
def get_targetrightascension(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    value = state.get("targetrightascension")
    if value is None:
        raise AlpacaError(0x402, "Target right ascension has not been set")
    return DoubleResponse(
        Value=value,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/targetrightascension", response_model=AlpacaResponse)
def set_targetrightascension(
    device_number: int = Path(..., ge=0),
    TargetRightAscension: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if TargetRightAscension < 0.0 or TargetRightAscension >= 24.0:
        raise AlpacaError(0x401, "Right ascension must be between 0 and 24 hours")

    update_device_state("telescope", device_number, {"targetrightascension": TargetRightAscension})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/tracking", response_model=BoolResponse)
def get_tracking(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return BoolResponse(
        Value=state.get("tracking", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/tracking", response_model=AlpacaResponse)
def set_tracking(
    device_number: int = Path(..., ge=0),
    Tracking: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("telescope", device_number, {"tracking": Tracking})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/trackingrate", response_model=IntResponse)
def get_trackingrate(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return IntResponse(
        Value=state.get("trackingrate", DriveRates.SIDEREAL),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/trackingrate", response_model=AlpacaResponse)
def set_trackingrate(
    device_number: int = Path(..., ge=0),
    TrackingRate: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    valid_rates = [
        DriveRates.SIDEREAL,
        DriveRates.LUNAR,
        DriveRates.SOLAR,
        DriveRates.KING,
    ]
    if TrackingRate not in valid_rates:
        raise AlpacaError(0x401, "Invalid tracking rate")

    update_device_state("telescope", device_number, {"trackingrate": TrackingRate})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/trackingrates", response_model=IntArrayResponse)
def get_trackingrates(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    return IntArrayResponse(
        Value=[DriveRates.SIDEREAL, DriveRates.LUNAR, DriveRates.SOLAR, DriveRates.KING],
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/utcdate", response_model=StringResponse)
def get_utcdate(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    utc_now = datetime.now(timezone.utc)
    return StringResponse(
        Value=utc_now.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/utcdate", response_model=AlpacaResponse)
def set_utcdate(
    device_number: int = Path(..., ge=0),
    UTCDate: str = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)

    # In a real implementation, this might synchronize the system clock
    # For simulation purposes, we'll just accept the value

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Action methods


@router.put("/telescope/{device_number}/abortslew", response_model=AlpacaResponse)
def abortslew(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    update_device_state(
        "telescope",
        device_number,
        {
            "slewing": False,
            "slew_target_ra": None,
            "slew_target_dec": None,
            "slew_target_alt": None,
            "slew_target_az": None,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/axisrates", response_model=RateArrayResponse)
def get_axisrates(
    device_number: int = Path(..., ge=0),
    Axis: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)

    if Axis not in [
        TelescopeAxes.PRIMARY,
        TelescopeAxes.SECONDARY,
        TelescopeAxes.TERTIARY,
    ]:
        raise AlpacaError(0x401, "Invalid axis")

    # Return available rates for the axis
    rates = [state.get(f"axis{Axis}rates", None) or Rate()]

    return RateArrayResponse(
        Value=rates,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/canmoveaxis", response_model=BoolResponse)
def get_canmoveaxis(
    device_number: int = Path(..., ge=0),
    Axis: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)

    if Axis not in [
        TelescopeAxes.PRIMARY,
        TelescopeAxes.SECONDARY,
        TelescopeAxes.TERTIARY,
    ]:
        raise AlpacaError(0x401, "Invalid axis")

    can_move = state.get(f"canmoveaxis{Axis}", True)
    return BoolResponse(
        Value=can_move,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/destinationsideofpier", response_model=IntResponse)
def get_destinationsideofpier(
    device_number: int = Path(..., ge=0),
    RightAscension: float = Query(...),
    Declination: float = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("telescope", device_number)

    # Simple logic: if RA is east of meridian, use west side of pier
    current_sidereal = 12.0  # Simplified
    if RightAscension > current_sidereal:
        pier_side = PierSide.WEST
    else:
        pier_side = PierSide.EAST

    return IntResponse(
        Value=pier_side,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/findhome", response_model=AlpacaResponse)
def findhome(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    update_device_state(
        "telescope",
        device_number,
        {"athome": True, "slewing": False, "rightascension": 0.0, "declination": 0.0},
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/moveaxis", response_model=AlpacaResponse)
def moveaxis(
    device_number: int = Path(..., ge=0),
    Axis: int = Form(...),
    Rate: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)

    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    if Axis not in [
        TelescopeAxes.PRIMARY,
        TelescopeAxes.SECONDARY,
        TelescopeAxes.TERTIARY,
    ]:
        raise AlpacaError(0x401, f"Invalid axis: {Axis}")

    # Rate=0 is always valid (stop command). For non-zero rates, check supported range.
    if Rate != 0.0:
        axis_rates = state.get(f"axis{Axis}rates")
        if axis_rates is not None:
            max_rate = (
                axis_rates["Maximum"] if isinstance(axis_rates, dict) else axis_rates.Maximum
            )
            if abs(Rate) > max_rate:
                raise AlpacaError(0x401, f"Rate {Rate} is outside the valid range for axis {Axis}")

    _AXIS_KEY = {
        TelescopeAxes.PRIMARY: "primary",
        TelescopeAxes.SECONDARY: "secondary",
        TelescopeAxes.TERTIARY: "tertiary",
    }
    axis_key = _AXIS_KEY[Axis]
    rate_key = f"moveaxis_{axis_key}_rate"
    saved_tracking_key = f"moveaxis_{axis_key}_saved_tracking"

    updates: dict = {}

    if Rate != 0.0:
        # Save tracking state the first time this axis starts moving so it can be
        # restored when Rate=0 is called, per the ASCOM specification.
        if state.get(rate_key, 0.0) == 0.0:
            updates[saved_tracking_key] = state.get("tracking", False)
        updates[rate_key] = Rate
        updates["slewing"] = True
    else:
        # Rate=0: stop this axis immediately and restore the previous tracking state.
        updates[rate_key] = 0.0
        saved_tracking = state.get(saved_tracking_key)
        if saved_tracking is not None:
            updates["tracking"] = saved_tracking
            updates[saved_tracking_key] = None
        # Slewing remains True only if another axis is still in motion.
        other_axes = [k for k in _AXIS_KEY.values() if k != axis_key]
        any_moving = any(state.get(f"moveaxis_{ax}_rate", 0.0) != 0.0 for ax in other_axes)
        updates["slewing"] = any_moving

    update_device_state("telescope", device_number, updates)

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/park", response_model=AlpacaResponse)
def park(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("telescope", device_number)
    park_ra = state.get("parkrightascension", 180.0)
    park_dec = state.get("parkdeclination", 45.0)

    update_device_state(
        "telescope",
        device_number,
        {
            "atpark": True,
            "slewing": False,
            "tracking": False,
            "rightascension": park_ra,
            "declination": park_dec,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/pulseguide", response_model=AlpacaResponse)
def pulseguide(
    device_number: int = Path(..., ge=0),
    Direction: int = Form(...),
    Duration: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    if Direction not in [
        GuideDirections.NORTH,
        GuideDirections.SOUTH,
        GuideDirections.EAST,
        GuideDirections.WEST,
    ]:
        raise AlpacaError(0x402, "Invalid guide direction")

    if Duration < 0:
        raise AlpacaError(0x402, "Duration must be positive")

    RightAscension = state.get("rightascension", 0.0)
    Declination = state.get("declination", 0.0)

    # Simulate movement
    if Direction == GuideDirections.NORTH:
        Declination += (Duration / 1000.0) * state.get("guideratedeclination", 15.0)
    elif Direction == GuideDirections.SOUTH:
        Declination -= (Duration / 1000.0) * state.get("guideratedeclination", 15.0)
    elif Direction == GuideDirections.EAST:
        RightAscension += (Duration / 1000.0) * state.get("guideraterightascension", 15.0) / 15
    elif Direction == GuideDirections.WEST:
        RightAscension -= (Duration / 1000.0) * state.get("guideraterightascension", 15.0) / 15

    update_device_state(
        "telescope",
        device_number,
        {
            "rightascension": RightAscension,
            "declination": Declination,
            "ispulseguiding": True,
        },
    )

    # Reset IsPulseGuiding asynchronously after the guide duration expires
    threading.Thread(
        target=_complete_pulseguide,
        args=(device_number, Duration / 1000.0),
        daemon=True,
    ).start()

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/setpark", response_model=AlpacaResponse)
def setpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    # Set current position as park position
    current_ra = state.get("rightascension", 0.0)
    current_dec = state.get("declination", 0.0)

    update_device_state(
        "telescope",
        device_number,
        {"parkrightascension": current_ra, "parkdeclination": current_dec},
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/slewtoaltaz", response_model=AlpacaResponse)
def slewtoaltaz(
    device_number: int = Path(..., ge=0),
    Azimuth: float = Form(...),
    Altitude: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    if Altitude < 0.0 or Altitude > 90.0:
        raise AlpacaError(0x401, "Altitude must be between 0 and 90 degrees")

    if Azimuth < 0.0 or Azimuth > 360.0:
        raise AlpacaError(0x401, "Azimuth must be between 0 and 360 degrees")

    now = datetime.now(timezone.utc).timestamp()
    ra, dec = _altaz_to_radec(
        Altitude,
        Azimuth,
        state.get("sitelatitude", 0.0),
        state.get("sitelongitude", 0.0),
        now,
    )
    update_device_state(
        "telescope",
        device_number,
        {
            "azimuth": Azimuth,
            "altitude": Altitude,
            "rightascension": ra,
            "declination": dec,
            "last_motion_update": now,
            "slewing": False,
            "atpark": False,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/slewtoaltazasync", response_model=AlpacaResponse)
def slewtoaltazasync(
    device_number: int = Path(..., ge=0),
    Azimuth: float = Form(...),
    Altitude: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    if Altitude < 0.0 or Altitude > 90.0:
        raise AlpacaError(0x401, "Altitude must be between 0 and 90 degrees")

    if Azimuth < 0.0 or Azimuth > 360.0:
        raise AlpacaError(0x401, "Azimuth must be between 0 and 360 degrees")

    # Start async slew – background loop interpolates toward the AltAz target.
    update_device_state(
        "telescope",
        device_number,
        {
            "slew_target_alt": Altitude,
            "slew_target_az": Azimuth,
            "slew_target_ra": None,
            "slew_target_dec": None,
            "slewing": True,
            "atpark": False,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/slewtocoordinates", response_model=AlpacaResponse)
def slewtocoordinates(
    device_number: int = Path(..., ge=0),
    RightAscension: float = Form(...),
    Declination: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    if RightAscension < 0.0 or RightAscension >= 24.0:
        raise AlpacaError(0x401, "Right ascension must be between 0 and 24 hours")

    if Declination < -90.0 or Declination > 90.0:
        raise AlpacaError(0x401, "Declination must be between -90 and +90 degrees")

    update_device_state(
        "telescope",
        device_number,
        {
            "rightascension": RightAscension,
            "declination": Declination,
            "targetrightascension": RightAscension,
            "targetdeclination": Declination,
            "slewing": False,  # Simplified - immediate slew
            "atpark": False,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/slewtocoordinatesasync", response_model=AlpacaResponse)
def slewtocoordinatesasync(
    device_number: int = Path(..., ge=0),
    RightAscension: float = Form(...),
    Declination: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    if RightAscension < 0.0 or RightAscension >= 24.0:
        raise AlpacaError(0x401, "Right ascension must be between 0 and 24 hours")

    if Declination < -90.0 or Declination > 90.0:
        raise AlpacaError(0x401, "Declination must be between -90 and +90 degrees")

    # Start async slew – background loop interpolates toward the RA/Dec target.
    update_device_state(
        "telescope",
        device_number,
        {
            "slew_target_ra": RightAscension,
            "slew_target_dec": Declination,
            "slew_target_alt": None,
            "slew_target_az": None,
            "targetrightascension": RightAscension,
            "targetdeclination": Declination,
            "slewing": True,
            "atpark": False,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/slewtotarget", response_model=AlpacaResponse)
def slewtotarget(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    target_ra = state.get("targetrightascension")
    target_dec = state.get("targetdeclination")

    if target_ra is None or target_dec is None:
        raise AlpacaError(0x402, "Target coordinates not set")

    update_device_state(
        "telescope",
        device_number,
        {
            "rightascension": target_ra,
            "declination": target_dec,
            "slewing": False,  # Simplified - immediate slew
            "atpark": False,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/slewtotargetasync", response_model=AlpacaResponse)
def slewtotargetasync(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    target_ra = state.get("targetrightascension")
    target_dec = state.get("targetdeclination")

    if target_ra is None or target_dec is None:
        raise AlpacaError(0x402, "Target coordinates not set")

    # Start async slew – background loop interpolates toward the RA/Dec target.
    update_device_state(
        "telescope",
        device_number,
        {
            "slew_target_ra": target_ra,
            "slew_target_dec": target_dec,
            "slew_target_alt": None,
            "slew_target_az": None,
            "slewing": True,
            "atpark": False,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/synctoaltaz", response_model=AlpacaResponse)
def synctoaltaz(
    device_number: int = Path(..., ge=0),
    Azimuth: float = Form(...),
    Altitude: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    if Altitude < 0.0 or Altitude > 90.0:
        raise AlpacaError(0x401, "Altitude must be between 0 and 90 degrees")

    if Azimuth < 0.0 or Azimuth > 360.0:
        raise AlpacaError(0x401, "Azimuth must be between 0 and 360 degrees")

    update_device_state("telescope", device_number, {"azimuth": Azimuth, "altitude": Altitude})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/synctocoordinates", response_model=AlpacaResponse)
def synctocoordinates(
    device_number: int = Path(..., ge=0),
    RightAscension: float = Form(...),
    Declination: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    if RightAscension < 0.0 or RightAscension >= 24.0:
        raise AlpacaError(0x401, "Right ascension must be between 0 and 24 hours")

    if Declination < -90.0 or Declination > 90.0:
        raise AlpacaError(0x401, "Declination must be between -90 and +90 degrees")

    update_device_state(
        "telescope",
        device_number,
        {
            "rightascension": RightAscension,
            "declination": Declination,
            "targetrightascension": RightAscension,
            "targetdeclination": Declination,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/synctotarget", response_model=AlpacaResponse)
def synctotarget(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    if state.get("atpark", False):
        raise AlpacaError(0x408, "Telescope is parked")

    target_ra = state.get("targetrightascension")
    target_dec = state.get("targetdeclination")

    if target_ra is None or target_dec is None:
        raise AlpacaError(0x402, "Target coordinates not set")

    update_device_state(
        "telescope",
        device_number,
        {"rightascension": target_ra, "declination": target_dec},
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/unpark", response_model=AlpacaResponse)
def unpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("telescope", device_number, {"atpark": False})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
