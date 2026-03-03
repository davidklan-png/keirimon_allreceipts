"""
SHA-256 hash utilities for file integrity verification.
"""

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.

    Returns string prefixed with "sha256:" for audit log format.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def sha256_bytes(data: bytes) -> str:
    """
    Calculate SHA-256 hash of bytes.

    Useful for in-memory file processing before writing to disk.
    """
    return f"sha256:{hashlib.sha256(data).hexdigest()}"
