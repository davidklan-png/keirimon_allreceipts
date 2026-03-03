# Agent Context — AllReceipts

## Starting a New Session

The three `.md` files in the project root are your context bridge. Read them first to understand the full picture.

**Suggested opening prompt:**
```
Read REQUIREMENTS.md and ARCHITECTURE.md, then scaffold the
backend directory structure from ARCHITECTURE.md — starting
with main.py, models.py, database.py, and the four service
files. Use FastAPI and SQLModel. Don't build the routes yet.
```

---

## Project Overview

A local-network web application for a Japanese 合同会社 (GK) to capture, categorize, file, and report receipts in compliance with 電子帳簿保存法 and インボイス制度.

**Key characteristics:**
- Single Mac runs the server; browsers on other Macs/iPhones access via local network
- No cloud dependencies except OCR (Google Cloud Vision API) and NTA Invoice validation
- All data stored locally: SQLite ledger + filesystem PDF storage
- Japanese language support throughout (UTF-8)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ / FastAPI |
| Database | SQLite (via SQLModel) |
| OCR | Google Cloud Vision API |
| Frontend | React 18 + Vite |
| Validation | NTA Invoice API (public, no auth) |

---

## Environment Variables

```bash
GOOGLE_CLOUD_VISION_API_KEY=your_key_here
RECEIPTS_BASE_PATH=/Users/you/AllReceipts
DB_PATH=/Users/you/AllReceipts/receipts.db
AUDIT_LOG_PATH=/Users/you/AllReceipts/audit.log
COMPANY_NAME=Your GK Name
FISCAL_YEAR_START_MONTH=2  # February — FY runs Feb 1 – Jan 31
UPLOAD_TEMP_PATH=/tmp/receipt_uploads
NTA_API_BASE=https://web-api.invoice-kohyo.nta.go.jp/1
NTA_CACHE_DAYS=30
```

---

## Project Structure

```
receipt-capture-app/
├── README.md
├── REQUIREMENTS.md      # Full functional/non-functional requirements
├── ARCHITECTURE.md      # System design and API docs
├── COMPLIANCE.md        # Japanese tax compliance reference
├── AGENT.md            # This file
├── dev.sh              # Start both frontend and backend
│
├── backend/
│   ├── main.py         # FastAPI app, route registration
│   ├── models.py       # SQLModel table definitions
│   ├── database.py     # SQLite connection, init_db()
│   ├── routes/         # API endpoint handlers
│   ├── services/       # Business logic (OCR, filing, NTA, audit, export)
│   ├── utils/          # Fiscal year, filename builder, hash utilities
│   ├── data/           # Seed data (vendors.json)
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── components/
│       ├── hooks/
│       └── api/
│
└── tests/
    └── test_*.py
```

---

## Fiscal Year Rules

**Critical:** Japan fiscal year for this GK is **February 1 – January 31**.

```python
if receipt_date.month == 1:
    fy = f"FY{receipt_date.year - 1}"  # Jan 2027 → FY2026
else:
    fy = f"FY{receipt_date.year}"      # Feb 2027 → FY2027
```

Examples:
- 2027-04-15 → FY2027
- 2027-01-30 → FY2026
- 2028-02-01 → FY2027 (first day of new FY)

---

## Filename Convention

All filed receipts follow this pattern:

```
YYYYMMDD_CAT_NN_VENDOR_JPYAMT.pdf
```

- `YYYYMMDD` = receipt_date
- `CAT` = 3-letter category code (e.g., `KTL`, `SHO`, `RND`)
- `NN` = 2-digit sequence (auto-incremented per day+category)
- `VENDOR` = ASCII/romaji only, max 20 chars, no spaces
- `JPYAMT` = integer amount, no commas

---

## Category Codes

| Code | 経費科目 | Description |
|---|---|---|
| SHO | 消耗品費 | Water, coffee, stationery, small accessories |
| KTL | 接待交際費 | Entertainment, client dining, gifts |
| RND | 研究開発費 | AI/cloud services, supplements, domain |
| TRS | 出張交通費 | Flights, Shinkansen, rental cars |
| LOC | 交通費 | Local taxi, bus, train |
| ACC | 出張宿泊費 | Hotels, guesthouses |
| WEL | 福利厚生費 | Sports, health subscriptions |
| COM | 通信費 | Shipping, domain, phone |
| MTG | 会議費 | Meeting room, business dining |
| EQP | 工具機器備品 | Computers, equipment (>¥10,000) |
| ADV | 広告宣伝費 | Web advertising |
| FEE | 支払手数料 | Consulting, coaching |

---

## API Endpoints

### OCR
```
POST /api/ocr/upload
  Body: file (PDF | JPEG | PNG)
  Response: { ocr_id, extracted, suggested_category, suggested_filename, nta_status }
```

### Receipts
```
POST /api/receipts      # File a confirmed receipt
GET  /api/receipts/{id} # Get receipt by ID
DELETE /api/receipts/{id} # Delete (blocked within 7-year retention)
```

### Search & Export
```
GET /api/search              # Filter by date, amount, vendor, category, FY
GET /api/export/moneyforward # Monthly CSV export
GET /api/audit/verify        # Tamper detection
```

### Vendors
```
GET    /api/vendors    # List all
POST   /api/vendors    # Create new
PUT    /api/vendors/{id} # Update
```

---

## NTA 登録番号 Validation

Public API (no authentication):
```
GET https://web-api.invoice-kohyo.nta.go.jp/1/num?id=T{13digits}&type=21
```

- `process == "01"` = registered and active (green badge)
- Otherwise = unregistered (amber badge, reduced deduction)

Cache results for 30 days to avoid redundant API calls.

---

## Compliance Notes

### 電子帳簿保存法
- **真実性:** Append-only audit.log + SHA-256 hashes at filing time
- **可視性:** Search by date/amount/vendor, results in <3 seconds
- **保存期間:** 7 years from receipt_date (enforced at delete)

### インボイス制度
- Registered vendors: 100% 仕入税額控除
- Unregistered: 80% until Sep 2026, then 50%, then 0%

---

## Development Commands

```bash
# Start both servers
./dev.sh

# Backend only
cd backend && source .venv/bin/activate && uvicorn main:app --reload

# Frontend only
cd frontend && npm run dev

# Run tests
cd backend && python -m pytest ../tests/
```

---

## Code Style Guidelines

- Japanese text preserved as UTF-8 in display fields
- Only filename `VENDOR` segment uses romaji conversion
- All file operations use absolute paths from `RECEIPTS_BASE_PATH`
- Database transactions rolled back on any filing failure
- Audit log is append-only — never delete or modify entries

---

## Common Tasks

### Adding a new OCR field
1. Update `models.py` → add column to `Receipt` model
2. Update `ocr_service.py` → extract new field from Vision API response
3. Update `ConfirmForm.jsx` → show field for user confirmation
4. Update migration logic if needed

### Adding a new category
1. Update `backend/data/vendors.json` seed data
2. Update category dropdown in frontend
3. Update `REQUIREMENTS.md` reference table

### Debugging NTA validation
- Check `nta_cache` table for cached responses
- NTA API public docs: https://www.invoice-kohyo.nta.go.jp/web-api/index.html

---

## Important Files to Read First

- `REQUIREMENTS.md` — Full specification
- `ARCHITECTURE.md` — System design and data model
- `backend/models.py` — Database schema
- `backend/services/filing_service.py` — Filename and folder logic
- `backend/utils/fy_calculator.py` — Fiscal year calculation

---

## Testing

Run unit tests before committing:
```bash
cd backend && python -m pytest ../tests/ -v
```

Manual test checklist for sign-off:
1. Upload Japanese PDF → OCR extracts correctly
2. Upload USD receipt → both amounts captured
3. Invalid 登録番号 → amber warning, can still file
4. Search by date range → <3 second response
5. Delete within 7 years → blocked with retention message
6. Monthly export → valid MoneyForward CSV
7. Audit verify → all hashes match
8. Access from second Mac → full functionality
