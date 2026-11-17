"""Central configuration for the BizFlow AI/ML package.

All settings come from environment variables (or a .env file).
No secrets are hardcoded anywhere in this project.
"""

import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

# Folder paths: Path(__file__) is this file; .parent is the ai_ml folder.
AI_ML_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AI_ML_DIR.parent
SAMPLE_DATA_DIR = AI_ML_DIR / "sample_data"

# Load .env from the project root, then from ai_ml/ as a fallback.
# load_dotenv never overwrites variables that are already set.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(AI_ML_DIR / ".env")

# Groq settings
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_TIMEOUT_SECONDS: float = float(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))

# OCR settings
# Full path to tesseract.exe if it is not on PATH; empty means use PATH.
TESSERACT_CMD: str | None = os.getenv("TESSERACT_CMD") or None
# A PDF page with fewer characters than this is treated as scanned.
MIN_TEXT_CHARS_PER_PAGE: int = int(os.getenv("MIN_TEXT_CHARS_PER_PAGE", "30"))
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".jpg", ".jpeg", ".png"})

# Validation settings
# Allowed difference when checking subtotal + tax == total (in rupees).
AMOUNT_TOLERANCE: Decimal = Decimal(os.getenv("AMOUNT_TOLERANCE", "1.00"))


def require_groq_api_key() -> str:
    """Return the Groq API key, or raise a clear error if it is missing."""
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file "
            "(GROQ_API_KEY=your_key) and restart the program."
        )
    return GROQ_API_KEY