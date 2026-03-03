"""
Receipt routes — file, get, delete receipts.
"""

import os
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session

from ..database import get_session
from ..models import Receipt, ReceiptCreate, ReceiptRead
from ..services.filing_service import file_receipt, delete_receipt, get_receipt as get_receipt_service
from ..services.ocr_service import process_receipt_upload

router = APIRouter()

UPLOAD_TEMP_PATH = Path(os.getenv("UPLOAD_TEMP_PATH", "/tmp/receipt_uploads"))
UPLOAD_TEMP_PATH.mkdir(parents=True, exist_ok=True)


@router.post("/receipts", response_model=ReceiptRead)
async def create_receipt(
    receipt_data: ReceiptCreate,
    session: Session = Depends(get_session),
):
    """
    File a confirmed receipt.

    Expects OCR to have already been run (ocr_id references the OCR result).
    Copies file to target folder, writes DB entry, appends audit log.
    """
    # In a real implementation, we'd:
    # 1. Verify ocr_id exists and temp file is still present
    # 2. Load the temp file
    # 3. Call file_receipt()

    # For now, we need the temp file path - this would come from OCR step
    temp_file = UPLOAD_TEMP_PATH / f"{receipt_data.ocr_id}.pdf"

    if not temp_file.exists():
        raise HTTPException(status_code=404, detail="OCR upload not found or expired")

    try:
        receipt = file_receipt(
            temp_file_path=temp_file,
            receipt_date=receipt_data.receipt_date,
            category_code=receipt_data.category_code,
            vendor_name=receipt_data.vendor_name,
            amount_jpy=receipt_data.amount_jpy,
            amount_foreign=receipt_data.amount_foreign,
            currency_foreign=receipt_data.currency_foreign,
            registration_number=receipt_data.registration_number,
            payment_method=receipt_data.payment_method,
            notes=receipt_data.notes,
            filename_override=receipt_data.filename_override,
        )

        # Clean up temp file after successful filing
        temp_file.unlink()

        return ReceiptRead.from_orm(receipt)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/receipts/{receipt_id}", response_model=ReceiptRead)
def get_receipt(
    receipt_id: int,
    session: Session = Depends(get_session),
):
    """Get a receipt by ID."""
    receipt = get_receipt_service(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return ReceiptRead.from_orm(receipt)


@router.delete("/receipts/{receipt_id}")
def delete_receipt_endpoint(
    receipt_id: int,
    session: Session = Depends(get_session),
):
    """
    Delete a receipt.

    Blocked if within 7-year retention period.
    """
    try:
        delete_receipt(receipt_id)
        return {"message": "Receipt deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        if "保存義務" in str(e) or "7年" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/receipts", response_model=list[ReceiptRead])
def list_receipts(
    fiscal_year: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """List receipts with optional filters."""
    query = session.query(Receipt)

    if fiscal_year:
        query = query.filter(Receipt.fiscal_year == fiscal_year)
    if category:
        query = query.filter(Receipt.category_code == category)

    query = query.order_by(Receipt.receipt_date.desc())
    query = query.offset(offset).limit(limit)

    receipts = query.all()
    return [ReceiptRead.from_orm(r) for r in receipts]
