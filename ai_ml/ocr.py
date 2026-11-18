
"""OCR utilities for invoice images and PDF files."""

import logging
import tempfile
from pathlib import Path

import pymupdf
from PIL import Image
from rapidocr import RapidOCR

from ai_ml import config

logger = logging.getLogger(__name__)

# Initialize the OCR engine only when it is first needed.
# This avoids loading the OCR model just because another module imports this file.
ocr_engine = None


def _get_ocr_engine():
    """Return the shared RapidOCR engine, initializing it when necessary."""

    global ocr_engine

    if ocr_engine is None:
        ocr_engine = RapidOCR()

    return ocr_engine


def extract_text_from_image(file_path: str | Path) -> str:
    """Extract text from a PNG, JPG, or JPEG invoice image."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Invoice image not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Invoice image path is not a file: {file_path}")

    # Verify that the file is a readable image before passing it to OCR.
    try:
        with Image.open(file_path) as image:
            image.verify()
    except Exception as exc:
        raise ValueError(
            f"Cannot read invoice image '{file_path}': {exc}"
        ) from exc

    result = _get_ocr_engine()(str(file_path))

    if result is None or not result.txts:
        logger.info("No text detected in image: %s", file_path.name)
        return ""

    return "\n".join(
        text.strip()
        for text in result.txts
        if isinstance(text, str) and text.strip()
    )


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract text from digital and scanned PDF invoices."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Invoice PDF not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Invoice PDF path is not a file: {file_path}")

    extracted_pages = []

    try:
        with pymupdf.open(file_path) as pdf:

            if pdf.needs_pass:
                raise ValueError(
                    "The invoice PDF is password-protected. "
                    "Provide an unlocked PDF."
                )

            if len(pdf) == 0:
                return ""

            for page_number, page in enumerate(pdf, start=1):

                # First try extracting embedded PDF text.
                page_text = page.get_text().strip()

                if len(page_text) >= config.MIN_TEXT_CHARS_PER_PAGE:
                    extracted_pages.append(page_text)
                    continue

                # Sparse or scanned pages need OCR.
                # A unique temporary filename avoids collisions between
                # simultaneous invoice-processing operations.
                temporary_path = None

                try:
                    pixmap = page.get_pixmap(
                        matrix=pymupdf.Matrix(2, 2),
                        alpha=False,
                    )

                    with tempfile.NamedTemporaryFile(
                        suffix=".png",
                        prefix="bizflow_ocr_",
                        delete=False,
                    ) as temporary_file:
                        temporary_path = Path(temporary_file.name)

                    pixmap.save(str(temporary_path))

                    page_text = extract_text_from_image(temporary_path)
                    extracted_pages.append(page_text)

                except Exception as exc:
                    raise RuntimeError(
                        f"OCR failed on PDF page {page_number}: {exc}"
                    ) from exc

                finally:
                    if temporary_path is not None:
                        try:
                            temporary_path.unlink(missing_ok=True)
                        except OSError:
                            logger.warning(
                                "Could not remove temporary OCR file: %s",
                                temporary_path,
                            )

    except ValueError:
        # Preserve clear errors such as password protection.
        raise
    except RuntimeError:
        # Preserve page-specific OCR errors.
        raise
    except Exception as exc:
        raise ValueError(
            f"Could not read invoice PDF '{file_path}': {exc}"
        ) from exc

    return "\n\n".join(
        text for text in extracted_pages if text.strip()
    )


def extract_invoice_text(file_path: str | Path) -> str:
    """Extract invoice text from supported image or PDF formats."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Invoice file not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Invoice path is not a file: {file_path}")

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)

    if extension in {".png", ".jpg", ".jpeg"}:
        return extract_text_from_image(file_path)

    raise ValueError(
        f"Unsupported invoice format: {extension or 'no extension'}"
    )
