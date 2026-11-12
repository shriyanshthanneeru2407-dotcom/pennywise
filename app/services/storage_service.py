"""
app/services/storage_service.py — File storage abstraction.

Provides a single interface for saving and retrieving uploaded files,
regardless of whether we're in local dev or production (S3/R2).

Usage:
    key = storage_service.save(file_object, original_filename, mime_type)
    url = storage_service.get_url(key)
    storage_service.delete(key)

The STORAGE_PROVIDER config value selects the backend:
    'local' → saves to instance/uploads/
    's3'    → saves to an S3-compatible bucket
"""

import os
import uuid
from flask import current_app, url_for


# --- Allowed file types for receipt uploads ---
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
ALLOWED_MIMETYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def allowed_file(filename: str, mime_type: str) -> bool:
    """
    Validate that a file is safe to upload.

    Security note: We check BOTH extension AND MIME type.
    Never trust only the extension (a .jpg can be renamed to anything).
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXTENSIONS and mime_type in ALLOWED_MIMETYPES


def _generate_storage_key(original_filename: str) -> str:
    """
    Generate a safe, unique storage key from the original filename.

    WHY: The original filename may contain path traversal characters
    (e.g., '../secret') or collisions. We use UUID to avoid both.
    """
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "bin"
    return f"receipts/{uuid.uuid4().hex}.{ext}"


# --- Local filesystem storage ---

def _local_save(file_obj, key: str) -> None:
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    dest_dir = os.path.join(upload_folder, os.path.dirname(key))
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(upload_folder, key)
    file_obj.save(dest_path)


def _local_delete(key: str) -> None:
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    path = os.path.join(upload_folder, key)
    if os.path.exists(path):
        os.remove(path)


def _local_get_url(key: str) -> str:
    return url_for("expenses.serve_receipt", key=key, _external=False)


# --- S3-compatible storage (Cloudflare R2, AWS S3, etc.) ---

def _s3_client():
    import boto3
    return boto3.client(
        "s3",
        aws_access_key_id=current_app.config["STORAGE_ACCESS_KEY"],
        aws_secret_access_key=current_app.config["STORAGE_SECRET_KEY"],
        endpoint_url=current_app.config.get("STORAGE_ENDPOINT_URL") or None,
    )


def _s3_save(file_obj, key: str, mime_type: str) -> None:
    client = _s3_client()
    bucket = current_app.config["STORAGE_BUCKET"]
    client.upload_fileobj(file_obj, bucket, key, ExtraArgs={"ContentType": mime_type})


def _s3_delete(key: str) -> None:
    client = _s3_client()
    bucket = current_app.config["STORAGE_BUCKET"]
    client.delete_object(Bucket=bucket, Key=key)


def _s3_get_url(key: str) -> str:
    """Generate a presigned URL valid for 1 hour."""
    client = _s3_client()
    bucket = current_app.config["STORAGE_BUCKET"]
    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
    )


# --- Public API ---

def save(file_obj, original_filename: str, mime_type: str) -> str:
    """
    Save an uploaded file and return the storage key.
    The key is what we store in the receipts table.
    """
    key = _generate_storage_key(original_filename)
    provider = current_app.config.get("STORAGE_PROVIDER", "local")

    if provider == "s3":
        _s3_save(file_obj, key, mime_type)
    else:
        _local_save(file_obj, key)

    return key


def delete(key: str) -> None:
    """Delete a stored file by its storage key."""
    provider = current_app.config.get("STORAGE_PROVIDER", "local")
    if provider == "s3":
        _s3_delete(key)
    else:
        _local_delete(key)


def get_url(key: str) -> str:
    """Return a URL to access the stored file."""
    provider = current_app.config.get("STORAGE_PROVIDER", "local")
    if provider == "s3":
        return _s3_get_url(key)
    else:
        return _local_get_url(key)


def get_local_path(key: str) -> str:
    """Return the absolute local filesystem path for a stored file (local only)."""
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    return os.path.join(upload_folder, key)
