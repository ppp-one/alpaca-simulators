# ASCOM Alpaca Simulators

A comprehensive simulator for ASCOM Alpaca devices that provides a RESTful API for testing and developing observatory control software.

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

## Quick Start

The fastest way to run the simulator is using [uv](https://docs.astral.sh/uv/).

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ppp-one/alpaca-simulators
   cd alpaca-simulators
   ```

2. **Run the simulator:**
   ```bash
   uv run alpaca-simulators
   ```
   *This will automatically install dependencies and start the server at `http://0.0.0.0:11111`.*

## Configuration & Options

The simulator supports several command-line arguments:

```bash
# Run on a different port with auto-reload enabled
uv run alpaca-simulators --port 8080 --reload

# Use a specific configuration file
uv run alpaca-simulators --config my_custom_setup.yaml
```

### Test Interface

The simulator includes a web-based test UI at `http://localhost:11111/test_interface` that allows you to:

- **GET properties**: Retrieve current values from any device property
- **PUT operations**: Set values and trigger actions using form inputs


### Device Configuration

On first run, the simulator generates `src/alpaca_simulators/config/config.yaml` from a template. You can modify this file to set:

- Device names and descriptions
- Initial property values
- Capabilities and limits
- Available options (e.g., filter names, camera properties)


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
