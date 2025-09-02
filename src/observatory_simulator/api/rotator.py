from fastapi import APIRouter, Form, Path, Query

from observatory_simulator.api.common import AlpacaError, validate_device
from observatory_simulator.state import (
    AlpacaResponse,
    BoolResponse,
    DoubleResponse,
    get_device_config,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()


@router.get("/rotator/{device_number}/canreverse", response_model=BoolResponse)
def get_canreverse(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("rotator", device_number)
    config = get_device_config("rotator", device_number)
    return BoolResponse(
        Value=config.get("canreverse", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/rotator/{device_number}/ismoving", response_model=BoolResponse)
def get_ismoving(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("rotator", device_number)
    state = get_device_state("rotator", device_number)
    return BoolResponse(
        Value=state.get("ismoving", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/rotator/{device_number}/mechanicalposition", response_model=DoubleResponse)
def get_mechanicalposition(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("rotator", device_number)
    state = get_device_state("rotator", device_number)
    return DoubleResponse(
        Value=state.get("mechanicalposition", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/rotator/{device_number}/position", response_model=DoubleResponse)
def get_position(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("rotator", device_number)
    state = get_device_state("rotator", device_number)
    return DoubleResponse(
        Value=state.get("position", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/rotator/{device_number}/reverse", response_model=BoolResponse)
def get_reverse(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("rotator", device_number)
    state = get_device_state("rotator", device_number)
    return BoolResponse(
        Value=state.get("reverse", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/rotator/{device_number}/reverse", response_model=AlpacaResponse)
def set_reverse(
    device_number: int = Path(..., ge=0),
    Reverse: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("rotator", device_number)
    # state = get_device_state("rotator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    config = get_device_config("rotator", device_number)
    if not config.get("canreverse", True):
        raise AlpacaError(0x401, "Rotator cannot reverse")

    update_device_state("rotator", device_number, {"reverse": Reverse})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/rotator/{device_number}/stepsize", response_model=DoubleResponse)
def get_stepsize(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("rotator", device_number)
    config = get_device_config("rotator", device_number)
    return DoubleResponse(
        Value=config.get("stepsize", 0.1),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/rotator/{device_number}/targetposition", response_model=DoubleResponse)
def get_targetposition(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("rotator", device_number)
    state = get_device_state("rotator", device_number)
    return DoubleResponse(
        Value=state.get("targetposition", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/rotator/{device_number}/halt", response_model=AlpacaResponse)
def halt(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("rotator", device_number)
    # state = get_device_state("rotator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("rotator", device_number, {"ismoving": False})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/rotator/{device_number}/move", response_model=AlpacaResponse)
def move(
    device_number: int = Path(..., ge=0),
    Position: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("rotator", device_number)
    state = get_device_state("rotator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    current_position = state.get("position", 0.0)
    new_position = current_position + Position

    # Normalize to 0-360 degrees
    new_position = new_position % 360.0

    update_device_state(
        "rotator",
        device_number,
        {
            "position": new_position,
            "mechanicalposition": new_position,
            "targetposition": new_position,
            "ismoving": False,  # Instantaneous for simulator
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/rotator/{device_number}/moveabsolute", response_model=AlpacaResponse)
def moveabsolute(
    device_number: int = Path(..., ge=0),
    Position: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("rotator", device_number)
    # state = get_device_state("rotator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    # Normalize to 0-360 degrees
    position = Position % 360.0

    update_device_state(
        "rotator",
        device_number,
        {
            "position": position,
            "mechanicalposition": position,
            "targetposition": position,
            "ismoving": False,  # Instantaneous for simulator
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/rotator/{device_number}/movemechanical", response_model=AlpacaResponse)
def movemechanical(
    device_number: int = Path(..., ge=0),
    Position: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("rotator", device_number)
    # state = get_device_state("rotator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    # Normalize to 0-360 degrees
    position = Position % 360.0

    update_device_state(
        "rotator",
        device_number,
        {
            "mechanicalposition": position,
            "position": position,  # Assume no offset for simulator
            "targetposition": position,
            "ismoving": False,  # Instantaneous for simulator
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/rotator/{device_number}/sync", response_model=AlpacaResponse)
def sync(
    device_number: int = Path(..., ge=0),
    Position: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("rotator", device_number)
    # state = get_device_state("rotator", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    # Normalize to 0-360 degrees
    position = Position % 360.0

    # Sync just updates the position without moving
    update_device_state(
        "rotator", device_number, {"position": position, "targetposition": position}
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
