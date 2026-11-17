"""OCR: invoice file -> raw text."""
from typing import TypedDict


class OCRResult(TypedDict):
    text: str
    page_errors: list[str]


def extract_text(file_path: str) -> OCRResult:
    """Return raw text + per-page errors. PDF -> images -> Tesseract/EasyOCR."""
    raise NotImplementedError
