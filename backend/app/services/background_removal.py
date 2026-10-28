"""
Background removal service using rembg (U2-Net).
Produces RGBA images with proper alpha channels.
"""

from __future__ import annotations

import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

# Lazy-loaded model session
_session = None
_model_loaded = False
_load_error: Optional[str] = None


def _get_session():
    """Lazy-initialise the rembg session on first call."""
    global _session, _model_loaded, _load_error
    if _model_loaded and _session is not None:
        return _session
    try:
        from rembg import new_session
        try:
            _session = new_session("u2netp")
        except Exception:
            _session = new_session("u2net")
        _model_loaded = True
        logger.info("rembg model loaded successfully")
    except (Exception, SystemExit) as exc:
        _load_error = str(exc)
        _model_loaded = True  # Prevent retrying
        logger.error("Failed to load rembg model: %s", exc)
    return _session


def is_available() -> bool:
    """Check if the background removal model can be loaded."""
    try:
        import rembg  # noqa: F401
        return True
    except (ImportError, Exception, SystemExit):
        return False


def remove_background(
    img: Image.Image,
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
) -> Image.Image:
    """
    Remove the background from an image.

    Returns an RGBA image with a transparent background.
    Raises RuntimeError if the model is unavailable.
    """
    session = _get_session()
    if session is None:
        raise RuntimeError(
            f"Background removal model is not available. "
            f"Install rembg: pip install rembg. "
            f"Error: {_load_error or 'unknown'}"
        )

    from rembg import remove

    # Ensure input is RGB or RGBA
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    result = remove(
        img,
        session=session,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
        alpha_matting_background_threshold=alpha_matting_background_threshold,
    )

    # Ensure output is RGBA with proper alpha
    if result.mode != "RGBA":
        result = result.convert("RGBA")

    return result
