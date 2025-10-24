import math
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
    IntResponse,
    PierSide,
    StringArrayResponse,
    StringResponse,
    TelescopeAxes,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()


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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("telescope", device_number, {"declinationrate": DeclinationRate})

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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("telescope", device_number, {"rightascensionrate": RightAscensionRate})

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
        raise AlpacaError(0x402, "Latitude must be between -90 and +90 degrees")

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
        raise AlpacaError(0x402, "Longitude must be between -180 and +180 degrees")

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


@router.get("/telescope/{device_number}/slewsettletime", response_model=DoubleResponse)
def get_slewsettletime(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    return DoubleResponse(
        Value=state.get("slewsettletime", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/slewsettletime", response_model=AlpacaResponse)
def set_slewsettletime(
    device_number: int = Path(..., ge=0),
    SlewSettleTime: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("telescope", device_number)
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if SlewSettleTime < 0.0:
        raise AlpacaError(0x402, "Slew settle time cannot be negative")

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
    return DoubleResponse(
        Value=state.get("targetdeclination", 0.0),
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
        raise AlpacaError(0x402, "Declination must be between -90 and +90 degrees")

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
    return DoubleResponse(
        Value=state.get("targetrightascension", 0.0),
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
        raise AlpacaError(0x402, "Right ascension must be between 0 and 24 hours")

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
        raise AlpacaError(0x402, "Invalid tracking rate")

    update_device_state("telescope", device_number, {"trackingrate": TrackingRate})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/trackingrates", response_model=StringArrayResponse)
def get_trackingrates(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)
    rates = state.get("trackingrates", ["0", "1", "2", "3"])  # Sidereal, Lunar, Solar, King
    return StringArrayResponse(
        Value=rates,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/utcdate", response_model=StringResponse)
def get_utcdate(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("telescope", device_number)
    utc_now = datetime.now(timezone.utc)
    return StringResponse(
        Value=utc_now.isoformat(),
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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("telescope", device_number, {"slewing": False})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/telescope/{device_number}/axisrates", response_model=StringArrayResponse)
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
        raise AlpacaError(0x402, "Invalid axis")

    # Return available rates for the axis
    rates = state.get(f"axis{Axis}rates", ["0.0", "1.0", "2.0"])
    return StringArrayResponse(
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
        raise AlpacaError(0x402, "Invalid axis")

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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if Axis not in [
        TelescopeAxes.PRIMARY,
        TelescopeAxes.SECONDARY,
        TelescopeAxes.TERTIARY,
    ]:
        raise AlpacaError(0x402, "Invalid axis")

    # Store the axis movement rate
    update_device_state("telescope", device_number, {f"axis{Axis}rate": Rate})

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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if Direction not in [
        GuideDirections.NORTH,
        GuideDirections.SOUTH,
        GuideDirections.EAST,
        GuideDirections.WEST,
    ]:
        raise AlpacaError(0x402, "Invalid guide direction")

    if Duration < 0:
        raise AlpacaError(0x402, "Duration must be positive")

    state = get_device_state("telescope", device_number)
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
        },
    )

    # Simulate pulse guiding
    update_device_state("telescope", device_number, {"ispulseguiding": True})

    # In a real implementation, this would start a timer
    # For simulation, we immediately stop pulse guiding
    update_device_state("telescope", device_number, {"ispulseguiding": False})

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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if Altitude < 0.0 or Altitude > 90.0:
        raise AlpacaError(0x402, "Altitude must be between 0 and 90 degrees")

    if Azimuth < 0.0 or Azimuth >= 360.0:
        raise AlpacaError(0x402, "Azimuth must be between 0 and 360 degrees")

    update_device_state(
        "telescope",
        device_number,
        {
            "azimuth": Azimuth,
            "altitude": Altitude,
            "slewing": False,  # Simplified - immediate slew
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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if Altitude < 0.0 or Altitude > 90.0:
        raise AlpacaError(0x402, "Altitude must be between 0 and 90 degrees")

    if Azimuth < 0.0 or Azimuth >= 360.0:
        raise AlpacaError(0x402, "Azimuth must be between 0 and 360 degrees")

    # Start async slew
    update_device_state("telescope", device_number, {"slewing": True, "atpark": False})

    # In a real implementation, this would start a background task
    # For simulation, we set the final position immediately but keep slewing=True briefly

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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if RightAscension < 0.0 or RightAscension >= 24.0:
        raise AlpacaError(0x402, "Right ascension must be between 0 and 24 hours")

    if Declination < -90.0 or Declination > 90.0:
        raise AlpacaError(0x402, "Declination must be between -90 and +90 degrees")

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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if RightAscension < 0.0 or RightAscension >= 24.0:
        raise AlpacaError(0x402, "Right ascension must be between 0 and 24 hours")

    if Declination < -90.0 or Declination > 90.0:
        raise AlpacaError(0x402, "Declination must be between -90 and +90 degrees")

    # Start async slew
    update_device_state(
        "telescope",
        device_number,
        {
            "rightascension": RightAscension,
            "declination": Declination,
            "slewing": True,
            "atpark": False,
            "last_slew_time": datetime.now(timezone.utc),
        },
    )

    sleep(3)

    update_device_state(
        "telescope",
        device_number,
        {
            "rightascension": RightAscension,
            "declination": Declination,
            "slewing": False,
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

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

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

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    target_ra = state.get("targetrightascension")
    target_dec = state.get("targetdeclination")

    if target_ra is None or target_dec is None:
        raise AlpacaError(0x402, "Target coordinates not set")

    # Start async slew
    update_device_state("telescope", device_number, {"slewing": True, "atpark": False})

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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if Altitude < 0.0 or Altitude > 90.0:
        raise AlpacaError(0x402, "Altitude must be between 0 and 90 degrees")

    if Azimuth < 0.0 or Azimuth >= 360.0:
        raise AlpacaError(0x402, "Azimuth must be between 0 and 360 degrees")

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
    # state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if RightAscension < 0.0 or RightAscension >= 24.0:
        raise AlpacaError(0x402, "Right ascension must be between 0 and 24 hours")

    if Declination < -90.0 or Declination > 90.0:
        raise AlpacaError(0x402, "Declination must be between -90 and +90 degrees")

    update_device_state(
        "telescope",
        device_number,
        {"rightascension": RightAscension, "declination": Declination},
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/telescope/{device_number}/synctotarget", response_model=AlpacaResponse)
def synctotarget(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("telescope", device_number)
    state = get_device_state("telescope", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

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
