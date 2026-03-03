"""
SQLModel table definitions for AllReceipts.

Data models defined in REQUIREMENTS.md §5
"""

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Receipt(SQLModel, table=True):
    """
    Receipt ledger entry.
    Corresponds to receipts table in REQUIREMENTS.md §5
    """

    __tablename__ = "receipts"

    id: Optional[int] = Field(default=None, primary_key=True)
    receipt_date: date = Field(index=True)
    fiscal_year: str = Field(index=True)

    statement_date: Optional[date] = None
    category_code: str = Field(index=True)
    category_name_jp: str
    vendor_name: str = Field(index=True)

    amount_jpy: int
    amount_foreign: Optional[float] = None
    currency_foreign: Optional[str] = None

    registration_number: Optional[str] = Field(default=None)
    nta_validated: bool = False

    payment_method: str = "AMEX"  # AMEX | CASH | OTHER
    is_recurring: bool = False

    notes: Optional[str] = None

    filename: str = Field(unique=True)
    filepath: str = Field(unique=True)
    file_hash_sha256: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
    retention_until: date


class Vendor(SQLModel, table=True):
    """
    Vendor-to-category lookup table.
    Mirrors data/vendors.json seed data.
    """

    __tablename__ = "vendors"

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_pattern: str = Field(unique=True, index=True)
    category_code: str
    romaji_name: str
    is_recurring: bool = False
    notes: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NtaCache(SQLModel, table=True):
    """
    NTA Invoice API validation cache.
    Reduces redundant API calls for 30 days.
    """

    __tablename__ = "nta_cache"

    registration_number: str = Field(primary_key=True)
    is_valid: bool
    company_name: Optional[str] = None
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


# Response models for API endpoints

class ReceiptRead(SQLModel):
    """Public view of a receipt (no internal fields)"""

    id: int
    receipt_date: date
    fiscal_year: str
    statement_date: Optional[date] = None
    category_code: str
    category_name_jp: str
    vendor_name: str
    amount_jpy: int
    amount_foreign: Optional[float] = None
    currency_foreign: Optional[str] = None
    registration_number: Optional[str] = None
    nta_validated: bool
    payment_method: str
    is_recurring: bool
    notes: Optional[str] = None
    filename: str
    filepath: str
    created_at: datetime
    retention_until: date


class ReceiptCreate(SQLModel):
    """Payload for filing a new receipt"""

    ocr_id: str
    receipt_date: date
    amount_jpy: int
    amount_foreign: Optional[float] = None
    currency_foreign: Optional[str] = None
    vendor_name: str
    registration_number: Optional[str] = None
    category_code: str
    payment_method: str = "AMEX"
    notes: Optional[str] = None
    filename_override: Optional[str] = None


class OcrResult(SQLModel):
    """OCR extraction result with confidence scores"""

    receipt_date: Optional[str] = None
    amount_jpy: Optional[int] = None
    amount_foreign: Optional[float] = None
    currency_foreign: Optional[str] = None
    vendor_name: Optional[str] = None
    registration_number: Optional[str] = None
    notes: Optional[str] = None
    confidence: dict = {}


# Vendor DTOs

class VendorRead(SQLModel):
    """Public view of a vendor"""

    id: int
    vendor_pattern: str
    category_code: str
    romaji_name: str
    is_recurring: bool
    notes: Optional[str] = None
    updated_at: datetime


class VendorCreate(SQLModel):
    """Payload for creating a new vendor"""

    vendor_pattern: str
    category_code: str
    romaji_name: str
    is_recurring: bool = False
    notes: Optional[str] = None


class VendorUpdate(SQLModel):
    """Payload for updating a vendor"""

    vendor_pattern: Optional[str] = None
    category_code: Optional[str] = None
    romaji_name: Optional[str] = None
    is_recurring: Optional[bool] = None
    notes: Optional[str] = None
