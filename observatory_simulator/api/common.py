from fastapi import APIRouter, Path, Query, Request, HTTPException, Body, Form
from observatory_simulator.state import (
    get_device_config,
    get_device_state,
    update_device_state,
    validate_device_exists,
    BoolResponse,
    StringResponse,
    IntResponse,
    DoubleResponse,
    StringArrayResponse,
    get_server_transaction_id,
    AlpacaResponse,
    DeviceStateResponse,
)
from typing import Any, Dict, Optional
import json

router = APIRouter()


# ASCOM Error Codes
class AlpacaError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# Common validation
def validate_device(device_type: str, device_number: int):
    if not validate_device_exists(device_type, device_number):
        raise AlpacaError(0x400, f"Device {device_type}:{device_number} not found")


async def get_form_data(request: Request) -> Dict[str, Any]:
    """Extract form data or JSON data from request"""
    content_type = request.headers.get("content-type", "")

    try:
        if "application/x-www-form-urlencoded" in content_type:
            # Handle form data
            form_data = await request.form()
            return dict(form_data)
        elif "application/json" in content_type:
            # Handle JSON data
            body = await request.body()
            if body:
                return json.loads(body)
        else:
            # For other content types or no content type, try form first
            try:
                form_data = await request.form()
                return dict(form_data)
            except:
                # If form parsing fails, try JSON
                try:
                    body = await request.body()
                    if body:
                        return json.loads(body)
                except:
                    pass
    except Exception as e:
        # If all parsing fails, return empty dict
        pass

    return {}


# Common endpoints that exist for all device types
@router.get("/{device_type}/{device_number}/connected", response_model=BoolResponse)
def get_connected(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Query(0),
):
    validate_device(device_type, device_number)
    state = get_device_state(device_type, device_number)
    return BoolResponse(
        Value=state.get("connected", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# @router.put("/{device_type}/{device_number}/connected", response_model=AlpacaResponse)
# def set_connected(
#     device_type: str = Path(...),
#     device_number: int = Path(..., ge=0),
#     Connected: bool = Form(...),
#     ClientTransactionID: int = Form(0),
# ):
#     validate_device(device_type, device_number)

#     update_device_state(device_type, device_number, {"connected": Connected})
#     return AlpacaResponse(
#         ClientTransactionID=ClientTransactionID,
#         ServerTransactionID=get_server_transaction_id(),
#     )


@router.put("/{device_type}/{device_number}/connected", response_model=AlpacaResponse)
async def set_connected(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    Connected: str = Form(...),
    ClientTransactionID: int = Form(0),
    ClientID: int = Form(None),
):
    print(f"Setting connected state for {device_type}:{device_number} to {Connected}")
    validate_device(device_type, device_number)
    print(f"Connected state for {device_type}:{device_number} is {Connected}")
    connected_bool = Connected.lower() in ("true", "1", "yes", "on")
    print(f"Connected boolean for {device_type}:{device_number} is {connected_bool}")
    update_device_state(device_type, device_number, {"connected": connected_bool})
    print(
        f"Updated connected state for {device_type}:{device_number} to {connected_bool}"
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/{device_type}/{device_number}/description", response_model=StringResponse)
def get_description(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Query(0),
):
    validate_device(device_type, device_number)
    cfg = get_device_config(device_type, device_number)
    return StringResponse(
        Value=cfg.get("description", f"Simulated {device_type.title()} Device"),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/{device_type}/{device_number}/driverinfo", response_model=StringResponse)
def get_driverinfo(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Query(0),
):
    validate_device(device_type, device_number)
    cfg = get_device_config(device_type, device_number)
    return StringResponse(
        Value=cfg.get("driverinfo", "ASCOM Alpaca Observatory Simulator Driver v1.0"),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/{device_type}/{device_number}/driverversion", response_model=StringResponse
)
def get_driverversion(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Query(0),
):
    validate_device(device_type, device_number)
    cfg = get_device_config(device_type, device_number)
    return StringResponse(
        Value=cfg.get("driverversion", "1.0.0"),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/{device_type}/{device_number}/interfaceversion", response_model=IntResponse
)
def get_interfaceversion(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Query(0),
):
    validate_device(device_type, device_number)
    cfg = get_device_config(device_type, device_number)
    return IntResponse(
        Value=cfg.get("interfaceversion", 3),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/{device_type}/{device_number}/name", response_model=StringResponse)
def get_name(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Query(0),
):
    validate_device(device_type, device_number)
    cfg = get_device_config(device_type, device_number)
    return StringResponse(
        Value=cfg.get("name", f"Simulator {device_type.title()} #{device_number}"),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/{device_type}/{device_number}/supportedactions",
    response_model=StringArrayResponse,
)
def get_supportedactions(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Query(0),
):
    validate_device(device_type, device_number)
    # Return empty list for simulator - no custom actions supported
    return StringArrayResponse(
        Value=[],
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/{device_type}/{device_number}/action", response_model=StringResponse)
def action(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    Action: str = Form(""),
    Parameters: str = Form(""),
    ClientTransactionID: int = Form(0),
):
    validate_device(device_type, device_number)

    # For simulator, return empty string for any action
    # In a real driver, this would execute the custom action
    return StringResponse(
        Value="",
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/{device_type}/{device_number}/commandblind", response_model=AlpacaResponse
)
def commandblind(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    Command: str = Form(""),
    Raw: bool = Form(False),
    ClientTransactionID: int = Form(0),
):
    validate_device(device_type, device_number)

    # For simulator, just acknowledge the command
    # In a real driver, this would execute the command without returning a result
    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/{device_type}/{device_number}/commandbool", response_model=BoolResponse)
def commandbool(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    Command: str = Form(""),
    Raw: bool = Form(False),
    ClientTransactionID: int = Form(0),
):
    validate_device(device_type, device_number)

    # For simulator, return false for any command
    # In a real driver, this would execute the command and return a boolean result
    return BoolResponse(
        Value=False,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/{device_type}/{device_number}/commandstring", response_model=StringResponse
)
def commandstring(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    Command: str = Form(""),
    Raw: bool = Form(False),
    ClientTransactionID: int = Form(0),
):
    validate_device(device_type, device_number)

    # For simulator, return empty string for any command
    # In a real driver, this would execute the command and return a string result
    return StringResponse(
        Value="",
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Platform 7 methods
@router.put("/{device_type}/{device_number}/connect", response_model=AlpacaResponse)
def connect(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Form(0),
):
    validate_device(device_type, device_number)

    # Set connected to true
    update_device_state(device_type, device_number, {"connected": True})
    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/{device_type}/{device_number}/connecting", response_model=BoolResponse)
def get_connecting(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Query(0),
):
    validate_device(device_type, device_number)
    # For simulator, always return false (connection is instant)
    return BoolResponse(
        Value=False,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/{device_type}/{device_number}/disconnect", response_model=AlpacaResponse)
def disconnect(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Form(0),
):
    validate_device(device_type, device_number)

    # Set connected to false
    update_device_state(device_type, device_number, {"connected": False})
    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/{device_type}/{device_number}/devicestate", response_model=DeviceStateResponse
)
def get_devicestate(
    device_type: str = Path(...),
    device_number: int = Path(..., ge=0),
    ClientTransactionID: int = Query(0),
):
    validate_device(device_type, device_number)
    state = get_device_state(device_type, device_number)
    return DeviceStateResponse(
        Value=dict(state),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
