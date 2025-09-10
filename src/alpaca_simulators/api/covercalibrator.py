from fastapi import APIRouter, Form, Path, Query

from alpaca_simulators.api.common import AlpacaError, validate_device
from alpaca_simulators.state import (
    AlpacaResponse,
    BoolResponse,
    CalibratorStatus,
    CoverStatus,
    IntResponse,
    get_device_config,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()


@router.get("/covercalibrator/{device_number}/brightness", response_model=IntResponse)
def get_brightness(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("covercalibrator", device_number)
    state = get_device_state("covercalibrator", device_number)
    return IntResponse(
        Value=state.get("brightness", 0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/covercalibrator/{device_number}/calibratorchanging", response_model=BoolResponse)
def get_calibratorchanging(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("covercalibrator", device_number)
    state = get_device_state("covercalibrator", device_number)
    return BoolResponse(
        Value=state.get("calibratorchanging", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/covercalibrator/{device_number}/calibratorstate", response_model=IntResponse)
def get_calibratorstate(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("covercalibrator", device_number)
    state = get_device_state("covercalibrator", device_number)
    return IntResponse(
        Value=state.get("calibratorstate", CalibratorStatus.NOT_PRESENT),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/covercalibrator/{device_number}/covermoving", response_model=BoolResponse)
def get_covermoving(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("covercalibrator", device_number)
    state = get_device_state("covercalibrator", device_number)
    return BoolResponse(
        Value=state.get("covermoving", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/covercalibrator/{device_number}/coverstate", response_model=IntResponse)
def get_coverstate(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("covercalibrator", device_number)
    state = get_device_state("covercalibrator", device_number)
    return IntResponse(
        Value=state.get("coverstate", CoverStatus.CLOSED),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/covercalibrator/{device_number}/maxbrightness", response_model=IntResponse)
def get_maxbrightness(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("covercalibrator", device_number)
    config = get_device_config("covercalibrator", device_number)
    return IntResponse(
        Value=config.get("maxbrightness", 255),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/covercalibrator/{device_number}/calibratoroff", response_model=AlpacaResponse)
def calibratoroff(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("covercalibrator", device_number)
    # state = get_device_state("covercalibrator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state(
        "covercalibrator",
        device_number,
        {
            "brightness": 0,
            "calibratorstate": CalibratorStatus.OFF,
            "calibratorchanging": False,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/covercalibrator/{device_number}/calibratoron", response_model=AlpacaResponse)
def calibratoron(
    device_number: int = Path(..., ge=0),
    Brightness: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("covercalibrator", device_number)
    # state = get_device_state("covercalibrator", device_number)
    config = get_device_config("covercalibrator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    max_brightness = config.get("maxbrightness", 255)
    if Brightness < 0 or Brightness > max_brightness:
        raise AlpacaError(0x402, f"Brightness out of range (0-{max_brightness})")

    update_device_state(
        "covercalibrator",
        device_number,
        {
            "brightness": Brightness,
            "calibratorstate": CalibratorStatus.READY,
            "calibratorchanging": False,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/covercalibrator/{device_number}/closecover", response_model=AlpacaResponse)
def closecover(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("covercalibrator", device_number)
    # state = get_device_state("covercalibrator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state(
        "covercalibrator",
        device_number,
        {"coverstate": CoverStatus.CLOSED, "covermoving": False},
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/covercalibrator/{device_number}/haltcover", response_model=AlpacaResponse)
def haltcover(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("covercalibrator", device_number)
    # state = get_device_state("covercalibrator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("covercalibrator", device_number, {"covermoving": False})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/covercalibrator/{device_number}/opencover", response_model=AlpacaResponse)
def opencover(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("covercalibrator", device_number)
    # state = get_device_state("covercalibrator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state(
        "covercalibrator",
        device_number,
        {"coverstate": CoverStatus.OPEN, "covermoving": False},
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
