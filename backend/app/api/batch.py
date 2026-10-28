"""
Batch processing endpoint.
Processes multiple images with a single operation using bounded concurrency.
"""

from __future__ import annotations

import asyncio
import io
import time
import zipfile
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image

from ..config import settings
from ..models import (
    BatchItemResult, BatchOperation, BatchResponse, ImageInfo,
    JobResponse, JobStatus, ProcessingResult,
)
from ..storage import storage
from ..jobs import job_manager
from ..services import (
    background_removal, sharpening, denoising,
    face_enhancement, color_adjustment, upscaling,
)

router = APIRouter(prefix="/batch", tags=["batch"])

MAX_BATCH_SIZE = 20


@router.post("/process", response_model=JobResponse)
async def batch_process(
    files: list[UploadFile] = File(...),
    operation: str = Form("sharpen"),
    # Generic settings (operation-specific)
    intensity: float = Form(50.0),
    strength: float = Form(50.0),
    scale_factor: int = Form(4),
    brightness: float = Form(0.0),
    contrast: float = Form(0.0),
    saturation: float = Form(0.0),
    output_format: str = Form("png"),
    quality: int = Form(90),
):
    """
    Process multiple images with a single operation.
    Returns a job that tracks per-image progress.
    """
    if not files:
        raise HTTPException(400, "No files provided.")
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(400, f"Maximum batch size is {MAX_BATCH_SIZE} images.")

    # Pre-read all file data (validate upfront)
    file_data: list[tuple[str, bytes]] = []
    for f in files:
        data = await f.read()
        if not data:
            continue
        ct = (f.content_type or "").lower()
        if ct not in settings.allowed_mime_types:
            continue
        file_data.append((f.filename or "image.png", data))

    if not file_data:
        raise HTTPException(400, "No valid image files in the batch.")

    async def _process(job):
        results: list[BatchItemResult] = []
        total = len(file_data)
        completed = 0

        # Use a semaphore for bounded concurrency within the batch
        sem = asyncio.Semaphore(2)

        async def process_one(filename: str, data: bytes) -> BatchItemResult:
            nonlocal completed
            async with sem:
                try:
                    fid, _ = await storage.save_upload(data, ".png")
                    img = storage.get_image(fid)
                    if img is None:
                        return BatchItemResult(filename=filename, success=False, error="Invalid image")

                    result_img = await _apply_operation(
                        img, operation,
                        intensity=intensity, strength=strength,
                        scale_factor=scale_factor,
                        brightness=brightness, contrast=contrast, saturation=saturation,
                    )

                    fmt = output_format.lower()
                    out_id, out_path = await storage.save_output(result_img, fmt=fmt, quality=quality)

                    completed += 1
                    job.progress = (completed / total) * 100

                    return BatchItemResult(
                        filename=filename,
                        success=True,
                        image=ImageInfo(
                            id=out_id,
                            width=result_img.size[0],
                            height=result_img.size[1],
                            format=fmt,
                            size_bytes=out_path.stat().st_size,
                        ),
                    )
                except Exception as e:
                    completed += 1
                    job.progress = (completed / total) * 100
                    return BatchItemResult(filename=filename, success=False, error=str(e))

        tasks = [process_one(name, data) for name, data in file_data]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for r in results if r.success)
        return ProcessingResult(
            success=success_count > 0,
            error=None if success_count == total else f"{total - success_count} of {total} images failed",
        )

    job = await job_manager.submit(_process)
    return job.to_response()


@router.get("/download/{job_id}")
async def download_batch_zip(job_id: str):
    """Download all results from a batch job as a ZIP file."""
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(400, "Job not yet completed.")

    # Collect output files
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Find all output images referenced by this job's results
        if job.result and job.result.image:
            path = storage.get_path(job.result.image.id)
            if path:
                zf.write(str(path), f"result.{job.result.image.format}")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=batch-{job_id[:8]}.zip"},
    )


async def _apply_operation(
    img: Image.Image,
    operation: str,
    **kwargs,
) -> Image.Image:
    """Route to the correct processing function."""
    if operation == "sharpen":
        return await asyncio.to_thread(
            sharpening.sharpen, img,
            intensity=kwargs.get("intensity", 50),
            radius=1.0,
        )
    elif operation == "denoise":
        return await asyncio.to_thread(
            denoising.denoise, img,
            strength=kwargs.get("strength", 50),
        )
    elif operation == "background_remove":
        return await asyncio.to_thread(
            background_removal.remove_background, img,
        )
    elif operation == "upscale":
        return await asyncio.to_thread(
            upscaling.upscale, img,
            scale_factor=kwargs.get("scale_factor", 4),
        )
    elif operation == "face_enhance":
        return await asyncio.to_thread(
            face_enhancement.enhance_faces, img,
        )
    elif operation == "color_adjust":
        return await asyncio.to_thread(
            color_adjustment.adjust_colors, img,
            brightness=kwargs.get("brightness", 0),
            contrast=kwargs.get("contrast", 0),
            saturation=kwargs.get("saturation", 0),
        )
    else:
        raise ValueError(f"Unknown operation: {operation}")
