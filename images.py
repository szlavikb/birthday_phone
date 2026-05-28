"""
Image file operations: list, save, delete.
Security: all filenames are sanitised to prevent path traversal.
"""
import os
import re
from pathlib import Path
from urllib.parse import quote
from werkzeug.datastructures import FileStorage

from config import IMAGES_DIR

_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _safe_name(filename: str) -> str:
    """Strip dangerous characters from a filename."""
    return re.sub(r"[^\w.\-]", "_", filename)


def list_images(phone_name: str) -> list[str]:
    """Return sorted list of image URLs for a phone."""
    folder = IMAGES_DIR / phone_name
    if not folder.exists():
        return []
    files = sorted(
        f.name for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in _ALLOWED_EXTS
    )
    return [f"/static/images/{quote(phone_name)}/{quote(name)}" for name in files]


def save_image(phone_name: str, file: FileStorage) -> str:
    """Save an uploaded image, avoiding overwrites. Returns the URL."""
    folder = IMAGES_DIR / phone_name
    folder.mkdir(parents=True, exist_ok=True)

    safe = _safe_name(file.filename or "image")
    dest = folder / safe
    stem, suffix = os.path.splitext(safe)
    counter = 1
    while dest.exists():
        dest = folder / f"{stem}_{counter}{suffix}"
        counter += 1

    file.save(dest)
    return f"/static/images/{quote(phone_name)}/{quote(dest.name)}"


def delete_image(phone_name: str, filename: str) -> bool:
    """Delete an image file. Returns True if deleted, False if not found."""
    target = IMAGES_DIR / phone_name / _safe_name(filename)
    if target.exists():
        target.unlink()
        return True
    return False
