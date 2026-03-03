# 領収書管理システム — Receipt Capture App

A local-network web app for a Japanese GK (合同会社) to capture, categorise, file, and report receipts in compliance with 電子帳簿保存法 and インボイス制度.

One Mac runs the server. Every other Mac (or iPhone) opens a browser tab and uses the same UI. No cloud required.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11+ / FastAPI | Fast to vibe-code, async file I/O, great Japanese UTF-8 handling |
| Database | SQLite (via SQLModel) | Zero-config, single file, sufficient for ~200 receipts/year |
| OCR | Google Vision API | Best accuracy on Japanese receipts and mixed-currency amounts |
| Frontend | React + Vite (single page) | Camera API access, drag-drop upload, runs in any browser |
| File store | Local filesystem | AllReceipts folder (existing structure preserved) |
| NTA Validation | NTA Invoice API (REST) | Live validation of 登録番号 (T + 13 digits) |

---

## Quickstart (5 steps)

### Prerequisites
- Python 3.11+
- Node 18+
- A Google Cloud project with Vision API enabled
- The `AllReceipts/` folder path on this machine

```bash
# 1. Clone and enter
git clone <your-repo> receipt-capture-app
cd receipt-capture-app

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in your values

# 3. Frontend
cd ../frontend
npm install

# 4. Run both (from project root)
./dev.sh                      # starts FastAPI on :8000 and Vite on :5173

# 5. Open in browser
open http://localhost:5173
```

Other Macs on the same network: `http://<server-ip>:5173`

To find your server IP: `ipconfig getifaddr en0`

---

## Environment Variables (`.env`)

```
GOOGLE_VISION_API_KEY=your_key_here
RECEIPTS_BASE_PATH=/Users/you/AllReceipts
DB_PATH=/Users/you/AllReceipts/receipts.db
AUDIT_LOG_PATH=/Users/you/AllReceipts/audit.log
COMPANY_NAME=Your GK Name
FISCAL_YEAR_START_MONTH=2          # February — FY runs Feb 1 – Jan 31
```

---

## MVP Scope (v1.0)

- [x] Upload receipt PDF/image or capture via phone camera
- [x] OCR extracts date, JPY amount, foreign amount, vendor name
- [x] Manual confirm/correct before filing
- [x] Auto-generate filename: `YYYYMMDD_CAT_NN_VENDOR_JPYAMT.pdf`
- [x] Auto-file to correct `FY / Month` folder
- [x] Write ledger entry to SQLite
- [x] Append-only audit log (電帳法 真実性)
- [x] Search receipts by date range, amount, vendor
- [x] NTA 登録番号 validation
- [x] Monthly CSV export (MoneyForward format)

## Out of Scope for v1.0 (backlog)

- Recurring expense auto-generation (BOSS templates)
- AMEX CSV auto-import
- freee export format
- Email receipt ingestion
- Multi-user auth
- Automated timestamp service (JIIMA-certified)

---

## Folder Structure (Runtime)

```
AllReceipts/
├── FY2027/
│   ├── 02_Feb/
│   │   └── 20270204_KTL_01_BOSS_12175.pdf
│   └── 03_Mar/
├── receipts.db       ← SQLite ledger
└── audit.log         ← append-only, never delete
```

---

## Compliance Summary

| Requirement | How satisfied |
|---|---|
| 電帳法 — 電子取引データ保存 | PDFs stored in filesystem, metadata in SQLite |
| 電帳法 — 真実性 | Append-only audit log + 事務処理規程 (see COMPLIANCE.md) |
| 電帳法 — 可視性 | Search by date / amount / vendor in <3s |
| インボイス制度 | 登録番号 captured + NTA API validated at entry |
| 保存期間 | 7-year deletion lock enforced in app |

See `REQUIREMENTS.md` for full spec and `ARCHITECTURE.md` for technical design.
