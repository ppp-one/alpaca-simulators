import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from observatory_simulator.api import (
    camera,
    common,
    covercalibrator,
    dome,
    filterwheel,
    focuser,
    observingconditions,
    rotator,
    safetymonitor,
    switch,
    telescope,
)
from observatory_simulator.api.common import AlpacaError
from observatory_simulator.endpoint_discovery import (
    discover_device_endpoints,
    get_action_endpoints,
)
from observatory_simulator.state import get_server_transaction_id, reload_config

app = FastAPI(
    title="Alpaca Observatory Simulator",
    description="A simulator for Alpaca devices based on the AlpacaDeviceAPI_v1.yaml specification.",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


@app.exception_handler(AlpacaError)
async def alpaca_exception_handler(request: Request, exc: AlpacaError):
    client_transaction_id = 0

    # Try to get ClientTransactionID from query params
    if "ClientTransactionID" in request.query_params:
        try:
            client_transaction_id = int(request.query_params["ClientTransactionID"])
        except (ValueError, TypeError):
            pass

    # Note: We don't try to read the request body here as it may have been
    # consumed by FastAPI's form parsing. The ClientTransactionID should be
    # handled by the endpoint itself if it's in the body.

    return JSONResponse(
        status_code=200,  # Per Alpaca spec, most errors return HTTP 200
        content={
            "ErrorNumber": exc.code,
            "ErrorMessage": exc.message,
            "ClientTransactionID": client_transaction_id,
            "ServerTransactionID": get_server_transaction_id(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and convert them to Alpaca format when appropriate"""
    client_transaction_id = 0

    if "ClientTransactionID" in request.query_params:
        try:
            client_transaction_id = int(request.query_params["ClientTransactionID"])
        except (ValueError, TypeError):
            pass

    if exc.status_code == 404:
        return JSONResponse(
            status_code=400,  # Alpaca uses 400 for bad requests
            content=f"Device or method not found: {request.url.path}",
        )
    elif exc.status_code == 422:
        return JSONResponse(
            status_code=400,  # Alpaca uses 400 for bad requests
            content=f"Invalid parameters: {exc.detail}",
        )
    else:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    client_transaction_id = 0

    if "ClientTransactionID" in request.query_params:
        try:
            client_transaction_id = int(request.query_params["ClientTransactionID"])
        except (ValueError, TypeError):
            pass

    return JSONResponse(
        status_code=500,
        content={
            "ErrorNumber": 0x500,
            "ErrorMessage": f"Internal server error: {str(exc)}",
            "ClientTransactionID": client_transaction_id,
            "ServerTransactionID": get_server_transaction_id(),
        },
    )


# Include routers
app.include_router(common.router, prefix="/api/v1", tags=["Common"])
app.include_router(camera.router, prefix="/api/v1", tags=["Camera"])
app.include_router(safetymonitor.router, prefix="/api/v1", tags=["SafetyMonitor"])
app.include_router(filterwheel.router, prefix="/api/v1", tags=["FilterWheel"])
app.include_router(focuser.router, prefix="/api/v1", tags=["Focuser"])
app.include_router(rotator.router, prefix="/api/v1", tags=["Rotator"])
app.include_router(switch.router, prefix="/api/v1", tags=["Switch"])
app.include_router(
    observingconditions.router, prefix="/api/v1", tags=["ObservingConditions"]
)
app.include_router(covercalibrator.router, prefix="/api/v1", tags=["CoverCalibrator"])
app.include_router(telescope.router, prefix="/api/v1", tags=["Telescope"])
app.include_router(dome.router, prefix="/api/v1", tags=["Dome"])


@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "Alpaca Observatory Simulator",
        "version": "1.0.0",
        "description": "ASCOM Alpaca compatible device simulator",
        "api_docs": "/docs",
        "test_interface": "/test",
        "management_api": "/management",
        "device_api": "/api/v1",
    }


@app.get("/test", response_class=HTMLResponse)
async def test_interface(request: Request):
    """Dynamic test interface for all devices"""
    # Discover available endpoints dynamically
    endpoints = discover_device_endpoints(app)

    return templates.TemplateResponse(
        "index2.html.j2",
        {
            "request": request,
            "endpoints": endpoints,
        },
    )


@app.get("/reload")
async def reload_config_state():
    """Reload default state config"""
    reload_config()
    return {"message": "State config reloaded"}


@app.get("/api/v1")
async def api_info():
    """API information endpoint"""
    return {
        "name": "ASCOM Alpaca Device API",
        "version": "v1",
        "description": "RESTful API for ASCOM Alpaca device communication",
        "documentation": "/docs",
    }


@app.get("/api/endpoints")
async def get_discovered_endpoints():
    """Return discovered endpoints for all device types"""
    endpoints = discover_device_endpoints(app)
    return {
        "discovered_endpoints": endpoints,
        "summary": {
            device_type: {
                "action_count": len(get_action_endpoints(device_type, endpoints)),
                "total_endpoints": len(endpoints.get(device_type, {}).get("GET", []))
                + len(endpoints.get(device_type, {}).get("PUT", [])),
            }
            for device_type in endpoints.keys()
        },
    }


# Add management endpoints for Alpaca discovery
@app.get("/management/apiversions")
async def get_api_versions():
    """Return supported API versions"""
    return {"Value": [1], "ErrorNumber": 0, "ErrorMessage": ""}


@app.get("/management/v1/description")
async def get_management_description():
    """Return management API description"""
    return {
        "Value": {
            "ServerName": "Alpaca Observatory Simulator",
            "Manufacturer": "ASCOM Initiative",
            "ManufacturerVersion": "1.0.0",
            "Location": "Observatory Simulator",
        },
        "ErrorNumber": 0,
        "ErrorMessage": "",
    }


@app.get("/management/v1/configureddevices")
async def get_configured_devices():
    """Return list of configured devices"""
    from observatory_simulator.state import config

    devices = []
    device_number = 0

    for device_type, device_configs in config.get("devices", {}).items():
        for dev_num, dev_config in device_configs.items():
            devices.append(
                {
                    "DeviceName": dev_config.get(
                        "name", f"Simulator {device_type.title()}"
                    ),
                    "DeviceType": device_type.title(),
                    "DeviceNumber": dev_num,
                    "UniqueID": f"{device_type}-{dev_num}",
                }
            )

    return {"Value": devices, "ErrorNumber": 0, "ErrorMessage": ""}
