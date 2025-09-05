# parse_spec.py
import os
from collections import defaultdict

import yaml


def get_device_type_from_path(path):
    """
    Extract device type from API path.
    Returns 'common' for template endpoints with {device_type} or the specific device type.
    """
    if not path.startswith("/"):
        return "unknown"

    parts = path.strip("/").split("/")

    # Handle management endpoints like /management/v1/...
    if parts[0] == "management":
        return "management"

    # Handle template paths like /{device_type}/{device_number}/... (these are common)
    if parts[0] == "{device_type}":
        return "common"

    # Handle device-specific endpoints like /camera/{device_number}/...
    if len(parts) >= 2:
        device_type = parts[0]
        return device_type

    return "unknown"


def analyze_api_spec(file_path="AlpacaDeviceAPI_v1.yaml", output_dir="api_docs"):
    """
    Parses the Alpaca OpenAPI YAML file and writes a summary
    of endpoints to separate files by device type.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    with open(file_path) as f:
        spec = yaml.safe_load(f)

    if not spec.get("paths"):
        print("No paths found in the specification.")
        return

    # Group endpoints by device type
    endpoints_by_type = defaultdict(list)

    for path, path_item in spec["paths"].items():
        device_type = get_device_type_from_path(path)

        for method, operation in path_item.items():
            summary = operation.get("summary", "No summary provided.")
            endpoints_by_type[device_type].append(
                {"method": method.upper(), "path": path, "summary": summary}
            )

    # Write separate files for each device type
    for device_type, endpoints in endpoints_by_type.items():
        output_file = os.path.join(output_dir, f"{device_type}_endpoints.txt")

        with open(output_file, "w") as out_f:
            out_f.write(f"📄 {device_type.upper()} API Endpoints\n")
            out_f.write("=" * 50 + "\n\n")

            for endpoint in endpoints:
                out_f.write(f"{endpoint['method']:<7} {endpoint['path']}\n")
                out_f.write(f"    Summary: {endpoint['summary']}\n\n")

        print(f"✅ {device_type.capitalize()} endpoints written to: {output_file}")

    print(
        "\n🎉 Analysis complete! "
        + f"{len(endpoints_by_type)} files created in '{output_dir}' directory."
    )


if __name__ == "__main__":
    analyze_api_spec()
