from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.pipeline import analyze_raw_image, ingest_image


router = APIRouter()


class AnalyzePipelineBody(BaseModel):
    raw_image_id: int
    threshold: float | None = 0.01


@router.post('/pipeline/ingest')
async def pipeline_ingest(
    file: UploadFile = File(...),
    lot_number: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
):
    data = await file.read()
    result = await ingest_image(session=session, file_bytes=data, filename=file.filename or 'upload.png', lot_number=lot_number)
    return result


@router.post('/pipeline/analyze')
async def pipeline_analyze(body: AnalyzePipelineBody, session: AsyncSession = Depends(get_session)):
    result = await analyze_raw_image(session=session, raw_image_id=body.raw_image_id, threshold=body.threshold or 0.01)
    return result
