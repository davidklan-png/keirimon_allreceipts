"""
Audit service — append-only log for 電子帳簿保存法 compliance.

Every receipt filing event is logged with SHA-256 hash for tamper detection.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def log_event(log_path: Path, event: str, filepath: str, file_hash: str):
    """
    Append a JSON line to the audit log.

    Entry format:
    {"ts": "2027-04-15T10:23:01Z", "event": "CREATE", "file": "...", "user": "system", "hash": "sha256:..."}

    Events: CREATE, DELETE, VERIFY

    Note: Audit log is append-only. Never delete or modify entries.
    """
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "file": filepath,
        "user": "system",  # TODO: Add real user auth later
        "hash": file_hash,
    }

    # Ensure parent directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Append line
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def verify_integrity(
    log_path: Path, base_path: Path
) -> dict[str, any]:
    """
    Verify all filed receipts against audit log.

    Returns:
        {
            "checked": int,
            "ok": int,
            "tampered": [
                {"filepath": "...", "expected_hash": "...", "actual_hash": "..."},
                ...
            ]
        }
    """
    tampered = []
    checked = 0

    # Read all audit log entries
    entries = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    except FileNotFoundError:
        return {"checked": 0, "ok": 0, "tampered": []}

    # Check each CREATE event
    for entry in entries:
        if entry.get("event") != "CREATE":
            continue

        checked += 1
        filepath = entry.get("file", "")
        expected_hash = entry.get("hash", "")

        if not filepath or not expected_hash:
            continue

        # Verify file exists and hash matches
        full_path = base_path / filepath
        if not full_path.exists():
            tampered.append(
                {
                    "filepath": filepath,
                    "expected_hash": expected_hash,
                    "actual_hash": "FILE_NOT_FOUND",
                }
            )
            continue

        # Calculate actual hash
        from ..utils.hash_utils import sha256_file
        actual_hash = sha256_file(full_path)

        if actual_hash != expected_hash:
            tampered.append(
                {
                    "filepath": filepath,
                    "expected_hash": expected_hash,
                    "actual_hash": actual_hash,
                }
            )

    return {
        "checked": checked,
        "ok": checked - len(tampered),
        "tampered": tampered,
    }


def get_audit_log_tail(log_path: Path, lines: int = 100) -> list[dict]:
    """
    Get last N lines from audit log for display.
    """
    entries = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                if line.strip():
                    entries.append(json.loads(line))
    except FileNotFoundError:
        pass
    return entries
