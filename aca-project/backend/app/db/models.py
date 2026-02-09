import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RawImageStatus(str, enum.Enum):
    PENDING = 'PENDING'
    PROCESSED = 'PROCESSED'


class Verdict(str, enum.Enum):
    OK = 'OK'
    NG = 'NG'


class DatasetSplit(str, enum.Enum):
    TRAIN = 'train'
    TEST = 'test'
    GROUND_TRUTH = 'ground_truth'


class RawImage(Base):
    __tablename__ = 'raw_images'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lot_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RawImageStatus] = mapped_column(Enum(RawImageStatus), default=RawImageStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    inspection_results: Mapped[list['InspectionResult']] = relationship(back_populates='raw_image')


class InspectionResult(Base):
    __tablename__ = 'inspection_results'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    raw_image_id: Mapped[int] = mapped_column(ForeignKey('raw_images.id'))
    is_anomaly: Mapped[bool] = mapped_column(default=False)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    verdict: Mapped[Verdict] = mapped_column(Enum(Verdict), default=Verdict.OK)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    raw_image: Mapped[RawImage] = relationship(back_populates='inspection_results')
    calibration_logs: Mapped[list['CalibrationLog']] = relationship(back_populates='inspection_result')


class CalibrationLog(Base):
    __tablename__ = 'calibration_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey('inspection_results.id'))
    initial_gv: Mapped[float] = mapped_column(Float)
    target_gv: Mapped[float] = mapped_column(Float)
    final_gv: Mapped[float] = mapped_column(Float)
    gain_applied: Mapped[float] = mapped_column(Float)
    black_level_applied: Mapped[float] = mapped_column(Float)
    converged: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    inspection_result: Mapped[InspectionResult] = relationship(back_populates='calibration_logs')


class DatasetImage(Base):
    __tablename__ = 'dataset_images'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item: Mapped[str] = mapped_column(String(64), nullable=False)
    split: Mapped[DatasetSplit] = mapped_column(Enum(DatasetSplit), nullable=False)
    defect_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_mask: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedImage(Base):
    __tablename__ = 'saved_images'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_image_id: Mapped[int | None] = mapped_column(ForeignKey('dataset_images.id'), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    gain: Mapped[float] = mapped_column(Float, default=0.0)
    black_level: Mapped[float] = mapped_column(Float, default=0.0)
    gv_mean: Mapped[float] = mapped_column(Float, default=0.0)
    is_auto_calibration: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
