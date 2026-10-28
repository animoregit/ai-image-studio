"""
Core image processing utilities shared by all services.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)


def pil_to_cv2(img: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR(A) numpy array."""
    if img.mode == "RGBA":
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)
    elif img.mode == "RGB":
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    elif img.mode == "L":
        return np.array(img)
    else:
        return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def cv2_to_pil(arr: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR(A) array to PIL Image."""
    if len(arr.shape) == 2:
        return Image.fromarray(arr, mode="L")
    elif arr.shape[2] == 4:
        return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA), mode="RGBA")
    else:
        return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB), mode="RGB")


def ensure_rgb(img: Image.Image) -> Image.Image:
    """Convert to RGB, preserving alpha if present as RGBA."""
    if img.mode in ("RGB", "RGBA"):
        return img
    if img.mode in ("LA", "PA"):
        return img.convert("RGBA")
    return img.convert("RGB")


def resize_image(
    img: Image.Image,
    width: Optional[int] = None,
    height: Optional[int] = None,
    maintain_aspect: bool = True,
    resample: int = Image.LANCZOS,
) -> Image.Image:
    """Resize a PIL Image with optional aspect-ratio preservation."""
    orig_w, orig_h = img.size

    if width is None and height is None:
        return img

    if maintain_aspect:
        if width and height:
            ratio = min(width / orig_w, height / orig_h)
            width = int(orig_w * ratio)
            height = int(orig_h * ratio)
        elif width:
            ratio = width / orig_w
            height = int(orig_h * ratio)
        else:
            ratio = height / orig_h
            width = int(orig_w * ratio)
    else:
        width = width or orig_w
        height = height or orig_h

    return img.resize((max(1, width), max(1, height)), resample)


def crop_image(
    img: Image.Image, x: int, y: int, width: int, height: int
) -> Image.Image:
    """Crop a region from the image with boundary validation."""
    img_w, img_h = img.size
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    x2 = max(x + 1, min(x + width, img_w))
    y2 = max(y + 1, min(y + height, img_h))
    return img.crop((x, y, x2, y2))


def rotate_image(img: Image.Image, angle: float, expand: bool = True) -> Image.Image:
    """Rotate image by the given angle in degrees (counter-clockwise)."""
    return img.rotate(angle, expand=expand, resample=Image.BICUBIC)


def flip_image(img: Image.Image, direction: str) -> Image.Image:
    """Flip image horizontally or vertically."""
    if direction == "horizontal":
        return img.transpose(Image.FLIP_LEFT_RIGHT)
    elif direction == "vertical":
        return img.transpose(Image.FLIP_TOP_BOTTOM)
    return img


def get_image_info(img: Image.Image) -> dict:
    """Return basic metadata about an image."""
    return {
        "width": img.size[0],
        "height": img.size[1],
        "mode": img.mode,
        "format": img.format or "unknown",
    }


def image_to_bytes(img: Image.Image, fmt: str = "png", quality: int = 90) -> bytes:
    """Encode a PIL Image to bytes in the given format."""
    buf = io.BytesIO()
    save_kwargs = {}
    if fmt.lower() in ("jpeg", "jpg"):
        if img.mode in ("RGBA", "LA", "PA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        save_kwargs["quality"] = quality
        fmt = "JPEG"
    elif fmt.lower() == "webp":
        save_kwargs["quality"] = quality
        fmt = "WEBP"
    else:
        fmt = "PNG"

    img.save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()
