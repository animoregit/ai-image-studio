"""
Pydantic models for all API requests and responses.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────

class OutputFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FlipDirection(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class BackgroundType(str, Enum):
    COLOR = "color"
    IMAGE = "image"
    GRADIENT = "gradient"
    BLUR = "blur"
    TRANSPARENT = "transparent"


class BatchOperation(str, Enum):
    UPSCALE = "upscale"
    BACKGROUND_REMOVE = "background_remove"
    SHARPEN = "sharpen"
    DENOISE = "denoise"
    FACE_ENHANCE = "face_enhance"
    COLOR_ADJUST = "color_adjust"


# ── Response Models ──────────────────────────────────────────────────────

class ImageInfo(BaseModel):
    """Metadata about an uploaded or processed image."""
    id: str
    width: int
    height: int
    format: str
    size_bytes: int
    filename: str = ""


class ProcessingResult(BaseModel):
    """Result of an image processing operation."""
    success: bool
    image: Optional[ImageInfo] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None


class JobResponse(BaseModel):
    """Status of a background processing job."""
    job_id: str
    status: JobStatus
    progress: float = 0.0  # 0..100, only set when measurable
    result: Optional[ProcessingResult] = None
    error: Optional[str] = None
    created_at: Optional[str] = None


class HealthResponse(BaseModel):
    """Backend health check."""
    status: str = "ok"
    version: str = "1.0.0"
    device: str = "cpu"
    models: dict[str, bool] = {}


class ErrorResponse(BaseModel):
    """Standardised error envelope."""
    error: str
    detail: Optional[str] = None


class BatchItemResult(BaseModel):
    """Result for a single item in a batch."""
    filename: str
    success: bool
    image: Optional[ImageInfo] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    """Combined result of batch processing."""
    job_id: str
    status: JobStatus
    total: int
    completed: int = 0
    results: list[BatchItemResult] = []
    zip_url: Optional[str] = None
