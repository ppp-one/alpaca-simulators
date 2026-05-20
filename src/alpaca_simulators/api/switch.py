from typing import Any

from fastapi import APIRouter, Form, Path, Query

from alpaca_simulators.api.common import AlpacaError, validate_device
from alpaca_simulators.state import (
    AlpacaResponse,
    BoolResponse,
    DoubleResponse,
    IntResponse,
    StringResponse,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()


def _switches(state: dict) -> dict:
    """Return the configured switches dict (tolerates legacy ``maxswitch``)."""
    return state.get("switches", {}) or {}


def _switch_config(state: dict, switch_id: int) -> dict[str, Any]:
    """Look up a switch's config by ID, tolerating int or str keys (PyYAML
    typically loads ``0:`` as an int but quoted ``"0":`` as a string).

    Raises InvalidValue (0x401) if the ID is unknown.
    """
    switches = _switches(state)
    if switch_id in switches:
        return switches[switch_id]
    if str(switch_id) in switches:
        return switches[str(switch_id)]
    raise AlpacaError(0x401, f"Invalid switch ID: {switch_id}")


def _store_switch_value(device_number: int, state: dict, switch_id: int, value):
    """Write back a switch value, preserving the existing key type."""
    switches = _switches(state)
    key = switch_id if switch_id in switches else str(switch_id)
    switches[key]["value"] = value
    update_device_state("switch", device_number, {"switches": switches})


@router.get("/switch/{device_number}/maxswitch", response_model=IntResponse)
def get_maxswitch(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("switch", device_number)
    state = get_device_state("switch", device_number)
    # MaxSwitch is the count of configured switches; deriving it here keeps it
    # consistent with which IDs the other endpoints will accept.
    return IntResponse(
        Value=len(_switches(state)),
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
    state = get_device_state("switch", device_number)
    switch_config = _switch_config(state, Id)
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
    state = get_device_state("switch", device_number)
    switch_config = _switch_config(state, Id)
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
    switch_config = _switch_config(state, Id)
    value = switch_config.get("value", False)
    bool_value = bool(value) if isinstance(value, int | float) else value
    return BoolResponse(
        Value=bool_value,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/switch/{device_number}/getswitchdescription", response_model=StringResponse)
def get_getswitchdescription(
    device_number: int = Path(..., ge=0),
    Id: int = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("switch", device_number)
    state = get_device_state("switch", device_number)
    switch_config = _switch_config(state, Id)
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
    state = get_device_state("switch", device_number)
    switch_config = _switch_config(state, Id)
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
    switch_config = _switch_config(state, Id)
    return DoubleResponse(
        Value=float(switch_config.get("value", 0.0)),
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
    state = get_device_state("switch", device_number)
    switch_config = _switch_config(state, Id)
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
    state = get_device_state("switch", device_number)
    switch_config = _switch_config(state, Id)
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
    state = get_device_state("switch", device_number)
    switch_config = _switch_config(state, Id)
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
    state = get_device_state("switch", device_number)
    # Validate the ID even though the result is fixed, so callers get a proper
    # InvalidValue for unknown switches.
    _switch_config(state, Id)
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
    switch_config = _switch_config(state, Id)

    if not switch_config.get("canwrite", True):
        raise AlpacaError(0x400, f"Switch {Id} is read-only")

    _store_switch_value(device_number, state, Id, State)

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
    switch_config = _switch_config(state, Id)

    if not switch_config.get("canwrite", True):
        raise AlpacaError(0x400, f"Switch {Id} is read-only")

    min_val = switch_config.get("minimum", 0.0)
    max_val = switch_config.get("maximum", 1.0)
    if Value < min_val or Value > max_val:
        raise AlpacaError(0x401, f"Value {Value} out of range ({min_val}-{max_val})")

    _store_switch_value(device_number, state, Id, Value)

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
    _switch_config(state, Id)
    # For simulator we acknowledge but don't persist name changes.
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
    switch_config = _switch_config(state, Id)

    if not switch_config.get("canasync", False):
        raise AlpacaError(0x400, f"Switch {Id} does not support async operation")

    _store_switch_value(device_number, state, Id, State)

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
    switch_config = _switch_config(state, Id)

    if not switch_config.get("canasync", False):
        raise AlpacaError(0x400, f"Switch {Id} does not support async operation")

    min_val = switch_config.get("minimum", 0.0)
    max_val = switch_config.get("maximum", 1.0)
    if Value < min_val or Value > max_val:
        raise AlpacaError(0x401, f"Value {Value} out of range ({min_val}-{max_val})")

    _store_switch_value(device_number, state, Id, Value)

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
