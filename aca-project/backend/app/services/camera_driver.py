from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple

import aiofiles
import numpy as np

from app.api.schemas import SimulationMode
from app.core.config import settings
from app.services.vision_engine import VisionEngine


logger = logging.getLogger('aca.camera')


class VirtualCamera:
    def __init__(self) -> None:
        self.gain = 8.0
        self.black_level = 10
        self.engine = VisionEngine()
        self.capture_count = 0
        self.simulation_mode = SimulationMode.CLEAN

    def get_status(self) -> str:
        return 'online'

    def get_parameters(self) -> dict[str, Any]:
        return {'gain': self.gain, 'black_level': self.black_level}

    def set_parameters(self, gain: float, black_level: int) -> None:
        self.gain = float(max(0.0, min(24.0, gain)))
        self.black_level = int(max(0, min(255, black_level)))

    def set_mode(self, mode: SimulationMode) -> None:
        self.simulation_mode = mode

    async def capture(self, session, lot_number: str | None = None) -> Tuple[str, dict[str, Any]]:
        self.capture_count += 1
        image = self._generate_image()
        image = self._apply_simulation(image)
        gv_mean = float(self.engine.calc_gv(image))
        timestamp = datetime.utcnow()

        image_dir = Path(settings.static_dir) / settings.image_subdir
        image_dir.mkdir(parents=True, exist_ok=True)
        filename = f'img_{timestamp.strftime("%Y%m%d_%H%M%S_%f")}.png'
        file_path = image_dir / filename

        import cv2

        _, png = cv2.imencode('.png', image)
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(png.tobytes())

        from app.db.models import RawImage

        async with session.begin():
            raw = RawImage(
                lot_number=lot_number,
                timestamp=timestamp,
                file_path=str(file_path),
            )
            session.add(raw)

        await session.refresh(raw)

        image_url = f"{settings.static_url}/{settings.image_subdir}/{filename}"
        metadata = {
            'gain': self.gain,
            'black_level': float(self.black_level),
            'gv_mean': gv_mean,
            'timestamp': timestamp.isoformat(),
            'raw_image_id': raw.id,
            'capture_count': self.capture_count,
            'simulation_mode': self.simulation_mode,
        }
        logger.info('capture', extra={'metadata': metadata})
        return image_url, metadata

    def _generate_image(self) -> np.ndarray:
        base = np.full((480, 640), 90, dtype=np.float32)
        gradient = np.tile(np.linspace(0, 40, 640, dtype=np.float32), (480, 1))
        img = base + gradient

        img = img * (1.0 + self.gain / 24.0) + self.black_level
        img = np.clip(img, 0, 255).astype(np.uint8)
        img = np.stack([img, img, img], axis=-1)
        return img

    def _apply_simulation(self, image: np.ndarray) -> np.ndarray:
        if self.simulation_mode == SimulationMode.CLEAN:
            return self._add_gaussian_noise(image, sigma=5.0)
        if self.simulation_mode == SimulationMode.OPTICAL_NOISE:
            img = self._add_vignetting(image, intensity=0.4)
            img = self._add_blur(img, ksize=5)
            img = self._add_gaussian_noise(img, sigma=10.0)
            return img
        if self.simulation_mode == SimulationMode.DEFECTIVE:
            img = self._add_vignetting(image, intensity=0.4)
            img = self._add_gaussian_noise(img, sigma=12.0)
            img = self._add_synthetic_defect(img)
            return img
        return image

    def _add_vignetting(self, image: np.ndarray, intensity: float) -> np.ndarray:
        rows, cols = image.shape[:2]
        x = np.linspace(-1, 1, cols)
        y = np.linspace(-1, 1, rows)
        xv, yv = np.meshgrid(x, y)
        mask = 1 - intensity * (xv**2 + yv**2)
        mask = np.clip(mask, 0.3, 1.0)
        out = image.astype(np.float32) * mask[..., None]
        return np.clip(out, 0, 255).astype(np.uint8)

    def _add_gaussian_noise(self, image: np.ndarray, sigma: float) -> np.ndarray:
        noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
        out = image.astype(np.float32) + noise
        return np.clip(out, 0, 255).astype(np.uint8)

    def _add_blur(self, image: np.ndarray, ksize: int) -> np.ndarray:
        import cv2

        k = max(3, ksize | 1)
        return cv2.GaussianBlur(image, (k, k), 0)

    def _add_synthetic_defect(self, image: np.ndarray) -> np.ndarray:
        import cv2

        out = image.copy()
        h, w = out.shape[:2]
        for _ in range(6):
            x1 = np.random.randint(0, w)
            y1 = np.random.randint(0, h)
            x2 = np.random.randint(0, w)
            y2 = np.random.randint(0, h)
            cv2.line(out, (x1, y1), (x2, y2), (255, 255, 255), 1)
        for _ in range(12):
            cx = np.random.randint(0, w)
            cy = np.random.randint(0, h)
            r = np.random.randint(2, 6)
            cv2.circle(out, (cx, cy), r, (0, 0, 0), -1)
        return out


_camera: VirtualCamera | None = None


def get_camera() -> VirtualCamera:
    global _camera
    if _camera is None:
        _camera = VirtualCamera()
    return _camera
