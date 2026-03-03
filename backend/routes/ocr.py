"""
OCR routes — upload receipt for OCR extraction.
"""

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session

from ..database import get_session
from ..models import OcrResult
from ..services.ocr_service import process_receipt_upload

router = APIRouter()

UPLOAD_TEMP_PATH = Path(os.getenv("UPLOAD_TEMP_PATH", "/tmp/receipt_uploads"))
UPLOAD_TEMP_PATH.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/ocr/upload")
async def ocr_upload(
    file: UploadFile = File(...),
):
    """
    Upload receipt for OCR extraction.

    Accepts PDF, JPEG, PNG up to 20MB.
    Returns extracted fields with confidence scores.
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate unique ID for this upload
    upload_id = str(uuid.uuid4())
    temp_file_path = UPLOAD_TEMP_PATH / f"{upload_id}{file_ext}"

    try:
        # Save uploaded file to temp location
        contents = await file.read()

        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        temp_file_path.write_bytes(contents)

        # Process with OCR
        ocr_id, extracted, suggested_category, suggested_filename, nta_status = \
            await process_receipt_upload(temp_file_path)

        # Rename temp file to use ocr_id for later retrieval
        ocr_temp_path = UPLOAD_TEMP_PATH / f"{ocr_id}{file_ext}"
        temp_file_path.rename(ocr_temp_path)

        return {
            "ocr_id": ocr_id,
            "extracted": extracted.dict(),
            "suggested_category": suggested_category,
            "suggested_filename": suggested_filename,
            "nta_status": nta_status,
            "temp_file": str(ocr_temp_path),
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise
    except Exception as e:
        # Clean up temp file on error
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@router.get("/ocr/status/{ocr_id}")
def ocr_status(ocr_id: str):
    """
    Check if an OCR result is still available (not yet filed).

    OCR results are kept in temp for a limited time.
    """
    temp_files = list(UPLOAD_TEMP_PATH.glob(f"{ocr_id}.*"))

    if not temp_files:
        raise HTTPException(status_code=404, detail="OCR result not found or expired")

    return {
        "ocr_id": ocr_id,
        "status": "pending",
        "expires_at": "1 hour from upload",  # TODO: implement actual expiry
    }
