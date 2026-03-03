"""
NTA Invoice API service for 登録番号 validation.

Public API — no authentication required.
Caches results for 30 days to reduce redundant calls.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import httpx
from dotenv import load_dotenv

from ..database import get_session
from ..models import NtaCache

load_dotenv()

NTA_API_BASE = os.getenv("NTA_API_BASE", "https://web-api.invoice-kohyo.nta.go.jp/1")
NTA_CACHE_DAYS = int(os.getenv("NTA_CACHE_DAYS", "30"))


async def validate_registration_number(
    registration_number: str,
) -> Tuple[bool, Optional[str]]:
    """
    Validate a T + 13 digit registration number via NTA API.

    Returns:
        (is_valid, company_name)

    Caches results for 30 days.
    """
    # Normalize input (strip T prefix if present, ensure format)
    if not registration_number:
        return False, None

    # Ensure T prefix
    if not registration_number.startswith("T"):
        registration_number = f"T{registration_number}"

    # Check cache first
    cached = _get_cached_result(registration_number)
    if cached:
        return cached.is_valid, cached.company_name

    # Call NTA API
    is_valid, company_name = await _call_nta_api(registration_number)

    # Cache the result
    _cache_result(registration_number, is_valid, company_name)

    return is_valid, company_name


async def _call_nta_api(registration_number: str) -> Tuple[bool, Optional[str]]:
    """
    Call NTA Invoice API and parse response.

    API: GET https://web-api.invoice-kohyo.nta.go.jp/1/num?id=T{13digits}&type=21

    Response field `res.registrations[0].process` == "01" means registered and active.
    """
    url = f"{NTA_API_BASE}/num"
    params = {"id": registration_number, "type": "21"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Parse response
            # Check if we have valid registrations
            registrations = data.get("res", {}).get("registrations", [])

            if not registrations:
                return False, None

            # Check first registration's process status
            # "01" = registered and active
            process = registrations[0].get("process")
            is_valid = process == "01"

            # Extract company name if available
            company_name = None
            if is_valid:
                # Try various possible name fields
                name_fields = ["name", "companyName", "company_name", "na—youyakuName"]
                for field in name_fields:
                    if field in registrations[0]:
                        company_name = registrations[0][field]
                        break

            return is_valid, company_name

        except httpx.HTTPError:
            # API unreachable — allow filing but mark as unvalidated
            # Caller should handle this case
            return False, None


def _get_cached_result(registration_number: str) -> Optional[NtaCache]:
    """Check cache for non-expired result."""
    with next(get_session()) as session:
        cached = session.get(NtaCache, registration_number)
        if cached and cached.expires_at > datetime.now(timezone.utc):
            return cached
    return None


def _cache_result(registration_number: str, is_valid: bool, company_name: Optional[str]):
    """Cache validation result with expiry."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=NTA_CACHE_DAYS)

    with next(get_session()) as session:
        cached = session.get(NtaCache, registration_number)
        if cached:
            # Update existing
            cached.is_valid = is_valid
            cached.company_name = company_name
            cached.validated_at = datetime.now(timezone.utc)
            cached.expires_at = expires_at
        else:
            # Create new
            cached = NtaCache(
                registration_number=registration_number,
                is_valid=is_valid,
                company_name=company_name,
                validated_at=datetime.now(timezone.utc),
                expires_at=expires_at,
            )
            session.add(cached)
        session.commit()


def clear_expired_cache():
    """Remove expired cache entries. Call periodically."""
    with next(get_session()) as session:
        expired = (
            session.query(NtaCache)
            .filter(NtaCache.expires_at < datetime.now(timezone.utc))
            .all()
        )
        for item in expired:
            session.delete(item)
        session.commit()
        return len(expired)
