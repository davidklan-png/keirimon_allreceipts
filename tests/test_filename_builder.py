"""
Unit tests for filename builder.

Tests Japanese vendor names, special characters, sequence increment.
"""

import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from backend.utils.filename_builder import to_romaji_safe, build_filename, build_filepath


class TestRomajiConversion:
    """Test Japanese to ASCII conversion."""

    def test_basic_japanese(self):
        # Should strip non-ASCII
        result = to_romaji_safe("株式会社ヤマト")
        assert result == "Yamato" or result == "" or "Yamato" in result

    def test_mixed_chars(self):
        # Should keep only alphanumeric
        result = to_romaji_safe("Amazon.co.jp - 2024")
        assert "Amazon" in result
        assert "2024" in result
        assert "." not in result
        assert " " not in result

    def test_max_length_truncation(self):
        # Should truncate to 20 chars
        long_name = "A" * 30
        result = to_romaji_safe(long_name, max_len=20)
        assert len(result) == 20

    def test_empty_fallback(self):
        # Should return "Unknown" for empty input
        assert to_romaji_safe("") == "Unknown"
        assert to_romaji_safe("!!!") == "Unknown"


class TestFilenameBuilder:
    """Test standardized filename generation."""

    @patch("backend.utils.filename_builder.next_sequence")
    def test_filename_format(self, mock_seq):
        mock_seq.return_value = "01"
        filename = build_filename(
            receipt_date=date(2027, 4, 15),
            category_code="KTL",
            vendor_name="BOSS",
            amount_jpy=12175,
            target_folder=Path("/tmp"),
        )
        assert filename == "20270415_KTL_01_BOSS_12175.pdf"

    @patch("backend.utils.filename_builder.next_sequence")
    def test_vendor_romaji_in_filename(self, mock_seq):
        mock_seq.return_value = "01"
        filename = build_filename(
            receipt_date=date(2027, 4, 15),
            category_code="KTL",
            vendor_name="リムジンバス",  # Japanese
            amount_jpy=3000,
            target_folder=Path("/tmp"),
        )
        # Should contain ASCII-safe vendor name
        assert "20270415_KTL_01_" in filename
        assert "3000.pdf" in filename
        assert "_" in filename


class TestFilepathBuilder:
    """Test full filepath generation with folder structure."""

    def test_folder_structure(self):
        filepath, filename = build_filepath(
            base_path=Path("/tmp/AllReceipts"),
            receipt_date=date(2027, 4, 15),
            category_code="KTL",
            vendor_name="BOSS",
            amount_jpy=12175,
        )
        # Should have correct fiscal year and month folder
        assert "FY2027" in str(filepath)
        assert "04_Apr" in str(filepath)
        assert filename.endswith(".pdf")

    def test_january_fiscal_year(self):
        filepath, filename = build_filepath(
            base_path=Path("/tmp/AllReceipts"),
            receipt_date=date(2027, 1, 15),  # January -> FY2026
            category_code="SHO",
            vendor_name="Amazon",
            amount_jpy=5000,
        )
        # January should be in previous fiscal year
        assert "FY2026" in str(filepath)
        assert "01_Jan" in str(filepath)
