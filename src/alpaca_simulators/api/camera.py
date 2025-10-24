import asyncio
from datetime import datetime, timezone

import cabaret
import numpy as np
from fastapi import APIRouter, BackgroundTasks, Form, Path, Query
from fastapi.responses import StreamingResponse

from alpaca_simulators.api.common import AlpacaError, validate_device
from alpaca_simulators.config import Config
from alpaca_simulators.state import (
    AlpacaResponse,
    BoolResponse,
    CameraStates,
    DoubleResponse,
    GuideDirections,
    ImageArrayResponse,
    IntResponse,
    SensorTypes,
    StringArrayResponse,
    StringResponse,
    get_device_state,
    get_server_transaction_id,
    update_device_state,
)

router = APIRouter()

image_cache = {}


def make_cache_key(ra, dec, duration, light, focus, sunlight):
    return f"{ra}_{dec}_{duration}_{light}_{focus}_{sunlight}"


async def bytes_generator(image_array, numx, numy):
    b = (1).to_bytes(4, "little")  # metaversion
    b += (0).to_bytes(4, "little")  # error
    b += (0).to_bytes(4, "little")  # clientid
    b += (0).to_bytes(4, "little")  # deviceid
    b += (44).to_bytes(4, "little")  # DataStart
    b += (2).to_bytes(4, "little")  # ImageElementType
    b += (8).to_bytes(4, "little")  # TransmissionElementType
    b += (2).to_bytes(4, "little")  # Rank
    b += int(numx).to_bytes(4, "little")  # Dimension1
    b += int(numy).to_bytes(4, "little")  # Dimension2
    b += (0).to_bytes(4, "little")  # Dimension3

    b += image_array.T.tobytes()

    yield b


async def exposure_task(device_number: int, duration: float, light: bool):
    """Background task to simulate camera exposure"""
    global image_cache
    try:
        # Update camera state to exposing
        update_device_state(
            "camera",
            device_number,
            {
                "camera_state": CameraStates.EXPOSING,
                "image_ready": False,
                "exposure_start_time": datetime.now(timezone.utc).isoformat(),
                "exposure_duration": duration,
                "light": light,
                "percentcompleted": 0,
            },
        )

        # Simulate exposure progress
        steps = 10
        for i in range(steps):
            await asyncio.sleep(duration / steps)
            progress = int((i + 1) * 100 / steps)
            update_device_state("camera", device_number, {"percentcompleted": progress})

        # Update to reading state
        update_device_state("camera", device_number, {"camera_state": CameraStates.READING})
        await asyncio.sleep(0.01)  # Simulate readout time

        # Generate image using cabaret
        cam_state = get_device_state("camera", device_number)
        tel_state = get_device_state("telescope", 0)  # Assume telescope 0
        focuser_state = get_device_state("focuser", 0)  # Assume focuser 0

        # Calculate seeing multiplier based on focuser position
        seeing_multiplier = 1 + np.abs(focuser_state.get("position", 0) - 10_000) / 100

        if seeing_multiplier > 5:
            seeing_multiplier = 5

        # Get current coordinates from telescope
        pointing_error_ra = Config().load().get("pointing_error_ra", 0.0)  # arcmin
        pointing_error_dec = Config().load().get("pointing_error_dec", 0.0)  # arcmin
        ra = tel_state.get("rightascension", 0.0) + (pointing_error_ra / 60) / 15
        dec = tel_state.get("declination", 0.0) + (pointing_error_dec / 60)
        # gaia breaks
        if dec >= 90.0 or dec <= -90.0:
            dec = 89.99 if dec >= 0 else -89.99

        if ra <= 0.0 or ra >= 24.0:
            ra = 0.01 if ra <= 0.0 else 23.99

        # Initialise cabaret
        cabaret_camera = cabaret.Camera(
            width=cam_state.get("numx"),
            height=cam_state.get("numy"),
            bin_x=cam_state.get("binx", 1),
            bin_y=cam_state.get("biny", 1),
            pitch=cam_state.get("pixelsizex", 10.0),
            gain=cam_state.get("gain", 1.0),
            well_depth=cam_state.get("fullwellcapacity", 2**16),
            dark_current=0.2
            * 2 ** ((cam_state.get("ccdtemperature", -60) - (-10)) / 6),  # doubles every 6C
            pixel_defects=cam_state.get("pixel_defects", {}),
        )
        sunlight = Config().load().get("sunlight", False)
        if sunlight:
            cabaret_site = cabaret.Site(
                sky_background=150,
                seeing=1 * seeing_multiplier,
                latitude=tel_state.get("sitelatitude", None),
                longitude=tel_state.get("sitelongitude", None),
            )
        else:
            cabaret_site = cabaret.Site(
                sky_background=150,
                seeing=1 * seeing_multiplier,
            )

        cabaret_telescope = cabaret.Telescope(
            focal_length=tel_state.get("focallength", 8.0),
            diameter=tel_state.get("aperturediameter", 0.2),
        )

        cabaret_observatory = cabaret.Observatory(
            camera=cabaret_camera, site=cabaret_site, telescope=cabaret_telescope
        )

        bad_tracking = Config().load().get("bad_tracking", False)
        if bad_tracking:
            bad_tracking_rate = Config().load().get("bad_tracking_rate", 0.01)  # arcsec per second
            last_slew_time = tel_state.get("last_slew_time", datetime.now(timezone.utc))
            print("LAST_SLEW_TIME", last_slew_time)
            # drift RA/Dec based on time since last slew
            time_elapsed = (datetime.now(timezone.utc) - last_slew_time).total_seconds()
            ra += time_elapsed * (bad_tracking_rate / 3600) / 15  # convert to hours
            dec += time_elapsed * bad_tracking_rate / 3600

        # Generate star field image
        key = make_cache_key(
            ra, dec, duration, light, focuser_state.get("position", 0), sunlight=sunlight
        )
        if key in image_cache:
            image_data = image_cache[key]
        else:
            image_data = cabaret_observatory.generate_image(
                ra=(ra / 24) * 360,
                dec=dec,
                exp_time=duration,
                light=1 if light else 0,
                timeout=Config().load().get("gaia_query_timeout", 30),
            )
            image_cache[key] = image_data

        # Update to download state with image ready
        update_device_state(
            "camera",
            device_number,
            {
                "camera_state": CameraStates.IDLE,
                "image_ready": True,
                "image_data": image_data,
                "percentcompleted": 100,
            },
        )

    except Exception as e:
        # Set error state
        update_device_state(
            "camera",
            device_number,
            {
                "camera_state": CameraStates.ERROR,
                "image_ready": False,
                "image_data": None,
            },
        )
        raise AlpacaError(0x40D, f"Issue with camera exposure: {e}")


# Camera-specific endpoints
@router.get("/camera/{device_number}/camerastate", response_model=IntResponse)
def get_camerastate(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("camera_state", CameraStates.IDLE),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/imageready", response_model=BoolResponse)
def get_imageready(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("image_ready", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/imagearray", response_model=ImageArrayResponse)
def get_imagearray(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)

    # if not state.get("image_ready"):
    #     raise AlpacaError(0x40D, "Image not ready")

    image_data = state.get("image_data")
    if image_data is None:
        raise AlpacaError(0x40D, "No image data available")

    cam_state = get_device_state("camera", device_number)

    # Clear the image after download and return to idle
    update_device_state(
        "camera",
        device_number,
        {
            "camera_state": CameraStates.IDLE,
            "image_ready": False,
            # "image_data": None,
            "percentcompleted": 0,
        },
    )

    return StreamingResponse(
        bytes_generator(image_data, cam_state.get("numx"), cam_state.get("numy")),
        headers={"Content-Type": "application/imagebytes"},
        media_type="application/imagebytes",
    )


@router.put("/camera/{device_number}/startexposure", response_model=AlpacaResponse)
def start_exposure(
    background_tasks: BackgroundTasks,
    device_number: int = Path(..., ge=0),
    Duration: float = Form(...),
    Light: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if state["camera_state"] != CameraStates.IDLE:
        raise AlpacaError(0x40C, "Camera is not idle")

    state = get_device_state("camera", device_number)
    if Duration < state.get("exposuremin", 0.001):
        raise AlpacaError(
            0x402,
            f"Exposure duration too short (minimum: {state.get('exposuremin', 0.001)}s)",
        )

    if Duration > state.get("exposuremax", 3600.0):
        raise AlpacaError(
            0x402,
            f"Exposure duration too long (maximum: {state.get('exposuremax', 3600.0)}s)",
        )

    # Start exposure task
    background_tasks.add_task(exposure_task, device_number, Duration, Light)

    # Set to waiting state
    # update_device_state("camera", device_number, {"camera_state": CameraStates.WAITING})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/abortexposure", response_model=AlpacaResponse)
def abort_exposure(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("camera", device_number)
    # state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    if not state.get("canabortexposure", True):
        raise AlpacaError(0x401, "Camera cannot abort exposures")

    # Return to idle state
    update_device_state(
        "camera",
        device_number,
        {
            "camera_state": CameraStates.IDLE,
            "image_ready": False,
            "image_data": None,
            "percentcompleted": 0,
        },
    )

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/stopexposure", response_model=AlpacaResponse)
def stop_exposure(device_number: int = Path(..., ge=0), ClientTransactionID: int = Form(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    if not state.get("canstopexposure", True):
        raise AlpacaError(0x401, "Camera cannot stop exposures")

    # If exposing, transition to reading state
    if state["camera_state"] == CameraStates.EXPOSING:
        update_device_state("camera", device_number, {"camera_state": CameraStates.READING})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Camera properties
@router.get("/camera/{device_number}/cameraxsize", response_model=IntResponse)
def get_cameraxsize(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("cameraxsize", 1024),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/cameraysize", response_model=IntResponse)
def get_cameraysize(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("cameraysize", 1024),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/pixelsizex", response_model=DoubleResponse)
def get_pixelsizex(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("pixelsizex", 5.4),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/pixelsizey", response_model=DoubleResponse)
def get_pixelsizey(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("pixelsizey", 5.4),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/maxbinx", response_model=IntResponse)
def get_maxbinx(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("maxbinx", 8),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/maxbiny", response_model=IntResponse)
def get_maxbiny(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("maxbiny", 8),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Binning
@router.get("/camera/{device_number}/binx", response_model=IntResponse)
def get_binx(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("binx", 1),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/binx", response_model=AlpacaResponse)
def set_binx(
    device_number: int = Path(..., ge=0),
    BinX: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    if BinX < 1 or BinX > state.get("maxbinx", 8):
        raise AlpacaError(0x402, f"Invalid binning value: {BinX}")
    update_device_state("camera", device_number, {"binx": BinX})
    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/biny", response_model=IntResponse)
def get_biny(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("biny", 1),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/biny", response_model=AlpacaResponse)
def set_biny(
    device_number: int = Path(..., ge=0),
    BinY: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    if BinY < 1 or BinY > state.get("maxbiny", 8):
        raise AlpacaError(0x402, f"Invalid binning value: {BinY}")
    update_device_state("camera", device_number, {"biny": BinY})
    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Readout modes
@router.get("/camera/{device_number}/readoutmodes", response_model=StringArrayResponse)
def get_readoutmodes(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return StringArrayResponse(
        Value=state.get("readoutmodes", ["Fast", "Normal"]),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/readoutmode", response_model=IntResponse)
def get_readoutmode(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("readoutmode", 0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/readoutmode", response_model=AlpacaResponse)
def set_readoutmode(
    device_number: int = Path(..., ge=0),
    ReadoutMode: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    modes = state.get("readoutmodes", ["Fast", "Normal"])
    if ReadoutMode < 0 or ReadoutMode >= len(modes):
        raise AlpacaError(0x402, f"Invalid readout mode: {ReadoutMode}")
    update_device_state("camera", device_number, {"readoutmode": ReadoutMode})
    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Additional camera endpoints would go here...
@router.get("/camera/{device_number}/percentcompleted", response_model=IntResponse)
def get_percentcompleted(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("percentcompleted", 0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Bayer pattern support
@router.get("/camera/{device_number}/bayeroffsetx", response_model=IntResponse)
def get_bayeroffsetx(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("bayeroffsetx", 0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/bayeroffsety", response_model=IntResponse)
def get_bayeroffsety(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("bayeroffsety", 0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Capability endpoints
@router.get("/camera/{device_number}/canabortexposure", response_model=BoolResponse)
def get_canabortexposure(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("canabortexposure", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/canasymmetricbin", response_model=BoolResponse)
def get_canasymmetricbin(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("canasymmetricbin", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/canfastreadout", response_model=BoolResponse)
def get_canfastreadout(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("canfastreadout", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/cangetcoolerpower", response_model=BoolResponse)
def get_cangetcoolerpower(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("cangetcoolerpower", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/canpulseguide", response_model=BoolResponse)
def get_canpulseguide(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("canpulseguide", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/cansetccdtemperature", response_model=BoolResponse)
def get_cansetccdtemperature(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("cansetccdtemperature", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/canstopexposure", response_model=BoolResponse)
def get_canstopexposure(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("canstopexposure", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Exposure limits and properties
@router.get("/camera/{device_number}/exposuremax", response_model=DoubleResponse)
def get_exposuremax(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("exposuremax", 3600.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/exposuremin", response_model=DoubleResponse)
def get_exposuremin(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("exposuremin", 0.001),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/exposureresolution", response_model=DoubleResponse)
def get_exposureresolution(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("exposureresolution", 0.001),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/lastexposureduration", response_model=DoubleResponse)
def get_lastexposureduration(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("exposure_duration", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/lastexposurestarttime", response_model=StringResponse)
def get_lastexposurestarttime(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return StringResponse(
        Value=str(state.get("exposure_start_time", "")),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Camera sensor properties
@router.get("/camera/{device_number}/electronsperadu", response_model=DoubleResponse)
def get_electronsperadu(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("electronsperadu", 1.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/fullwellcapacity", response_model=DoubleResponse)
def get_fullwellcapacity(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("fullwellcapacity", 100000.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/hasshutter", response_model=BoolResponse)
def get_hasshutter(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("hasshutter", True),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/maxadu", response_model=IntResponse)
def get_maxadu(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("maxadu", 65535),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/sensorname", response_model=StringResponse)
def get_sensorname(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return StringResponse(
        Value=state.get("sensorname", "Simulated CCD"),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/sensortype", response_model=IntResponse)
def get_sensortype(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("sensortype", SensorTypes.MONOCHROME),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Temperature control
@router.get("/camera/{device_number}/ccdtemperature", response_model=DoubleResponse)
def get_ccdtemperature(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("ccdtemperature", 20.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/setccdtemperature", response_model=DoubleResponse)
def get_setccdtemperature(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("setccdtemperature", 20.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/setccdtemperature", response_model=AlpacaResponse)
def set_ccdtemperature(
    device_number: int = Path(..., ge=0),
    SetCCDTemperature: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    # state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    if not state.get("cansetccdtemperature", True):
        raise AlpacaError(0x401, "Camera does not support temperature control")

    update_device_state("camera", device_number, {"setccdtemperature": SetCCDTemperature})

    update_device_state("camera", device_number, {"ccdtemperature": SetCCDTemperature})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/cooleron", response_model=BoolResponse)
def get_cooleron(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("cooleron", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/cooleron", response_model=AlpacaResponse)
def set_cooleron(
    device_number: int = Path(..., ge=0),
    CoolerOn: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    # state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    if not state.get("cansetccdtemperature", True):
        raise AlpacaError(0x401, "Camera does not support temperature control")

    update_device_state("camera", device_number, {"cooleron": CoolerOn})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/coolerpower", response_model=DoubleResponse)
def get_coolerpower(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("coolerpower", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Gain control
@router.get("/camera/{device_number}/gain", response_model=DoubleResponse)
def get_gain(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("gain", 1.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/gain", response_model=AlpacaResponse)
def set_gain(
    device_number: int = Path(..., ge=0),
    Gain: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    # state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    min_gain = state.get("gainmin", 0.1)
    max_gain = state.get("gainmax", 10.0)

    if Gain < min_gain or Gain > max_gain:
        raise AlpacaError(0x402, f"Gain out of range ({min_gain} to {max_gain})")

    update_device_state("camera", device_number, {"gain": Gain})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/gainmax", response_model=DoubleResponse)
def get_gainmax(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("gainmax", 10.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/gainmin", response_model=DoubleResponse)
def get_gainmin(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("gainmin", 0.1),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/gains", response_model=StringArrayResponse)
def get_gains(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return StringArrayResponse(
        Value=state.get("gains", ["Low", "Medium", "High"]),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Offset control
@router.get("/camera/{device_number}/offset", response_model=DoubleResponse)
def get_offset(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("offset", 0.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/offset", response_model=AlpacaResponse)
def set_offset(
    device_number: int = Path(..., ge=0),
    Offset: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    # state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    min_offset = state.get("offsetmin", -1000.0)
    max_offset = state.get("offsetmax", 1000.0)

    if Offset < min_offset or Offset > max_offset:
        raise AlpacaError(0x402, f"Offset out of range ({min_offset} to {max_offset})")

    update_device_state("camera", device_number, {"offset": Offset})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/offsetmax", response_model=DoubleResponse)
def get_offsetmax(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("offsetmax", 1000.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/offsetmin", response_model=DoubleResponse)
def get_offsetmin(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("offsetmin", -1000.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/offsets", response_model=StringArrayResponse)
def get_offsets(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return StringArrayResponse(
        Value=state.get("offsets", ["Low", "Medium", "High"]),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Subframe control
@router.get("/camera/{device_number}/numx", response_model=IntResponse)
def get_numx(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("numx", state.get("cameraxsize", 1024)),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/numx", response_model=AlpacaResponse)
def set_numx(
    device_number: int = Path(..., ge=0),
    NumX: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    max_x = state.get("cameraxsize", 1024)
    startx = state.get("startx", 0)

    if NumX < 1 or (startx + NumX) > max_x:
        raise AlpacaError(0x402, f"NumX out of range (1 to {max_x - startx})")

    update_device_state("camera", device_number, {"numx": NumX})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/numy", response_model=IntResponse)
def get_numy(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("numy", state.get("cameraysize", 1024)),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/numy", response_model=AlpacaResponse)
def set_numy(
    device_number: int = Path(..., ge=0),
    NumY: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    max_y = state.get("cameraysize", 1024)
    starty = state.get("starty", 0)

    if NumY < 1 or (starty + NumY) > max_y:
        raise AlpacaError(0x402, f"NumY out of range (1 to {max_y - starty})")

    update_device_state("camera", device_number, {"numy": NumY})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/startx", response_model=IntResponse)
def get_startx(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("startx", 0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/startx", response_model=AlpacaResponse)
def set_startx(
    device_number: int = Path(..., ge=0),
    StartX: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    max_x = state.get("cameraxsize", 1024)
    numx = state.get("numx", max_x)

    if StartX < 0 or (StartX + numx) > max_x:
        raise AlpacaError(0x402, f"StartX out of range (0 to {max_x - numx})")

    update_device_state("camera", device_number, {"startx": StartX})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/starty", response_model=IntResponse)
def get_starty(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=state.get("starty", 0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/starty", response_model=AlpacaResponse)
def set_starty(
    device_number: int = Path(..., ge=0),
    StartY: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    max_y = state.get("cameraysize", 1024)
    numy = state.get("numy", max_y)

    if StartY < 0 or (StartY + numy) > max_y:
        raise AlpacaError(0x402, f"StartY out of range (0 to {max_y - numy})")

    update_device_state("camera", device_number, {"starty": StartY})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Fast readout mode
@router.get("/camera/{device_number}/fastreadout", response_model=BoolResponse)
def get_fastreadout(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("fastreadout", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/fastreadout", response_model=AlpacaResponse)
def set_fastreadout(
    device_number: int = Path(..., ge=0),
    FastReadout: bool = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    # state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    if not state.get("canfastreadout", True):
        raise AlpacaError(0x401, "Camera does not support fast readout mode")

    update_device_state("camera", device_number, {"fastreadout": FastReadout})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Heat sink temperature
@router.get("/camera/{device_number}/heatsinktemperature", response_model=DoubleResponse)
def get_heatsinktemperature(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    # Simulate heat sink temperature (usually a bit warmer than CCD)
    ccd_temp = state.get("ccdtemperature", 20.0)
    return DoubleResponse(
        Value=ccd_temp + 5.0,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Pulse guiding
@router.get("/camera/{device_number}/ispulseguiding", response_model=BoolResponse)
def get_ispulseguiding(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return BoolResponse(
        Value=state.get("ispulseguiding", False),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/pulseguide", response_model=AlpacaResponse)
def pulseguide(
    device_number: int = Path(..., ge=0),
    Direction: int = Form(...),
    Duration: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    # state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    state = get_device_state("camera", device_number)
    if not state.get("canpulseguide", True):
        raise AlpacaError(0x401, "Camera does not support pulse guiding")

    if Direction not in [
        GuideDirections.NORTH,
        GuideDirections.SOUTH,
        GuideDirections.EAST,
        GuideDirections.WEST,
    ]:
        raise AlpacaError(0x402, "Invalid guide direction")

    if Duration < 0:
        raise AlpacaError(0x402, "Duration must be positive")

    # Simulate pulse guiding
    update_device_state("camera", device_number, {"ispulseguiding": True})

    # In a real implementation, this would start a timer
    # For simulation, we immediately stop pulse guiding
    update_device_state("camera", device_number, {"ispulseguiding": False})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Sub-exposure duration
@router.get("/camera/{device_number}/subexposureduration", response_model=DoubleResponse)
def get_subexposureduration(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return DoubleResponse(
        Value=state.get("subexposureduration", 1.0),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/subexposureduration", response_model=AlpacaResponse)
def set_subexposureduration(
    device_number: int = Path(..., ge=0),
    SubExposureDuration: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    # state = get_device_state("camera", device_number)

    # if not state.get("connected"):
    # raise AlpacaError(0x407, "Device is not connected")

    if SubExposureDuration <= 0:
        raise AlpacaError(0x402, "Sub-exposure duration must be positive")

    update_device_state("camera", device_number, {"subexposureduration": SubExposureDuration})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Deprecated endpoint for compatibility
@router.get("/camera/{device_number}/imagearrayvariant", response_model=ImageArrayResponse)
def get_imagearrayvariant(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    """Deprecated - use imagearray instead"""
    return get_imagearray(device_number, ClientTransactionID)
