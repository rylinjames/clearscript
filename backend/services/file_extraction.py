"""
Shared file text extraction for uploaded contracts, SPC documents, and
plan documents.

Supports:
  - PDF via pdfplumber (primary, better table handling) with PyPDF2 fallback
  - Plain text files with utf-8 → latin-1 decoding fallback

Previously each router (contracts, spc) reimplemented this with slightly
different fallback strategies and error handling. This module is the
single source of truth.
"""

import io
import logging

logger = logging.getLogger(__name__)


class FileExtractionError(Exception):
    """Raised when text cannot be extracted from an uploaded file."""


def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    """
    Extract text from an uploaded file. For PDFs, tries pdfplumber first
    (better table extraction), then PyPDF2. For text files, tries utf-8
    then latin-1.

    Raises FileExtractionError if no text can be extracted. Callers are
    expected to translate this into an appropriate HTTP 422.
    """
    lower = filename.lower()

    if lower.endswith(".pdf"):
        text = _extract_pdf(file_bytes, filename)
        if text.strip():
            return text
        raise FileExtractionError(
            "Could not extract text from PDF. If this is a scanned PDF, "
            "OCR is not yet supported — please upload a text-based PDF "
            "or a .txt / .docx copy."
        )

    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return file_bytes.decode("latin-1")
    except Exception as e:
        raise FileExtractionError(
            "Could not decode file as text. Please upload a PDF or UTF-8 text file."
        ) from e


def _extract_pdf(file_bytes: bytes, filename: str) -> str:
    """Try pdfplumber first, fall back to PyPDF2. Returns "" if both fail."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
            extracted = "\n\n".join(pages)
            if extracted.strip():
                logger.info(f"Extracted {len(pages)} pages via pdfplumber from {filename}")
                return extracted
    except ImportError:
        logger.debug("pdfplumber not available, trying PyPDF2")
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed on {filename}: {e}, trying PyPDF2")

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
        extracted = "\n\n".join(pages)
        if extracted.strip():
            logger.info(f"Extracted {len(pages)} pages via PyPDF2 from {filename}")
            return extracted
    except ImportError:
        logger.warning("Neither pdfplumber nor PyPDF2 available for PDF extraction")
    except Exception as e:
        logger.warning(f"PyPDF2 extraction failed on {filename}: {e}")

    return ""
