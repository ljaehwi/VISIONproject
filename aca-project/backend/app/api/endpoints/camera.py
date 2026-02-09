from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import CameraParams, CaptureResponse, SimulationModeBody
from app.db.session import get_session
from app.services.camera_driver import get_camera


router = APIRouter()


@router.get('/camera/capture', response_model=CaptureResponse)
async def camera_capture(session: AsyncSession = Depends(get_session)):
    camera = get_camera()
    image_url, metadata = await camera.capture(session=session)
    return {'image_url': image_url, 'metadata': metadata}


@router.post('/camera/parameters')
async def camera_parameters(body: CameraParams):
    camera = get_camera()
    camera.set_parameters(gain=body.gain, black_level=body.black_level)
    return {'gain': camera.gain, 'black_level': camera.black_level}


@router.post('/camera/simulation')
async def camera_simulation(body: SimulationModeBody):
    camera = get_camera()
    camera.set_mode(body.mode)
    return {'mode': camera.simulation_mode}
