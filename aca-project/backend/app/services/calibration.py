from __future__ import annotations

import asyncio
import logging

from app.services.camera_driver import get_camera
from app.services.vision_engine import VisionEngine


logger = logging.getLogger('aca.calibration')


class CalibrationAgent:
    def __init__(self) -> None:
        self.camera = get_camera()
        self.engine = VisionEngine()

    async def run_auto_calibration(self, session, target_gv: float, tolerance: float, max_iterations: int) -> dict:
        current_gv = 0.0
        initial_gv = None
        last_meta = None
        last_image_url = None

        for step in range(1, max_iterations + 1):
            last_image_url, last_meta = await self.camera.capture(session=session)
            current_gv = float(last_meta['gv_mean'])
            if initial_gv is None:
                initial_gv = current_gv

            error = target_gv - current_gv
            logger.info('calibration_step', extra={'step': step, 'current_gv': current_gv, 'target_gv': target_gv})

            if abs(error) <= tolerance:
                await self._record_log(
                    session=session,
                    meta=last_meta,
                    initial_gv=initial_gv,
                    target_gv=target_gv,
                    final_gv=current_gv,
                    converged=True,
                )
                return {
                    'status': 'CONVERGED',
                    'step': step,
                    'current_gv': current_gv,
                    'target_gv': target_gv,
                    'image_url': last_image_url,
                }

            self.camera.set_parameters(
                gain=self.camera.gain + 0.1 * error,
                black_level=self.camera.black_level + int(0.05 * error),
            )

        await self._record_log(
            session=session,
            meta=last_meta,
            initial_gv=initial_gv or current_gv,
            target_gv=target_gv,
            final_gv=current_gv,
            converged=False,
        )
        return {
            'status': 'FAILED',
            'step': max_iterations,
            'current_gv': current_gv,
            'target_gv': target_gv,
            'image_url': last_image_url,
        }

    async def stream_to_websocket(self, websocket, target_gv: float, tolerance: float, max_iterations: int):
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            for step in range(1, max_iterations + 1):
                image_url, meta = await self.camera.capture(session=session)
                current_gv = float(meta['gv_mean'])
                error = target_gv - current_gv
                status = 'ADJUSTING'

                if abs(error) <= tolerance:
                    status = 'CONVERGED'

                await websocket.send_json({
                    'step': step,
                    'current_gv': current_gv,
                    'target_gv': target_gv,
                    'applied_gain': self.camera.gain,
                    'applied_black_level': self.camera.black_level,
                    'status': status,
                    'message': 'calibrating' if status == 'ADJUSTING' else 'done',
                    'image_url': image_url,
                    'raw_image_id': meta.get('raw_image_id'),
                    'inspection_id': None,
                })

                logger.info('calibration_stream', extra={'step': step, 'status': status})

                if status == 'CONVERGED':
                    await self._record_log(
                        session=session,
                        meta=meta,
                        initial_gv=current_gv,
                        target_gv=target_gv,
                        final_gv=current_gv,
                        converged=True,
                    )
                    break

                if step == max_iterations:
                    await websocket.send_json({
                        'step': step,
                        'current_gv': current_gv,
                        'target_gv': target_gv,
                        'applied_gain': self.camera.gain,
                        'applied_black_level': self.camera.black_level,
                        'status': 'FAILED',
                        'message': 'max iterations reached',
                        'image_url': image_url,
                        'raw_image_id': meta.get('raw_image_id'),
                        'inspection_id': None,
                    })
                    await self._record_log(
                        session=session,
                        meta=meta,
                        initial_gv=current_gv,
                        target_gv=target_gv,
                        final_gv=current_gv,
                        converged=False,
                    )
                    break

                self.camera.set_parameters(
                    gain=self.camera.gain + 0.1 * error,
                    black_level=self.camera.black_level + int(0.05 * error),
                )
                await asyncio.sleep(0.2)

    async def _record_log(self, session, meta, initial_gv, target_gv, final_gv, converged: bool) -> None:
        from app.db.models import CalibrationLog, InspectionResult

        async with session.begin():
            inspection = InspectionResult(
                raw_image_id=meta['raw_image_id'],
                is_anomaly=False,
                anomaly_score=0.0,
                verdict='OK',
            )
            session.add(inspection)

        await session.refresh(inspection)

        async with session.begin():
            log = CalibrationLog(
                inspection_id=inspection.id,
                initial_gv=float(initial_gv),
                target_gv=float(target_gv),
                final_gv=float(final_gv),
                gain_applied=float(self.camera.gain),
                black_level_applied=float(self.camera.black_level),
                converged=converged,
            )
            session.add(log)
