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
def get_issafe(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("safetymonitor", device_number)
    state = get_device_state("safetymonitor", device_number)
    return BoolResponse(
        Value=state.get("issafe", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/safetymonitor/{device_number}/issafe", response_model=AlpacaResponse)
def set_issafe(
    device_number: int = Path(..., ge=0),
    IsSafe: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("safetymonitor", device_number)
    state = get_device_state("safetymonitor", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("safetymonitor", device_number, {"issafe": IsSafe})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
