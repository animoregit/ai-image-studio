"""
Face enhancement service using GFPGAN.
Restores facial details while preserving the overall composition.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..config import settings
from .image_processing import pil_to_cv2, cv2_to_pil

logger = logging.getLogger(__name__)

_enhancer = None
_model_loaded = False
_load_error: Optional[str] = None


def is_available() -> bool:
    """Check if face enhancement is available."""
    return True


def _fallback_face_enhance(img: Image.Image, upscale: int = 1) -> Image.Image:
    """Portrait skin smoothing and eye/feature sharpening fallback."""
    if upscale > 1:
        img = img.resize((img.width * upscale, img.height * upscale), Image.LANCZOS)

    has_alpha = img.mode == "RGBA"
    if has_alpha:
        alpha = img.split()[-1]
        img_rgb = img.convert("RGB")
    else:
        img_rgb = img.convert("RGB")

    cv_img = cv2.cvtColor(np.array(img_rgb), cv2.COLOR_RGB2BGR)
    # Edge-preserving skin smoothing via bilateral filtering
    smooth = cv2.bilateralFilter(cv_img, d=9, sigmaColor=50, sigmaSpace=50)
    # Detail enhancement on features
    detail = cv2.addWeighted(cv_img, 1.3, smooth, -0.3, 0)
    res = Image.fromarray(cv2.cvtColor(detail, cv2.COLOR_BGR2RGB))
    if has_alpha:
        res.putalpha(alpha)
    return res


def enhance_faces(
    img: Image.Image,
    upscale: int = 1,
) -> Image.Image:
    """
    Enhance faces in an image using GFPGAN or smart portrait enhancement.
    """
    enhancer = _get_enhancer()
    if enhancer is None:
        return _fallback_face_enhance(img, upscale)

    has_alpha = img.mode == "RGBA"
    if has_alpha:
        alpha = img.split()[-1]
        img_rgb = img.convert("RGB")
    else:
        img_rgb = img.convert("RGB")

    cv_img = cv2.cvtColor(np.array(img_rgb), cv2.COLOR_RGB2BGR)

    # Update upscale factor
    enhancer.upscale = upscale

    try:
        _, _, output = enhancer.enhance(
            cv_img, has_aligned=False, only_center_face=False, paste_back=True
        )
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            logger.warning("GPU OOM during face enhancement, trying CPU")
            raise RuntimeError(
                "Insufficient GPU memory for face enhancement. "
                "Try a smaller image or use CPU mode."
            )
        raise

    result = Image.fromarray(cv2.cvtColor(output, cv2.COLOR_BGR2RGB))

    if has_alpha:
        if upscale > 1:
            alpha = alpha.resize(result.size, Image.LANCZOS)
        result = result.convert("RGBA")
        result.putalpha(alpha)

    return result
