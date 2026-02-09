from __future__ import annotations

import numpy as np


class VisionEngine:
    def calc_gv(self, image: np.ndarray) -> float:
        gray = image.mean(axis=2)
        return float(gray.mean())

    def histogram(self, image: np.ndarray) -> list[int]:
        gray = image.mean(axis=2).astype(np.uint8)
        hist, _ = np.histogram(gray, bins=256, range=(0, 255))
        return hist.tolist()

    async def calc_gv_from_path(self, path: str) -> float:
        import cv2

        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            return 0.0
        return self.calc_gv(img)
