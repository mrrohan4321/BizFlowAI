
from types import SimpleNamespace

import pymupdf
import pytest
from PIL import Image

from ai_ml import ocr


class FakeOCREngine:
    def __init__(self, result=None):
        self.result = result or SimpleNamespace(
            txts=["Invoice Number: INV-001", "Total: 7080"]
        )
        self.calls = []

    def __call__(self, file_path):
        self.calls.append(file_path)
        return self.result


def create_image(path):
    Image.new("RGB", (100, 100), "white").save(path)


def test_extract_text_from_image(monkeypatch, tmp_path):
    image_path = tmp_path / "invoice.png"
    create_image(image_path)

    engine = FakeOCREngine()
    monkeypatch.setattr(ocr, "ocr_engine", engine)

    result = ocr.extract_text_from_image(image_path)

    assert "Invoice Number: INV-001" in result
    assert "Total: 7080" in result
    assert len(engine.calls) == 1


def test_extract_text_from_image_returns_empty_when_no_text(
    monkeypatch,
    tmp_path,
):
    image_path = tmp_path / "blank.png"
    create_image(image_path)

    engine = FakeOCREngine(
        SimpleNamespace(txts=[])
    )
    monkeypatch.setattr(ocr, "ocr_engine", engine)

    assert ocr.extract_text_from_image(image_path) == ""


def test_missing_image_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        ocr.extract_text_from_image(tmp_path / "missing.png")


def test_invalid_image_raises_error(tmp_path):
    image_path = tmp_path / "invalid.png"
    image_path.write_text("This is not an image.")

    with pytest.raises(ValueError, match="Cannot read invoice image"):
        ocr.extract_text_from_image(image_path)


def test_extract_text_from_digital_pdf(tmp_path):
    pdf_path = tmp_path / "digital_invoice.pdf"

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Invoice Number INV-001. Customer ABC Traders. "
            "Subtotal 6000. Tax 1080. Total 7080.",
        )
        document.save(pdf_path)

    result = ocr.extract_text_from_pdf(pdf_path)

    assert "INV-001" in result
    assert "ABC Traders" in result


def test_scanned_pdf_page_uses_ocr_and_cleans_temp_file(
    monkeypatch,
    tmp_path,
):
    pdf_path = tmp_path / "scanned_invoice.pdf"

    with pymupdf.open() as document:
        document.new_page()
        document.save(pdf_path)

    captured_paths = []

    def fake_extract_text_from_image(path):
        path = __import__("pathlib").Path(path)
        captured_paths.append(path)

        assert path.exists()
        return "Scanned invoice OCR text"

    monkeypatch.setattr(
        ocr,
        "extract_text_from_image",
        fake_extract_text_from_image,
    )

    result = ocr.extract_text_from_pdf(pdf_path)

    assert result == "Scanned invoice OCR text"
    assert len(captured_paths) == 1
    assert not captured_paths[0].exists()


def test_unsupported_invoice_format_raises_error(tmp_path):
    file_path = tmp_path / "invoice.docx"
    file_path.write_text("Not a supported invoice.")

    with pytest.raises(ValueError, match="Unsupported invoice format"):
        ocr.extract_invoice_text(file_path)


def test_empty_pdf_returns_empty_text(monkeypatch, tmp_path):
    pdf_path = tmp_path / "empty.pdf"

    # Create a valid PDF containing one blank page.
    with pymupdf.open() as document:
        document.new_page()
        document.save(pdf_path)

    # Simulate OCR finding no text on the blank page.
    monkeypatch.setattr(
        ocr,
        "extract_text_from_image",
        lambda path: "",
    )

    assert ocr.extract_text_from_pdf(pdf_path) == ""
