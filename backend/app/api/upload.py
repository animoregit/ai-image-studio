"""
Image upload and download endpoints.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import settings
from ..models import ImageInfo
from ..storage import storage

router = APIRouter(tags=["files"])


def _validate_upload(file: UploadFile, data: bytes) -> str:
    """Validate an uploaded file. Returns the safe extension."""
    # Check size
    if len(data) > settings.max_file_size:
        raise HTTPException(413, f"File too large. Maximum is {settings.max_file_size // (1024*1024)} MB.")

    # Check MIME type from header (don't trust it fully — also validate with Pillow later)
    ct = (file.content_type or "").lower()
    if ct not in settings.allowed_mime_types:
        raise HTTPException(
            415, f"Unsupported file type '{ct}'. Allowed: {', '.join(sorted(settings.allowed_mime_types))}"
        )

    # Derive safe extension from content type
    ext_map = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tif",
    }
    ext = ext_map.get(ct, ".png")

    return ext


@router.post("/upload", response_model=ImageInfo)
async def upload_image(file: UploadFile = File(...)):
    """Upload an image for processing. Returns image metadata and a server-side ID."""
    data = await file.read()

    if not data:
        raise HTTPException(400, "Empty file.")

    ext = _validate_upload(file, data)

    # Save to temp storage
    file_id, path = await storage.save_upload(data, ext)

    # Validate that the file is a real image by opening with Pillow
    try:
        img = storage.get_image(file_id)
        if img is None:
            raise ValueError("Could not decode image")
        width, height = img.size
        fmt = img.format or ext.lstrip(".")
    except Exception:
        # Remove the invalid file
        path.unlink(missing_ok=True)
        raise HTTPException(422, "The uploaded file is not a valid image.")

    return ImageInfo(
        id=file_id,
        width=width,
        height=height,
        format=fmt.lower(),
        size_bytes=len(data),
        filename=file.filename or "",
    )


@router.get("/images/{file_id}")
async def download_image(file_id: str):
    """Download a processed or uploaded image by its ID."""
    # Sanitise: file_id must be a hex string only
    if not file_id.replace("-", "").isalnum():
        raise HTTPException(400, "Invalid file ID.")

    path = storage.get_path(file_id)
    if path is None:
        raise HTTPException(404, "Image not found or expired.")

    # Determine content type from extension
    ext = path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=f"ai-image-studio-{file_id}{ext}",
    )
