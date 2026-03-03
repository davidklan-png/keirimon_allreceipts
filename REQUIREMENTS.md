# Requirements Specification

## 1. Background

**Entity:** Japanese 合同会社 (GK / LLC)
**Use case:** Capture, categorise, file, and report business expense receipts for monthly bookkeeping and annual 法人税 filing.
**Volume:** ~80–100 receipts/year across three input types — AMEX digital, cash/physical, and paper scans.
**Fiscal year:** February 1 – January 31 (e.g. FY2027 = Feb 1 2027 – Jan 31 2028).
**Primary card:** American Express (AMEX) — statement date is the 4th of each month, covering the prior month's charges.

---

## 2. MVP Scope (v1.0)

### In scope
- Receipt ingestion via file upload (PDF, JPEG, PNG) and smartphone camera capture
- OCR extraction of key fields
- Human confirmation step before filing (OCR is never fully trusted)
- Auto-generated filename in the standard format
- Auto-filing to the correct FY/Month folder
- SQLite ledger entry on every filed receipt
- Append-only audit log
- 登録番号 capture and NTA API validation
- Search by date, amount, vendor
- Monthly CSV export in MoneyForward スモールビジネス import format

### Out of scope (v1.0 — track as backlog)
- Recurring expense templates (BOSS, water, coffee)
- AMEX CSV auto-import
- freee export
- Email ingestion (forward-to-file)
- Multi-user authentication
- JIIMA-certified timestamp service
- Mobile app (PWA or native)

---

## 3. Functional Requirements

### 3.1 Receipt Ingestion

**FR-01** The app MUST accept file upload of PDF, JPEG, and PNG files up to 20 MB.
**FR-02** The app MUST provide a camera capture interface accessible from a mobile browser (using the browser `<input capture="environment">` API — no native app required).
**FR-03** On upload, the app MUST display a loading state while OCR is running.
**FR-04** The app MUST NOT file a receipt automatically — a human confirmation screen MUST be shown before any write operation.

### 3.2 OCR Extraction

**FR-05** The OCR pipeline MUST attempt to extract the following fields from every receipt:

| Field | Type | Required |
|---|---|---|
| `receipt_date` | Date (YYYY-MM-DD) | Required |
| `amount_jpy` | Integer (¥) | Required |
| `amount_foreign` | Float | Optional |
| `currency_foreign` | String (ISO 4217) | Optional if amount_foreign present |
| `vendor_name` | String | Required |
| `registration_number` | String (T + 13 digits) | Optional |
| `notes` | String | Optional |

**FR-06** The app MUST display each extracted field with an editable text input so the user can correct OCR errors before confirmation.
**FR-07** The app MUST show the original receipt image alongside the extracted fields during confirmation (side-by-side on desktop, tabbed on mobile).
**FR-08** If OCR confidence is below 70% on any required field, the app MUST visually flag that field (yellow highlight) and require explicit user input.

### 3.3 Categorisation

**FR-09** The app MUST maintain an editable vendor-to-category lookup table (stored as `data/vendors.json`).
**FR-10** When `vendor_name` matches a known vendor in the lookup table, the app MUST pre-select the corresponding category code automatically.
**FR-11** When `vendor_name` does not match, the app MUST present a category code dropdown for manual selection. The selected mapping MUST be saved to the lookup table for future auto-classification (after user confirms "remember this vendor").
**FR-12** The category code dropdown MUST list all 12 standard codes (see Section 6).

### 3.4 Filename Generation

**FR-13** The app MUST generate the standard filename using confirmed field values:

```
YYYYMMDD_{CAT}_{NN}_{VENDOR}_{JPYAMT}.pdf
```

Where:
- `YYYYMMDD` = `receipt_date` formatted as 8-digit date
- `CAT` = 3-letter category code (e.g. `KTL`, `SHO`, `RND`)
- `NN` = 2-digit zero-padded sequence number, auto-incremented per day+category combination
- `VENDOR` = vendor name sanitised to ASCII/romaji, max 20 characters, no spaces (use CamelCase)
- `JPYAMT` = integer JPY amount, no commas

**FR-14** The generated filename MUST be shown to the user during the confirmation step and MUST be editable.
**FR-15** The app MUST prevent duplicate filenames by checking the target folder before writing.

### 3.5 Fiscal Year and Folder Routing

**FR-16** The fiscal year MUST be determined by `receipt_date`, not by statement date or upload date.
**FR-17** FY calculation rule: if `receipt_date` month >= 2 (February), FY = year of `receipt_date`. If month == 1 (January), FY = year of `receipt_date` - 1. Examples:
  - 2027-04-15 → FY2027
  - 2027-01-30 → FY2026
  - 2028-02-01 → FY2027 (first day of new FY)

**FR-18** The target folder MUST follow this structure:
```
{RECEIPTS_BASE_PATH}/FY{YYYY}/{MM}_{MonthName_EN}/
```
Example: `AllReceipts/FY2027/04_Apr/`

**FR-19** The app MUST create the target folder if it does not exist.
**FR-20** For AMEX receipts where the statement date and purchase date differ, the user MUST be able to manually override the `receipt_date` field to the actual purchase date during confirmation.

### 3.6 Filing and Ledger

**FR-21** On confirmation, the app MUST:
  1. Copy the original file to the target folder with the generated filename
  2. Write a ledger row to SQLite (see Section 5 — Data Model)
  3. Append a CREATE event to the audit log
  4. Return a success response with the filed path

**FR-22** The original uploaded file MUST be deleted from the temp upload directory after successful filing.
**FR-23** If any step in FR-21 fails, the app MUST roll back (delete the copied file if written, do not write the ledger row) and return a clear error message.

### 3.7 NTA 登録番号 Validation

**FR-24** When `registration_number` is populated, the app MUST call the NTA Invoice API to validate it:
```
GET https://web-api.invoice-kohyo.nta.go.jp/1/num?id=T{13-digit-number}&type=21
```
**FR-25** If the number is valid, display a green "登録済み" badge.
**FR-26** If the number is invalid or the vendor is not registered, display an amber "未登録" badge with the note: "仕入税額控除は80%まで（R11.9まで）".
**FR-27** If the NTA API is unreachable, the app MUST allow filing to proceed but MUST flag the record in the ledger as `nta_validated = false`.
**FR-28** The app MUST cache NTA validation results per registration number for 30 days to avoid redundant API calls.

### 3.8 Search

**FR-29** The search screen MUST support the following filters, individually or combined:
  - Date range (`from_date`, `to_date`)
  - Amount range (`min_jpy`, `max_jpy`)
  - Vendor name (case-insensitive substring match)
  - Category code (single select or "all")
  - Fiscal year (single select or "all")
  - Recurring flag (boolean)

**FR-30** Search results MUST return within 3 seconds for the full 7-year dataset.
**FR-31** Each search result row MUST include a link to open/download the original PDF.
**FR-32** Search results MUST be exportable as CSV.

### 3.9 Monthly Export

**FR-33** The export screen MUST allow selection of FY and month, then generate a CSV in MoneyForward スモールビジネス import format.
**FR-34** The MoneyForward CSV format requires these columns (in order):

```
計算対象,日付,内容,金額（円）,内税／外税,税率,勘定科目,税区分,補助科目,部門,メモ,仕訳メモ,管理番号
```

**FR-35** Category code → MoneyForward 勘定科目 mapping (see Section 6).

### 3.10 Audit Log

**FR-36** The audit log file (`audit.log`) MUST be append-only. The app MUST NEVER overwrite or delete any line.
**FR-37** Every audit log entry MUST be a single JSON line with these fields:
```json
{"ts": "2027-04-15T10:23:01Z", "event": "CREATE", "file": "FY2027/04_Apr/20270415_KTL_01_BOSS_12175.pdf", "user": "system", "hash": "sha256:..."}
```
**FR-38** `hash` MUST be the SHA-256 of the filed PDF at the time of creation.
**FR-39** A separate endpoint `GET /audit/verify` MUST recompute hashes for all filed PDFs and return a list of any files whose current hash does not match the audit log (tamper detection).

### 3.11 Retention

**FR-40** The app MUST prevent deletion of any record or file that is less than 7 years old (measured from `receipt_date`).
**FR-41** If a user attempts to delete a record within the retention window, the app MUST display: "この領収書は法人税法上7年間の保存義務があります（保存期限：{date}）" and refuse the operation.
**FR-42** After the 7-year retention period, the app MAY allow deletion but MUST require explicit confirmation.

---

## 4. Non-Functional Requirements

**NFR-01 Performance:** Search query response time < 3 seconds on a dataset of 2,000 records on a 2019+ MacBook.
**NFR-02 Availability:** The app is a local-network service. No uptime SLA required. Cold start must be < 5 seconds.
**NFR-03 File safety:** The app MUST never modify or delete the original receipt file after filing. Filed PDFs are write-once.
**NFR-04 Encoding:** All filenames, paths, and database strings MUST be UTF-8. All Japanese characters MUST be preserved without transliteration in display fields (only the filename `VENDOR` segment uses romaji).
**NFR-05 Portability:** The `RECEIPTS_BASE_PATH` and `DB_PATH` MUST be configurable via `.env` so the app works regardless of where the AllReceipts folder is mounted on each Mac.
**NFR-06 No external data storage:** No receipt data or metadata MUST be sent to any third party except: Google Vision API (image for OCR, no storage), and NTA Invoice API (registration number query only).
**NFR-07 Browser support:** Latest versions of Safari and Chrome on macOS. Camera capture must work on Safari iOS 16+.

---

## 5. Data Model

### `receipts` table (SQLite)

```sql
CREATE TABLE receipts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_date        DATE NOT NULL,                     -- actual purchase date
    fiscal_year         TEXT NOT NULL,                     -- e.g. "FY2027"
    statement_date      DATE,                              -- AMEX statement date if applicable
    category_code       TEXT NOT NULL,                     -- e.g. "KTL"
    category_name_jp    TEXT NOT NULL,                     -- e.g. "接待交際費"
    vendor_name         TEXT NOT NULL,
    amount_jpy          INTEGER NOT NULL,
    amount_foreign      REAL,
    currency_foreign    TEXT,                              -- ISO 4217 e.g. "USD"
    registration_number TEXT,                              -- T + 13 digits
    nta_validated       BOOLEAN DEFAULT FALSE,
    payment_method      TEXT NOT NULL DEFAULT 'AMEX',      -- AMEX | CASH | OTHER
    is_recurring        BOOLEAN DEFAULT FALSE,
    notes               TEXT,
    filename            TEXT NOT NULL UNIQUE,              -- the generated filename
    filepath            TEXT NOT NULL UNIQUE,              -- full path from RECEIPTS_BASE_PATH
    file_hash_sha256    TEXT NOT NULL,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    retention_until     DATE NOT NULL                      -- receipt_date + 7 years
);
```

### `vendors` table (SQLite, mirrors `data/vendors.json`)

```sql
CREATE TABLE vendors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_pattern  TEXT NOT NULL UNIQUE,   -- substring to match against OCR vendor name
    category_code   TEXT NOT NULL,
    romaji_name     TEXT NOT NULL,          -- used in filename VENDOR segment
    is_recurring    BOOLEAN DEFAULT FALSE,
    notes           TEXT,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `nta_cache` table

```sql
CREATE TABLE nta_cache (
    registration_number TEXT PRIMARY KEY,
    is_valid            BOOLEAN NOT NULL,
    company_name        TEXT,
    validated_at        DATETIME NOT NULL,
    expires_at          DATETIME NOT NULL   -- validated_at + 30 days
);
```

---

## 6. Reference Data

### Category Codes

| Code | 経費科目（日本語） | MoneyForward 勘定科目 | Description |
|---|---|---|---|
| SHO | 消耗品費 | 消耗品費 | Water, coffee, stationery, small accessories |
| KTL | 接待交際費 | 接待交際費 | Entertainment, client dining, gifts |
| RND | 研究開発費 | 研究開発費 | AI/cloud services, supplements, domain registration |
| TRS | 出張交通費 | 旅費交通費 | Flights, Shinkansen, rental cars, limousine bus |
| LOC | 交通費 | 旅費交通費 | Local taxi, bus, train (short distance) |
| ACC | 出張宿泊費 | 旅費交通費 | Hotels, guesthouses, Airbnb |
| WEL | 福利厚生費 | 福利厚生費 | Sports events, health subscriptions (Oura etc.) |
| COM | 通信費 | 通信費 | Yamato shipping, domain, phone |
| MTG | 会議費 | 会議費 | Meeting room, dining at business meetings |
| EQP | 工具機器備品 | 工具器具備品 | Computers, phones, equipment (>¥10,000) |
| ADV | 広告宣伝費 | 広告宣伝費 | Web advertising, promotional domain |
| FEE | 支払手数料 | 支払手数料 | Consulting, coaching fees |

### Known Recurring Vendors (seed data for `vendors` table)

```json
[
  { "vendor_pattern": "BOSS",        "category_code": "KTL", "romaji_name": "BOSS",        "is_recurring": true },
  { "vendor_pattern": "ヤマト",       "category_code": "COM", "romaji_name": "Yamato",       "is_recurring": true },
  { "vendor_pattern": "Yamato",      "category_code": "COM", "romaji_name": "Yamato",       "is_recurring": true },
  { "vendor_pattern": "Microsoft",   "category_code": "SHO", "romaji_name": "Microsoft",    "is_recurring": true },
  { "vendor_pattern": "Anthropic",   "category_code": "RND", "romaji_name": "Anthropic",    "is_recurring": true },
  { "vendor_pattern": "CLAUDE",      "category_code": "RND", "romaji_name": "Claude",       "is_recurring": true },
  { "vendor_pattern": "OpenAI",      "category_code": "RND", "romaji_name": "OpenAI",       "is_recurring": true },
  { "vendor_pattern": "bluehost",    "category_code": "RND", "romaji_name": "bluehost",     "is_recurring": true },
  { "vendor_pattern": "iHerb",       "category_code": "RND", "romaji_name": "iHerb",        "is_recurring": false },
  { "vendor_pattern": "Oura",        "category_code": "WEL", "romaji_name": "Oura",         "is_recurring": true },
  { "vendor_pattern": "Yamathon",    "category_code": "WEL", "romaji_name": "Yamathon",     "is_recurring": true },
  { "vendor_pattern": "Spartan",     "category_code": "WEL", "romaji_name": "Spartan",      "is_recurring": false },
  { "vendor_pattern": "Amazon",      "category_code": "SHO", "romaji_name": "Amazon",       "is_recurring": false },
  { "vendor_pattern": "Apple",       "category_code": "EQP", "romaji_name": "AppleStore",   "is_recurring": false },
  { "vendor_pattern": "Delta",       "category_code": "TRS", "romaji_name": "Delta",        "is_recurring": false },
  { "vendor_pattern": "Enterprise",  "category_code": "TRS", "romaji_name": "Enterprise",   "is_recurring": false },
  { "vendor_pattern": "TaxiGO",      "category_code": "LOC", "romaji_name": "TaxiGO",       "is_recurring": false },
  { "vendor_pattern": "GO Taxi",     "category_code": "LOC", "romaji_name": "GoTaxi",       "is_recurring": false },
  { "vendor_pattern": "Hover",       "category_code": "COM", "romaji_name": "Hover",        "is_recurring": true },
  { "vendor_pattern": "Stripe",      "category_code": "RND", "romaji_name": "Stripe",       "is_recurring": false },
  { "vendor_pattern": "食べログ",     "category_code": "MTG", "romaji_name": "Tabelog",      "is_recurring": false },
  { "vendor_pattern": "Booking",     "category_code": "ACC", "romaji_name": "Booking",      "is_recurring": false },
  { "vendor_pattern": "リムジン",     "category_code": "TRS", "romaji_name": "LimousineBus", "is_recurring": false }
]
```

### Month Folder Names

```python
MONTH_FOLDERS = {
    1: "01_Jan", 2: "02_Feb", 3: "03_Mar", 4: "04_Apr",
    5: "05_May", 6: "06_Jun", 7: "07_Jul", 8: "08_Aug",
    9: "09_Sep", 10: "10_Oct", 11: "11_Nov", 12: "12_Dec"
}
```

---

## 7. Compliance Requirements

### 7.1 電子帳簿保存法 — 電子取引データ保存 (Mandatory since Jan 1 2024)

Any receipt received electronically (email PDF, website download, app receipt) MUST be stored as electronic data. Printing and keeping paper is not permitted.

**真実性の確保 (Authenticity):**
This app satisfies authenticity via the **事務処理規程** approach (simplest compliant method for small GK):
- An internal control procedure document is on file with the accountant (see `COMPLIANCE.md` — template provided)
- The app enforces: append-only audit log, SHA-256 hash recorded at filing time, no-delete within retention window
- No JIIMA-certified timestamp API is required under this approach

**可視性の確保 (Accessibility):**
- Search by `receipt_date` range, `amount_jpy` range, and `vendor_name` substring (FR-29)
- All records returnable within 3 seconds (NFR-01)
- Original PDFs accessible via direct link from search results (FR-31)

### 7.2 電子帳簿保存法 — スキャナ保存 (Optional but recommended for paper receipts)

Paper receipts scanned via smartphone camera satisfy this rule when:
- Scan is created within **2 months + 7 business days** of physical receipt of document
- Image resolution is 200dpi+ (all modern iPhone/Android cameras satisfy this)
- The scan is filed through this app (which records creation timestamp and SHA-256)
- The 事務処理規程 document covers scan procedures

**Operational rule:** Never batch-scan months of paper at year-end. Scan within the same week as receiving.

### 7.3 インボイス制度 (Since Oct 1 2023)

- Suppliers must be 適格請求書発行事業者 (registered issuers) for you to claim 100% 仕入税額控除
- App validates 登録番号 via NTA API at capture time (FR-24 to FR-28)
- If unregistered: 80% deductible until Sep 30 2026, then 50% until Sep 30 2029, then 0%
- App stores 登録番号 in ledger for audit purposes

### 7.4 Retention Period

- 法人税法 requires 7 years for all 帳簿書類
- Receipts filed on `receipt_date` must be retained until `receipt_date + 7 years`
- App enforces this at the delete operation (FR-40 to FR-42)

---

## 8. Edge Cases

| Situation | Required handling |
|---|---|
| AMEX statement splits across FY boundary | User manually sets `receipt_date` to actual purchase date (not statement date) |
| Foreign currency receipt (USD/EUR/GBP) | Both foreign amount and JPY equivalent captured; filename uses JPY equivalent |
| Receipt covers multiple items (combined scan) | User creates one ledger entry per logical expense; app allows splitting into multiple confirms from one upload |
| Paper receipt with no 登録番号 | Field left blank; `nta_validated = false`; amber warning shown |
| Duplicate amount + vendor + date | App warns "Similar receipt already exists" but allows proceeding after confirmation |
| OCR completely fails | User manually fills all fields; original image still required |
| Network offline at filing time | NTA API validation skipped; `nta_validated = false`; all other operations proceed locally |
