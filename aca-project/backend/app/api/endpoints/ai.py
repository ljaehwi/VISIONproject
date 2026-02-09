from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_core.anomaly import train_async
from app.api.schemas import AnalyzeBody, AnalyzeResponse
from app.db.session import get_session
from app.services.pipeline import analyze_raw_image


router = APIRouter()


class TrainBody(BaseModel):
    epochs: int = 5
    lr: float = 1e-3


@router.post('/ai/train')
async def ai_train(body: TrainBody):
    result = await train_async(epochs=body.epochs, lr=body.lr)
    return result


@router.post('/ai/analyze', response_model=AnalyzeResponse)
async def ai_analyze(body: AnalyzeBody, session: AsyncSession = Depends(get_session)):
    result = await analyze_raw_image(session=session, raw_image_id=body.raw_image_id)
    if not result.get('found'):
        return AnalyzeResponse(is_anomaly=False, score=0.0, heatmap_url=None, recon_url=None)
    return AnalyzeResponse(
        is_anomaly=result['is_anomaly'],
        score=result['score'],
        heatmap_url=result.get('heatmap_url'),
        recon_url=result.get('recon_url'),
    )
