from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.camera_driver import get_camera


router = APIRouter()


@router.get('/health/system')
async def health_system(session: AsyncSession = Depends(get_session)):
    await session.execute(text('SELECT 1'))
    return {'status': 'ok', 'db': 'ok'}


@router.get('/health/camera')
async def health_camera():
    camera = get_camera()
    return {'status': 'ok', 'camera': camera.get_status()}
