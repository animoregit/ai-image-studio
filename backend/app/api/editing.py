"""
Image editing endpoints: crop, resize, rotate, flip.
These are fast operations — results are returned directly.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image

from ..config import settings as app_settings
from ..models import ImageInfo, ProcessingResult
from ..storage import storage
from ..services.image_processing import crop_image, resize_image, rotate_image, flip_image

router = APIRouter(prefix="/image", tags=["editing"])


@router.post("/crop", response_model=ProcessingResult)
async def crop(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    x: int = Form(0),
    y: int = Form(0),
    width: int = Form(...),
    height: int = Form(...),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """Crop a region from the image."""
    img = await _resolve_image(image_id, file)

    if width <= 0 or height <= 0:
        raise HTTPException(400, "Crop width and height must be positive.")
    if width > img.size[0] or height > img.size[1]:
        raise HTTPException(400, "Crop region exceeds image bounds.")

    start = time.time()
    result_img = crop_image(img, x, y, width, height)
    return await _save_result(result_img, output_format, quality, start)


@router.post("/resize", response_model=ProcessingResult)
async def resize(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    width: int = Form(None),
    height: int = Form(None),
    maintain_aspect: bool = Form(True),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """Resize an image."""
    img = await _resolve_image(image_id, file)

    if width is None and height is None:
        raise HTTPException(400, "Provide at least one of width or height.")
    if width is not None and (width <= 0 or width > app_settings.max_output_dimension):
        raise HTTPException(400, f"Width must be between 1 and {app_settings.max_output_dimension}.")
    if height is not None and (height <= 0 or height > app_settings.max_output_dimension):
        raise HTTPException(400, f"Height must be between 1 and {app_settings.max_output_dimension}.")

    start = time.time()
    result_img = resize_image(img, width=width, height=height, maintain_aspect=maintain_aspect)
    return await _save_result(result_img, output_format, quality, start)


@router.post("/rotate", response_model=ProcessingResult)
async def rotate(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    angle: float = Form(90.0),
    expand: bool = Form(True),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """Rotate an image by the given angle in degrees (counter-clockwise)."""
    img = await _resolve_image(image_id, file)

    start = time.time()
    result_img = rotate_image(img, angle, expand=expand)
    return await _save_result(result_img, output_format, quality, start)


@router.post("/flip", response_model=ProcessingResult)
async def flip(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    direction: str = Form("horizontal"),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """Flip an image horizontally or vertically."""
    if direction not in ("horizontal", "vertical"):
        raise HTTPException(400, "Direction must be 'horizontal' or 'vertical'.")

    img = await _resolve_image(image_id, file)

    start = time.time()
    result_img = flip_image(img, direction)
    return await _save_result(result_img, output_format, quality, start)


# ── Helpers ──────────────────────────────────────────────────────────

async def _save_result(
    result_img: Image.Image, output_format: str, quality: int, start: float
) -> ProcessingResult:
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
