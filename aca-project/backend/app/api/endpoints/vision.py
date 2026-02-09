from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AutoCalibrateBody, AutoCalibrateResponse
from app.db.session import get_session
from app.services.calibration import CalibrationAgent


router = APIRouter()


@router.post('/process/auto-calibrate', response_model=AutoCalibrateResponse)
async def auto_calibrate(body: AutoCalibrateBody, session: AsyncSession = Depends(get_session)):
    agent = CalibrationAgent()
    result = await agent.run_auto_calibration(
        session=session,
        target_gv=body.target_gv,
        tolerance=body.tolerance or 2.0,
        max_iterations=body.max_iterations or 20,
    )
    return result


@router.websocket('/ws/calibration')
async def ws_calibration(websocket: WebSocket):
    await websocket.accept()
    agent = CalibrationAgent()
    try:
        init = await websocket.receive_json()
        target_gv = float(init.get('target_gv', 140.0))
        tolerance = float(init.get('tolerance', 2.0))
        max_iterations = int(init.get('max_iterations', 20))
        await agent.stream_to_websocket(
            websocket=websocket,
            target_gv=target_gv,
            tolerance=tolerance,
            max_iterations=max_iterations,
        )
    except WebSocketDisconnect:
        return
