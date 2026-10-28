"""
Image denoising service using OpenCV's fastNlMeansDenoising.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from PIL import Image

from .image_processing import pil_to_cv2, cv2_to_pil

logger = logging.getLogger(__name__)


def denoise(
    img: Image.Image,
    strength: float = 50.0,
) -> Image.Image:
    """
    Reduce noise in an image.

    Parameters
    ----------
    strength : Denoising strength 0-100.
              Mapped to the filter h parameter (higher = more smoothing).
    """
    strength = max(0.0, min(100.0, strength))
    if strength < 1.0:
        return img

    # Map 0-100 to h parameter range 1-30
    h = 1.0 + (strength / 100.0) * 29.0

    has_alpha = img.mode == "RGBA"
    if has_alpha:
        alpha = img.split()[-1]
        img_rgb = img.convert("RGB")
    else:
        img_rgb = img.convert("RGB") if img.mode not in ("RGB", "L") else img

    if img_rgb.mode == "L":
        # Grayscale denoising
        cv_img = np.array(img_rgb)
        denoised = cv2.fastNlMeansDenoising(
            cv_img,
            None,
            h=h,
            templateWindowSize=7,
            searchWindowSize=21,
        )
        result = Image.fromarray(denoised, mode="L")
    else:
        # Color denoising
        cv_img = pil_to_cv2(img_rgb)
        denoised = cv2.fastNlMeansDenoisingColored(
            cv_img,
            None,
            h=h,
            hForColorComponents=h,
            templateWindowSize=7,
            searchWindowSize=21,
        )
        result = cv2_to_pil(denoised)

    if has_alpha:
        result = result.convert("RGBA")
        result.putalpha(alpha)

    return result
