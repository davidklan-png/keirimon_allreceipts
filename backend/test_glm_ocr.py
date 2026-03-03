#!/usr/bin/env python3
"""
Test GLM-OCR API connection.

Run this to verify your API key is working:
    python test_glm_ocr.py
"""

import base64
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing httpx...")
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

API_KEY = os.getenv("GLM_OCR_API_KEY")
API_URL = "https://open.bigmodel.cn/api/paas/v4/layout_parsing"

print("=" * 50)
print("GLM-OCR Connection Test")
print("=" * 50)

# Check API key
if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
    print("❌ GLM_OCR_API_KEY not set!")
    print("   Edit backend/.env and set your key:")
    print("   GLM_OCR_API_KEY=your_actual_key_here")
    sys.exit(1)

print(f"✅ API Key: {API_KEY[:8]}...{API_KEY[-4:]}")

# Create a simple test image (1x1 pixel PNG)
def create_test_image():
    """Create a minimal test PNG image."""
    # 1x1 red pixel PNG
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0'
        b'\x00\x00\x00\x03\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    test_path = Path("/tmp/test_ocr.png")
    test_path.write_bytes(png_data)
    return test_path


def test_connection():
    """Test the GLM-OCR API connection."""
    print("\n📸 Creating test image...")
    test_image = create_test_image()
    print(f"   Test image: {test_image}")

    # Read and encode image
    with open(test_image, "rb") as f:
        file_bytes = f.read()

    b64 = base64.b64encode(file_bytes).decode("utf-8")
    data_uri = f"data:image/png;base64,{b64}"

    payload = {
        "model": "glm-ocr",
        "file": data_uri,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    print("\n🌐 Calling GLM-OCR API...")
    print(f"   Endpoint: {API_URL}")

    try:
        response = httpx.post(API_URL, json=payload, headers=headers, timeout=120.0)
        response.raise_for_status()

        data = response.json()

        print("\n✅ API Connection Successful!")
        print(f"\n📄 Response keys: {list(data.keys())}")

        if "md_results" in data:
            md_text = data["md_results"]
            preview = md_text[:100] if md_text else "(empty)"
            print(f"\n📝 Markdown preview: {preview}...")

        if "usage" in data:
            print(f"\n📊 Token usage: {data['usage']}")

        print("\n" + "=" * 50)
        print("✅ All checks passed! GLM-OCR is working.")
        print("=" * 50)
        return True

    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error {e.response.status_code}")
        print(f"   Response: {e.response.text[:200]}")
        if e.response.status_code == 401:
            print("\n   401 Unauthorized: Check your API key!")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPossible issues:")
        print("  1. Invalid API key")
        print("  2. Network connectivity problem")
        print("  3. API service down")
        print("\nCheck your API key at: https://open.bigmodel.cn")
        return False
    finally:
        # Cleanup
        if test_image.exists():
            test_image.unlink()


if __name__ == "__main__":
    test_connection()
