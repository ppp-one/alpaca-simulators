import logging
import os
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from alpaca_simulators.api import (
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
from alpaca_simulators.api.common import AlpacaError
from alpaca_simulators.config import Config
from alpaca_simulators.endpoint_discovery import (
    discover_device_endpoints,
    get_action_endpoints,
)
from alpaca_simulators.state import (
    get_all_configured_devices,
    get_server_transaction_id,
    reload_config,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    devices = get_all_configured_devices()
    telescope.start_background_updater(devices.get("telescope", []))
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Alpaca Observatory Simulator",
    description=(
        "A simulator for Alpaca devices based on the AlpacaDeviceAPI_v1.yaml specification."
    ),
    version=version("alpaca-simulators"),
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
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


def _client_transaction_id(request: Request) -> int:
    # Only query params: the body may already have been consumed by FastAPI's
    # form parsing, so endpoints handle a ClientTransactionID sent in the body.
    try:
        return int(request.query_params.get("ClientTransactionID", 0))
    except ValueError:
        return 0


@app.exception_handler(AlpacaError)
async def alpaca_exception_handler(request: Request, exc: AlpacaError):
    return JSONResponse(
        status_code=200,  # Per Alpaca spec, most errors return HTTP 200
        content={
            "ErrorNumber": exc.code,
            "ErrorMessage": exc.message,
            "ClientTransactionID": _client_transaction_id(request),
            "ServerTransactionID": get_server_transaction_id(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and convert them to Alpaca format when appropriate"""
    error_response: dict[str, object] = {
        "error": {
            "message": exc.detail,
            "client_transaction_id": _client_transaction_id(request),
        }
    }

    if exc.status_code == 404:
        error_response["url"] = str(request.url)
        return JSONResponse(
            status_code=400,  # Alpaca uses 400 for bad requests
            content=f"Device or method not found: {error_response}",
        )
    elif exc.status_code == 422:
        return JSONResponse(
            status_code=400,  # Alpaca uses 400 for bad requests
            content=f"Invalid parameters: {error_response}",
        )
    else:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "ErrorNumber": 0x500,
            "ErrorMessage": f"Internal server error: {str(exc)}",
            "ClientTransactionID": _client_transaction_id(request),
            "ServerTransactionID": get_server_transaction_id(),
        },
    )


API_PREFIX = "/api/v1"

# (router, prefix, tag) for every device API router. This list drives both the
# router registration below and the endpoint discovery used by the test
# interface, so discovery does not depend on how a FastAPI version stores
# included routes in app.routes.
ROUTERS = [
    (common.router, API_PREFIX, "Common"),
    (camera.router, API_PREFIX, "Camera"),
    (safetymonitor.router, API_PREFIX, "SafetyMonitor"),
    (filterwheel.router, API_PREFIX, "FilterWheel"),
    (focuser.router, API_PREFIX, "Focuser"),
    (rotator.router, API_PREFIX, "Rotator"),
    (switch.router, API_PREFIX, "Switch"),
    (observingconditions.router, API_PREFIX, "ObservingConditions"),
    (covercalibrator.router, API_PREFIX, "CoverCalibrator"),
    (telescope.router, API_PREFIX, "Telescope"),
    (dome.router, API_PREFIX, "Dome"),
]

# Routers paired with their mount prefix, for endpoint discovery.
DISCOVERY_ROUTERS = [(router, prefix) for router, prefix, _ in ROUTERS]

# Include routers
for router, prefix, tag in ROUTERS:
    app.include_router(router, prefix=prefix, tags=[tag])


@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "Alpaca Observatory Simulator",
        "description": "ASCOM Alpaca compatible device simulator",
        "api_docs": "/docs",
        "test_interface": "/test_interface",
        "device_api": "/api/v1",
        "sunlight_control": "/sunlight",
    }


@app.get("/test_interface", response_class=HTMLResponse)
async def test_interface(request: Request):
    """Dynamic test interface for all devices"""
    # Discover available endpoints dynamically
    endpoints = discover_device_endpoints(DISCOVERY_ROUTERS)

    return templates.TemplateResponse(
        request,
        "index2.html.j2",
        {"endpoints": endpoints},
    )


@app.get("/reload")
async def reload_config_state():
    """Reload default state config"""
    reload_config()
    return {"message": "State config reloaded"}


@app.put("/sunlight")
async def enable_sunlight(state: bool):
    """Enable or disable sunlight simulation"""
    Config().load().update({"sunlight": state})
    logging.info(f"sunlight simulation set to {state}")

    return {"message": f"Sunlight simulation {'enabled' if state else 'disabled'}"}


@app.get("/sunlight")
async def get_sunlight():
    """Get current sunlight simulation state"""
    state = Config().load().get("sunlight", False)
    return {"sunlight": state}


@app.put("/bad_tracking")
async def enable_bad_tracking(state: bool):
    """Enable or disable bad_tracking simulation"""
    Config().load().update({"bad_tracking": state})
    logging.info(f"bad_tracking simulation set to {state}")

    return {"message": f"bad_tracking simulation {'enabled' if state else 'disabled'}"}


@app.get("/bad_tracking")
async def get_bad_tracking():
    """Get current bad_tracking simulation state"""
    state = Config().load().get("bad_tracking", False)
    return {"bad_tracking": state}


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
    endpoints = discover_device_endpoints(DISCOVERY_ROUTERS)
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
