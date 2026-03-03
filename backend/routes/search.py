"""
Search routes — query receipts by date, amount, vendor, category, FY.
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Receipt, ReceiptRead

router = APIRouter()


@router.get("/search")
def search_receipts(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    min_jpy: Optional[int] = None,
    max_jpy: Optional[int] = None,
    vendor: Optional[str] = None,
    category: Optional[str] = None,
    fy: Optional[str] = None,
    is_recurring: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """
    Search receipts with multiple filters.

    All filters are optional and combined with AND.
    Returns paginated results.
    """
    query = select(Receipt)

    # Date range filter
    if from_date:
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
            query = query.where(Receipt.receipt_date >= start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format. Use YYYY-MM-DD")

    if to_date:
        try:
            end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
            query = query.where(Receipt.receipt_date <= end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format. Use YYYY-MM-DD")

    # Amount range filter
    if min_jpy is not None:
        query = query.where(Receipt.amount_jpy >= min_jpy)
    if max_jpy is not None:
        query = query.where(Receipt.amount_jpy <= max_jpy)

    # Vendor filter (case-insensitive substring match)
    if vendor:
        query = query.where(Receipt.vendor_name.ilike(f"%{vendor}%"))

    # Category filter
    if category:
        query = query.where(Receipt.category_code == category)

    # Fiscal year filter
    if fy:
        # Ensure FY prefix if not provided
        fy_value = fy if fy.startswith("FY") else f"FY{fy}"
        query = query.where(Receipt.fiscal_year == fy_value)

    # Recurring filter
    if is_recurring is not None:
        query = query.where(Receipt.is_recurring == is_recurring)

    # Order by date descending (newest first)
    query = query.order_by(Receipt.receipt_date.desc())

    # Get total count before pagination
    count_query = select(Receipt.id)
    # Apply same filters to count query (simplified - would be better to refactor)
    # For now, we'll fetch results and count

    # Apply pagination
    query = query.offset(offset).limit(limit)

    results = session.exec(query).all()

    return {
        "total": len(results),
        "results": [ReceiptRead.from_orm(r) for r in results],
        "limit": limit,
        "offset": offset,
    }
