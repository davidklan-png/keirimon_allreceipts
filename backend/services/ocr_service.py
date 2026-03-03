"""
OCR service using Google Cloud Vision API.

Extracts receipt fields from PDF/JPEG/PNG uploads.

Uses HTTP API with API key authentication.
"""

import base64
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

from ..models import OcrResult

load_dotenv()

GOOGLE_CLOUD_VISION_API_KEY = os.getenv("GOOGLE_CLOUD_VISION_API_KEY")
VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"


async def call_vision_api(file_path: Path) -> dict:
    """
    Send file to Google Cloud Vision API for OCR.

    Returns raw API response with full text and annotations.
    """
    if not GOOGLE_CLOUD_VISION_API_KEY:
        raise ValueError("GOOGLE_CLOUD_VISION_API_KEY not configured")

    # Read and encode image
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Detect file type for PDF handling
    if file_bytes[:5] == b"%PDF-":
        # For PDF, use the async batch annotation endpoint or handle separately
        # For now, base64 encode the entire PDF
        b64_content = base64.b64encode(file_bytes).decode("utf-8")
    else:
        b64_content = base64.b64encode(file_bytes).decode("utf-8")

    # Build request payload
    url = f"{VISION_API_URL}?key={GOOGLE_CLOUD_VISION_API_KEY}"

    payload = {
        "requests": [
            {
                "image": {
                    "content": b64_content
                },
                "features": [
                    {
                        "type": "DOCUMENT_TEXT_DETECTION",
                        "maxResults": 10
                    }
                ]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def parse_vision_response(data: dict) -> OcrResult:
    """
    Parse Google Vision API response and extract receipt fields.

    Google Vision returns fullTextAnnotation with all detected text.
    This function extracts structured receipt data using regex patterns.
    """
    # Extract full text from response
    full_text = ""
    if "responses" in data and data["responses"]:
        resp = data["responses"][0]

        if "fullTextAnnotation" in resp:
            full_text = resp["fullTextAnnotation"].get("text", "")
        elif "textAnnotations" in resp:
            # Fallback: concatenate all text annotations (skip first one which is entire text)
            texts = [annotation.get("description", "") for annotation in resp["textAnnotations"][1:]]
            full_text = "\n".join(texts)

    confidence = {}

    return OcrResult(
        receipt_date=_extract_date(full_text, confidence),
        amount_jpy=_extract_amount_jpy(full_text, confidence),
        amount_foreign=_extract_amount_foreign(full_text, confidence),
        currency_foreign=_extract_currency_foreign(full_text, confidence),
        vendor_name=_extract_vendor_name(full_text, confidence),
        registration_number=_extract_registration_number(full_text, confidence),
        notes=_extract_notes(full_text),
        confidence=confidence,
    )


def _extract_date(text: str, confidence: dict) -> Optional[str]:
    """
    Extract receipt date in YYYY-MM-DD format.

    Looks for patterns like:
    - 2027年04月15日
    - 2027/04/15
    - 2027-04-15
    - 令和4年4月15日
    """
    # Japanese era date: 令和X年X月X日
    reiwa_match = re.search(r'令和(\d+)年(\d+)月(\d+)日', text)
    if reiwa_match:
        year = 2018 + int(reiwa_match.group(1))  # Reiwa 1 = 2019
        month = int(reiwa_match.group(2)).zfill(2)
        day = int(reiwa_match.group(3)).zfill(2)
        confidence["date"] = 0.9
        return f"{year}-{month}-{day}"

    # Standard formats
    patterns = [
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',  # 2027年4月15日
        r'(\d{4})/(\d{1,2})/(\d{1,2})',     # 2027/04/15
        r'(\d{4})-(\d{1,2})-(\d{1,2})',     # 2027-04-15
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            year = match.group(1)
            month = match.group(2).zfill(2)
            day = match.group(3).zfill(2)
            confidence["date"] = 0.95
            return f"{year}-{month}-{day}"

    confidence["date"] = 0.0
    return None


def _extract_amount_jpy(text: str, confidence: dict) -> Optional[int]:
    """
    Extract JPY amount.

    Looks for patterns like:
    - ¥12,175
    - ￥12,175
    - 12,175円
    - 12175円
    """
    patterns = [
        r'[¥￥]\s*([0-9,]+)',           # ¥12,175
        r'([0-9,]+)\s*円',               # 12,175円
        r'金額\s*[:：]\s*([0-9,]+)',     # 金額: 12,175
        r'合計\s*[:：]\s*([0-9,]+)',     # 合計: 12,175
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = int(amount_str)
                confidence["amount"] = 0.95
                return amount
            except ValueError:
                pass

    confidence["amount"] = 0.0
    return None


def _extract_amount_foreign(text: str, confidence: dict) -> Optional[float]:
    """
    Extract foreign currency amount (USD, EUR, etc.).

    Looks for patterns like:
    - $12.50
    - €12.50
    - USD 12.50
    """
    patterns = [
        r'[$€£]\s*([0-9,]+\.?\d*)',      # $12.50
        r'(USD|EUR|GBP|CNY)\s*([0-9,]+\.?\d*)',  # USD 12.50
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.group(1) in ['USD', 'EUR', 'GBP', 'CNY']:
                amount_str = match.group(2)
            else:
                amount_str = match.group(1)

            try:
                amount = float(amount_str.replace(',', ''))
                confidence["amount_foreign"] = 0.9
                return amount
            except ValueError:
                pass

    confidence["amount_foreign"] = 0.0
    return None


def _extract_currency_foreign(text: str, confidence: dict) -> Optional[str]:
    """Extract foreign currency code (USD, EUR, GBP, etc.)."""
    if confidence.get("amount_foreign", 0) > 0:
        match = re.search(r'\b(USD|EUR|GBP|CNY)\b', text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def _extract_vendor_name(text: str, confidence: dict) -> Optional[str]:
    """
    Extract vendor name.

    Looks for common patterns in Japanese receipts.
    """
    lines = text.split('\n')

    # First non-empty line is often the store name
    for line in lines[:10]:
        line = line.strip()
        if line and len(line) > 2 and len(line) < 50:
            # Skip obvious non-vendor lines
            skip_patterns = ['領収書', '明細', '日付', '金額', '合計', '税', 'RECEIPT']
            if not any(p in line for p in skip_patterns):
                confidence["vendor"] = 0.8
                return line

    confidence["vendor"] = 0.0
    return None


def _extract_registration_number(text: str, confidence: dict) -> Optional[str]:
    """
    Extract 登録番号 (T + 13 digits).

    Format: T1234567890123
    """
    match = re.search(r'T(\d{13})', text)
    if match:
        confidence["registration_number"] = 1.0
        return f"T{match.group(1)}"

    # Also look for 「登録番号」pattern
    match = re.search(r'登録番号\s*[:：]\s*[Tt]?(\d{13})', text)
    if match:
        confidence["registration_number"] = 1.0
        return f"T{match.group(1)}"

    confidence["registration_number"] = 0.0
    return None


def _extract_notes(text: str) -> Optional[str]:
    """Extract any additional notes from the receipt."""
    if text and len(text) > 10:
        return text[:200]
    return None


async def process_receipt_upload(
    file_path: Path,
) -> tuple[str, OcrResult, Optional[str], Optional[str], str]:
    """
    Full OCR pipeline: upload, extract, parse, suggest.

    Returns:
        (ocr_id, extracted_data, suggested_category, suggested_filename, nta_status)
    """
    import uuid
    from ..services.nta_service import validate_registration_number

    ocr_id = str(uuid.uuid4())

    # Step 1: Call Google Vision API
    vision_response = await call_vision_api(file_path)

    # Step 2: Parse response into structured data
    extracted = parse_vision_response(vision_response)

    # Step 3: Suggest category based on vendor (if vendor found)
    suggested_category = None
    if extracted.vendor_name:
        # TODO: Look up vendor in database for category suggestion
        pass

    # Step 4: Suggest filename (if we have enough data)
    suggested_filename = None
    base_path = Path(os.getenv("RECEIPTS_BASE_PATH", "./AllReceipts"))

    if extracted.receipt_date and extracted.amount_jpy:
        from ..utils.filename_builder import build_filepath

        receipt_date = datetime.strptime(extracted.receipt_date, "%Y-%m-%d").date()
        temp_category = suggested_category or "SHO"
        filepath, filename = build_filepath(
            base_path=base_path,
            receipt_date=receipt_date,
            category_code=temp_category,
            vendor_name=extracted.vendor_name or "Unknown",
            amount_jpy=extracted.amount_jpy,
        )
        suggested_filename = filename

    # Step 5: Check NTA status if registration number found
    nta_status = "unchecked"
    if extracted.registration_number:
        is_valid, _ = await validate_registration_number(extracted.registration_number)
        nta_status = "valid" if is_valid else "invalid"

    return ocr_id, extracted, suggested_category, suggested_filename, nta_status
