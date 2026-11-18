"""Backend settings. .env is loaded BEFORE anything imports ai_ml (ai_ml.config reads env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


DATABASE_URL = os.getenv("DATABASE_URL", "")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(REPO_ROOT / "uploads"))).resolve()
MAX_UPLOAD_BYTES = _int("MAX_UPLOAD_MB", 10) * 1024 * 1024
EXTRACTION_TTL_MINUTES = _int("EXTRACTION_TTL_MINUTES", 60)

# Auth: Supabase-issued JWT (HS256 shared secret)
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "authenticated")
