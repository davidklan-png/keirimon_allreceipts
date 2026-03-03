"""
Filing service — handles receipt file storage and ledger entry.

Orchestrates: file copy, database write, audit log, rollback on failure.
"""

import os
import shutil
from datetime import date
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from ..database import get_session
from ..models import Receipt
from ..utils.filename_builder import build_filepath
from ..utils.hash_utils import sha256_file
from ..utils.fy_calculator import calculate_retention_date, is_within_retention_period
from .audit_service import log_event

load_dotenv()

RECEIPTS_BASE_PATH = Path(os.getenv("RECEIPTS_BASE_PATH", "./AllReceipts"))
UPLOAD_TEMP_PATH = Path(os.getenv("UPLOAD_TEMP_PATH", "/tmp/receipt_uploads"))


def file_receipt(
    temp_file_path: Path,
    receipt_date: date,
    category_code: str,
    vendor_name: str,
    amount_jpy: int,
    amount_foreign: Optional[float] = None,
    currency_foreign: Optional[str] = None,
    registration_number: Optional[str] = None,
    category_name_jp: Optional[str] = None,
    payment_method: str = "AMEX",
    notes: Optional[str] = None,
    filename_override: Optional[str] = None,
) -> Receipt:
    """
    File a receipt with full transaction safety.

    On success: copies file, writes DB entry, appends audit log
    On failure: rolls back (deletes copied file, no DB write)

    Returns: Created Receipt record
    """

    from ..utils.fy_calculator import get_fiscal_year

    # Determine category name from code
    if not category_name_jp:
        category_name_jp = _get_category_name(category_code)

    # Build target filepath
    if filename_override:
        # Use custom filename (user override)
        filename = filename_override
        fiscal_year = get_fiscal_year(receipt_date)
        month_folder = _get_month_folder(receipt_date)
        target_folder = RECEIPTS_BASE_PATH / fiscal_year / month_folder
        target_folder.mkdir(parents=True, exist_ok=True)
        filepath = target_folder / filename
    else:
        filepath, filename = build_filepath(
            base_path=RECEIPTS_BASE_PATH,
            receipt_date=receipt_date,
            category_code=category_code,
            vendor_name=vendor_name,
            amount_jpy=amount_jpy,
        )

    # Calculate hash before moving
    file_hash = sha256_file(temp_file_path)

    # Calculate retention date
    retention_until = calculate_retention_date(receipt_date)

    # Build relative filepath for storage
    fiscal_year = get_fiscal_year(receipt_date)
    month_folder = _get_month_folder(receipt_date)
    relative_filepath = f"{fiscal_year}/{month_folder}/{filename}"

    try:
        # Copy file to target location
        shutil.copy2(temp_file_path, filepath)

        # Write database entry
        with next(get_session()) as session:
            receipt = Receipt(
                receipt_date=receipt_date,
                fiscal_year=fiscal_year,
                category_code=category_code,
                category_name_jp=category_name_jp,
                vendor_name=vendor_name,
                amount_jpy=amount_jpy,
                amount_foreign=amount_foreign,
                currency_foreign=currency_foreign,
                registration_number=registration_number,
                payment_method=payment_method,
                notes=notes,
                filename=filename,
                filepath=relative_filepath,
                file_hash_sha256=file_hash,
                retention_until=retention_until,
            )
            session.add(receipt)
            session.commit()
            session.refresh(receipt)

        # Write audit log (after successful DB commit)
        log_event(
            log_path=Path(os.getenv("AUDIT_LOG_PATH", RECEIPTS_BASE_PATH / "audit.log")),
            event="CREATE",
            filepath=relative_filepath,
            file_hash=file_hash,
        )

        return receipt

    except Exception as e:
        # Rollback: delete copied file if it exists
        if filepath.exists():
            filepath.unlink()
        raise e


def delete_receipt(receipt_id: int) -> bool:
    """
    Delete a receipt if outside retention period.

    Returns: True if deleted, False if blocked by retention
    Raises: Exception if deletion fails
    """
    with next(get_session()) as session:
        receipt = session.get(Receipt, receipt_id)
        if not receipt:
            raise ValueError(f"Receipt {receipt_id} not found")

        # Check retention period
        if is_within_retention_period(receipt.receipt_date):
            raise RetentionError(
                f"この領収書は法人税法上7年間の保存義務があります（保存期限：{receipt.retention_until}）"
            )

        # Delete file
        full_path = RECEIPTS_BASE_PATH / receipt.filepath
        if full_path.exists():
            full_path.unlink()

        # Log deletion
        log_event(
            log_path=Path(os.getenv("AUDIT_LOG_PATH", RECEIPTS_BASE_PATH / "audit.log")),
            event="DELETE",
            filepath=receipt.filepath,
            file_hash=receipt.file_hash_sha256,
        )

        # Delete database record
        session.delete(receipt)
        session.commit()

        return True


def get_receipt(receipt_id: int) -> Optional[Receipt]:
    """Get receipt by ID."""
    with next(get_session()) as session:
        return session.get(Receipt, receipt_id)


class RetentionError(Exception):
    """Raised when deletion is blocked by retention period."""
    pass


def _get_category_name(code: str) -> str:
    """Map category code to Japanese name."""
    CATEGORY_MAP = {
        "SHO": "消耗品費",
        "KTL": "接待交際費",
        "RND": "研究開発費",
        "TRS": "出張交通費",
        "LOC": "交通費",
        "ACC": "出張宿泊費",
        "WEL": "福利厚生費",
        "COM": "通信費",
        "MTG": "会議費",
        "EQP": "工具機器備品",
        "ADV": "広告宣伝費",
        "FEE": "支払手数料",
    }
    return CATEGORY_MAP.get(code, "その他")


def _get_month_folder(receipt_date: date) -> str:
    """Get month folder name."""
    from ..utils.fy_calculator import MONTH_FOLDERS
    return MONTH_FOLDERS[receipt_date.month]
