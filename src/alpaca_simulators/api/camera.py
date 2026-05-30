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


def make_cache_key(
    ra,
    dec,
    duration,
    light,
    focus,
    sunlight,
    tracking_ra_rate,
    tracking_dec_rate,
    numx,
    numy,
    binx,
    biny,
):
    return (
        f"{ra}_{dec}_{duration}_{light}_{focus}_{sunlight}_"
        f"{tracking_ra_rate}_{tracking_dec_rate}_{numx}x{numy}_b{binx}x{biny}"
    )


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
            width=cam_state.get("numx") * cam_state.get("binx", 1),
            height=cam_state.get("numy") * cam_state.get("biny", 1),
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
            # drift RA/Dec based on time since last slew
            time_elapsed = (datetime.now(timezone.utc) - last_slew_time).total_seconds()
            ra += time_elapsed * (bad_tracking_rate / 3600) / 15  # convert to hours
            dec += time_elapsed * bad_tracking_rate / 3600

        # Convert ASCOM tracking rates to arcseconds per second for cabaret.
        # RightAscensionRate and DeclinationRate are ASCOM offsets from sidereal tracking.
        # The pointing coordinates (ra/dec) already account for sidereal drift via
        # _advance_telescope_motion in telescope.py, so only the rate offsets are passed
        # here to simulate trailing from non-sidereal tracking.
        # rightascensionrate is RA-seconds/sidereal-second; × 15 converts to arcsec/s.
        # declinationrate is already arcseconds/sidereal-second ≈ arcsec/s.
        # MoveAxis rates are in deg/s; × 3600 converts to arcsec/s.
        tracking_ra_rate = (
            tel_state.get("rightascensionrate", 0.0) * 15.0
            + tel_state.get("moveaxis_primary_rate", 0.0) * 3600.0
        )
        tracking_dec_rate = (
            tel_state.get("declinationrate", 0.0)
            + tel_state.get("moveaxis_secondary_rate", 0.0) * 3600.0
        )

        # Generate star field image
        key = make_cache_key(
            ra,
            dec,
            duration,
            light,
            focuser_state.get("position", 0),
            sunlight=sunlight,
            tracking_ra_rate=tracking_ra_rate,
            tracking_dec_rate=tracking_dec_rate,
            numx=cam_state.get("numx"),
            numy=cam_state.get("numy"),
            binx=cam_state.get("binx", 1),
            biny=cam_state.get("biny", 1),
        )
        if key in image_cache:
            print(f"Using cached image for key: {key}")
            image_data = image_cache[key]
        else:
            print(f"Generating new image for key: {key}")
            image_data = cabaret_observatory.generate_image(
                ra=(ra / 24) * 360,
                dec=dec,
                exp_time=duration,
                light=1 if light else 0,
                timeout=Config().load().get("gaia_query_timeout", 30),
                tracking_ra_rate=tracking_ra_rate,
                tracking_dec_rate=tracking_dec_rate,
                tap_source=Config().load().get("tap_source", None),
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
            0x401,
            f"Exposure duration too short (minimum: {state.get('exposuremin', 0.001)}s)",
        )

    if Duration > state.get("exposuremax", 3600.0):
        raise AlpacaError(
            0x401,
            f"Exposure duration too long (maximum: {state.get('exposuremax', 3600.0)}s)",
        )

    # Validate the subframe in binned pixels (NumX/NumY/StartX/StartY are binned).
    binx = state.get("binx", 1)
    biny = state.get("biny", 1)
    max_binned_x = state.get("cameraxsize", 1024) // binx
    max_binned_y = state.get("cameraysize", 1024) // biny
    numx = state.get("numx", max_binned_x)
    numy = state.get("numy", max_binned_y)
    startx = state.get("startx", 0)
    starty = state.get("starty", 0)
    if numx < 1 or startx < 0 or startx + numx > max_binned_x:
        raise AlpacaError(
            0x401,
            f"Subframe X out of range: StartX={startx}, NumX={numx}, max={max_binned_x}",
        )
    if numy < 1 or starty < 0 or starty + numy > max_binned_y:
        raise AlpacaError(
            0x401,
            f"Subframe Y out of range: StartY={starty}, NumY={numy}, max={max_binned_y}",
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
    if not state.get("exposure_start_time"):
        raise AlpacaError(0x40B, "No exposure has been taken")
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
    start_time = state.get("exposure_start_time")
    if not start_time:
        raise AlpacaError(0x40B, "No exposure has been taken")
    return StringResponse(
        Value=str(start_time),
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
        raise AlpacaError(0x400, "Camera does not support temperature control")

    if SetCCDTemperature <= -273.15 or SetCCDTemperature >= 100.0:
        raise AlpacaError(
            0x401,
            f"SetCCDTemperature {SetCCDTemperature} out of range (-273.15, 100.0)",
        )

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
# This camera operates in "Gains" list mode: Gain returns the integer index into
# the Gains list, and GainMin/GainMax must return PropertyNotImplemented because
# the two modes (Gains list vs. numeric min/max) are mutually exclusive in ASCOM.
@router.get("/camera/{device_number}/gain", response_model=IntResponse)
def get_gain(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=int(state.get("gain", 0)),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/gain", response_model=AlpacaResponse)
def set_gain(
    device_number: int = Path(..., ge=0),
    Gain: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)

    state = get_device_state("camera", device_number)
    gains = state.get("gains", [])
    if Gain < 0 or Gain >= len(gains):
        raise AlpacaError(0x401, f"Gain index out of range (0 to {len(gains) - 1})")

    update_device_state("camera", device_number, {"gain": Gain + 1})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/gainmax", response_model=IntResponse)
def get_gainmax(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    raise AlpacaError(0x400, "GainMax not implemented when Gains list is provided")


@router.get("/camera/{device_number}/gainmin", response_model=IntResponse)
def get_gainmin(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    raise AlpacaError(0x400, "GainMin not implemented when Gains list is provided")


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
# This camera operates in "Offsets" list mode: Offset returns the integer index
# into the Offsets list, and OffsetMin/OffsetMax must return PropertyNotImplemented
# because the two modes are mutually exclusive in ASCOM.
@router.get("/camera/{device_number}/offset", response_model=IntResponse)
def get_offset(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    state = get_device_state("camera", device_number)
    return IntResponse(
        Value=int(state.get("offset", 0)),
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.put("/camera/{device_number}/offset", response_model=AlpacaResponse)
def set_offset(
    device_number: int = Path(..., ge=0),
    Offset: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)

    state = get_device_state("camera", device_number)
    offsets = state.get("offsets", [])
    if Offset < 0 or Offset >= len(offsets):
        raise AlpacaError(0x401, f"Offset index out of range (0 to {len(offsets) - 1})")

    update_device_state("camera", device_number, {"offset": Offset})

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


@router.get("/camera/{device_number}/offsetmax", response_model=IntResponse)
def get_offsetmax(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    raise AlpacaError(0x400, "OffsetMax not implemented when Offsets list is provided")


@router.get("/camera/{device_number}/offsetmin", response_model=IntResponse)
def get_offsetmin(device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)):
    validate_device("camera", device_number)
    raise AlpacaError(0x400, "OffsetMin not implemented when Offsets list is provided")


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

    # Permissive setter: the combined subframe geometry is validated in
    # StartExposure. Only obvious garbage is rejected here. ConformU expects to
    # be able to write out-of-range values to test that StartExposure rejects
    # them.
    if NumX < 1:
        raise AlpacaError(0x401, f"NumX must be >= 1, got {NumX}")

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

    if NumY < 1:
        raise AlpacaError(0x401, f"NumY must be >= 1, got {NumY}")

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

    if StartX < 0:
        raise AlpacaError(0x401, f"StartX must be >= 0, got {StartX}")

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

    if StartY < 0:
        raise AlpacaError(0x401, f"StartY must be >= 0, got {StartY}")

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
    if not state.get("canfastreadout", False):
        raise AlpacaError(0x400, "Camera does not support fast readout mode")
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

    state = get_device_state("camera", device_number)
    if not state.get("canfastreadout", False):
        raise AlpacaError(0x400, "Camera does not support fast readout mode")

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


async def _pulseguide_task(device_number: int, duration_ms: int):
    """Hold IsPulseGuiding=True for the requested duration, then clear it."""
    try:
        await asyncio.sleep(duration_ms / 1000.0)
    finally:
        update_device_state("camera", device_number, {"ispulseguiding": False})


@router.put("/camera/{device_number}/pulseguide", response_model=AlpacaResponse)
def pulseguide(
    background_tasks: BackgroundTasks,
    device_number: int = Path(..., ge=0),
    Direction: int = Form(...),
    Duration: int = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)

    state = get_device_state("camera", device_number)
    if not state.get("canpulseguide", True):
        raise AlpacaError(0x400, "Camera does not support pulse guiding")

    if Direction not in [
        GuideDirections.NORTH,
        GuideDirections.SOUTH,
        GuideDirections.EAST,
        GuideDirections.WEST,
    ]:
        raise AlpacaError(0x401, "Invalid guide direction")

    if Duration < 0:
        raise AlpacaError(0x401, "Duration must be positive")

    update_device_state("camera", device_number, {"ispulseguiding": True})
    background_tasks.add_task(_pulseguide_task, device_number, Duration)

    return AlpacaResponse(
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=get_server_transaction_id(),
    )


# Sub-exposure duration
# This simulator does not support sub-exposure stacking, so both get and set
# return PropertyNotImplemented per ASCOM convention.
@router.get("/camera/{device_number}/subexposureduration", response_model=DoubleResponse)
def get_subexposureduration(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    validate_device("camera", device_number)
    raise AlpacaError(0x400, "SubExposureDuration is not implemented")


@router.put("/camera/{device_number}/subexposureduration", response_model=AlpacaResponse)
def set_subexposureduration(
    device_number: int = Path(..., ge=0),
    SubExposureDuration: float = Form(...),
    ClientTransactionID: int = Form(0),
):
    validate_device("camera", device_number)
    raise AlpacaError(0x400, "SubExposureDuration is not implemented")


# Deprecated endpoint for compatibility
@router.get("/camera/{device_number}/imagearrayvariant", response_model=ImageArrayResponse)
def get_imagearrayvariant(
    device_number: int = Path(..., ge=0), ClientTransactionID: int = Query(0)
):
    """Deprecated - use imagearray instead"""
    return get_imagearray(device_number, ClientTransactionID)
