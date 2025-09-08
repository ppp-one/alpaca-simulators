import logging

from fastapi import APIRouter, Form, Path, Query

from observatory_simulator.api.common import validate_device
from observatory_simulator.state import (
    AlpacaResponse,
    BoolResponse,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()


@router.get("/safetymonitor/{device_number}/issafe", response_model=BoolResponse)
def get_issafe(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("safetymonitor", device_number)
    state = get_device_state("safetymonitor", device_number)
    issafe_value = state.get("issafe", True)
    server_transaction_id = get_server_transaction_id()
    logging.debug(
        f"GET /safetymonitor/{device_number}/issafe: device_number={device_number}, "
        f"ClientTransactionID={ClientTransactionID}, "
        f"ServerTransactionID={server_transaction_id}, Value={issafe_value}"
    )
    return BoolResponse(
        Value=issafe_value,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=server_transaction_id,
    )


@router.put("/safetymonitor/{device_number}/issafe", response_model=AlpacaResponse)
def set_issafe(
    device_number: int = Path(..., ge=0),
    IsSafe: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("safetymonitor", device_number)
    # state = get_device_state("safetymonitor", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("safetymonitor", device_number, {"issafe": IsSafe})
    server_transaction_id = get_server_transaction_id()
    logging.debug(
        f"PUT /safetymonitor/{device_number}/issafe: device_number={device_number}, "
        f"IsSafe={IsSafe}, ClientTransactionID={ClientTransactionID}, "
        f"ServerTransactionID={server_transaction_id}"
    )
    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=server_transaction_id,
    )
