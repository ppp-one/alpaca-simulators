from fastapi import APIRouter, Path, Query, Form
from observatory_simulator.state import (
    get_device_state,
    update_device_state,
    get_device_config,
    get_server_transaction_id,
    BoolResponse,
    IntResponse,
    DoubleResponse,
    AlpacaResponse,
)
from observatory_simulator.api.common import validate_device, AlpacaError

router = APIRouter()


@router.get("/focuser/{device_number}/absolute", response_model=BoolResponse)
def get_absolute(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("focuser", device_number)
    config = get_device_config("focuser", device_number)
    return BoolResponse(
        Value=config.get("absolute", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/focuser/{device_number}/ismoving", response_model=BoolResponse)
def get_ismoving(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("focuser", device_number)
    state = get_device_state("focuser", device_number)
    return BoolResponse(
        Value=state.get("ismoving", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/focuser/{device_number}/maxincrement", response_model=IntResponse)
def get_maxincrement(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("focuser", device_number)
    config = get_device_config("focuser", device_number)
    return IntResponse(
        Value=config.get("maxincrement", 1000),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/focuser/{device_number}/maxstep", response_model=IntResponse)
def get_maxstep(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("focuser", device_number)
    config = get_device_config("focuser", device_number)
    return IntResponse(
        Value=config.get("maxstep", 100000),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/focuser/{device_number}/position", response_model=IntResponse)
def get_position(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("focuser", device_number)
    state = get_device_state("focuser", device_number)
    return IntResponse(
        Value=state.get("position", 50000),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/focuser/{device_number}/stepsize", response_model=DoubleResponse)
def get_stepsize(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("focuser", device_number)
    config = get_device_config("focuser", device_number)
    return DoubleResponse(
        Value=config.get("stepsize", 1.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/focuser/{device_number}/tempcomp", response_model=BoolResponse)
def get_tempcomp(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("focuser", device_number)
    state = get_device_state("focuser", device_number)
    return BoolResponse(
        Value=state.get("tempcomp", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/focuser/{device_number}/tempcomp", response_model=AlpacaResponse)
def set_tempcomp(
    device_number: int = Path(..., ge=0),
    TempComp: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("focuser", device_number)
    state = get_device_state("focuser", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    config = get_device_config("focuser", device_number)
    if not config.get("tempcompavailable", True):
        raise AlpacaError(0x401, "Temperature compensation not available")

    update_device_state("focuser", device_number, {"tempcomp": TempComp})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/focuser/{device_number}/tempcompavailable", response_model=BoolResponse)
def get_tempcompavailable(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("focuser", device_number)
    config = get_device_config("focuser", device_number)
    return BoolResponse(
        Value=config.get("tempcompavailable", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/focuser/{device_number}/temperature", response_model=DoubleResponse)
def get_temperature(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("focuser", device_number)
    state = get_device_state("focuser", device_number)
    return DoubleResponse(
        Value=state.get("temperature", 20.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/focuser/{device_number}/halt", response_model=AlpacaResponse)
def halt(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("focuser", device_number)
    state = get_device_state("focuser", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("focuser", device_number, {"ismoving": False})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/focuser/{device_number}/move", response_model=AlpacaResponse)
def move(
    device_number: int = Path(..., ge=0),
    Position: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("focuser", device_number)
    state = get_device_state("focuser", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    config = get_device_config("focuser", device_number)
    max_step = config.get("maxstep", 100000)

    if Position < 0 or Position > max_step:
        raise AlpacaError(0x402, f"Position out of range (0-{max_step})")

    # Simulate movement
    update_device_state(
        "focuser",
        device_number,
        {
            "position": Position,
            "ismoving": False,  # For simulator, movement is instantaneous
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
