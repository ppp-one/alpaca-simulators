"""
Dynamic endpoint discovery for the observatory simulator.
Analyzes the API routers to determine available endpoints for each device type.
"""

import inspect
from collections.abc import Iterable

from fastapi import APIRouter


def _iter_routes(routers: Iterable[tuple[APIRouter, str]]):
    """
    Yield (path, methods, endpoint) for every route in the given routers.

    Each router is paired with the prefix it is mounted under, so the paths
    match the ones the application serves.

    Discovery reads the routers directly instead of ``app.routes``. FastAPI
    changed how ``include_router`` stores sub-routes: older versions copy the
    sub-routes into ``app.routes``, newer versions append a single lazy object
    per router. Reading the routers works with both.
    """
    for router, prefix in routers:
        for route in router.routes:
            if hasattr(route, "path") and hasattr(route, "methods") and hasattr(route, "endpoint"):
                yield f"{prefix}{route.path}", route.methods, route.endpoint


def discover_device_endpoints(
    routers: Iterable[tuple[APIRouter, str]],
) -> dict[str, dict[str, list[str]]]:
    """
    Discover all available endpoints for each device type.

    Takes an iterable of (router, prefix) pairs, where prefix is the path the
    router is mounted under.

    Returns a dictionary mapping device types to their available GET and PUT
    endpoints.
    """
    device_endpoints = {}

    for path, methods, endpoint_func in _iter_routes(routers):
        # Analyze function signature
        sig = inspect.signature(endpoint_func)

        # Parse device-specific endpoints
        device_type = path.split("/")[3] if len(path.split("/")) > 3 else None
        if f"/{device_type}/" in path and "/{device_number}/" in path:
            # Extract the property name from the path
            # Example: /api/v1/camera/{device_number}/temperature -> temperature
            path_parts = path.split("/")
            if len(path_parts) >= 5:  # /api/v1/device/{device_number}/property
                property_name = path_parts[-1]

                # Skip if it's just a device number
                if property_name == "{device_number}":
                    continue

                params = []
                for param_name, param in sig.parameters.items():
                    if param_name not in [
                        "device_number",
                        "ClientTransactionID",
                    ]:
                        params.append({"name": param_name, "type": param.annotation.__name__})

                # Initialize device entry if not exists
                if device_type not in device_endpoints:
                    device_endpoints[device_type] = {
                        "GET": [],
                        "PUT": [],
                        "info": {},
                    }

                # Add endpoints by method
                for method in methods:
                    if method in ["GET", "PUT"]:
                        device_endpoints[device_type][method].append(property_name)

                device_endpoints[device_type]["info"][property_name] = (
                    params if (len(params) > 0) else {"name": "Value", "type": "bool"}
                )

    return device_endpoints


def get_action_endpoints(
    device_type: str, endpoints: dict[str, dict[str, list[str]]]
) -> list[str]:
    """
    Get list of action endpoints (PUT endpoints that don't correspond to properties).
    """
    if device_type not in endpoints:
        return []

    put_endpoints = set(endpoints[device_type].get("PUT", []))
    get_endpoints = set(endpoints[device_type].get("GET", []))

    # Action endpoints are PUT-only (no corresponding GET)
    actions = put_endpoints - get_endpoints

    return sorted(actions)
