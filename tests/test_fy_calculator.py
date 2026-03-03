"""
Unit tests for fiscal year calculator.

Tests boundary cases (Jan 31, Feb 1, Feb 29 leap year).
"""

import pytest
from datetime import date

from backend.utils.fy_calculator import get_fiscal_year, get_month_folder, is_within_retention_period


class TestFiscalYear:
    """Test fiscal year calculation rules."""

    def test_february_returns_current_year(self):
        assert get_fiscal_year(date(2027, 2, 1)) == "FY2027"
        assert get_fiscal_year(date(2027, 2, 15)) == "FY2027"
        assert get_fiscal_year(date(2027, 2, 28)) == "FY2027"

    def test_january_returns_previous_year(self):
        assert get_fiscal_year(date(2027, 1, 1)) == "FY2026"
        assert get_fiscal_year(date(2027, 1, 15)) == "FY2026"
        assert get_fiscal_year(date(2027, 1, 31)) == "FY2026"

    def test_all_other_months_return_current_year(self):
        for month in range(3, 13):
            assert get_fiscal_year(date(2027, month, 15)) == "FY2027"

    def test_leap_year_february(self):
        # Feb 29 exists in leap years
        assert get_fiscal_year(date(2028, 2, 29)) == "FY2028"


class TestMonthFolder:
    """Test month folder naming."""

    def test_all_months(self):
        assert get_month_folder(date(2027, 1, 15)) == "01_Jan"
        assert get_month_folder(date(2027, 2, 15)) == "02_Feb"
        assert get_month_folder(date(2027, 3, 15)) == "03_Mar"
        assert get_month_folder(date(2027, 4, 15)) == "04_Apr"
        assert get_month_folder(date(2027, 5, 15)) == "05_May"
        assert get_month_folder(date(2027, 6, 15)) == "06_Jun"
        assert get_month_folder(date(2027, 7, 15)) == "07_Jul"
        assert get_month_folder(date(2027, 8, 15)) == "08_Aug"
        assert get_month_folder(date(2027, 9, 15)) == "09_Sep"
        assert get_month_folder(date(2027, 10, 15)) == "10_Oct"
        assert get_month_folder(date(2027, 11, 15)) == "11_Nov"
        assert get_month_folder(date(2027, 12, 15)) == "12_Dec"


class TestRetentionPeriod:
    """Test 7-year retention lock."""

    def test_recent_receipt_within_retention(self):
        # A receipt from 2 years ago should be locked
        from datetime import date as today_date
        recent_date = today_date(today_date.today().year - 2, 1, 1)
        assert is_within_retention_period(recent_date) is True

    def test_old_receipt_outside_retention(self):
        # A receipt from 8 years ago should be unlocked
        from datetime import date as today_date
        old_date = today_date(today_date.today().year - 8, 1, 1)
        assert is_within_retention_period(old_date) is False
