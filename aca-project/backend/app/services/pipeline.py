from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles

from app.ai_core.anomaly import analyze_async
from app.core.config import settings
from app.db.models import InspectionResult, RawImage, RawImageStatus
from app.services.vision_engine import VisionEngine


async def ingest_image(session, file_bytes: bytes, filename: str, lot_number: str | None = None) -> dict[str, Any]:
    timestamp = datetime.utcnow()
    image_dir = Path(settings.static_dir) / settings.image_subdir
    image_dir.mkdir(parents=True, exist_ok=True)

    safe_name = filename.replace('..', '').replace('/', '').replace('\\', '')
    out_name = f'upload_{timestamp.strftime("%Y%m%d_%H%M%S_%f")}_{safe_name}'
    file_path = image_dir / out_name

    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_bytes)

    engine = VisionEngine()
    gv_mean = await engine.calc_gv_from_path(str(file_path))

    async with session.begin():
        raw = RawImage(
            lot_number=lot_number,
            timestamp=timestamp,
            file_path=str(file_path),
            status=RawImageStatus.PENDING,
        )
        session.add(raw)

    await session.refresh(raw)

    image_url = f"{settings.static_url}/{settings.image_subdir}/{out_name}"
    return {
        'raw_image_id': raw.id,
        'image_url': image_url,
        'gv_mean': float(gv_mean),
        'timestamp': timestamp.isoformat(),
    }


async def analyze_raw_image(session, raw_image_id: int, threshold: float = 0.01) -> dict[str, Any]:
    raw = await session.get(RawImage, raw_image_id)
    if raw is None:
        return {'found': False}

    result = await analyze_async(raw.file_path, threshold=threshold)

    async with session.begin():
        inspection = InspectionResult(
            raw_image_id=raw.id,
            is_anomaly=result.is_anomaly,
            anomaly_score=result.score,
            verdict='NG' if result.is_anomaly else 'OK',
        )
        session.add(inspection)
        raw.status = RawImageStatus.PROCESSED

    heatmap_url = None
    recon_url = None
    if result.heatmap_path:
        heatmap_url = result.heatmap_path.replace(settings.static_dir, settings.static_url).replace('\\', '/')
    if result.recon_path:
        recon_url = result.recon_path.replace(settings.static_dir, settings.static_url).replace('\\', '/')

    return {
        'found': True,
        'raw_image_id': raw.id,
        'inspection_id': inspection.id,
        'is_anomaly': result.is_anomaly,
        'score': result.score,
        'heatmap_url': heatmap_url,
        'recon_url': recon_url,
    }
