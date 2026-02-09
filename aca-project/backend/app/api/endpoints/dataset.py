from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DatasetImageItem, SaveDatasetBody, SaveDatasetResponse
from app.db.models import DatasetImage, DatasetSplit, SavedImage
from app.db.session import get_session
from app.services.vision_engine import VisionEngine


router = APIRouter()


@router.get('/dataset/images', response_model=list[DatasetImageItem])
async def list_dataset_images(
    item: str | None = Query(default=None),
    split: DatasetSplit | None = Query(default=None),
    defect_type: str | None = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(DatasetImage)
    if item:
        stmt = stmt.where(DatasetImage.item == item)
    if split:
        stmt = stmt.where(DatasetImage.split == split)
    if defect_type:
        stmt = stmt.where(DatasetImage.defect_type == defect_type)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        DatasetImageItem(
            id=r.id,
            item=r.item,
            split=r.split.value,
            defect_type=r.defect_type,
            file_url=f"/dataset/image/{r.id}",
            is_mask=r.is_mask,
        )
        for r in rows
    ]


@router.get('/dataset/image/{image_id}')
async def get_dataset_image(image_id: int, session: AsyncSession = Depends(get_session)):
    row = await session.get(DatasetImage, image_id)
    if row is None:
        raise HTTPException(status_code=404, detail='not found')
    return FileResponse(row.file_path)


@router.get('/dataset/filters')
async def get_dataset_filters(session: AsyncSession = Depends(get_session)):
    items = (await session.execute(select(distinct(DatasetImage.item)))).scalars().all()
    splits = (await session.execute(select(distinct(DatasetImage.split)))).scalars().all()
    defects = (await session.execute(select(distinct(DatasetImage.defect_type)))).scalars().all()
    return {
        'items': sorted([i for i in items if i]),
        'splits': sorted([s.value if hasattr(s, 'value') else s for s in splits]),
        'defect_types': sorted([d for d in defects if d]),
    }


@router.post('/dataset/save', response_model=SaveDatasetResponse)
async def save_dataset_image(body: SaveDatasetBody, session: AsyncSession = Depends(get_session)):
    row = await session.get(DatasetImage, body.dataset_image_id)
    if row is None:
        raise HTTPException(status_code=404, detail='not found')

    import cv2
    import numpy as np
    from datetime import datetime
    from pathlib import Path

    img = cv2.imread(row.file_path, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail='image load failed')

    gain = float(body.gain)
    black_level = float(body.black_level)
    adjusted = img.astype(np.float32) * (1.0 + gain / 24.0) + black_level
    adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)

    out_dir = Path('app/static/saved')
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    out_path = out_dir / f'saved_{row.id}_{ts}.png'
    cv2.imwrite(str(out_path), adjusted)

    gv_mean = VisionEngine().calc_gv(adjusted)
    async with session.begin():
        saved = SavedImage(
            dataset_image_id=row.id,
            file_path=str(out_path),
            gain=gain,
            black_level=black_level,
            gv_mean=float(gv_mean),
            is_auto_calibration=body.is_auto_calibration,
            note=body.note,
        )
        session.add(saved)

    await session.refresh(saved)

    image_url = f"/static/saved/{out_path.name}"
    return SaveDatasetResponse(saved_image_id=saved.id, image_url=image_url, gv_mean=float(gv_mean))
