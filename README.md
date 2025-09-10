# Simple ASCOM Alpaca Simulators (WIP)

A comprehensive simulator for ASCOM Alpaca devices that provides a RESTful API for testing and developing observatory control software. The Alpaca API uses RESTful techniques and TCP/IP to enable ASCOM applications and devices to communicate across modern network environments.

## Features

- **Complete Device Simulation**: Supports all major ASCOM device types including:

  - Camera
  - Telescope
  - Dome
  - Focuser
  - Filter Wheel
  - Rotator
  - Safety Monitor
  - Switch
  - Observing Conditions
  - Cover Calibrator

- **Realistic Image Generation**: Uses [cabaret](https://github.com/ppp-one/cabaret) to generate authentic astronomical images for camera simulation
- **RESTful API**: Fully compliant with the ASCOM Alpaca Device API specification
- **Interactive Test Interface**: Web-based control panel for manual testing
- **Configurable Devices**: YAML-based configuration for all device properties
- **Management API**: Standard Alpaca discovery and configuration endpoints

## Installation

Clone the repository:

```bash
git clone https://github.com/ppp-one/alpaca-simulators
cd alpaca-simulators
```

Install the package:
```bash
pip install .
```

## Usage

Run the simulator using:
```bash
alpaca-simulators --host 0.0.0.0 --port 11111
```

### API Endpoints

Once running, the simulator provides several key endpoints:

- **Root**: `http://localhost:11111/` - Basic information and navigation
- **API Documentation**: `http://localhost:11111/docs` - Interactive Swagger/OpenAPI docs
- **Device API**: `http://localhost:11111/api/v1/` - Main Alpaca device endpoints
- **Management API**: `http://localhost:11111/management/` - Alpaca discovery endpoints

### Test Interface

The simulator includes a powerful web-based test interface at `http://localhost:11111/test` that allows you to:

- **Interact with all devices**: Each device type has its own expandable section
- **GET properties**: Retrieve current values from any device property
- **PUT operations**: Set values and trigger actions using form inputs
- **Real-time testing**: Immediate feedback for testing observatory control software
- **Parameter validation**: Type-appropriate input controls (checkboxes for booleans, number inputs for numeric values)

This test interface is particularly useful for:

- Testing your observatory control software against realistic device responses
- Manually setting device states to test edge cases
- Verifying API compliance and response formats
- Debugging client applications

### Device Configuration

On first run, the simulator generates `src/alpaca_simulators/config/config.yaml` from a template. You can modify this file to set:

- Device names and descriptions
- Initial property values
- Capabilities and limits
- Available options (e.g., filter names, readout modes)

You can create and maintain multiple configuration files for different setups in `src/alpaca_simulators/config`. To select them, pass their filename with the `--config option`:
```bash
uv run alpaca-simulators --config my_config.yaml
```

### Example API Calls

```bash
# Get telescope position
curl http://localhost:11111/api/v1/telescope/0/rightascension

# Set camera exposure time
curl -X PUT http://localhost:11111/api/v1/camera/0/startexposure \
  -d "Duration=5.0&Light=true"

# Check if dome is at home
curl http://localhost:11111/api/v1/dome/0/athome
```

## Development

The simulator is built with:

- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **Jinja2**: Template engine for the test interface
- **PyYAML**: Configuration file parsing
- **Cabaret**: Astronomical image generation library for realistic camera simulation

### Project Structure

```
alpaca_simulators/
├── main.py              # FastAPI application and routing
├── config/              # Device-specific API implementations
│   ├── template.yaml    # Template device configuration tracked by git
│   ├── config.yaml      # Default device configuration
├── config.py            # Configuration class
├── state.py             # Global state management
├── endpoint_discovery.py # Dynamic endpoint discovery
├── api/                 # Device-specific API implementations
│   ├── common.py        # Common Alpaca functionality
│   ├── camera.py        # Camera device endpoints
│   ├── telescope.py     # Telescope device endpoints
│   └── ...              # Other device types
└── templates/
    └── index2.html.j2   # Test interface template
```

## Contributing

Contributions are welcome! Please ensure:

- Code follows the existing style
- All device endpoints return proper Alpaca responses
- Test interface updates work with the dynamic discovery system
- Configuration changes are documented


## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. First, install uv if you haven't already:

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

```

Then clone the repository:

```bash
git clone https://github.com/ppp-one/alpaca-simulators
cd alpaca-simulators
```

### (Recommended) Create and activate a virtual environment with uv

```bash
uv venv .venv
source .venv/bin/activate
```

### Install project

```bash
uv pip install .
```

### Run the simulator

```bash
uv run alpaca-simulators --host 0.0.0.0 --port 11111
```

For development with auto-reload:

```bash
uv run alpaca-simulators --host 0.0.0.0 --port 11111 --reload
```

## License

This project implements the ASCOM Alpaca Device API specification and is intended for testing and development purposes.
