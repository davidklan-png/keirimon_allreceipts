#!/usr/bin/env bash
#
# setup_github_milestones.sh
#
# Creates all MVP and Full Integration milestones and issues on GitHub
# for the keirimon_allreceipts project.
#
# Usage:
#   export GH_TOKEN="ghp_your_personal_access_token"
#   ./scripts/setup_github_milestones.sh
#
# Or pass the token inline:
#   GH_TOKEN="ghp_..." ./scripts/setup_github_milestones.sh
#
# Requirements:
#   - curl
#   - A GitHub personal access token with 'repo' scope
#

set -euo pipefail

REPO="davidklan-png/keirimon_allreceipts"
API="https://api.github.com"

if [ -z "${GH_TOKEN:-}" ]; then
  echo "ERROR: GH_TOKEN environment variable is required."
  echo "  export GH_TOKEN='ghp_your_token_here'"
  echo "  $0"
  exit 1
fi

AUTH="Authorization: Bearer $GH_TOKEN"
ACCEPT="Accept: application/vnd.github+json"
API_VER="X-GitHub-Api-Version: 2022-11-28"

# Helper: create a milestone and return its number
create_milestone() {
  local title="$1"
  local description="$2"
  local due_on="${3:-}"

  local payload
  if [ -n "$due_on" ]; then
    payload=$(cat <<EOJSON
{"title":"$title","description":"$description","due_on":"${due_on}T08:00:00Z"}
EOJSON
)
  else
    payload=$(cat <<EOJSON
{"title":"$title","description":"$description"}
EOJSON
)
  fi

  local response
  response=$(curl -s -X POST "$API/repos/$REPO/milestones" \
    -H "$AUTH" -H "$ACCEPT" -H "$API_VER" \
    -H "Content-Type: application/json" \
    -d "$payload")

  local number
  number=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('number',''))" 2>/dev/null || echo "")

  if [ -z "$number" ]; then
    echo "  WARNING: Failed to create milestone '$title'. Response: $response" >&2
    echo ""
  else
    echo "  Created milestone #$number: $title" >&2
    echo "$number"
  fi
}

# Helper: create an issue with labels and milestone
create_issue() {
  local title="$1"
  local body="$2"
  local milestone="$3"
  local labels="$4"

  local payload
  payload=$(python3 -c "
import json, sys
d = {
    'title': sys.argv[1],
    'body': sys.argv[2],
    'labels': json.loads(sys.argv[4])
}
m = sys.argv[3]
if m:
    d['milestone'] = int(m)
print(json.dumps(d))
" "$title" "$body" "$milestone" "$labels")

  local response
  response=$(curl -s -X POST "$API/repos/$REPO/issues" \
    -H "$AUTH" -H "$ACCEPT" -H "$API_VER" \
    -H "Content-Type: application/json" \
    -d "$payload")

  local issue_number
  issue_number=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('number',''))" 2>/dev/null || echo "")

  if [ -z "$issue_number" ]; then
    echo "    WARNING: Failed to create issue '$title'. Response: $response" >&2
  else
    echo "    Created issue #$issue_number: $title" >&2
  fi
}

# Helper: create a label (ignore if exists)
create_label() {
  local name="$1"
  local color="$2"
  local description="$3"

  curl -s -X POST "$API/repos/$REPO/labels" \
    -H "$AUTH" -H "$ACCEPT" -H "$API_VER" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$name\",\"color\":\"$color\",\"description\":\"$description\"}" > /dev/null 2>&1 || true
}

echo "=== Creating labels ==="
create_label "backend"     "0075ca" "Backend (FastAPI/Python)"
create_label "frontend"    "a2eeef" "Frontend (React/Vite)"
create_label "ocr"         "d876e3" "OCR pipeline"
create_label "compliance"  "e4e669" "電帳法/インボイス compliance"
create_label "testing"     "bfd4f2" "Tests and QA"
create_label "infra"       "f9d0c4" "Infrastructure, CI/CD, deployment"
create_label "security"    "b60205" "Security hardening"
create_label "integration" "1d76db" "External API integration"
create_label "ux"          "c5def5" "User experience"
create_label "bug"         "d73a4a" "Bug fix"
create_label "debt"        "fbca04" "Technical debt"
create_label "P0-critical" "b60205" "Must have for MVP"
create_label "P1-important" "ff9f1c" "Important but not blocking"
create_label "P2-nice"     "0e8a16" "Nice to have"

echo ""
echo "=== Creating milestones ==="

M1=$(create_milestone \
  "M1: Backend Core Fixes & Completion" \
  "Complete remaining backend TODOs, fix code duplication, and ensure all API endpoints are production-ready. This is the foundation everything else depends on.")

M2=$(create_milestone \
  "M2: Frontend MVP" \
  "Build the React+Vite frontend with all core screens: upload, OCR confirm, search, export, and vendor management. Camera capture for mobile browsers.")

M3=$(create_milestone \
  "M3: End-to-End Integration & Testing" \
  "Wire frontend to backend, complete the full upload-to-file workflow, add integration tests, and verify all 42 functional requirements from REQUIREMENTS.md.")

M4=$(create_milestone \
  "M4: Security & Compliance Hardening" \
  "Restrict CORS, add input validation, enforce file safety, and verify all 電帳法 and インボイス制度 compliance requirements with test evidence.")

M5=$(create_milestone \
  "M5: Production Readiness & Deployment" \
  "Local network deployment, dev.sh polish, multi-Mac verification, performance benchmarks, and documentation finalization. This milestone means MVP is shippable.")

M6=$(create_milestone \
  "M6: Full Integration & Post-MVP" \
  "Post-MVP features: recurring expense templates, AMEX CSV import, freee export, email ingestion, PWA support, and JIIMA timestamp integration.")

echo ""
echo "=== Creating issues for M1: Backend Core Fixes ==="

create_issue \
  "Load vendors.json seed data into DB on startup" \
  "$(cat <<'EOF'
## Context
`backend/main.py:26` has a TODO to load `data/vendors.json` into the `vendors` table on startup.

## Requirements
- On startup, check if the `vendors` table is empty
- If empty, read `data/vendors.json` and insert all 23 seed vendors
- If not empty, skip (don't duplicate data on restart)
- Log how many vendors were loaded

## Acceptance Criteria
- [ ] Server starts and loads vendors when DB is fresh
- [ ] Server restarts without duplicating vendors
- [ ] `GET /api/vendors` returns all 23 seed vendors after first boot

Refs: FR-09, FR-10
EOF
)" "$M1" '["backend","P0-critical"]'

create_issue \
  "Implement NTA cache cleanup background task" \
  "$(cat <<'EOF'
## Context
`backend/main.py:27` has a TODO to start a background task for NTA cache cleanup.

## Requirements
- Run a periodic task (e.g., every 6 hours) that deletes expired rows from `nta_cache`
- Expiry: rows where `expires_at < now()`
- Use FastAPI `BackgroundTasks` or `asyncio.create_task` on startup

## Acceptance Criteria
- [ ] Expired NTA cache entries are cleaned up automatically
- [ ] Task runs without blocking request handling
- [ ] Logged: how many entries purged per run

Refs: FR-28
EOF
)" "$M1" '["backend","integration"]'

create_issue \
  "Extract shared CATEGORY_MAP to a single source of truth" \
  "$(cat <<'EOF'
## Context
`CATEGORY_MAP` is duplicated in:
- `backend/services/filing_service.py:181`
- `backend/routes/export.py:22`

This is a DRY violation and a maintenance risk.

## Requirements
- Create a shared constants file (e.g., `backend/constants.py`) with the canonical CATEGORY_MAP
- Import from both `filing_service.py` and `export.py`
- Include all 12 category codes from REQUIREMENTS.md Section 6

## Acceptance Criteria
- [ ] Single definition of CATEGORY_MAP
- [ ] Both filing_service and export route import from shared location
- [ ] All 12 codes present and correct
EOF
)" "$M1" '["backend","debt"]'

create_issue \
  "Restrict CORS to localhost and local network" \
  "$(cat <<'EOF'
## Context
`backend/main.py:46` has `allow_origins=["*"]` with a TODO to restrict in production.

## Requirements
- Default to `["http://localhost:5173", "http://127.0.0.1:5173"]`
- Add env var `CORS_ORIGINS` (comma-separated) for the user to add their local network IPs
- Example: `CORS_ORIGINS=http://192.168.1.100:5173,http://192.168.1.101:5173`

## Acceptance Criteria
- [ ] CORS no longer allows `*`
- [ ] localhost/127.0.0.1 always allowed
- [ ] Additional origins configurable via `.env`

Refs: NFR-06, security
EOF
)" "$M1" '["backend","security","P0-critical"]'

create_issue \
  "Implement OCR vendor category suggestion from DB" \
  "$(cat <<'EOF'
## Context
`backend/services/ocr_service.py:292` has a TODO to look up vendor patterns in the database for category auto-suggestion.

## Requirements
- After OCR extracts `vendor_name`, query the `vendors` table for pattern matches
- Use case-insensitive substring matching against `vendor_pattern`
- If matched, return `category_code` and `romaji_name` in the OCR response
- If multiple matches, prefer the most specific (longest pattern)

## Acceptance Criteria
- [ ] Known vendors (e.g., "BOSS", "Anthropic") auto-suggest correct category
- [ ] Unknown vendors return no suggestion (user picks manually)
- [ ] Pattern matching is case-insensitive

Refs: FR-09, FR-10
EOF
)" "$M1" '["backend","ocr"]'

create_issue \
  "Implement OCR temp file cleanup with TTL timer" \
  "$(cat <<'EOF'
## Context
`backend/routes/ocr.py:105` has a TODO to implement actual temp file cleanup.

## Requirements
- After OCR upload, temp files should be deleted after 30 minutes (configurable)
- Use `asyncio.create_task` with a delay, or a periodic sweep
- Clean up both the uploaded file and any generated thumbnails

## Acceptance Criteria
- [ ] Temp files deleted within 30 min of upload
- [ ] No temp file buildup after extended use
- [ ] Successful filings still clean up immediately (existing behavior)
EOF
)" "$M1" '["backend","P1-important"]'

create_issue \
  "Add input validation for file uploads" \
  "$(cat <<'EOF'
## Context
File uploads currently lack validation for:
- File type verification (magic bytes, not just extension)
- Path traversal in filenames
- Reasonable file size limits enforcement before full upload

## Requirements
- Validate MIME type matches PDF/JPEG/PNG using magic bytes (first few bytes)
- Sanitize original filename to prevent path traversal
- Enforce 20 MB limit with clear error message
- Reject files with suspicious content

## Acceptance Criteria
- [ ] Non-PDF/JPEG/PNG files rejected with clear error
- [ ] Filenames with `../` or absolute paths rejected
- [ ] Files > 20 MB rejected before processing
- [ ] Appropriate HTTP 400 errors returned

Refs: FR-01
EOF
)" "$M1" '["backend","security","P0-critical"]'

create_issue \
  "Add tax rate detection for MoneyForward export" \
  "$(cat <<'EOF'
## Context
`backend/routes/export.py:103` has a TODO to auto-detect 8% tax for food items vs 10% default.

## Requirements
- Default tax rate: 10% (標準税率)
- For categories SHO (消耗品費) items that are food/beverage: use 8% (軽減税率)
- Add a `tax_rate` field to the receipt model or derive from category + notes
- MoneyForward CSV column 税率 should output correct rate

## Acceptance Criteria
- [ ] Standard 10% rate applied by default
- [ ] 8% rate applied when appropriate (food/beverage receipts)
- [ ] MoneyForward CSV exports correct tax rates

Refs: FR-34, FR-35
EOF
)" "$M1" '["backend","compliance","P1-important"]'

create_issue \
  "Fix async/sync inconsistencies in services" \
  "$(cat <<'EOF'
## Context
The codebase mixes async and sync patterns:
- `ocr_service.py` - properly async
- `nta_service.py` - properly async
- `filing_service.py` - synchronous (blocks event loop)
- `database.py` - synchronous `get_session()`

## Requirements
- Make `filing_service.py` async (use `aiofiles` for file ops, async DB session)
- Consider async SQLAlchemy session for database operations
- Ensure no blocking I/O in request handlers

## Acceptance Criteria
- [ ] `filing_service.py` uses async file operations
- [ ] No blocking I/O in FastAPI route handlers
- [ ] Upload → file workflow doesn't block other requests
EOF
)" "$M1" '["backend","debt","P1-important"]'

echo ""
echo "=== Creating issues for M2: Frontend MVP ==="

create_issue \
  "Scaffold React + Vite frontend project" \
  "$(cat <<'EOF'
## Context
The frontend directory is referenced in `dev.sh` but no code exists yet.

## Requirements
- Initialize with `npm create vite@latest frontend -- --template react`
- Set up project structure:
  ```
  frontend/
  ├── src/
  │   ├── components/
  │   ├── hooks/
  │   ├── api/
  │   ├── pages/
  │   └── App.jsx
  ├── package.json
  └── vite.config.js
  ```
- Configure Vite proxy to forward `/api` to FastAPI on `:8000`
- Bind dev server to `0.0.0.0` for LAN access
- Add basic routing (react-router-dom)

## Acceptance Criteria
- [ ] `cd frontend && npm install && npm run dev` starts successfully
- [ ] `dev.sh` works end-to-end (backend + frontend)
- [ ] API proxy to :8000 works from browser
- [ ] Accessible from other machines on LAN
EOF
)" "$M2" '["frontend","P0-critical"]'

create_issue \
  "Build API client module for frontend" \
  "$(cat <<'EOF'
## Requirements
Create `frontend/src/api/client.js` with functions for all backend endpoints:
- `uploadForOcr(file)` → POST /api/ocr/upload
- `getOcrStatus(ocrId)` → GET /api/ocr/status/{ocr_id}
- `fileReceipt(data)` → POST /api/receipts
- `getReceipt(id)` → GET /api/receipts/{id}
- `listReceipts(params)` → GET /api/receipts
- `searchReceipts(filters)` → GET /api/search
- `exportMoneyForward(fy, month)` → GET /api/export/moneyforward
- `getExportSummary(fy)` → GET /api/export/summary
- `verifyAudit()` → GET /api/audit/verify
- `getAuditLog(limit)` → GET /api/audit/log
- `listVendors()` → GET /api/vendors
- `createVendor(data)` → POST /api/vendors
- `updateVendor(id, data)` → PUT /api/vendors/{id}
- `deleteVendor(id)` → DELETE /api/vendors/{id}

## Acceptance Criteria
- [ ] All backend endpoints covered
- [ ] Proper error handling (show user-friendly messages)
- [ ] Loading states supported via return values
EOF
)" "$M2" '["frontend","P0-critical"]'

create_issue \
  "Build UploadZone component (drag-drop + camera capture)" \
  "$(cat <<'EOF'
## Requirements
- Drag-and-drop zone for PDF/JPEG/PNG files
- File picker button as fallback
- Camera capture button using `<input type="file" accept="image/*" capture="environment">`
- Show file preview (image thumbnail or PDF icon) after selection
- Upload to `/api/ocr/upload` with loading spinner
- On success, navigate to confirmation screen with OCR results
- Mobile-responsive layout

## Acceptance Criteria
- [ ] Drag-drop works on desktop Safari/Chrome
- [ ] Camera capture works on iOS Safari 16+
- [ ] File type validation (reject non-PDF/JPEG/PNG)
- [ ] Loading state during OCR processing
- [ ] Error state with retry option

Refs: FR-01, FR-02, FR-03, NFR-07
EOF
)" "$M2" '["frontend","ux","P0-critical"]'

create_issue \
  "Build ConfirmForm component (OCR result review)" \
  "$(cat <<'EOF'
## Requirements
- Display original receipt image alongside extracted fields (side-by-side desktop, tabbed mobile)
- Editable fields: receipt_date, amount_jpy, amount_foreign, currency_foreign, vendor_name, registration_number, notes
- Category dropdown with all 12 codes (pre-selected if vendor matched)
- Low-confidence fields (< 70%) highlighted in yellow
- Generated filename preview (editable)
- NTA validation badge (green/amber) when registration_number present
- Payment method selector (AMEX / CASH / OTHER)
- "File Receipt" button → POST /api/receipts
- Success/error feedback

## Acceptance Criteria
- [ ] All required fields editable
- [ ] Category auto-selected for known vendors
- [ ] Low-confidence OCR fields highlighted
- [ ] NTA badge shows validation status
- [ ] Filing succeeds and shows confirmation
- [ ] Side-by-side on desktop, tabbed on mobile

Refs: FR-04, FR-06, FR-07, FR-08, FR-11, FR-12, FR-14, FR-25, FR-26
EOF
)" "$M2" '["frontend","ux","P0-critical"]'

create_issue \
  "Build SearchPanel component" \
  "$(cat <<'EOF'
## Requirements
- Filter controls: date range, amount range, vendor name, category dropdown, FY selector, recurring toggle
- Results table with columns: date, vendor, category, amount, filename, actions
- Click filename to open/download the original PDF
- Export search results as CSV
- Pagination for large result sets
- Responsive layout

## Acceptance Criteria
- [ ] All filter types work individually and combined
- [ ] Results load within 3 seconds for full dataset
- [ ] PDF links work (open in new tab)
- [ ] CSV export downloads correctly
- [ ] Mobile-friendly layout

Refs: FR-29, FR-30, FR-31, FR-32
EOF
)" "$M2" '["frontend","ux","P0-critical"]'

create_issue \
  "Build ExportPanel component (MoneyForward CSV)" \
  "$(cat <<'EOF'
## Requirements
- FY selector dropdown
- Month selector (or "all months" for full FY)
- "Generate CSV" button → triggers download
- Summary view: total receipts, total amount, breakdown by category
- Preview table before download

## Acceptance Criteria
- [ ] FY/month selection works
- [ ] CSV downloads with correct MoneyForward format
- [ ] Summary statistics display correctly
- [ ] Empty months handled gracefully

Refs: FR-33, FR-34, FR-35
EOF
)" "$M2" '["frontend","P0-critical"]'

create_issue \
  "Build VendorTable component (lookup editor)" \
  "$(cat <<'EOF'
## Requirements
- Table listing all vendors: pattern, category, romaji name, recurring flag
- Add new vendor form (inline or modal)
- Edit existing vendor (inline editing)
- Delete vendor with confirmation
- Search/filter within vendor list

## Acceptance Criteria
- [ ] All CRUD operations work
- [ ] Changes persist (reflected in next OCR upload)
- [ ] Vendor count shown
- [ ] Confirmation before delete

Refs: FR-09, FR-11
EOF
)" "$M2" '["frontend","P1-important"]'

create_issue \
  "Build AuditDashboard component" \
  "$(cat <<'EOF'
## Requirements
- Display recent audit log entries (last 50)
- "Verify All" button → triggers hash verification
- Show verification results: pass/fail per file
- Statistics: total filed, total verified, any mismatches

## Acceptance Criteria
- [ ] Audit log entries display with timestamps
- [ ] Verification runs and shows results
- [ ] Tampered files clearly highlighted
- [ ] Stats summary at top

Refs: FR-36, FR-39
EOF
)" "$M2" '["frontend","compliance","P1-important"]'

echo ""
echo "=== Creating issues for M3: End-to-End Integration ==="

create_issue \
  "Complete filing_service integration tests" \
  "$(cat <<'EOF'
## Context
`tests/test_filing_service.py` has skeleton structure but incomplete implementations.

## Requirements
- Test successful filing: file copied, DB entry created, audit log appended
- Test rollback on failure: file not left behind, no DB entry
- Test 7-year retention lock: deletion blocked within window
- Test duplicate filename prevention
- Mock filesystem and database

## Acceptance Criteria
- [ ] All filing_service methods have test coverage
- [ ] Rollback scenario tested
- [ ] Retention lock tested
- [ ] Tests pass in CI
EOF
)" "$M3" '["testing","P0-critical"]'

create_issue \
  "Add API route integration tests" \
  "$(cat <<'EOF'
## Requirements
Using FastAPI TestClient, test all routes:
- POST /api/ocr/upload - file upload + OCR processing
- POST /api/receipts - receipt filing
- GET /api/receipts - listing with pagination
- GET /api/search - multi-filter search
- GET /api/export/moneyforward - CSV generation
- GET /api/audit/verify - hash verification
- CRUD /api/vendors - vendor management
- DELETE /api/receipts/{id} - retention lock enforcement

## Acceptance Criteria
- [ ] Every route has at least one happy-path test
- [ ] Error cases covered (404, 400, validation failures)
- [ ] Retention lock tested (delete within 7 years → 403)
- [ ] Tests use isolated test database
EOF
)" "$M3" '["testing","P0-critical"]'

create_issue \
  "Add OCR extraction unit tests" \
  "$(cat <<'EOF'
## Requirements
Test `ocr_service.py` extraction functions:
- Japanese date parsing (令和X年 format, standard YYYY/MM/DD, etc.)
- Amount extraction (¥, 円, comma-separated, foreign currencies)
- Vendor name extraction (first non-skip line logic)
- Registration number extraction (T + 13 digits)
- Confidence scoring logic
- Edge cases: empty text, garbage OCR, mixed languages

## Acceptance Criteria
- [ ] Date parsing covers all formats in ocr_service.py
- [ ] Amount parsing handles ¥, 円, USD, EUR patterns
- [ ] Registration number regex validated
- [ ] Confidence scoring tested
EOF
)" "$M3" '["testing","ocr","P0-critical"]'

create_issue \
  "End-to-end workflow test: upload → OCR → confirm → file" \
  "$(cat <<'EOF'
## Requirements
A full integration test that:
1. Uploads a sample receipt image/PDF
2. Receives OCR results
3. Submits confirmed data to file the receipt
4. Verifies: file exists in correct FY/Month folder, DB entry exists, audit log entry exists, hash matches
5. Verifies search returns the filed receipt
6. Verifies MoneyForward export includes the receipt

Use a mock Google Vision API response for deterministic testing.

## Acceptance Criteria
- [ ] Full workflow completes without errors
- [ ] File in correct location with correct name
- [ ] DB entry has all required fields
- [ ] Audit log entry present with correct hash
- [ ] Search finds the receipt
- [ ] Export includes the receipt
EOF
)" "$M3" '["testing","P0-critical"]'

create_issue \
  "Verify all 42 functional requirements" \
  "$(cat <<'EOF'
## Requirements
Create a test checklist or test suite that verifies every FR from REQUIREMENTS.md:
- FR-01 through FR-42
- Document which tests cover which FRs
- Identify any gaps

## Acceptance Criteria
- [ ] Mapping document: FR → test file/function
- [ ] All required FRs have at least one test
- [ ] Test report showing pass/fail per FR
EOF
)" "$M3" '["testing","compliance","P0-critical"]'

create_issue \
  "Test multi-Mac network access" \
  "$(cat <<'EOF'
## Requirements
Per ARCHITECTURE.md manual test checklist:
- Start server on Mac A
- Access from Mac B via `http://<server-ip>:5173`
- Test full workflow: upload, OCR, confirm, file, search, export
- Test camera capture from iPhone on same network

## Acceptance Criteria
- [ ] Frontend loads from LAN IP
- [ ] API calls work cross-origin (CORS configured)
- [ ] Camera capture works on mobile Safari
- [ ] File download works from secondary machine
EOF
)" "$M3" '["testing","infra","P1-important"]'

echo ""
echo "=== Creating issues for M4: Security & Compliance ==="

create_issue \
  "Validate registration_number format before NTA API call" \
  "$(cat <<'EOF'
## Context
Currently no format validation before calling the NTA API.

## Requirements
- Validate registration_number matches pattern: T followed by exactly 13 digits
- Reject malformed numbers before making API call
- Return clear error message for invalid format

## Acceptance Criteria
- [ ] Valid format (T1234567890123) → NTA API called
- [ ] Invalid format → rejected with message, no API call
- [ ] Empty/null → skipped gracefully
EOF
)" "$M4" '["backend","security","compliance"]'

create_issue \
  "Add negative/zero amount validation" \
  "$(cat <<'EOF'
## Context
Amount fields are not validated for negative or zero values.

## Requirements
- `amount_jpy` must be positive integer (> 0)
- `amount_foreign` if present must be positive (> 0)
- Reject at API level with 400 error and clear message

## Acceptance Criteria
- [ ] Zero amounts rejected
- [ ] Negative amounts rejected
- [ ] Proper error messages returned
EOF
)" "$M4" '["backend","security"]'

create_issue \
  "Add date format validation and sanitization" \
  "$(cat <<'EOF'
## Context
Date parsing currently assumes correct format without explicit validation.

## Requirements
- Validate `receipt_date` is a valid date in YYYY-MM-DD format
- Reject future dates (receipt_date > today + 1 day)
- Reject dates > 8 years old (likely typo)
- Validate `statement_date` similarly if present

## Acceptance Criteria
- [ ] Invalid date formats rejected with clear message
- [ ] Future dates rejected
- [ ] Very old dates rejected with warning
EOF
)" "$M4" '["backend","security"]'

create_issue \
  "Implement duplicate receipt detection" \
  "$(cat <<'EOF'
## Context
Per REQUIREMENTS.md edge cases: "Duplicate amount + vendor + date → App warns but allows proceeding."

## Requirements
- Before filing, check for existing receipts with same date + vendor + amount
- If found, return warning in confirmation response
- User can still proceed (not blocked, just warned)

## Acceptance Criteria
- [ ] Duplicate detection fires on matching date+vendor+amount
- [ ] Warning message shown to user
- [ ] User can override and file anyway

Refs: REQUIREMENTS.md Edge Cases
EOF
)" "$M4" '["backend","ux","P1-important"]'

create_issue \
  "Verify 電帳法 compliance with test evidence" \
  "$(cat <<'EOF'
## Requirements
Create compliance verification tests for 電子帳簿保存法:

### 真実性 (Authenticity)
- [ ] Audit log is append-only (cannot modify/delete entries)
- [ ] SHA-256 hash recorded at filing time
- [ ] Hash verification detects file tampering
- [ ] Deletion blocked within 7-year retention window

### 可視性 (Accessibility)
- [ ] Search by date range works
- [ ] Search by amount range works
- [ ] Search by vendor name works
- [ ] Results return < 3 seconds on 2000 records
- [ ] Original PDF accessible from search results

### スキャナ保存
- [ ] Creation timestamp recorded
- [ ] SHA-256 hash stored

## Acceptance Criteria
- [ ] All checks pass
- [ ] Evidence document generated (test report)

Refs: REQUIREMENTS.md Section 7, COMPLIANCE.md
EOF
)" "$M4" '["compliance","testing","P0-critical"]'

create_issue \
  "Verify インボイス制度 compliance" \
  "$(cat <<'EOF'
## Requirements
- [ ] 登録番号 (T + 13 digits) captured during OCR
- [ ] NTA API validation returns correct status
- [ ] Valid numbers show green badge
- [ ] Invalid/unregistered show amber badge with 80% note
- [ ] API timeout → filing proceeds, flagged as unvalidated
- [ ] 30-day cache reduces redundant API calls
- [ ] Registration number stored in ledger for audit

## Acceptance Criteria
- [ ] All checks pass with test evidence
- [ ] Known valid and invalid numbers tested

Refs: FR-24 through FR-28
EOF
)" "$M4" '["compliance","testing","P0-critical"]'

echo ""
echo "=== Creating issues for M5: Production Readiness ==="

create_issue \
  "Polish dev.sh startup script" \
  "$(cat <<'EOF'
## Requirements
- Handle missing Python 3.11+ gracefully
- Handle missing Node 18+ gracefully
- Check for required .env variables before starting
- Add health check after startup (curl localhost:8000/docs)
- Add clean shutdown (trap SIGINT, kill both processes)
- Print LAN IP address for easy sharing

## Acceptance Criteria
- [ ] Fresh clone → `./dev.sh` works first time
- [ ] Missing prereqs → helpful error messages
- [ ] Ctrl+C cleanly stops both servers
- [ ] LAN IP printed at startup
EOF
)" "$M5" '["infra","P0-critical"]'

create_issue \
  "Performance benchmark: search on 2000 records" \
  "$(cat <<'EOF'
## Requirements
- Create a seed script that generates 2000 realistic test receipts
- Benchmark search queries (date range, amount, vendor, combined)
- Verify all return < 3 seconds on target hardware
- Add database indexes if needed

## Acceptance Criteria
- [ ] Seed script generates 2000 receipts
- [ ] All search queries < 3 seconds
- [ ] Benchmark results documented
- [ ] Indexes added if needed

Refs: NFR-01, FR-30
EOF
)" "$M5" '["testing","P1-important"]'

create_issue \
  "Create .env.example with complete documentation" \
  "$(cat <<'EOF'
## Requirements
- Ensure all env vars are documented with:
  - Purpose
  - Required vs optional
  - Default value (if any)
  - Example value
- Add `CORS_ORIGINS` (from CORS restriction issue)
- Add `UPLOAD_MAX_SIZE_MB`
- Add `OCR_TEMP_TTL_MINUTES`

## Acceptance Criteria
- [ ] Every env var documented
- [ ] New user can configure from .env.example alone
- [ ] No undocumented env vars in codebase
EOF
)" "$M5" '["infra","P1-important"]'

create_issue \
  "Final manual test: complete workflow checklist" \
  "$(cat <<'EOF'
## Requirements
Execute the full manual test checklist from ARCHITECTURE.md:

1. [ ] Upload Japanese PDF → OCR extracts fields → files to correct FY/Month folder
2. [ ] Upload USD receipt → both foreign and JPY amounts captured
3. [ ] Invalid 登録番号 → amber warning shown, filing still allowed
4. [ ] Search by date → results return < 3 seconds
5. [ ] Delete within 7 years → blocked with retention message
6. [ ] Export April → valid MoneyForward CSV generated
7. [ ] Audit verify → all hashes match
8. [ ] Network access from 2nd Mac → full functionality works

## Acceptance Criteria
- [ ] All 8 checks pass
- [ ] Screenshots/evidence collected
- [ ] Any issues logged as separate bugs
EOF
)" "$M5" '["testing","P0-critical"]'

create_issue \
  "Update README with final setup instructions" \
  "$(cat <<'EOF'
## Requirements
- Verify quickstart steps work on fresh clone
- Add troubleshooting section
- Add screenshots of key screens
- Document LAN access setup
- Link to ARCHITECTURE.md for technical details
- Add license information

## Acceptance Criteria
- [ ] New user can go from zero to working app following README alone
- [ ] All links work
- [ ] Screenshots current
EOF
)" "$M5" '["infra","P1-important"]'

echo ""
echo "=== Creating issues for M6: Full Integration (Post-MVP) ==="

create_issue \
  "Implement recurring expense templates" \
  "$(cat <<'EOF'
## Context
Monthly recurring expenses (BOSS coffee service, water delivery, etc.) have predictable amounts and vendors.

## Requirements
- Template system for recurring expenses
- One-click filing: select template → auto-fill all fields
- Still requires confirmation before filing
- Track which months have been filed vs pending

## Acceptance Criteria
- [ ] Templates created for known recurring vendors
- [ ] One-click pre-fill works
- [ ] Monthly tracking shows filed/pending status

Refs: REQUIREMENTS.md backlog
EOF
)" "$M6" '["frontend","backend","P2-nice"]'

create_issue \
  "AMEX CSV auto-import" \
  "$(cat <<'EOF'
## Context
AMEX statements arrive as CSV files with multiple transactions.

## Requirements
- Upload AMEX CSV file
- Parse all transactions
- Match against known vendors for auto-categorization
- Present all transactions for batch confirmation
- File each as individual receipt

## Acceptance Criteria
- [ ] AMEX CSV parsed correctly
- [ ] Known vendors auto-categorized
- [ ] Batch confirmation UI
- [ ] Individual receipts filed

Refs: REQUIREMENTS.md backlog
EOF
)" "$M6" '["frontend","backend","P2-nice"]'

create_issue \
  "freee export format support" \
  "$(cat <<'EOF'
## Requirements
- Add freee CSV export alongside MoneyForward
- Map category codes to freee 勘定科目
- Export endpoint: GET /api/export/freee

## Acceptance Criteria
- [ ] freee CSV format correct
- [ ] Category mapping complete
- [ ] Export works from UI

Refs: REQUIREMENTS.md backlog
EOF
)" "$M6" '["backend","frontend","P2-nice"]'

create_issue \
  "Email receipt ingestion" \
  "$(cat <<'EOF'
## Requirements
- Forward-to-file email endpoint
- Parse email for PDF attachments
- Auto-trigger OCR on received attachments
- Queue for user confirmation

## Acceptance Criteria
- [ ] Email forwarding configured
- [ ] PDF attachments extracted
- [ ] OCR triggered automatically
- [ ] Appears in confirmation queue

Refs: REQUIREMENTS.md backlog
EOF
)" "$M6" '["backend","P2-nice"]'

create_issue \
  "PWA support for mobile" \
  "$(cat <<'EOF'
## Requirements
- Add PWA manifest and service worker
- Offline-capable for viewing already-filed receipts
- Add to Home Screen support on iOS/Android
- Camera capture optimized for mobile

## Acceptance Criteria
- [ ] Installable as PWA on iOS and Android
- [ ] Offline viewing works
- [ ] Camera capture seamless from PWA

Refs: REQUIREMENTS.md backlog
EOF
)" "$M6" '["frontend","P2-nice"]'

create_issue \
  "Multi-user authentication" \
  "$(cat <<'EOF'
## Context
Currently all actions are logged as "system" user.

## Requirements
- Simple authentication (local accounts, no SSO needed)
- Track which user filed each receipt
- User management UI
- Audit log includes actual user

## Acceptance Criteria
- [ ] Users can log in
- [ ] Receipts attributed to filing user
- [ ] Audit log shows actual user
- [ ] User management available

Refs: REQUIREMENTS.md backlog
EOF
)" "$M6" '["backend","frontend","security","P2-nice"]'

echo ""
echo "=== Done! ==="
echo "All milestones and issues have been created."
echo "Visit: https://github.com/$REPO/milestones"
echo "Visit: https://github.com/$REPO/issues"
