from fastapi import APIRouter, Form, Path, Query

from alpaca_simulators.api.common import AlpacaError, validate_device
from alpaca_simulators.state import (
    AlpacaResponse,
    IntArrayResponse,
    IntResponse,
    StringArrayResponse,
    get_device_config,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()


@router.get("/filterwheel/{device_number}/focusoffsets", response_model=IntArrayResponse)
def get_focusoffsets(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("filterwheel", device_number)
    config = get_device_config("filterwheel", device_number)
    return IntArrayResponse(
        Value=config.get("focusoffsets", []),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/filterwheel/{device_number}/names", response_model=StringArrayResponse)
def get_names(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("filterwheel", device_number)
    config = get_device_config("filterwheel", device_number)
    return StringArrayResponse(
        Value=config.get("names", []),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/filterwheel/{device_number}/position", response_model=IntResponse)
def get_position(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("filterwheel", device_number)
    state = get_device_state("filterwheel", device_number)
    return IntResponse(
        Value=state.get("position", 0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/filterwheel/{device_number}/position", response_model=AlpacaResponse)
def set_position(
    device_number: int = Path(..., ge=0),
    Position: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("filterwheel", device_number)
    # state = get_device_state("filterwheel", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    config = get_device_config("filterwheel", device_number)
    max_position = len(config.get("names", [])) - 1

    if Position < 0 or Position > max_position:
        raise AlpacaError(0x402, f"Position out of range (0-{max_position})")

    update_device_state("filterwheel", device_number, {"position": Position})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
