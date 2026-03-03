"""
Fiscal year calculation utilities.

Japan fiscal year for this GK: February 1 – January 31.

Examples:
    2027-04-15 → FY2027
    2027-01-30 → FY2026
    2028-02-01 → FY2027 (first day of new FY)
"""

from datetime import date

MONTH_FOLDERS = {
    1: "01_Jan",
    2: "02_Feb",
    3: "03_Mar",
    4: "04_Apr",
    5: "05_May",
    6: "06_Jun",
    7: "07_Jul",
    8: "08_Aug",
    9: "09_Sep",
    10: "10_Oct",
    11: "11_Nov",
    12: "12_Dec",
}


def get_fiscal_year(receipt_date: date) -> str:
    """
    Calculate fiscal year from receipt date.

    FY runs Feb 1 – Jan 31.
    Jan 2027 → FY2026. Feb 2027 → FY2027.
    """
    if receipt_date.month == 1:
        return f"FY{receipt_date.year - 1}"
    return f"FY{receipt_date.year}"


def get_month_folder(receipt_date: date) -> str:
    """Get month folder name like '04_Apr' from receipt date."""
    return MONTH_FOLDERS[receipt_date.month]


def calculate_retention_date(receipt_date: date, years: int = 7) -> date:
    """
    Calculate retention end date (7 years from receipt date).
    Used for deletion lock enforcement.
    """
    # Same month and day, year + 7
    return receipt_date.replace(year=receipt_date.year + years)


def is_within_retention_period(receipt_date: date, years: int = 7) -> bool:
    """
    Check if receipt is within retention period.
    Returns True if deletion should be blocked.
    """
    from datetime import date as today_date

    retention_end = calculate_retention_date(receipt_date, years)
    return today_date.today() <= retention_end
