
from pathlib import Path
import logging

import pymupdf
from PIL import Image
from rapidocr import RapidOCR

logger = logging.getLogger(__name__)

# Initialize OCR engine
ocr_engine = RapidOCR()


def extract_text_from_image(file_path: str | Path) -> str:
    """Extract text from an invoice image using RapidOCR."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    result = ocr_engine(str(file_path))

    if not result or not result.txts:
        return ""

    return "\n".join(result.txts)


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract text from digital or scanned PDF invoices."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extracted_pages = []

    with pymupdf.open(file_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):

            # First try direct text extraction
            text = page.get_text().strip()

            if len(text) >= 30:
                extracted_pages.append(text)
                continue

            # If PDF page is scanned, convert it to an image
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
            image_path = file_path.parent / f"_ocr_temp_page_{page_number}.png"

            try:
                pixmap.save(image_path)
                page_text = extract_text_from_image(image_path)
                extracted_pages.append(page_text)
            finally:
                if image_path.exists():
                    image_path.unlink()

    return "\n\n".join(extracted_pages)


def extract_invoice_text(file_path: str | Path) -> str:
    """Main function: supports PDF, PNG, JPG and JPEG invoices."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)

    if extension in {".png", ".jpg", ".jpeg"}:
        return extract_text_from_image(file_path)

    raise ValueError(f"Unsupported invoice format: {extension}")
