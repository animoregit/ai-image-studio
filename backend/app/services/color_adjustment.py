"""
Color adjustment service using Pillow's ImageEnhance.
All adjustments are applied from the original image (non-destructive).
"""

from __future__ import annotations

import logging

import numpy as np
from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)


def adjust_colors(
    img: Image.Image,
    brightness: float = 0.0,
    contrast: float = 0.0,
    saturation: float = 0.0,
    exposure: float = 0.0,
    warmth: float = 0.0,
) -> Image.Image:
    """
    Apply colour adjustments to an image.

    All values range from -100 to 100, where 0 means no change.
    These are designed for nondestructive editing: always apply
    against the original image rather than a previously adjusted one.

    Parameters
    ----------
    brightness : -100 (dark) to 100 (bright).
    contrast : -100 (flat) to 100 (punchy).
    saturation : -100 (desaturated) to 100 (vivid).
    exposure : -100 (under) to 100 (over) — simulated via gamma.
    warmth : -100 (cool/blue) to 100 (warm/orange).
    """
    result = img.copy()

    has_alpha = result.mode == "RGBA"
    if has_alpha:
        alpha = result.split()[-1]
        result = result.convert("RGB")
    elif result.mode != "RGB":
        result = result.convert("RGB")

    # Brightness: map -100..100 → 0.0..2.0 (1.0 = no change)
    if brightness != 0:
        factor = 1.0 + brightness / 100.0
        result = ImageEnhance.Brightness(result).enhance(max(0.0, factor))

    # Contrast: map -100..100 → 0.0..2.0
    if contrast != 0:
        factor = 1.0 + contrast / 100.0
        result = ImageEnhance.Contrast(result).enhance(max(0.0, factor))

    # Saturation: map -100..100 → 0.0..2.0
    if saturation != 0:
        factor = 1.0 + saturation / 100.0
        result = ImageEnhance.Color(result).enhance(max(0.0, factor))

    # Exposure: simulate via gamma curve
    if exposure != 0:
        # Map -100..100 to gamma 0.3..3.0 (1.0 = no change)
        if exposure > 0:
            gamma = 1.0 / (1.0 + exposure / 50.0)  # < 1 brightens
        else:
            gamma = 1.0 + abs(exposure) / 50.0       # > 1 darkens
        arr = np.array(result, dtype=np.float64) / 255.0
        arr = np.power(arr, gamma) * 255.0
        result = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # Warmth: shift towards orange (warm) or blue (cool)
    if warmth != 0:
        arr = np.array(result, dtype=np.float64)
        shift = warmth / 100.0 * 25  # max 25-unit shift
        arr[:, :, 0] = np.clip(arr[:, :, 0] + shift, 0, 255)       # Red
        arr[:, :, 2] = np.clip(arr[:, :, 2] - shift, 0, 255)       # Blue
        result = Image.fromarray(arr.astype(np.uint8))

    if has_alpha:
        result = result.convert("RGBA")
        result.putalpha(alpha)

    return result
