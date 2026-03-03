"""
Filename building utilities.

Generates standardized filenames: YYYYMMDD_CAT_NN_VENDOR_JPYAMT.pdf
"""

import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Optional

from .fy_calculator import get_fiscal_year, get_month_folder


def to_romaji_safe(text: str, max_len: int = 20) -> str:
    """
    Convert Japanese text to ASCII-safe romaji.
    Strips non-ASCII, collapses spaces, truncates to max_len.
    """
    # Normalize to NFKD and encode to ASCII, ignoring non-ASCII chars
    ascii_only = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    # Remove anything that's not alphanumeric
    safe = re.sub(r"[^A-Za-z0-9]", "", ascii_only)
    # Truncate and fallback
    return safe[:max_len] or "Unknown"


def next_sequence(base_path: Path, date_str: str, category_code: str) -> str:
    """
    Count existing files matching YYYYMMDD_CAT_* to get next NN.

    Returns zero-padded 2-digit sequence number.
    """
    pattern = f"{date_str}_{category_code}_*.pdf"
    existing = list(base_path.glob(pattern))
    return str(len(existing) + 1).zfill(2)


def build_filename(
    receipt_date: date,
    category_code: str,
    vendor_name: str,
    amount_jpy: int,
    target_folder: Path,
) -> str:
    """
    Build standardized filename: YYYYMMDD_CAT_NN_VENDOR_JPYAMT.pdf
    """
    date_str = receipt_date.strftime("%Y%m%d")
    nn = next_sequence(target_folder, date_str, category_code)
    vendor_safe = to_romaji_safe(vendor_name, max_len=20)
    return f"{date_str}_{category_code}_{nn}_{vendor_safe}_{amount_jpy}.pdf"


def build_filepath(
    base_path: Path,
    receipt_date: date,
    category_code: str,
    vendor_name: str,
    amount_jpy: int,
) -> tuple[Path, str]:
    """
    Build full filepath and return (filepath, filename).

    Creates folder structure if needed:
    {base_path}/FY{YYYY}/{MM_MonthName}/filename.pdf
    """
    fiscal_year = get_fiscal_year(receipt_date)
    month_folder = get_month_folder(receipt_date)

    target_folder = base_path / fiscal_year / month_folder
    target_folder.mkdir(parents=True, exist_ok=True)

    filename = build_filename(receipt_date, category_code, vendor_name, amount_jpy, target_folder)
    filepath = target_folder / filename

    return filepath, filename
