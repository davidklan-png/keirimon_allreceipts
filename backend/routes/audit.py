"""
Audit routes — verify receipt integrity for compliance.
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..services.audit_service import verify_integrity, get_audit_log_tail

router = APIRouter()


@router.get("/audit/verify")
def audit_verify():
    """
    Verify all filed receipts against audit log.

    Checks SHA-256 hashes for tamper detection.
    Returns list of any files with mismatched hashes.
    """
    base_path = Path(os.getenv("RECEIPTS_BASE_PATH", "./AllReceipts"))
    audit_log_path = Path(os.getenv("AUDIT_LOG_PATH", base_path / "audit.log"))

    if not audit_log_path.exists():
        return {
            "checked": 0,
            "ok": 0,
            "tampered": [],
            "message": "Audit log not found. No receipts filed yet."
        }

    result = verify_integrity(audit_log_path, base_path)

    return result


@router.get("/audit/log")
def audit_log_tail(lines: int = 100):
    """
    Get recent entries from the audit log.

    Useful for displaying recent activity in the UI.
    """
    audit_log_path = Path(os.getenv(
        "AUDIT_LOG_PATH",
        Path(os.getenv("RECEIPTS_BASE_PATH", "./AllReceipts")) / "audit.log"
    ))

    if not audit_log_path.exists():
        return {
            "entries": [],
            "message": "Audit log not found."
        }

    entries = get_audit_log_tail(audit_log_path, lines)

    return {
        "entries": entries,
        "count": len(entries),
    }


@router.get("/audit/stats")
def audit_stats():
    """
    Get audit statistics.
    """
    base_path = Path(os.getenv("RECEIPTS_BASE_PATH", "./AllReceipts"))
    audit_log_path = Path(os.getenv("AUDIT_LOG_PATH", base_path / "audit.log"))

    if not audit_log_path.exists():
        return {
            "log_exists": False,
            "total_entries": 0,
            "create_events": 0,
            "delete_events": 0,
        }

    entries = get_audit_log_tail(audit_log_path, lines=100000)  # Get all

    create_count = sum(1 for e in entries if e.get("event") == "CREATE")
    delete_count = sum(1 for e in entries if e.get("event") == "DELETE")

    return {
        "log_exists": True,
        "log_path": str(audit_log_path),
        "total_entries": len(entries),
        "create_events": create_count,
        "delete_events": delete_count,
    }
