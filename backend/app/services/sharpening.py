"""
Image sharpening service using OpenCV unsharp mask.
Avoids excessive halos by clamping parameters.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from PIL import Image

from .image_processing import pil_to_cv2, cv2_to_pil

logger = logging.getLogger(__name__)


def sharpen(
    img: Image.Image,
    intensity: float = 50.0,
    radius: float = 1.0,
) -> Image.Image:
    """
    Sharpen an image using unsharp masking.

    Parameters
    ----------
    intensity : Sharpening strength 0-100 (mapped to actual amount).
    radius : Blur kernel radius 0.5-5.0 (controls edge width).
    """
    # Clamp params
    intensity = max(0.0, min(100.0, intensity))
    radius = max(0.5, min(5.0, radius))

    # Map intensity (0-100) to unsharp mask amount (0-3.0)
    amount = intensity / 100.0 * 3.0

    if amount < 0.01:
        return img  # No-op

    has_alpha = img.mode == "RGBA"
    if has_alpha:
        alpha = img.split()[-1]
        img_rgb = img.convert("RGB")
    else:
        img_rgb = img.convert("RGB") if img.mode != "RGB" else img

    cv_img = pil_to_cv2(img_rgb).astype(np.float64)

    # Gaussian blur for unsharp mask
    kernel_size = int(radius * 4) | 1  # Must be odd
    sigma = radius
    blurred = cv2.GaussianBlur(cv_img, (kernel_size, kernel_size), sigma)

    # Unsharp mask: output = original + amount * (original - blurred)
    sharpened = cv_img + amount * (cv_img - blurred)
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)

    result = cv2_to_pil(sharpened)

    if has_alpha:
        result = result.convert("RGBA")
        result.putalpha(alpha)

    return result
