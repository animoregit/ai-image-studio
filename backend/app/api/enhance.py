"""
Enhancement endpoints: sharpen, denoise, face enhance, color adjust.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image

from ..models import ImageInfo, ProcessingResult, JobResponse
from ..storage import storage
from ..jobs import job_manager
from ..services import sharpening, denoising, face_enhancement, color_adjustment

router = APIRouter(tags=["enhance"])


# ── Sharpen ──────────────────────────────────────────────────────────

@router.post("/sharpen", response_model=ProcessingResult)
async def sharpen_image(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    intensity: float = Form(50.0),
    radius: float = Form(1.0),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """Sharpen an image (fast — returns result directly)."""
    img = await _resolve_image(image_id, file)

    start = time.time()
    result_img = await asyncio.to_thread(
        sharpening.sharpen, img, intensity=intensity, radius=radius,
    )
    fmt = output_format.lower()
    out_id, out_path = await storage.save_output(result_img, fmt=fmt, quality=quality)
    elapsed = (time.time() - start) * 1000

    return ProcessingResult(
        success=True,
        image=ImageInfo(
            id=out_id,
            width=result_img.size[0],
            height=result_img.size[1],
            format=fmt,
            size_bytes=out_path.stat().st_size,
        ),
        processing_time_ms=round(elapsed, 1),
    )


# ── Denoise ──────────────────────────────────────────────────────────

@router.post("/denoise", response_model=ProcessingResult)
async def denoise_image(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    strength: float = Form(50.0),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """Reduce noise in an image (fast — returns result directly)."""
    img = await _resolve_image(image_id, file)

    start = time.time()
    result_img = await asyncio.to_thread(
        denoising.denoise, img, strength=strength,
    )
    fmt = output_format.lower()
    out_id, out_path = await storage.save_output(result_img, fmt=fmt, quality=quality)
    elapsed = (time.time() - start) * 1000

    return ProcessingResult(
        success=True,
        image=ImageInfo(
            id=out_id,
            width=result_img.size[0],
            height=result_img.size[1],
            format=fmt,
            size_bytes=out_path.stat().st_size,
        ),
        processing_time_ms=round(elapsed, 1),
    )


# ── Face Enhance ─────────────────────────────────────────────────────

@router.post("/face/enhance", response_model=JobResponse)
async def enhance_faces(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    upscale: int = Form(1),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """Enhance faces in an image using GFPGAN (long-running — returns job)."""
    img = await _resolve_image(image_id, file)

    async def _process(job):
        job.progress = 10
        start = time.time()
        try:
            result_img = await asyncio.to_thread(
                face_enhancement.enhance_faces, img, upscale=upscale,
            )
        except RuntimeError as e:
            return ProcessingResult(success=False, error=str(e))

        job.progress = 85

        fmt = output_format.lower()
        out_id, out_path = await storage.save_output(result_img, fmt=fmt, quality=quality)
        elapsed = (time.time() - start) * 1000

        return ProcessingResult(
            success=True,
            image=ImageInfo(
                id=out_id,
                width=result_img.size[0],
                height=result_img.size[1],
                format=fmt,
                size_bytes=out_path.stat().st_size,
            ),
            processing_time_ms=round(elapsed, 1),
        )

    job = await job_manager.submit(_process)
    return job.to_response()


# ── Color Adjust ─────────────────────────────────────────────────────

@router.post("/color/adjust", response_model=ProcessingResult)
async def adjust_colors(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    brightness: float = Form(0.0),
    contrast: float = Form(0.0),
    saturation: float = Form(0.0),
    exposure: float = Form(0.0),
    warmth: float = Form(0.0),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """Apply colour adjustments (fast — returns result directly)."""
    img = await _resolve_image(image_id, file)

    start = time.time()
    result_img = await asyncio.to_thread(
        color_adjustment.adjust_colors,
        img,
        brightness=brightness,
        contrast=contrast,
        saturation=saturation,
        exposure=exposure,
        warmth=warmth,
    )
    fmt = output_format.lower()
    out_id, out_path = await storage.save_output(result_img, fmt=fmt, quality=quality)
    elapsed = (time.time() - start) * 1000

    return ProcessingResult(
        success=True,
        image=ImageInfo(
            id=out_id,
            width=result_img.size[0],
            height=result_img.size[1],
            format=fmt,
            size_bytes=out_path.stat().st_size,
        ),
        processing_time_ms=round(elapsed, 1),
    )


# ── Helper ───────────────────────────────────────────────────────────

async def _resolve_image(image_id: Optional[str], file: Optional[UploadFile]) -> Image.Image:
    if image_id:
        img = storage.get_image(image_id)
        if img is None:
            raise HTTPException(404, f"Image '{image_id}' not found or expired.")
        return img
    if file is not None:
        data = await file.read()
        if not data:
            raise HTTPException(400, "Empty file.")
        fid, _ = await storage.save_upload(data, ".png")
        img = storage.get_image(fid)
        if img is None:
            raise HTTPException(422, "Invalid image file.")
        return img
    raise HTTPException(400, "Provide either 'image_id' or upload a 'file'.")
