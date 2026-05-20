import asyncio

from fastapi import APIRouter, BackgroundTasks, Form, Path, Query

from alpaca_simulators.api.common import AlpacaError, validate_device
from alpaca_simulators.state import (
    AlpacaResponse,
    BoolResponse,
    DoubleResponse,
    IntResponse,
    ShutterState,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()

# How long a simulated dome slew/find-home/park takes. Kept above ConformU's
# 3-second "is it slewing?" check so AbortSlew tests can observe Slewing=True.
_SLEW_DURATION_SECONDS = 4.0


async def _slew_task(device_number: int, axis: str, target: float, gen: int):
    """Hold Slewing=True for the slew duration, then apply target unless an
    abort or newer slew superseded this one (tracked by ``slew_gen``)."""
    await asyncio.sleep(_SLEW_DURATION_SECONDS)
    state = get_device_state("dome", device_number)
    if state.get("slew_gen") != gen or not state.get("slewing", False):
        # Aborted, or a newer slew took over — leave state alone.
        return
    update = {axis: target, "slewing": False, "atpark": False, "athome": False}
    update_device_state("dome", device_number, update)


def _begin_slew(device_number: int, axis: str, target: float, background_tasks: BackgroundTasks):
    """Mark the dome as slewing, bump the generation, and schedule completion."""
    state = get_device_state("dome", device_number)
    new_gen = state.get("slew_gen", 0) + 1
    update_device_state(
        "dome",
        device_number,
        {"slewing": True, "slew_gen": new_gen, "athome": False, "atpark": False},
    )
    background_tasks.add_task(_slew_task, device_number, axis, target, new_gen)


@router.get("/dome/{device_number}/altitude", response_model=DoubleResponse)
def get_altitude(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")
    return DoubleResponse(
        Value=state.get("altitude", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/athome", response_model=BoolResponse)
def get_athome(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("athome", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/atpark", response_model=BoolResponse)
def get_atpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("atpark", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/azimuth", response_model=DoubleResponse)
def get_azimuth(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")
    return DoubleResponse(
        Value=state.get("azimuth", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/canfindhome", response_model=BoolResponse)
def get_canfindhome(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("canfindhome", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/canpark", response_model=BoolResponse)
def get_canpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("canpark", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/cansetaltitude", response_model=BoolResponse)
def get_cansetaltitude(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("cansetaltitude", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/cansetazimuth", response_model=BoolResponse)
def get_cansetazimuth(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("cansetazimuth", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/cansetpark", response_model=BoolResponse)
def get_cansetpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("cansetpark", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/cansetshutter", response_model=BoolResponse)
def get_cansetshutter(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("cansetshutter", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/canslave", response_model=BoolResponse)
def get_canslave(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("canslave", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/cansyncazimuth", response_model=BoolResponse)
def get_cansyncazimuth(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("cansyncazimuth", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/shutterstatus", response_model=IntResponse)
def get_shutterstatus(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return IntResponse(
        Value=state.get("shutterstatus", ShutterState.CLOSED),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/slaved", response_model=BoolResponse)
def get_slaved(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("slaved", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/dome/{device_number}/slaved", response_model=AlpacaResponse)
def set_slaved(
    device_number: int = Path(..., ge=0),
    Slaved: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("dome", device_number)
    # state = get_device_state("dome", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("dome", device_number, {"slaved": Slaved})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/dome/{device_number}/slewing", response_model=BoolResponse)
def get_slewing(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)
    return BoolResponse(
        Value=state.get("slewing", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Action methods


@router.put("/dome/{device_number}/abortslew", response_model=AlpacaResponse)
def abortslew(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("dome", device_number)

    # Bump slew_gen so any in-flight slew task no-ops when it wakes up.
    state = get_device_state("dome", device_number)
    update_device_state(
        "dome",
        device_number,
        {"slewing": False, "slew_gen": state.get("slew_gen", 0) + 1},
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/dome/{device_number}/closeshutter", response_model=AlpacaResponse)
def closeshutter(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("dome", device_number)
    # state = get_device_state("dome", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("dome", device_number, {"shutterstatus": ShutterState.CLOSED})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/dome/{device_number}/findhome", response_model=AlpacaResponse)
def findhome(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("dome", device_number)
    # state = get_device_state("dome", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("dome", device_number, {"athome": True, "slewing": False, "azimuth": 0.0})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/dome/{device_number}/openshutter", response_model=AlpacaResponse)
def openshutter(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("dome", device_number)
    # state = get_device_state("dome", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state("dome", device_number, {"shutterstatus": ShutterState.OPEN})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/dome/{device_number}/park", response_model=AlpacaResponse)
def park(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("dome", device_number)
    # state = get_device_state("dome", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("dome", device_number)
    park_azimuth = state.get("parkazimuth", 0.0)

    update_device_state(
        "dome",
        device_number,
        {"atpark": True, "slewing": False, "azimuth": park_azimuth},
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/dome/{device_number}/setpark", response_model=AlpacaResponse)
def setpark(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("dome", device_number)
    state = get_device_state("dome", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    # Set current azimuth as park position
    current_azimuth = state.get("azimuth", 0.0)
    update_device_state("dome", device_number, {"parkazimuth": current_azimuth})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/dome/{device_number}/slewtoaltitude", response_model=AlpacaResponse)
def slewtoaltitude(
    background_tasks: BackgroundTasks,
    device_number: int = Path(..., ge=0),
    Altitude: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("dome", device_number)

    if Altitude < 0.0 or Altitude > 90.0:
        raise AlpacaError(0x401, "Altitude must be between 0 and 90 degrees")

    _begin_slew(device_number, "altitude", Altitude, background_tasks)

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/dome/{device_number}/slewtoazimuth", response_model=AlpacaResponse)
def slewtoazimuth(
    background_tasks: BackgroundTasks,
    device_number: int = Path(..., ge=0),
    Azimuth: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("dome", device_number)

    if Azimuth < 0.0 or Azimuth >= 360.0:
        raise AlpacaError(0x401, "Azimuth must be between 0 and 360 degrees")

    _begin_slew(device_number, "azimuth", Azimuth, background_tasks)

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/dome/{device_number}/synctoazimuth", response_model=AlpacaResponse)
def synctoazimuth(
    device_number: int = Path(..., ge=0),
    Azimuth: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("dome", device_number)

    if Azimuth < 0.0 or Azimuth >= 360.0:
        raise AlpacaError(0x401, "Azimuth must be between 0 and 360 degrees")

    # Sync is instantaneous: snap azimuth to the requested value without slewing.
    update_device_state("dome", device_number, {"azimuth": Azimuth})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
