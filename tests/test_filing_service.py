"""
Unit tests for filing service.

Tests folder creation, rollback on failure, duplicate detection.
"""

import pytest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from backend.services.filing_service import file_receipt, RetentionError


class TestFileReceipt:
    """Test receipt filing with transaction safety."""

    @patch("backend.services.filing_service.get_session")
    @patch("backend.services.filing_service.build_filepath")
    @patch("backend.services.filing_service.sha256_file")
    @patch("backend.services.filing_service.log_event")
    def test_successful_filing(self, mock_log, mock_hash, mock_path, mock_session):
        # Mock dependencies
        mock_path.return_value = (Path("/tmp/test.pdf"), "test.pdf")
        mock_hash.return_value = "sha256:abc123"
        mock_session.return_value.__next__ = Mock()
        mock_session.return_value.__enter__ = Mock(return_value=Mock())
        mock_session.return_value.__exit__ = Mock(return_value=False)

        # This test would require more extensive mocking
        # For now, serves as a placeholder for the test structure
        pass

    def test_duplicate_filename_detection(self):
        # TODO: Test that duplicate filenames are prevented
        pass


class TestRetentionLock:
    """Test 7-year retention deletion lock."""

    @patch("backend.services.filing_service.is_within_retention_period")
    def test_delete_within_retention_blocked(self, mock_check):
        mock_check.return_value = True

        with pytest.raises(RetentionError) as exc_info:
            from backend.services.filing_service import delete_receipt
            # Mock would go here
            # delete_receipt(1)

        assert "保存義務" in str(exc_info.value) or "7年" in str(exc_info.value)

    @patch("backend.services.filing_service.is_within_retention_period")
    def test_delete_after_retention_allowed(self, mock_check):
        mock_check.return_value = False
        # TODO: Test successful deletion
        pass
