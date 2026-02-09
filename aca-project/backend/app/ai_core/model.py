import os
from pathlib import Path

import torch
import torch.nn as nn


class ConvAutoencoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(1, 8, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(8, 16, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(32, 16, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(16, 8, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(8, 1, 3, stride=2, padding=1, output_padding=1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encoder(x)
        return self.decoder(z)


def get_weights_path() -> Path:
    base = Path(__file__).resolve().parent
    weights_dir = base / 'weights'
    weights_dir.mkdir(parents=True, exist_ok=True)
    return weights_dir / 'cae.pt'


def load_model(device: torch.device | None = None) -> ConvAutoencoder:
    device = device or torch.device('cpu')
    model = ConvAutoencoder().to(device)
    weights = get_weights_path()
    if weights.exists():
        model.load_state_dict(torch.load(weights, map_location=device))
    model.eval()
    return model


def save_model(model: ConvAutoencoder) -> None:
    torch.save(model.state_dict(), get_weights_path())
