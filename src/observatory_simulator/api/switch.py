from fastapi import APIRouter, Form, Path, Query

from observatory_simulator.api.common import AlpacaError, validate_device
from observatory_simulator.state import (
    AlpacaResponse,
    BoolResponse,
    DoubleResponse,
    IntResponse,
    StringResponse,
    get_device_config,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()


@router.get("/switch/{device_number}/maxswitch", response_model=IntResponse)
def get_maxswitch(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("switch", device_number)
    config = get_device_config("switch", device_number)
    return IntResponse(
        Value=config.get("maxswitch", 0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/canasync", response_model=BoolResponse)
def get_canasync(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    config = get_device_config("switch", device_number)
    switches = config.get("switches", {})

    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    return BoolResponse(
        Value=switch_config.get("canasync", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/canwrite", response_model=BoolResponse)
def get_canwrite(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    config = get_device_config("switch", device_number)
    switches = config.get("switches", {})

    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    return BoolResponse(
        Value=switch_config.get("canwrite", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/getswitch", response_model=BoolResponse)
def get_getswitch(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    state = get_device_state("switch", device_number)
    config = get_device_config("switch", device_number)
    switches = config.get("switches", {})

    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    # Get current value from state or default from config
    switch_states = state.get("switches", {})
    if str(Id) in switch_states:
        value = switch_states[str(Id)].get("value", False)
    else:
        value = switches[str(Id)].get("value", False)

    # Convert to boolean
    bool_value = bool(value) if isinstance(value, (int, float)) else value

    return BoolResponse(
        Value=bool_value,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/switch/{device_number}/getswitchdescription", response_model=StringResponse
)
def get_getswitchdescription(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    config = get_device_config("switch", device_number)
    switches = config.get("switches", {})

    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    return StringResponse(
        Value=switch_config.get("description", ""),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/getswitchname", response_model=StringResponse)
def get_getswitchname(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    config = get_device_config("switch", device_number)
    switches = config.get("switches", {})

    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    return StringResponse(
        Value=switch_config.get("name", f"Switch {Id}"),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/getswitchvalue", response_model=DoubleResponse)
def get_getswitchvalue(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    state = get_device_state("switch", device_number)
    config = get_device_config("switch", device_number)
    switches = config.get("switches", {})

    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    # Get current value from state or default from config
    switch_states = state.get("switches", {})
    if str(Id) in switch_states:
        value = switch_states[str(Id)].get("value", 0.0)
    else:
        value = switches[str(Id)].get("value", 0.0)

    return DoubleResponse(
        Value=float(value),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/minswitchvalue", response_model=DoubleResponse)
def get_minswitchvalue(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    config = get_device_config("switch", device_number)
    switches = config.get("switches", {})

    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    return DoubleResponse(
        Value=switch_config.get("minimum", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/maxswitchvalue", response_model=DoubleResponse)
def get_maxswitchvalue(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    config = get_device_config("switch", device_number)
    switches = config.get("switches", {})

    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    return DoubleResponse(
        Value=switch_config.get("maximum", 1.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/switchstep", response_model=DoubleResponse)
def get_switchstep(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    config = get_device_config("switch", device_number)
    switches = config.get("switches", {})

    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    return DoubleResponse(
        Value=switch_config.get("step", 1.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/statechangecomplete", response_model=BoolResponse)
def get_statechangecomplete(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    # For simulator, state changes are always complete
    return BoolResponse(
        Value=True,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/switch/{device_number}/setswitch", response_model=AlpacaResponse)
def set_setswitch(
    device_number: int = Path(..., ge=0),
    Id: int = Form(...),
    State: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("switch", device_number)
    state = get_device_state("switch", device_number)
    config = get_device_config("switch", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    switches = config.get("switches", {})
    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    if not switch_config.get("canwrite", True):
        raise AlpacaError(0x401, f"Switch {Id} is read-only")

    # Update switch state
    switch_states = state.get("switches", {})
    if str(Id) not in switch_states:
        switch_states[str(Id)] = {}

    switch_states[str(Id)]["value"] = State
    update_device_state("switch", device_number, {"switches": switch_states})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/switch/{device_number}/setswitchvalue", response_model=AlpacaResponse)
def set_setswitchvalue(
    device_number: int = Path(..., ge=0),
    Id: int = Form(...),
    Value: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("switch", device_number)
    state = get_device_state("switch", device_number)
    config = get_device_config("switch", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    switches = config.get("switches", {})
    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    if not switch_config.get("canwrite", True):
        raise AlpacaError(0x401, f"Switch {Id} is read-only")

    # Validate range
    min_val = switch_config.get("minimum", 0.0)
    max_val = switch_config.get("maximum", 1.0)
    if Value < min_val or Value > max_val:
        raise AlpacaError(0x402, f"Value {Value} out of range ({min_val}-{max_val})")

    # Update switch state
    switch_states = state.get("switches", {})
    if str(Id) not in switch_states:
        switch_states[str(Id)] = {}

    switch_states[str(Id)]["value"] = Value
    update_device_state("switch", device_number, {"switches": switch_states})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/switch/{device_number}/setswitchname", response_model=AlpacaResponse)
def set_setswitchname(
    device_number: int = Path(..., ge=0),
    Id: int = Form(...),
    Name: str = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("switch", device_number)
    state = get_device_state("switch", device_number)
    config = get_device_config("switch", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    switches = config.get("switches", {})
    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    # For simulator, we'll just acknowledge the name change
    # In a real implementation, this might update persistent configuration

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/switch/{device_number}/setasync", response_model=AlpacaResponse)
def set_setasync(
    device_number: int = Path(..., ge=0),
    Id: int = Form(...),
    State: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("switch", device_number)
    state = get_device_state("switch", device_number)
    config = get_device_config("switch", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    switches = config.get("switches", {})
    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    if not switch_config.get("canasync", False):
        raise AlpacaError(0x401, f"Switch {Id} does not support async operation")

    # For simulator, treat same as synchronous
    switch_states = state.get("switches", {})
    if str(Id) not in switch_states:
        switch_states[str(Id)] = {}

    switch_states[str(Id)]["value"] = State
    update_device_state("switch", device_number, {"switches": switch_states})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/switch/{device_number}/setasyncvalue", response_model=AlpacaResponse)
def set_setasyncvalue(
    device_number: int = Path(..., ge=0),
    Id: int = Form(...),
    Value: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("switch", device_number)
    state = get_device_state("switch", device_number)
    config = get_device_config("switch", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    switches = config.get("switches", {})
    if str(Id) not in switches:
        raise AlpacaError(0x402, f"Invalid switch ID: {Id}")

    switch_config = switches[str(Id)]
    if not switch_config.get("canasync", False):
        raise AlpacaError(0x401, f"Switch {Id} does not support async operation")

    # Validate range
    min_val = switch_config.get("minimum", 0.0)
    max_val = switch_config.get("maximum", 1.0)
    if Value < min_val or Value > max_val:
        raise AlpacaError(0x402, f"Value {Value} out of range ({min_val}-{max_val})")

    # For simulator, treat same as synchronous
    switch_states = state.get("switches", {})
    if str(Id) not in switch_states:
        switch_states[str(Id)] = {}

    switch_states[str(Id)]["value"] = Value
    update_device_state("switch", device_number, {"switches": switch_states})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
