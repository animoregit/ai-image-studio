"""
AI upscaling endpoint.
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
from ..services import upscaling

router = APIRouter(tags=["enhance"])


@router.post("/upscale", response_model=JobResponse)
async def upscale_image(
    image_id: str = Form(None),
    file: Optional[UploadFile] = File(None),
    scale_factor: int = Form(4),
    face_enhance: bool = Form(False),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """
    Upscale an image using Real-ESRGAN.
    Supports 2× and 4× scaling.
    """
    if scale_factor not in (2, 4):
        raise HTTPException(400, "Scale factor must be 2 or 4.")

    img = await _resolve_image(image_id, file)

    # Estimate output dimensions for validation
    out_w = img.size[0] * scale_factor
    out_h = img.size[1] * scale_factor
    if out_w * out_h > 8192 * 8192:
        raise HTTPException(
            400,
            f"Output would be {out_w}×{out_h} ({out_w*out_h:,} pixels). "
            f"Maximum supported is ~67 megapixels. Try a lower scale factor."
        )

    async def _process(job):
        job.progress = 5
        start = time.time()
        try:
            result_img = await asyncio.to_thread(
                upscaling.upscale,
                img,
                scale_factor=scale_factor,
                face_enhance=face_enhance,
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
