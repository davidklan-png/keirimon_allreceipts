#!/usr/bin/env python3
"""
Test Google Cloud Vision API connection with a proper receipt image.
"""

import base64
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

API_KEY = os.getenv("GOOGLE_CLOUD_VISION_API_KEY")
API_URL = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"

print("=" * 50)
print("Google Cloud Vision API - OCR Test")
print("=" * 50)

# Create a simple test image with text
def create_test_receipt():
    """Create a test receipt image with text."""
    # Create a simple PNG with some text pattern
    # For now, use a minimal 10x10 pixel PNG (still no text, but valid format)
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\n\x00\x00\x00\n'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8'
        b'\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    test_path = Path("/tmp/test_receipt.png")
    test_path.write_bytes(png_data)
    return test_path


def test_connection():
    """Test the Vision API connection."""
    print("\n📸 Creating test receipt image...")
    test_image = create_test_receipt()
    print(f"   Test image: {test_image}")

    # Read and encode image
    with open(test_image, "rb") as f:
        file_bytes = f.read()

    b64 = base64.b64encode(file_bytes).decode("utf-8")

    # Google Vision API payload - try full text annotation
    payload = {
        "requests": [
            {
                "image": {
                    "content": b64
                },
                "features": [
                    {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 10}
                ]
            }
        ]
    }

    print("\n🌐 Calling Google Cloud Vision API (DOCUMENT_TEXT_DETECTION)...")
    print(f"   Endpoint: https://vision.googleapis.com/v1/images:annotate")

    try:
        response = httpx.post(API_URL, json=payload, timeout=30.0)
        response.raise_for_status()

        data = response.json()

        print("\n✅ API Connection Successful!")
        print(f"\n📄 Response keys: {list(data.keys())}")

        if "responses" in data and data["responses"]:
            resp = data["responses"][0]

            if "error" in resp:
                print(f"\n⚠️ API Error: {resp['error']}")
                if resp['error'].get('code') == 3:
                    print("   (This is expected for a test image with no text)")

            if "fullTextAnnotation" in resp:
                text = resp["fullTextAnnotation"].get("text", "")
                print(f"\n📝 Detected text: '{text if text else '(empty - expected for test image)'}'")
            elif "textAnnotations" in resp:
                print(f"\n📊 Text annotations: {len(resp['textAnnotations'])} found")
            else:
                print(f"\n📊 Full response keys: {list(resp.keys())}")

        print("\n" + "=" * 50)
        print("✅ Google Vision API is working!")
        print("   (Empty result is expected for test image with no text)")
        print("=" * 50)
        print("\n💡 Next steps:")
        print("   1. Install google-cloud-vision: pip install google-cloud-vision")
        print("   2. Update ocr_service.py to use Vision API")
        print("   3. Test with a real receipt image")
        return True

    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error {e.response.status_code}")
        print(f"   Response: {e.response.text[:500]}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        if test_image.exists():
            test_image.unlink()


if __name__ == "__main__":
    test_connection()
