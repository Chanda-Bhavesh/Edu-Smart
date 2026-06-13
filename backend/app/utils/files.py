"""
Local file storage utility.

Files are saved under:
  uploads/assignments/<assignment_id>/  → faculty attachments
  uploads/submissions/<submission_id>/  → student submission files
"""
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

UPLOAD_ROOT = Path("uploads")
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg",
    ".zip", ".pptx", ".xlsx", ".py", ".java", ".cpp", ".c",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _validate_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )
    return ext


async def save_assignment_file(file: UploadFile, assignment_id: uuid.UUID) -> tuple[str, str]:
    """
    Save a faculty-uploaded assignment attachment.
    Returns (file_url, original_filename).
    """
    ext = _validate_extension(file.filename or "file.bin")
    data = await file.read()

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds maximum allowed size of 10 MB.",
        )

    dest_dir = UPLOAD_ROOT / "assignments" / str(assignment_id)
    _ensure_dir(dest_dir)

    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = dest_dir / unique_name
    dest_path.write_bytes(data)

    relative_url = f"/uploads/assignments/{assignment_id}/{unique_name}"
    return relative_url, file.filename or unique_name


async def save_submission_file(file: UploadFile, submission_id: uuid.UUID) -> tuple[str, str]:
    """
    Save a student submission file.
    Returns (file_url, original_filename).
    """
    ext = _validate_extension(file.filename or "file.bin")
    data = await file.read()

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds maximum allowed size of 10 MB.",
        )

    dest_dir = UPLOAD_ROOT / "submissions" / str(submission_id)
    _ensure_dir(dest_dir)

    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = dest_dir / unique_name
    dest_path.write_bytes(data)

    relative_url = f"/uploads/submissions/{submission_id}/{unique_name}"
    return relative_url, file.filename or unique_name


def delete_file(file_url: str) -> None:
    """Delete a stored file given its relative URL (best-effort, no error if missing)."""
    if not file_url:
        return
    # Strip leading slash to get relative path
    rel = file_url.lstrip("/")
    path = Path(rel)
    if path.exists():
        path.unlink(missing_ok=True)
