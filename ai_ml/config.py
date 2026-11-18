
"""Central configuration for the BizFlow AI/ML package.

Settings come from environment variables or a .env file.
Secrets are never hardcoded.
"""

import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dotenv import load_dotenv


# --------------------------------------------------------------------------
# Project paths
# --------------------------------------------------------------------------
AI_ML_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AI_ML_DIR.parent
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"


# --------------------------------------------------------------------------
# Environment loading
# --------------------------------------------------------------------------
# Existing environment variables take priority over .env values.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(AI_ML_DIR / ".env")


# --------------------------------------------------------------------------
# Configuration parsing helpers
# --------------------------------------------------------------------------
def _parse_positive_float(
    name: str,
    value: str | None,
    default: str,
) -> float:
    """Parse a finite positive floating-point setting."""

    raw_value = value if value is not None else default

    try:
        parsed = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be a valid number; received {raw_value!r}."
        ) from exc

    if not (0 < parsed < float("inf")):
        raise ValueError(
            f"{name} must be greater than zero and finite."
        )

    return parsed


def _parse_positive_int(
    name: str,
    value: str | None,
    default: str,
) -> int:
    """Parse a positive integer setting."""

    raw_value = value if value is not None else default

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be a valid integer; received {raw_value!r}."
        ) from exc

    if parsed < 1:
        raise ValueError(f"{name} must be at least 1.")

    return parsed


def _parse_nonnegative_decimal(
    name: str,
    value: str | None,
    default: str,
) -> Decimal:
    """Parse a finite, non-negative Decimal setting."""

    raw_value = value if value is not None else default

    try:
        parsed = Decimal(raw_value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be a valid decimal; received {raw_value!r}."
        ) from exc

    if not parsed.is_finite() or parsed < 0:
        raise ValueError(
            f"{name} must be a finite, non-negative number."
        )

    return parsed


# --------------------------------------------------------------------------
# Groq settings
# --------------------------------------------------------------------------
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY") or None

GROQ_MODEL: str = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
).strip()

if not GROQ_MODEL:
    raise ValueError("GROQ_MODEL cannot be empty.")

GROQ_TIMEOUT_SECONDS: float = _parse_positive_float(
    "GROQ_TIMEOUT_SECONDS",
    os.getenv("GROQ_TIMEOUT_SECONDS"),
    "30",
)


# --------------------------------------------------------------------------
# OCR settings
# --------------------------------------------------------------------------
MIN_TEXT_CHARS_PER_PAGE: int = _parse_positive_int(
    "MIN_TEXT_CHARS_PER_PAGE",
    os.getenv("MIN_TEXT_CHARS_PER_PAGE"),
    "30",
)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".jpg", ".jpeg", ".png"}
)


# --------------------------------------------------------------------------
# Invoice validation settings
# --------------------------------------------------------------------------
AMOUNT_TOLERANCE: Decimal = _parse_nonnegative_decimal(
    "AMOUNT_TOLERANCE",
    os.getenv("AMOUNT_TOLERANCE"),
    "1.00",
)


# --------------------------------------------------------------------------
# Runtime checks
# --------------------------------------------------------------------------
def require_groq_api_key() -> str:
    """Return the Groq API key or raise a clear configuration error."""

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your project-root "
            ".env file (GROQ_API_KEY=your_key) and restart the program."
        )

    return GROQ_API_KEY
