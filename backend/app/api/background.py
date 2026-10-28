"""
Background removal and background change endpoints.
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
from ..services import background_removal, background_changer

router = APIRouter(prefix="/background", tags=["background"])


@router.post("/remove", response_model=JobResponse)
async def remove_background(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    alpha_matting: bool = Form(False),
    output_format: str = Form("png"),
):
    """
    Remove the background from an image.
    Either provide an existing `image_id` or upload a `file` directly.
    Returns a job that can be polled for the result.
    """
    img = await _resolve_image(image_id, file)

    async def _process(job):
        job.progress = 10
        start = time.time()
        try:
            result_img = await asyncio.to_thread(
                background_removal.remove_background,
                img,
                alpha_matting=alpha_matting,
            )
        except RuntimeError as e:
            return ProcessingResult(success=False, error=str(e))

        job.progress = 80

        # Always save as PNG to preserve transparency
        fmt = "png" if output_format.lower() in ("png", "transparent") else output_format.lower()
        out_id, out_path = await storage.save_output(result_img, fmt=fmt)
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


@router.post("/change", response_model=JobResponse)
async def change_background(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    bg_type: str = Form("color"),
    bg_color: str = Form("#ffffff"),
    gradient_start: str = Form("#000000"),
    gradient_end: str = Form("#ffffff"),
    gradient_direction: str = Form("vertical"),
    blur_amount: float = Form(15.0),
    position_x: float = Form(0.5),
    position_y: float = Form(0.5),
    scale: float = Form(1.0),
    output_format: str = Form("png"),
    quality: int = Form(90),
    bg_file: Optional[UploadFile] = File(None),
    original_image_id: Optional[str] = Form(None),
):
    """
    Composite a foreground (RGBA) image onto a new background.
    The input should already have its background removed (RGBA).
    """
    fg_img = await _resolve_image(image_id, file)

    # Load optional background image
    bg_image = None
    if bg_type == "image" and bg_file is not None:
        bg_data = await bg_file.read()
        bg_id, _ = await storage.save_upload(bg_data, ".png")
        bg_image = storage.get_image(bg_id)

    # Load original image for blur mode
    original = None
    if bg_type == "blur" and original_image_id:
        original = storage.get_image(original_image_id)

    async def _process(job):
        job.progress = 10
        start = time.time()

        result_img = await asyncio.to_thread(
            background_changer.change_background,
            foreground=fg_img,
            bg_type=bg_type,
            bg_color=bg_color,
            bg_image=bg_image,
            gradient_start=gradient_start,
            gradient_end=gradient_end,
            gradient_direction=gradient_direction,
            blur_amount=blur_amount,
            original_image=original,
            position_x=position_x,
            position_y=position_y,
            scale=scale,
        )

        job.progress = 80

        fmt = output_format.lower()
        if fmt == "jpeg" and result_img.mode == "RGBA":
            fmt = "png"  # Can't store alpha in JPEG

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


# ── Helpers ──────────────────────────────────────────────────────────

async def _resolve_image(image_id: Optional[str], file: Optional[UploadFile]) -> Image.Image:
    """Load an image from either an existing ID or a fresh upload."""
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
