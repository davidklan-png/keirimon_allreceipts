# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Any Mac / iPhone                          │
│                   Browser (Safari/Chrome)                   │
│                   http://server-ip:5173                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / REST
┌──────────────────────────▼──────────────────────────────────┐
│                   Server Mac (always on)                    │
│                                                             │
│   ┌─────────────────┐     ┌───────────────────────────┐    │
│   │  Vite / React   │     │    FastAPI (port 8000)     │    │
│   │  (port 5173)    │────▶│                           │    │
│   │  Static SPA     │     │  /api/receipts  (CRUD)    │    │
│   └─────────────────┘     │  /api/ocr       (upload)  │    │
│                           │  /api/search    (query)   │    │
│                           │  /api/export    (CSV)     │    │
│                           │  /api/audit     (verify)  │    │
│                           │  /api/vendors   (lookup)  │    │
│                           └───────────┬───────────────┘    │
│                                       │                     │
│          ┌────────────────────────────┼──────────────┐     │
│          │                            │              │     │
│   ┌──────▼──────┐   ┌─────────────────▼──┐   ┌──────▼──┐  │
│   │  SQLite DB  │   │  AllReceipts/       │   │ audit   │  │
│   │ receipts.db │   │  FY2027/04_Apr/     │   │ .log    │  │
│   └─────────────┘   │  *.pdf              │   └─────────┘  │
│                     └────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
┌────────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│ Google Vision │  │  NTA Invoice │  │ (future:     │
│ API (OCR)     │  │  API         │  │  AMEX CSV)   │
└───────────────┘  └──────────────┘  └──────────────┘
```

---

## Directory Structure

```
receipt-capture-app/
│
├── README.md
├── REQUIREMENTS.md
├── ARCHITECTURE.md
├── COMPLIANCE.md
├── dev.sh                        # starts both frontend and backend
│
├── backend/
│   ├── main.py                   # FastAPI app, route registration
│   ├── models.py                 # SQLModel table definitions
│   ├── database.py               # SQLite connection, init_db()
│   ├── routes/
│   │   ├── receipts.py           # POST /file, GET /{id}, DELETE /{id}
│   │   ├── ocr.py                # POST /ocr/upload
│   │   ├── search.py             # GET /search
│   │   ├── export.py             # GET /export/moneyforward
│   │   ├── audit.py              # GET /audit/verify
│   │   └── vendors.py            # GET/POST/PUT /vendors
│   ├── services/
│   │   ├── ocr_service.py        # Google Vision API wrapper
│   │   ├── filing_service.py     # filename generation, folder routing
│   │   ├── nta_service.py        # NTA Invoice API + cache
│   │   ├── audit_service.py      # append-only log writer
│   │   └── export_service.py     # MoneyForward CSV builder
│   ├── utils/
│   │   ├── fy_calculator.py      # fiscal year logic
│   │   ├── filename_builder.py   # YYYYMMDD_CAT_NN_VENDOR_AMT
│   │   └── hash_utils.py        # SHA-256 helpers
│   ├── data/
│   │   └── vendors.json          # seed vendor lookup table
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js            # proxy /api → localhost:8000
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── components/
│       │   ├── UploadZone.jsx    # drag-drop + camera capture button
│       │   ├── ConfirmForm.jsx   # OCR result review + edit
│       │   ├── SearchPanel.jsx   # filter bar + results table
│       │   ├── ExportPanel.jsx   # FY + month selector + download
│       │   └── VendorTable.jsx   # editable vendor lookup table
│       ├── hooks/
│       │   ├── useOcr.js
│       │   └── useReceipts.js
│       └── api/
│           └── client.js         # fetch wrapper for /api/*
│
└── tests/
    ├── test_fy_calculator.py
    ├── test_filename_builder.py
    └── test_filing_service.py
```

---

## API Endpoints

### OCR

```
POST /api/ocr/upload
  Content-Type: multipart/form-data
  Body: file (PDF | JPEG | PNG)
  Response: {
    "ocr_id": "uuid",
    "extracted": {
      "receipt_date": "2027-04-15",
      "amount_jpy": 12175,
      "amount_foreign": null,
      "currency_foreign": null,
      "vendor_name": "BOSS",
      "registration_number": "T1234567890123",
      "confidence": { "date": 0.97, "amount": 0.99, "vendor": 0.88 }
    },
    "suggested_category": "KTL",
    "suggested_filename": "20270415_KTL_01_BOSS_12175.pdf",
    "nta_status": "valid" | "invalid" | "unchecked"
  }
```

### File a Receipt

```
POST /api/receipts
  Body: {
    "ocr_id": "uuid",
    "receipt_date": "2027-04-15",
    "amount_jpy": 12175,
    "amount_foreign": null,
    "currency_foreign": null,
    "vendor_name": "BOSS",
    "registration_number": "T1234567890123",
    "category_code": "KTL",
    "payment_method": "AMEX",
    "notes": "",
    "filename_override": null         # null = use generated name
  }
  Response: {
    "id": 42,
    "filepath": "FY2027/04_Apr/20270415_KTL_01_BOSS_12175.pdf",
    "retention_until": "2034-04-15"
  }
```

### Search

```
GET /api/search?from_date=2027-02-01&to_date=2027-04-30&vendor=BOSS&category=KTL&fy=FY2027
  Response: {
    "total": 3,
    "results": [ { ...receipt row... }, ... ]
  }
```

### Export (MoneyForward CSV)

```
GET /api/export/moneyforward?fy=FY2027&month=4
  Response: text/csv
  Content-Disposition: attachment; filename="MF_FY2027_04_Apr.csv"
```

### Audit Verify

```
GET /api/audit/verify
  Response: {
    "checked": 247,
    "ok": 246,
    "tampered": [
      { "filepath": "FY2027/04_Apr/...", "expected_hash": "...", "actual_hash": "..." }
    ]
  }
```

---

## Key Service Logic

### `fy_calculator.py`

```python
def get_fiscal_year(receipt_date: date) -> str:
    """
    FY runs Feb 1 – Jan 31.
    Jan 2027 → FY2026. Feb 2027 → FY2027.
    """
    if receipt_date.month == 1:
        return f"FY{receipt_date.year - 1}"
    return f"FY{receipt_date.year}"

def get_month_folder(receipt_date: date) -> str:
    folders = {
        1:"01_Jan", 2:"02_Feb", 3:"03_Mar", 4:"04_Apr",
        5:"05_May", 6:"06_Jun", 7:"07_Jul", 8:"08_Aug",
        9:"09_Sep", 10:"10_Oct", 11:"11_Nov", 12:"12_Dec"
    }
    return folders[receipt_date.month]
```

### `filename_builder.py`

```python
import re, unicodedata

def to_romaji_safe(text: str, max_len: int = 20) -> str:
    """Strip non-ASCII, collapse spaces to nothing, truncate."""
    ascii_only = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    safe = re.sub(r"[^A-Za-z0-9]", "", ascii_only)
    return safe[:max_len] or "Unknown"

def next_sequence(base_path: Path, date_str: str, cat: str) -> str:
    """Count existing files matching YYYYMMDD_CAT_* to get next NN."""
    pattern = f"{date_str}_{cat}_*.pdf"
    existing = list(base_path.glob(pattern))
    return str(len(existing) + 1).zfill(2)

def build_filename(
    receipt_date: date,
    category_code: str,
    vendor_name: str,
    amount_jpy: int,
    target_folder: Path
) -> str:
    date_str = receipt_date.strftime("%Y%m%d")
    nn = next_sequence(target_folder, date_str, category_code)
    vendor_safe = to_romaji_safe(vendor_name)
    return f"{date_str}_{category_code}_{nn}_{vendor_safe}_{amount_jpy}.pdf"
```

### `audit_service.py`

```python
import json, hashlib
from datetime import datetime, timezone
from pathlib import Path

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"

def log_event(log_path: Path, event: str, filepath: str, file_hash: str):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "file": filepath,
        "user": "system",
        "hash": file_hash,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

---

## MoneyForward CSV Format

MoneyForward スモールビジネス import column mapping:

| CSV Column | Source field | Notes |
|---|---|---|
| 計算対象 | `"1"` | Always 1 (include in calculation) |
| 日付 | `receipt_date` formatted `YYYY/MM/DD` | |
| 内容 | `vendor_name` | |
| 金額（円） | `amount_jpy` | Positive integer |
| 内税／外税 | `"外税"` | Default; adjust if needed |
| 税率 | `"10%"` | 10% standard; 8% for food |
| 勘定科目 | From category code table (REQUIREMENTS.md §6) | |
| 税区分 | `"課税仕入"` | Default for deductible expenses |
| 補助科目 | `""` | Leave blank |
| 部門 | `""` | Leave blank unless dept tracking needed |
| メモ | `registration_number` if present, else `""` | |
| 仕訳メモ | `notes` | |
| 管理番号 | `filename` (without .pdf) | Traceability back to filed PDF |

---

## Sharing Across Macs

### Network access
The Vite dev server and FastAPI both bind to `0.0.0.0` so they are reachable from any device on the local network.

In `dev.sh`:
```bash
#!/bin/bash
# Get local IP
LOCAL_IP=$(ipconfig getifaddr en0)
echo "Frontend: http://$LOCAL_IP:5173"
echo "API:      http://$LOCAL_IP:8000"

# Start backend
cd backend && source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &

# Start frontend
cd ../frontend
npm run dev -- --host 0.0.0.0
```

In `vite.config.js`:
```javascript
export default {
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
}
```

### Shared data
All Macs point at the same `AllReceipts/` folder (mounted via iCloud Drive, Dropbox, NAS, or SMB share). Only the server Mac runs the app — other Macs just use the browser UI. This means there is no concurrent write conflict; all writes go through the single FastAPI process.

If the AllReceipts folder is on iCloud Drive, set `RECEIPTS_BASE_PATH` to the iCloud path:
```
/Users/yourname/Library/Mobile Documents/com~apple~CloudDocs/AllReceipts
```

### Production hardening (post-MVP)
For a stable always-on setup, run the backend as a launchd service on the server Mac:
```xml
<!-- ~/Library/LaunchAgents/com.yourcompany.receipt-capture.plist -->
<key>ProgramArguments</key>
<array>
  <string>/path/to/.venv/bin/uvicorn</string>
  <string>main:app</string>
  <string>--host</string><string>0.0.0.0</string>
  <string>--port</string><string>8000</string>
</array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
```

---

## Environment Variables Reference

```bash
# backend/.env.example

# Google Vision API
GOOGLE_VISION_API_KEY=your_key_here

# File storage
RECEIPTS_BASE_PATH=/Users/you/AllReceipts
DB_PATH=/Users/you/AllReceipts/receipts.db
AUDIT_LOG_PATH=/Users/you/AllReceipts/audit.log

# Temp upload directory (cleared after filing)
UPLOAD_TEMP_PATH=/tmp/receipt_uploads

# App settings
COMPANY_NAME=Your GK Name Here
FISCAL_YEAR_START_MONTH=2

# NTA API (no key required — public API)
NTA_API_BASE=https://web-api.invoice-kohyo.nta.go.jp/1
NTA_CACHE_DAYS=30
```

---

## Dependencies

### Backend (`requirements.txt`)

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
sqlmodel>=0.0.18
python-multipart>=0.0.9
google-cloud-vision>=3.7.0
httpx>=0.27.0          # async HTTP for NTA API calls
python-dotenv>=1.0.0
aiofiles>=23.2.0
Pillow>=10.3.0         # image pre-processing before OCR
```

### Frontend (`package.json` dependencies)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0"
  },
  "devDependencies": {
    "vite": "^5.2.0",
    "@vitejs/plugin-react": "^4.3.0"
  }
}
```

---

## Testing Strategy

### Unit tests (pytest)
- `test_fy_calculator.py` — boundary cases (Jan 31, Feb 1, Feb 29 leap year)
- `test_filename_builder.py` — Japanese vendor names, special characters, sequence increment
- `test_filing_service.py` — folder creation, rollback on failure, duplicate detection

### Manual test cases for MVP sign-off
1. Upload a Japanese PDF receipt → OCR extracts correctly → file lands in correct FY/Month folder
2. Upload a USD receipt → both amounts captured → JPY used in filename
3. Upload receipt with invalid 登録番号 → amber warning shown → can still file
4. Search by date range → returns correct results within 3 seconds
5. Delete a receipt filed 2 years ago → blocked with retention message
6. Export April 2027 → valid MoneyForward CSV downloaded
7. Run audit verify → all hashes match on unmodified dataset
8. Access from a second Mac on the network → full functionality available
