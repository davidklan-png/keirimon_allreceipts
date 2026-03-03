# Project Milestones & Issues

This document defines all milestones and issues for bringing the receipt management system from current state to MVP and full integration readiness.

**Current state:** Backend ~85% complete (all 6 API route files, services, models, utilities), frontend 0% (no React code yet), tests partial.

To register these on GitHub, run:
```bash
export GH_TOKEN="ghp_your_token"
./scripts/setup_github_milestones.sh
```

---

## M1: Backend Core Fixes & Completion

Complete remaining backend TODOs, fix code duplication, and ensure all API endpoints are production-ready.

| # | Issue | Priority | Labels |
|---|-------|----------|--------|
| 1 | Load vendors.json seed data into DB on startup | P0 | backend |
| 2 | Implement NTA cache cleanup background task | P1 | backend, integration |
| 3 | Extract shared CATEGORY_MAP to single source of truth | P1 | backend, debt |
| 4 | Restrict CORS to localhost and local network | P0 | backend, security |
| 5 | Implement OCR vendor category suggestion from DB | P0 | backend, ocr |
| 6 | Implement OCR temp file cleanup with TTL timer | P1 | backend |
| 7 | Add input validation for file uploads | P0 | backend, security |
| 8 | Add tax rate detection for MoneyForward export | P1 | backend, compliance |
| 9 | Fix async/sync inconsistencies in services | P1 | backend, debt |

---

## M2: Frontend MVP

Build the React+Vite frontend with all core screens.

| # | Issue | Priority | Labels |
|---|-------|----------|--------|
| 10 | Scaffold React + Vite frontend project | P0 | frontend |
| 11 | Build API client module for frontend | P0 | frontend |
| 12 | Build UploadZone component (drag-drop + camera capture) | P0 | frontend, ux |
| 13 | Build ConfirmForm component (OCR result review) | P0 | frontend, ux |
| 14 | Build SearchPanel component | P0 | frontend, ux |
| 15 | Build ExportPanel component (MoneyForward CSV) | P0 | frontend |
| 16 | Build VendorTable component (lookup editor) | P1 | frontend |
| 17 | Build AuditDashboard component | P1 | frontend, compliance |

---

## M3: End-to-End Integration & Testing

Wire frontend to backend, complete the full workflow, add integration tests.

| # | Issue | Priority | Labels |
|---|-------|----------|--------|
| 18 | Complete filing_service integration tests | P0 | testing |
| 19 | Add API route integration tests | P0 | testing |
| 20 | Add OCR extraction unit tests | P0 | testing, ocr |
| 21 | End-to-end workflow test: upload → OCR → confirm → file | P0 | testing |
| 22 | Verify all 42 functional requirements | P0 | testing, compliance |
| 23 | Test multi-Mac network access | P1 | testing, infra |

---

## M4: Security & Compliance Hardening

Input validation, compliance verification, and security review.

| # | Issue | Priority | Labels |
|---|-------|----------|--------|
| 24 | Validate registration_number format before NTA API call | P0 | backend, security, compliance |
| 25 | Add negative/zero amount validation | P0 | backend, security |
| 26 | Add date format validation and sanitization | P0 | backend, security |
| 27 | Implement duplicate receipt detection | P1 | backend, ux |
| 28 | Verify 電帳法 compliance with test evidence | P0 | compliance, testing |
| 29 | Verify インボイス制度 compliance | P0 | compliance, testing |

---

## M5: Production Readiness & Deployment

Final polish, benchmarks, documentation — MVP ships after this milestone.

| # | Issue | Priority | Labels |
|---|-------|----------|--------|
| 30 | Polish dev.sh startup script | P0 | infra |
| 31 | Performance benchmark: search on 2000 records | P1 | testing |
| 32 | Create .env.example with complete documentation | P1 | infra |
| 33 | Final manual test: complete workflow checklist | P0 | testing |
| 34 | Update README with final setup instructions | P1 | infra |

---

## M6: Full Integration & Post-MVP

Features deferred from MVP scope per REQUIREMENTS.md.

| # | Issue | Priority | Labels |
|---|-------|----------|--------|
| 35 | Implement recurring expense templates | P2 | frontend, backend |
| 36 | AMEX CSV auto-import | P2 | frontend, backend |
| 37 | freee export format support | P2 | backend, frontend |
| 38 | Email receipt ingestion | P2 | backend |
| 39 | PWA support for mobile | P2 | frontend |
| 40 | Multi-user authentication | P2 | backend, frontend, security |

---

## Code Review Summary

### Strengths
- Well-documented architecture (ARCHITECTURE.md, REQUIREMENTS.md, COMPLIANCE.md)
- Clean separation of concerns: routes → services → utils
- Proper data models with compliance considerations (SQLModel)
- Good OCR extraction with Japanese date/currency/invoice patterns
- Correct fiscal year logic (Feb 1 – Jan 31) with edge cases
- Atomic filing with rollback on failure
- Append-only audit log design

### Issues Found

**Security (P0)**
- CORS set to `*` (main.py:46)
- No file type validation (magic bytes)
- No input sanitization on uploads
- No authentication (all endpoints public)

**Code Quality**
- CATEGORY_MAP duplicated in filing_service.py and export.py
- Async/sync mixing: filing_service.py is synchronous, blocking the event loop
- 7 TODO comments in codebase with unfinished features

**Testing Gaps**
- filing_service tests are stubs (skeleton only)
- No API route tests
- No OCR extraction tests
- No integration tests

**Missing Implementation**
- Frontend completely absent (0 React code)
- Vendor seed loading not implemented
- NTA cache cleanup not scheduled
- OCR temp file cleanup has no timer
- Tax rate detection stub in export

### Dependency on External Services
- **Google Cloud Vision API** — requires API key + billing, primary OCR bottleneck
- **NTA Invoice API** — public, no auth, 30-day cache implemented
- Both are gracefully handled when unavailable (filing proceeds, flagged as unvalidated)
