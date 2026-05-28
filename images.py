"""
Image operations via Cloudinary cloud storage.
Security: filenames are sanitised; uploads validated by extension.
"""
import os
import re
from pathlib import Path

import cloudinary
import cloudinary.api
import cloudinary.uploader
from werkzeug.datastructures import FileStorage

from config import CLOUDINARY_FOLDER

cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
    secure=True,
)

_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _folder_name(phone_name: str) -> str:
    """Convert a phone name to a Cloudinary folder path segment."""
    return phone_name.replace(" ", "_")


def _safe_stem(filename: str) -> str:
    """Strip dangerous characters from a filename stem."""
    return re.sub(r"[^\w.\-]", "_", filename)


def list_images(phone_name: str) -> list[str]:
    """Return sorted list of image URLs for a phone (from Cloudinary)."""
    prefix = f"{CLOUDINARY_FOLDER}/{_folder_name(phone_name)}/"
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix=prefix,
            max_results=500,
        )
        return sorted(r["secure_url"] for r in result.get("resources", []))
    except Exception:
        return []


def save_image(phone_name: str, file: FileStorage) -> str:
    """Upload an image to Cloudinary. Returns the secure URL."""
    suffix = Path(file.filename or "image").suffix.lower()
    if suffix not in _ALLOWED_EXTS:
        raise ValueError(f"Unsupported file type: {suffix}")
    folder = f"{CLOUDINARY_FOLDER}/{_folder_name(phone_name)}"
    result = cloudinary.uploader.upload(
        file.stream,
        folder=folder,
        use_filename=True,
        unique_filename=True,
        overwrite=False,
        resource_type="image",
    )
    return result["secure_url"]


def delete_image(phone_name: str, filename: str) -> bool:
    """Delete an image from Cloudinary. Returns True if deleted.

    filename is the last URL path segment, e.g. "photo_abc123.jpg".
    Cloudinary public_id = folder/stem (no extension).
    """
    stem = Path(filename).stem
    public_id = f"{CLOUDINARY_FOLDER}/{_folder_name(phone_name)}/{stem}"
    result = cloudinary.uploader.destroy(public_id)
    return result.get("result") == "ok"
