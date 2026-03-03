"""
Vendor routes — manage vendor-to-category lookup table.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Vendor, VendorRead, VendorCreate, VendorUpdate

router = APIRouter()


@router.get("/vendors", response_model=list[VendorRead])
def list_vendors(
    category_code: str = None,
    is_recurring: bool = None,
    session: Session = Depends(get_session),
):
    """List all vendors with optional filters."""
    query = select(Vendor)

    if category_code:
        query = query.where(Vendor.category_code == category_code)
    if is_recurring is not None:
        query = query.where(Vendor.is_recurring == is_recurring)

    query = query.order_by(Vendor.vendor_pattern)
    results = session.exec(query).all()
    return results


@router.post("/vendors", response_model=VendorRead)
def create_vendor(
    vendor_data: VendorCreate,
    session: Session = Depends(get_session),
):
    """
    Create a new vendor entry.

    If vendor_pattern already exists, returns error.
    """
    # Check for duplicate pattern
    existing = session.exec(
        select(Vendor).where(Vendor.vendor_pattern == vendor_data.vendor_pattern)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Vendor pattern '{vendor_data.vendor_pattern}' already exists"
        )

    vendor = Vendor.from_orm(vendor_data)
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return vendor


@router.get("/vendors/{vendor_id}", response_model=VendorRead)
def get_vendor(
    vendor_id: int,
    session: Session = Depends(get_session),
):
    """Get a vendor by ID."""
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.put("/vendors/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: int,
    vendor_data: VendorUpdate,
    session: Session = Depends(get_session),
):
    """Update an existing vendor."""
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Update only provided fields
    update_data = vendor_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(vendor, key, value)

    vendor.updated_at = datetime.utcnow()
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return vendor


@router.delete("/vendors/{vendor_id}")
def delete_vendor(
    vendor_id: int,
    session: Session = Depends(get_session),
):
    """Delete a vendor entry."""
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    session.delete(vendor)
    session.commit()
    return {"message": "Vendor deleted"}


@router.get("/vendors/lookup/{vendor_name}")
def lookup_vendor(
    vendor_name: str,
    session: Session = Depends(get_session),
):
    """
    Look up a category by vendor name.

    Returns the first matching vendor pattern found in the vendor name.
    Useful for auto-suggesting category during OCR confirmation.
    """
    vendors = session.exec(select(Vendor)).all()

    for vendor in vendors:
        if vendor.vendor_pattern.lower() in vendor_name.lower():
            return {
                "vendor_pattern": vendor.vendor_pattern,
                "category_code": vendor.category_code,
                "romaji_name": vendor.romaji_name,
                "is_recurring": vendor.is_recurring,
            }

    return {
        "vendor_pattern": None,
        "category_code": None,
        "romaji_name": None,
        "is_recurring": False,
    }
