from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
import torch.nn as nn
from PIL import Image

from app.ai_core.model import ConvAutoencoder, load_model, save_model
from app.core.config import settings


@dataclass
class AnalyzeResult:
    is_anomaly: bool
    score: float
    heatmap_path: str | None
    recon_path: str | None


def _load_image_grayscale(path: str, size: tuple[int, int] = (256, 256)) -> torch.Tensor:
    img = Image.open(path).convert('L').resize(size)
    arr = np.array(img, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0)
    return tensor


def _save_image(tensor: torch.Tensor, path: Path) -> None:
    arr = tensor.squeeze(0).squeeze(0).clamp(0, 1).mul(255).byte().cpu().numpy()
    Image.fromarray(arr, mode='L').save(path)


def _save_heatmap(diff: torch.Tensor, path: Path) -> None:
    arr = diff.squeeze(0).squeeze(0).clamp(0, 1).mul(255).byte().cpu().numpy()
    Image.fromarray(arr, mode='L').save(path)


def _image_paths_from_static() -> list[str]:
    img_dir = Path(settings.static_dir) / settings.image_subdir
    if not img_dir.exists():
        return []
    return [str(p) for p in img_dir.glob('*.png')]


def train_from_static(epochs: int = 5, lr: float = 1e-3) -> dict:
    device = torch.device('cpu')
    model: ConvAutoencoder = load_model(device=device)
    model.train()

    paths = _image_paths_from_static()
    if not paths:
        return {'trained': False, 'reason': 'no_images'}

    optim = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    for _ in range(epochs):
        for p in paths:
            x = _load_image_grayscale(p).to(device)
            optim.zero_grad()
            recon = model(x)
            loss = loss_fn(recon, x)
            loss.backward()
            optim.step()

    save_model(model)
    return {'trained': True, 'count': len(paths)}


def analyze_image(path: str, threshold: float = 0.01) -> AnalyzeResult:
    device = torch.device('cpu')
    model = load_model(device=device)

    x = _load_image_grayscale(path).to(device)
    with torch.no_grad():
        recon = model(x)

    mse = torch.mean((recon - x) ** 2).item()
    diff = (recon - x).abs()

    heat_dir = Path(settings.static_dir) / 'heatmaps'
    recon_dir = Path(settings.static_dir) / 'recon'
    heat_dir.mkdir(parents=True, exist_ok=True)
    recon_dir.mkdir(parents=True, exist_ok=True)

    heat_path = heat_dir / (Path(path).stem + '_heat.png')
    recon_path = recon_dir / (Path(path).stem + '_recon.png')

    _save_heatmap(diff, heat_path)
    _save_image(recon, recon_path)

    is_anomaly = mse > threshold
    return AnalyzeResult(
        is_anomaly=is_anomaly,
        score=float(mse),
        heatmap_path=str(heat_path),
        recon_path=str(recon_path),
    )


async def train_async(epochs: int = 5, lr: float = 1e-3) -> dict:
    return await asyncio.to_thread(train_from_static, epochs, lr)


async def analyze_async(path: str, threshold: float = 0.01) -> AnalyzeResult:
    return await asyncio.to_thread(analyze_image, path, threshold)
