"""
Application configuration with sensible defaults.
Auto-detects CUDA when torch + compatible GPU are available.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Settings:
    """Central configuration for the AI Image Studio backend."""

    # ── Server ──────────────────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ])

    # ── Storage ─────────────────────────────────────────────────────────
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    upload_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    models_dir: Optional[Path] = None
    max_file_size: int = 25 * 1024 * 1024          # 25 MB
    temp_file_ttl_seconds: int = 3600               # 1 hour
    cleanup_interval_seconds: int = 300             # 5 minutes
    allowed_mime_types: frozenset[str] = frozenset({
        "image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff",
    })
    allowed_extensions: frozenset[str] = frozenset({
        ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif",
    })

    # ── Processing ──────────────────────────────────────────────────────
    device: str = "cpu"
    max_concurrent_jobs: int = 2
    max_image_pixels: int = 8192 * 8192             # ~67 MP
    max_output_dimension: int = 8192
    default_jpeg_quality: int = 90
    default_webp_quality: int = 85

    # ── Model Info ──────────────────────────────────────────────────────
    realesrgan_model_name: str = "RealESRGAN_x4plus"
    gfpgan_model_version: str = "1.4"

    def __post_init__(self) -> None:
        # Resolve storage paths relative to backend/
        if self.upload_dir is None:
            self.upload_dir = self.base_dir / "storage" / "uploads"
        if self.output_dir is None:
            self.output_dir = self.base_dir / "storage" / "outputs"
        if self.models_dir is None:
            self.models_dir = self.base_dir / "models"

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Auto-detect CUDA when available
        if os.environ.get("FORCE_CPU", "").lower() in ("1", "true"):
            self.device = "cpu"
        else:
            try:
                import torch
                if torch.cuda.is_available():
                    self.device = "cuda"
            except ImportError:
                pass

        # Allow overriding CORS via env var (comma-separated)
        env_origins = os.environ.get("CORS_ORIGINS")
        if env_origins:
            self.cors_origins = [o.strip() for o in env_origins.split(",") if o.strip()]


settings = Settings()
