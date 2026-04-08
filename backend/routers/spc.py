"""Feature 15: SPC (Summary of Plan Coverage) Parser — extract structured benefit data from SPC PDFs."""

import logging
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.spc_service import parse_spc, compare_spcs
from services.usage_service import log_file_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/spc", tags=["SPC Parser"])


def _extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    """
    Extract text from an uploaded file.
    Supports PDF (via PyPDF2/pdfplumber if available) and plain text.
    """
    if filename.lower().endswith(".pdf"):
        # Try pdfplumber first (better table extraction), then PyPDF2
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                extracted = "\n\n".join(pages)
                if extracted.strip():
                    logger.info(f"Extracted {len(pages)} pages via pdfplumber from {filename}")
                    return extracted
        except ImportError:
            logger.debug("pdfplumber not available, trying PyPDF2")
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}, trying PyPDF2")

        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            extracted = "\n\n".join(pages)
            if extracted.strip():
                logger.info(f"Extracted {len(pages)} pages via PyPDF2 from {filename}")
                return extracted
        except ImportError:
            logger.warning("Neither pdfplumber nor PyPDF2 available for PDF extraction")
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")

        raise HTTPException(
            status_code=422,
            detail="Could not extract text from PDF. Install pdfplumber or PyPDF2, or upload a plain text file.",
        )

    # Plain text file
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=422, detail="Could not decode file as text. Please upload a PDF or UTF-8 text file.")


class SPCTextRequest(BaseModel):
    """For submitting SPC text directly (e.g. from a frontend text area)."""
    text: str
    plan_name: Optional[str] = None


class SPCCompareTextRequest(BaseModel):
    """For submitting two SPC texts directly for comparison."""
    text_a: str
    text_b: str
    plan_a_name: Optional[str] = None
    plan_b_name: Optional[str] = None


@router.post("/parse")
async def parse_spc_upload(file: UploadFile = File(None), body: SPCTextRequest = None):
    """
    Parse an SPC/SBC document and extract structured benefit data.

    Accepts either:
    - A file upload (PDF or text) via multipart form
    - A JSON body with the text field
    """
    text = None

    if file is not None:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
        text = _extract_text_from_upload(contents, file.filename or "upload.txt")
    elif body is not None and body.text:
        text = body.text
    else:
        raise HTTPException(status_code=400, detail="Provide either a file upload or a JSON body with 'text' field.")

    if not text or len(text.strip()) < 50:
        raise HTTPException(status_code=422, detail="Extracted text is too short to be a valid SPC document.")

    logger.info(f"Parsing SPC document, text length={len(text)}")

    result = await parse_spc(text)

    # Persist the original upload (raw bytes + extracted text) into the
    # data collection layer so every plan document the user has ever fed
    # the product is recoverable byte-for-byte.
    if file is not None:
        try:
            log_file_upload(
                upload_kind="plan_document",
                filename=file.filename,
                content_type=file.content_type,
                file_bytes=contents,
                extracted_text=text,
            )
        except Exception as e:
            logger.debug(f"file_upload logging failed: {e}")

    return {
        "status": "success",
        "source": file.filename if file else "text_input",
        "text_length": len(text),
        "benefits": result,
    }


@router.post("/compare")
async def compare_spc_uploads(
    file_a: UploadFile = File(None),
    file_b: UploadFile = File(None),
    body: SPCCompareTextRequest = None,
):
    """
    Compare two SPC/SBC documents side by side.

    Accepts either:
    - Two file uploads (PDF or text) via multipart form (file_a and file_b)
    - A JSON body with text_a and text_b fields
    """
    text_a = None
    text_b = None

    if file_a is not None and file_b is not None:
        contents_a = await file_a.read()
        contents_b = await file_b.read()

        if len(contents_a) == 0 or len(contents_b) == 0:
            raise HTTPException(status_code=400, detail="Both uploaded files must be non-empty.")
        if len(contents_a) > 10 * 1024 * 1024 or len(contents_b) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Files too large. Maximum size is 10MB each.")

        text_a = _extract_text_from_upload(contents_a, file_a.filename or "plan_a.txt")
        text_b = _extract_text_from_upload(contents_b, file_b.filename or "plan_b.txt")
    elif body is not None and body.text_a and body.text_b:
        text_a = body.text_a
        text_b = body.text_b
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either two file uploads (file_a and file_b) or a JSON body with 'text_a' and 'text_b' fields.",
        )

    if not text_a or len(text_a.strip()) < 50:
        raise HTTPException(status_code=422, detail="Plan A text is too short to be a valid SPC document.")
    if not text_b or len(text_b.strip()) < 50:
        raise HTTPException(status_code=422, detail="Plan B text is too short to be a valid SPC document.")

    logger.info(f"Comparing SPC documents, text_a={len(text_a)} chars, text_b={len(text_b)} chars")

    result = await compare_spcs(text_a, text_b)

    # Persist BOTH plan documents for comparison runs.
    if file_a is not None and file_b is not None:
        try:
            log_file_upload(
                upload_kind="plan_document",
                filename=file_a.filename,
                content_type=file_a.content_type,
                file_bytes=contents_a,
                extracted_text=text_a,
            )
            log_file_upload(
                upload_kind="plan_document",
                filename=file_b.filename,
                content_type=file_b.content_type,
                file_bytes=contents_b,
                extracted_text=text_b,
            )
        except Exception as e:
            logger.debug(f"file_upload logging failed: {e}")

    return {
        "status": "success",
        "source_a": file_a.filename if file_a else "text_input",
        "source_b": file_b.filename if file_b else "text_input",
        "comparison": result,
    }
