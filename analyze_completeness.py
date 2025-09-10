# analyze_completeness.py
import os
import re


def extract_endpoints_from_api_doc(file_path):
    """Extract endpoints from an API documentation file"""
    endpoints = []
    try:
        with open(file_path) as f:
            content = f.read()

        # Find all endpoints in the format: METHOD     /path
        pattern = r"^(GET|PUT|POST|DELETE)\s+(/[^\s]+)"
        matches = re.findall(pattern, content, re.MULTILINE)

        for method, path in matches:
            endpoints.append((method, path))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return endpoints


def extract_endpoints_from_python_file(file_path):
    """Extract implemented endpoints from a Python API file"""
    endpoints = []
    try:
        with open(file_path) as f:
            content = f.read()

        # Find router decorators with HTTP methods - handle multi-line decorators
        # First, remove line breaks within decorator definitions
        content = re.sub(
            r'@router\.(get|put|post|delete)\(\s*\n\s*"([^"]+)"',
            r'@router.\1("\2"',
            content,
            flags=re.MULTILINE,
        )

        # Now extract the patterns
        pattern = r'@router\.(get|put|post|delete)\("([^"]+)"'
        matches = re.findall(pattern, content, re.IGNORECASE)

        for method, path in matches:
            endpoints.append((method.upper(), path))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return endpoints


def normalize_path(path, device_type):
    """Normalize paths for comparison"""
    # Replace {device_number} with a placeholder
    normalized = path.replace("{device_number}", "{N}")

    # Replace actual device type with {device_type} for common endpoints
    if path.startswith(f"/{device_type}/"):
        normalized = path.replace(f"/{device_type}/", "/{device_type}/")

    return normalized


def analyze_device_completeness(device_type):
    """Analyze completeness for a specific device type"""
    print(f"\n{'=' * 60}")
    print(f"ANALYZING {device_type.upper()} COMPLETENESS")
    print(f"{'=' * 60}")

    # Read expected endpoints from API docs
    api_doc_path = f"api_docs/{device_type}_endpoints.txt"
    if not os.path.exists(api_doc_path):
        print(f"❌ API doc file not found: {api_doc_path}")
        return

    expected_endpoints = extract_endpoints_from_api_doc(api_doc_path)
    print(f"📋 Expected endpoints: {len(expected_endpoints)}")

    # Read implemented endpoints from Python file
    python_file_path = f"alpaca_simulators/api/{device_type}.py"
    if not os.path.exists(python_file_path):
        print(f"❌ Implementation file not found: {python_file_path}")
        return

    implemented_endpoints = extract_endpoints_from_python_file(python_file_path)
    print(f"✅ Implemented endpoints: {len(implemented_endpoints)}")

    # Normalize paths for comparison
    expected_normalized = set()
    for method, path in expected_endpoints:
        normalized_path = normalize_path(path, device_type)
        expected_normalized.add((method, normalized_path))

    implemented_normalized = set()
    for method, path in implemented_endpoints:
        normalized_path = normalize_path(path, device_type)
        implemented_normalized.add((method, normalized_path))

    # Find missing endpoints
    missing = expected_normalized - implemented_normalized
    extra = implemented_normalized - expected_normalized

    if missing:
        print(f"\n❌ MISSING ENDPOINTS ({len(missing)}):")
        for method, path in sorted(missing):
            print(f"   {method:<7} {path}")
    else:
        print("\n✅ All expected endpoints are implemented!")

    if extra:
        print(f"\n🔍 EXTRA ENDPOINTS ({len(extra)}):")
        for method, path in sorted(extra):
            print(f"   {method:<7} {path}")

    completion_rate = (
        ((len(expected_normalized) - len(missing)) / len(expected_normalized)) * 100
        if expected_normalized
        else 0
    )
    print(f"\n📊 Completion rate: {completion_rate:.1f}%")

    return {
        "device_type": device_type,
        "expected": len(expected_endpoints),
        "implemented": len(implemented_endpoints),
        "missing": len(missing),
        "completion_rate": completion_rate,
    }


def analyze_common_endpoints():
    """Analyze common endpoints implementation"""
    print(f"\n{'=' * 60}")
    print("ANALYZING COMMON ENDPOINTS")
    print(f"{'=' * 60}")

    # Read expected common endpoints
    common_doc_path = "api_docs/common_endpoints.txt"
    if not os.path.exists(common_doc_path):
        print(f"❌ Common API doc file not found: {common_doc_path}")
        return

    expected_endpoints = extract_endpoints_from_api_doc(common_doc_path)
    print(f"📋 Expected common endpoints: {len(expected_endpoints)}")

    # Read implemented common endpoints
    common_file_path = "alpaca_simulators/api/common.py"
    if not os.path.exists(common_file_path):
        print(f"❌ Common implementation file not found: {common_file_path}")
        return

    implemented_endpoints = extract_endpoints_from_python_file(common_file_path)
    print(f"✅ Implemented common endpoints: {len(implemented_endpoints)}")

    # Convert to sets for comparison (using device_type placeholder)
    expected_set = set()
    for method, path in expected_endpoints:
        expected_set.add((method, path))

    implemented_set = set()
    for method, path in implemented_endpoints:
        implemented_set.add((method, path))

    # Find missing endpoints
    missing = expected_set - implemented_set
    extra = implemented_set - expected_set

    if missing:
        print(f"\n❌ MISSING COMMON ENDPOINTS ({len(missing)}):")
        for method, path in sorted(missing):
            print(f"   {method:<7} {path}")
    else:
        print("\n✅ All expected common endpoints are implemented!")

    if extra:
        print(f"\n🔍 EXTRA COMMON ENDPOINTS ({len(extra)}):")
        for method, path in sorted(extra):
            print(f"   {method:<7} {path}")

    completion_rate = (
        ((len(expected_set) - len(missing)) / len(expected_set)) * 100 if expected_set else 0
    )
    print(f"\n📊 Common endpoints completion rate: {completion_rate:.1f}%")

    return {
        "expected": len(expected_endpoints),
        "implemented": len(implemented_endpoints),
        "missing": len(missing),
        "completion_rate": completion_rate,
    }


def main():
    print("🔍 Observatory Simulator API Completeness Analysis")
    print("=" * 60)

    # Check if we're in the right directory
    if not os.path.exists("api_docs") or not os.path.exists("alpaca_simulators/api"):
        print("❌ Please run this script from the project root directory")
        return

    # Analyze common endpoints first
    common_stats = analyze_common_endpoints()

    # Get list of device types from api_docs directory
    device_types = []
    for filename in os.listdir("api_docs"):
        if filename.endswith("_endpoints.txt") and filename != "common_endpoints.txt":
            device_type = filename.replace("_endpoints.txt", "")
            device_types.append(device_type)

    device_types.sort()

    # Analyze each device type
    device_stats = []
    for device_type in device_types:
        stats = analyze_device_completeness(device_type)
        if stats:
            device_stats.append(stats)

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")

    if common_stats:
        print(f"Common endpoints: {common_stats['completion_rate']:.1f}% complete")

    total_expected = 0
    total_implemented = 0
    total_missing = 0

    print("\nDevice-specific endpoints:")
    for stats in device_stats:
        print(
            f"  {stats['device_type']:<20}: {stats['completion_rate']:>5.1f}% complete "
            f"({stats['implemented']}/{stats['expected']} endpoints)"
        )
        total_expected += stats["expected"]
        total_implemented += stats["implemented"]
        total_missing += stats["missing"]

    if device_stats:
        overall_completion = (
            ((total_implemented) / (total_expected)) * 100 if total_expected > 0 else 0
        )
        print(
            f"\nOverall device endpoints: {overall_completion:.1f}% complete "
            f"({total_implemented}/{total_expected} endpoints)"
        )
        print(f"Total missing endpoints: {total_missing}")


if __name__ == "__main__":
    main()
