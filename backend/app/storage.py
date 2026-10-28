"""
Temporary file storage with automatic cleanup.
Files are identified by randomised UUIDs — never client-supplied names.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image

from .config import settings

logger = logging.getLogger(__name__)


def _safe_image_open(path: Path) -> Image.Image:
    """Open and validate an image file safely."""
    img = Image.open(path)
    # Check pixel limit to avoid decompression bombs
    pixels = img.size[0] * img.size[1]
    if pixels > settings.max_image_pixels:
        raise ValueError(
            f"Image too large: {img.size[0]}×{img.size[1]} "
            f"({pixels:,} pixels exceeds limit of {settings.max_image_pixels:,})"
        )
    img.load()  # Force full decode to catch corrupt files early
    return img


class FileStorage:
    """Manages temporary upload and output files with TTL-based cleanup."""

    def __init__(self) -> None:
        self._upload_dir = settings.upload_dir
        self._output_dir = settings.output_dir
        # {file_id: (path, created_timestamp)}
        self._registry: dict[str, tuple[Path, float]] = {}
        self._lock = asyncio.Lock()

    # ── Save helpers ────────────────────────────────────────────────

    async def save_upload(self, data: bytes, original_ext: str) -> tuple[str, Path]:
        """Store raw upload bytes and return (file_id, path)."""
        file_id = uuid.uuid4().hex
        ext = original_ext.lower().lstrip(".")
        if f".{ext}" not in settings.allowed_extensions:
            ext = "png"
        path = self._upload_dir / f"{file_id}.{ext}"
        path.write_bytes(data)
        async with self._lock:
            self._registry[file_id] = (path, time.time())
        return file_id, path

    async def save_output(self, img: Image.Image, fmt: str = "png",
                          quality: int = 90) -> tuple[str, Path]:
        """Save a PIL Image as an output file and return (file_id, path)."""
        file_id = uuid.uuid4().hex
        ext = fmt.lower()
        if ext == "jpeg":
            ext = "jpg"
        path = self._output_dir / f"{file_id}.{ext}"

        save_kwargs: dict = {}
        if ext in ("jpg", "jpeg"):
            # JPEG doesn't support alpha; composite onto white
            if img.mode in ("RGBA", "LA", "PA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        elif ext == "webp":
            save_kwargs["quality"] = quality
            save_kwargs["method"] = 4
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
        else:  # png
            if img.mode not in ("RGB", "RGBA", "L", "LA"):
                img = img.convert("RGBA")
            save_kwargs["optimize"] = True

        img.save(path, **save_kwargs)
        async with self._lock:
            self._registry[file_id] = (path, time.time())
        return file_id, path

    # ── Retrieval ───────────────────────────────────────────────────

    def get_path(self, file_id: str) -> Optional[Path]:
        """Return the filesystem path for a file_id, or None."""
        entry = self._registry.get(file_id)
        if entry and entry[0].exists():
            return entry[0]
        # Also check on-disk (for files created before this process)
        for directory in (self._upload_dir, self._output_dir):
            for p in directory.iterdir():
                if p.stem == file_id:
                    return p
        return None

    def get_image(self, file_id: str) -> Optional[Image.Image]:
        """Load and return a PIL Image for the given file_id."""
        path = self.get_path(file_id)
        if path is None:
            return None
        return _safe_image_open(path)

    # ── Cleanup ─────────────────────────────────────────────────────

    async def cleanup_expired(self) -> int:
        """Remove files older than TTL. Returns count removed."""
        now = time.time()
        expired: list[str] = []
        async with self._lock:
            for fid, (path, created) in self._registry.items():
                if now - created > settings.temp_file_ttl_seconds:
                    expired.append(fid)
            for fid in expired:
                path, _ = self._registry.pop(fid)
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

        # Also sweep orphan files on disk
        for directory in (self._upload_dir, self._output_dir):
            if not directory.exists():
                continue
            for p in directory.iterdir():
                if p.is_file():
                    age = now - p.stat().st_mtime
                    if age > settings.temp_file_ttl_seconds:
                        try:
                            p.unlink(missing_ok=True)
                        except OSError:
                            pass

        if expired:
            logger.info("Cleaned up %d expired files", len(expired))
        return len(expired)

    async def start_cleanup_loop(self) -> None:
        """Background task that periodically cleans up old files."""
        while True:
            try:
                await self.cleanup_expired()
            except Exception:
                logger.exception("Cleanup sweep failed")
            await asyncio.sleep(settings.cleanup_interval_seconds)


# Module-level singleton
storage = FileStorage()
