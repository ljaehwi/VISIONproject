from enum import Enum

from pydantic import BaseModel


class SimulationMode(str, Enum):
    CLEAN = 'CLEAN'
    OPTICAL_NOISE = 'OPTICAL_NOISE'
    DEFECTIVE = 'DEFECTIVE'


class CameraParams(BaseModel):
    gain: float
    black_level: int


class CaptureMetadata(BaseModel):
    gain: float
    black_level: float
    gv_mean: float
    timestamp: str
    raw_image_id: int
    capture_count: int
    simulation_mode: SimulationMode


class CaptureResponse(BaseModel):
    image_url: str
    metadata: CaptureMetadata


class AutoCalibrateBody(BaseModel):
    target_gv: float
    tolerance: float | None = 2.0
    max_iterations: int | None = 20


class AutoCalibrateResponse(BaseModel):
    status: str
    step: int
    current_gv: float
    target_gv: float
    image_url: str | None


class SimulationModeBody(BaseModel):
    mode: SimulationMode


class AnalyzeBody(BaseModel):
    raw_image_id: int


class AnalyzeResponse(BaseModel):
    is_anomaly: bool
    score: float
    heatmap_url: str | None
    recon_url: str | None


class DatasetImageItem(BaseModel):
    id: int
    item: str
    split: str
    defect_type: str
    file_url: str
    is_mask: bool


class SaveDatasetBody(BaseModel):
    dataset_image_id: int
    gain: float
    black_level: float
    is_auto_calibration: bool = False
    note: str | None = None


class SaveDatasetResponse(BaseModel):
    saved_image_id: int
    image_url: str
    gv_mean: float
