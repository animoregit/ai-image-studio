"""
Background changer service — composites a foreground onto new backgrounds.
Supports solid colors, gradients, background images, and blur effects.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from PIL import Image, ImageFilter, ImageDraw

logger = logging.getLogger(__name__)


def _parse_color(color: str) -> Tuple[int, int, int, int]:
    """Parse a CSS hex colour string into an RGBA tuple."""
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    if len(color) == 6:
        color += "ff"
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        a = int(color[6:8], 16)
        return (r, g, b, a)
    except (ValueError, IndexError):
        return (255, 255, 255, 255)


def _create_gradient(
    width: int,
    height: int,
    start_color: str,
    end_color: str,
    direction: str = "vertical",
) -> Image.Image:
    """Create a gradient background image."""
    sc = _parse_color(start_color)[:3]
    ec = _parse_color(end_color)[:3]

    gradient = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(gradient)

    if direction == "horizontal":
        for x in range(width):
            t = x / max(1, width - 1)
            r = int(sc[0] + (ec[0] - sc[0]) * t)
            g = int(sc[1] + (ec[1] - sc[1]) * t)
            b = int(sc[2] + (ec[2] - sc[2]) * t)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))
    elif direction == "diagonal":
        for y in range(height):
            for x in range(width):
                t = (x / max(1, width - 1) + y / max(1, height - 1)) / 2
                r = int(sc[0] + (ec[0] - sc[0]) * t)
                g = int(sc[1] + (ec[1] - sc[1]) * t)
                b = int(sc[2] + (ec[2] - sc[2]) * t)
                gradient.putpixel((x, y), (r, g, b))
    else:  # vertical
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(sc[0] + (ec[0] - sc[0]) * t)
            g = int(sc[1] + (ec[1] - sc[1]) * t)
            b = int(sc[2] + (ec[2] - sc[2]) * t)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    return gradient


def change_background(
    foreground: Image.Image,
    bg_type: str = "color",
    bg_color: str = "#ffffff",
    bg_image: Optional[Image.Image] = None,
    gradient_start: str = "#000000",
    gradient_end: str = "#ffffff",
    gradient_direction: str = "vertical",
    blur_amount: float = 0.0,
    original_image: Optional[Image.Image] = None,
    position_x: float = 0.5,
    position_y: float = 0.5,
    scale: float = 1.0,
) -> Image.Image:
    """
    Composite a foreground (RGBA) image onto a new background.

    Parameters
    ----------
    foreground : Image with alpha channel (from background removal).
    bg_type : "color", "image", "gradient", "blur", or "transparent".
    bg_color : Hex colour when bg_type is "color".
    bg_image : Background image when bg_type is "image".
    gradient_start/end : Gradient endpoints.
    gradient_direction : "vertical", "horizontal", or "diagonal".
    blur_amount : Blur radius when bg_type is "blur".
    original_image : Original image (needed for blur mode).
    position_x/y : Subject position (0..1, center = 0.5).
    scale : Subject scale factor.
    """
    if foreground.mode != "RGBA":
        foreground = foreground.convert("RGBA")

    w, h = foreground.size

    # Scale subject
    if scale != 1.0:
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        foreground = foreground.resize((new_w, new_h), Image.LANCZOS)

    fw, fh = foreground.size

    # Create background
    if bg_type == "transparent":
        result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    elif bg_type == "gradient":
        bg = _create_gradient(w, h, gradient_start, gradient_end, gradient_direction)
        result = bg.convert("RGBA")
    elif bg_type == "image" and bg_image is not None:
        bg = bg_image.resize((w, h), Image.LANCZOS)
        result = bg.convert("RGBA")
    elif bg_type == "blur" and original_image is not None:
        bg = original_image.copy()
        if bg.size != (w, h):
            bg = bg.resize((w, h), Image.LANCZOS)
        radius = max(1, int(blur_amount))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=radius))
        result = bg.convert("RGBA")
    else:  # "color"
        rgba = _parse_color(bg_color)
        result = Image.new("RGBA", (w, h), rgba)

    # Calculate position
    px = int((w - fw) * position_x)
    py = int((h - fh) * position_y)

    # Composite foreground onto background
    result.paste(foreground, (px, py), foreground)

    return result
