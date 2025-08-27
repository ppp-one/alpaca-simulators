from fastapi import APIRouter, Form, Path, Query

from observatory_simulator.api.common import AlpacaError, validate_device
from observatory_simulator.state import (
    AlpacaResponse,
    DoubleResponse,
    StringResponse,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()


@router.get(
    "/observingconditions/{device_number}/averageperiod", response_model=DoubleResponse
)
def get_averageperiod(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("averageperiod", 60.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/averageperiod", response_model=AlpacaResponse
)
def set_averageperiod(
    device_number: int = Path(..., ge=0),
    AveragePeriod: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if AveragePeriod <= 0:
        raise AlpacaError(0x402, "Average period must be positive")

    update_device_state(
        "observingconditions", device_number, {"averageperiod": AveragePeriod}
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/cloudcover", response_model=DoubleResponse
)
def get_cloudcover(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("cloudcover", 0.2),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/cloudcover", response_model=AlpacaResponse
)
def set_cloudcover(
    device_number: int = Path(..., ge=0),
    CloudCover: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if CloudCover < 0.0 or CloudCover > 1.0:
        raise AlpacaError(0x402, "Cloud cover must be between 0.0 and 1.0")

    update_device_state(
        "observingconditions", device_number, {"cloudcover": CloudCover}
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/dewpoint", response_model=DoubleResponse
)
def get_dewpoint(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("dewpoint", 5.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/dewpoint", response_model=AlpacaResponse
)
def set_dewpoint(
    device_number: int = Path(..., ge=0),
    DewPoint: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if DewPoint < -50.0 or DewPoint > 50.0:
        raise AlpacaError(0x402, "Dew point must be between -50.0°C and 50.0°C")

    update_device_state("observingconditions", device_number, {"dewpoint": DewPoint})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/humidity", response_model=DoubleResponse
)
def get_humidity(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("humidity", 60.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/humidity", response_model=AlpacaResponse
)
def set_humidity(
    device_number: int = Path(..., ge=0),
    Humidity: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if Humidity < 0.0 or Humidity > 100.0:
        raise AlpacaError(0x402, "Humidity must be between 0.0% and 100.0%")

    update_device_state("observingconditions", device_number, {"humidity": Humidity})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/pressure", response_model=DoubleResponse
)
def get_pressure(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("pressure", 1013.25),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/pressure", response_model=AlpacaResponse
)
def set_pressure(
    device_number: int = Path(..., ge=0),
    Pressure: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if Pressure < 800.0 or Pressure > 1200.0:
        raise AlpacaError(0x402, "Pressure must be between 800.0 and 1200.0 hPa")

    update_device_state("observingconditions", device_number, {"pressure": Pressure})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/rainrate", response_model=DoubleResponse
)
def get_rainrate(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("rainrate", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/rainrate", response_model=AlpacaResponse
)
def set_rainrate(
    device_number: int = Path(..., ge=0),
    RainRate: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if RainRate < 0.0 or RainRate > 100.0:
        raise AlpacaError(0x402, "Rain rate must be between 0.0 and 100.0 mm/hr")

    update_device_state("observingconditions", device_number, {"rainrate": RainRate})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/skybrightness", response_model=DoubleResponse
)
def get_skybrightness(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("skybrightness", 18.5),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/skybrightness", response_model=AlpacaResponse
)
def set_skybrightness(
    device_number: int = Path(..., ge=0),
    SkyBrightness: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    # if SkyBrightness < 10.0 or SkyBrightness > 25.0:
    #     raise AlpacaError(
    #         0x402, "Sky brightness must be between 10.0 and 25.0 mag/arcsec²"
    #     )

    update_device_state(
        "observingconditions", device_number, {"skybrightness": SkyBrightness}
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/skyquality", response_model=DoubleResponse
)
def get_skyquality(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("skyquality", 20.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/skyquality", response_model=AlpacaResponse
)
def set_skyquality(
    device_number: int = Path(..., ge=0),
    SkyQuality: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if SkyQuality < 15.0 or SkyQuality > 25.0:
        raise AlpacaError(
            0x402, "Sky quality must be between 15.0 and 25.0 mag/arcsec²"
        )

    update_device_state(
        "observingconditions", device_number, {"skyquality": SkyQuality}
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/skytemperature", response_model=DoubleResponse
)
def get_skytemperature(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("skytemperature", -10.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/skytemperature", response_model=AlpacaResponse
)
def set_skytemperature(
    device_number: int = Path(..., ge=0),
    SkyTemperature: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    update_device_state(
        "observingconditions", device_number, {"skytemperature": SkyTemperature}
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/starfwhm", response_model=DoubleResponse
)
def get_starfwhm(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("starfwhm", 2.5),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/starfwhm", response_model=AlpacaResponse
)
def set_starfwhm(
    device_number: int = Path(..., ge=0),
    StarFWHM: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if StarFWHM < 0.5 or StarFWHM > 10.0:
        raise AlpacaError(0x402, "Star FWHM must be between 0.5 and 10.0 arcseconds")

    update_device_state("observingconditions", device_number, {"starfwhm": StarFWHM})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/temperature", response_model=DoubleResponse
)
def get_temperature(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("temperature", 15.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/temperature", response_model=AlpacaResponse
)
def set_temperature(
    device_number: int = Path(..., ge=0),
    Temperature: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if Temperature < -50.0 or Temperature > 50.0:
        raise AlpacaError(0x402, "Temperature must be between -50.0°C and 50.0°C")

    update_device_state(
        "observingconditions", device_number, {"temperature": Temperature}
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/winddirection", response_model=DoubleResponse
)
def get_winddirection(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("winddirection", 180.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/winddirection", response_model=AlpacaResponse
)
def set_winddirection(
    device_number: int = Path(..., ge=0),
    WindDirection: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if WindDirection < 0.0 or WindDirection >= 360.0:
        raise AlpacaError(0x402, "Wind direction must be between 0.0 and 359.9 degrees")

    update_device_state(
        "observingconditions", device_number, {"winddirection": WindDirection}
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/windgust", response_model=DoubleResponse
)
def get_windgust(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("windgust", 5.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/windgust", response_model=AlpacaResponse
)
def set_windgust(
    device_number: int = Path(..., ge=0),
    WindGust: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if WindGust < 0.0 or WindGust > 150.0:
        raise AlpacaError(0x402, "Wind gust must be between 0.0 and 150.0 m/s")

    update_device_state("observingconditions", device_number, {"windgust": WindGust})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/windspeed", response_model=DoubleResponse
)
def get_windspeed(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)
    return DoubleResponse(
        Value=state.get("windspeed", 3.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/windspeed", response_model=AlpacaResponse
)
def set_windspeed(
    device_number: int = Path(..., ge=0),
    WindSpeed: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if WindSpeed < 0.0 or WindSpeed > 100.0:
        raise AlpacaError(0x402, "Wind speed must be between 0.0 and 100.0 m/s")

    update_device_state("observingconditions", device_number, {"windspeed": WindSpeed})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put(
    "/observingconditions/{device_number}/refresh", response_model=AlpacaResponse
)
def refresh(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("observingconditions", device_number)
    state = get_device_state("observingconditions", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    # For simulator, just acknowledge the refresh
    # In a real implementation, this would trigger sensor reading

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/sensordescription",
    response_model=StringResponse,
)
def get_sensordescription(
    device_number: int = Path(..., ge=0),
    SensorName: str = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("observingconditions", device_number)

    # Map sensor names to descriptions
    sensor_descriptions = {
        "CloudCover": "Cloud coverage sensor (0-1 fraction)",
        "DewPoint": "Dew point temperature sensor (°C)",
        "Humidity": "Relative humidity sensor (%)",
        "Pressure": "Atmospheric pressure sensor (hPa)",
        "RainRate": "Rain rate sensor (mm/hr)",
        "SkyBrightness": "Sky brightness sensor (mag/arcsec²)",
        "SkyQuality": "Sky quality sensor (mag/arcsec²)",
        "SkyTemperature": "Sky temperature sensor (°C)",
        "StarFWHM": "Star FWHM sensor (arcseconds)",
        "Temperature": "Ambient temperature sensor (°C)",
        "WindDirection": "Wind direction sensor (degrees)",
        "WindGust": "Wind gust sensor (m/s)",
        "WindSpeed": "Wind speed sensor (m/s)",
    }

    description = sensor_descriptions.get(SensorName, "Unknown sensor")

    return StringResponse(
        Value=description,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get(
    "/observingconditions/{device_number}/timesincelastupdate",
    response_model=DoubleResponse,
)
def get_timesincelastupdate(
    device_number: int = Path(..., ge=0),
    SensorName: str = Query(...),
    ClientTransactionID: int = Query(0),
):
    validate_device("observingconditions", device_number)

    # For simulator, return a small time since last update
    return DoubleResponse(
        Value=1.0,  # 1 second ago
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )
