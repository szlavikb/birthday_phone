"""
Image operations via Cloudinary cloud storage.
Security: filenames are sanitised; uploads validated by extension.
"""
import os
import re
import uuid
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


def _phone_folder(phone_name: str) -> str:
    """Full Cloudinary folder path for a phone."""
    return f"{CLOUDINARY_FOLDER}/{phone_name.replace(' ', '_')}"


def _safe_stem(name: str) -> str:
    """Strip dangerous characters from a filename stem."""
    return re.sub(r"[^\w.\-]", "_", Path(name).stem)


def list_images(phone_name: str) -> list[str]:
    """Return sorted list of image URLs for a phone (from Cloudinary)."""
    prefix = f"{_phone_folder(phone_name)}/"
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
    """Upload an image to Cloudinary. Returns the secure URL.

    Uses `folder` + `public_id` (stem only) so it works in both
    Cloudinary 'fixed folder' and 'dynamic folder' account modes.
    """
    file_path = Path(file.filename or "image")
    suffix = file_path.suffix.lower()
    if suffix not in _ALLOWED_EXTS:
        raise ValueError(f"Unsupported file type: {suffix}")
    stem = _safe_stem(file_path.name)
    asset_name = f"{stem}_{uuid.uuid4().hex[:8]}"
    folder = _phone_folder(phone_name)
    result = cloudinary.uploader.upload(
        file.stream,
        folder=folder,
        public_id=asset_name,
        overwrite=False,
        resource_type="image",
    )
    return result["secure_url"]


def delete_image(phone_name: str, filename: str) -> bool:
    """Delete an image from Cloudinary. Returns True if deleted.

    filename is the last URL path segment, e.g. "photo_abc123_xf9d1a2b.jpg".
    We search for the resource by prefix so we get the exact public_id
    regardless of Cloudinary folder mode.
    """
    stem = Path(filename).stem
    prefix = f"{_phone_folder(phone_name)}/{stem}"
    try:
        result = cloudinary.api.resources(type="upload", prefix=prefix, max_results=1)
        resources = result.get("resources", [])
        if not resources:
            return False
        public_id = resources[0]["public_id"]
    except Exception:
        return False
    destroy = cloudinary.uploader.destroy(public_id)
    return destroy.get("result") == "ok"
