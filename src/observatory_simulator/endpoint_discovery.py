"""
Dynamic endpoint discovery for the observatory simulator.
Analyzes the FastAPI application to determine available endpoints for each device type.
"""

from fastapi import FastAPI
from typing import Dict, List
import inspect


def discover_device_endpoints(app: FastAPI) -> Dict[str, Dict[str, List[str]]]:
    """
    Discover all available endpoints for each device type by analyzing the FastAPI routes.

    Returns a dictionary mapping device types to their available GET and PUT endpoints.
    """
    device_endpoints = {}

    # Extract routes from the FastAPI app
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            path = route.path
            methods = route.methods

            # Get the endpoint function
            endpoint_func = route.endpoint

            # Analyze function signature
            sig = inspect.signature(endpoint_func)

            # Parse device-specific endpoints
            # for device_type in device_modules.keys():
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
                            params.append(
                                {"name": param_name, "type": param.annotation.__name__}
                            )

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
                        params
                        if (len(params) > 0)
                        else {"name": "Value", "type": "bool"}
                    )

    return device_endpoints


def get_action_endpoints(
    device_type: str, endpoints: Dict[str, Dict[str, List[str]]]
) -> List[str]:
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
