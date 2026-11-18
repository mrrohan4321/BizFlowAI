"""Safe upload handling: type + size + magic-byte checks, server-generated filenames only."""
import os
import uuid
from pathlib import Path

from app import config
from app.errors import AppError

_ALLOWED = {".pdf": b"%PDF-", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff"}
_CHUNK = 1024 * 1024


def display_name(filename: str | None) -> str:
    """Original name kept for display only; never used as a path."""
    base = os.path.basename((filename or "").replace("\\", "/"))
    return "".join(c for c in base if c.isprintable())[:200] or "upload"


def store_upload(business_id: str, filename: str | None, stream) -> tuple[str, Path]:
    """Validate and save. Returns (relative stored name, absolute path). Raises AppError."""
    ext = Path(display_name(filename)).suffix.lower()
    if ext not in _ALLOWED:
        raise AppError(415, "unsupported_file_type", "Only PDF, JPG/JPEG and PNG files are accepted.")
    head = stream.read(16)
    if not head.startswith(_ALLOWED[ext]):
        raise AppError(415, "unsupported_file_type", "File content does not match its type.")
    folder = (config.UPLOAD_DIR / business_id).resolve()
    if config.UPLOAD_DIR.resolve() not in folder.parents:
        raise AppError(400, "invalid_request", "Invalid upload location.")
    folder.mkdir(parents=True, exist_ok=True)
    rel = f"{business_id}/{uuid.uuid4().hex}{ext}"
    path = config.UPLOAD_DIR / rel
    size = len(head)
    try:
        with open(path, "wb") as out:
            out.write(head)
            while chunk := stream.read(_CHUNK):
                size += len(chunk)
                if size > config.MAX_UPLOAD_BYTES:
                    raise AppError(413, "file_too_large",
                                   f"File exceeds the {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
                out.write(chunk)
        if size == len(head) and size < 16:
            raise AppError(422, "empty_file", "The uploaded file is empty or too small.")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return rel, path


def delete_stored(rel: str | None) -> None:
    if not rel:
        return
    path = (config.UPLOAD_DIR / rel).resolve()
    if config.UPLOAD_DIR.resolve() in path.parents:
        path.unlink(missing_ok=True)
