# Hybrid Intelligent Company Duplicate Detection System

A deterministic, high-precision web application for company entity duplicate detection. Built to resolve client complaints around look-alike confusion, preserved Entity IDs, domain-level matching, non-repetitive exports, and auditable human review.

Complies with all requirements from **Groups 1–8** and the agent execution contract in `COMPANY_DUPLICATE_DETECTION_.md`.

---

## 1. System Architecture

The application is architected as a clean modular monolith:
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.x + Alembic Migrations + RapidFuzz + tldextract (offline PSL).
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS (styled after the approved dark navy & teal Matching Results dashboard visual specification).
- **Database:** SQLite (`company_duplicates.db`) with `PRAGMA foreign_keys=ON`.
- **Three Primary Pages Only:**
  1. `Dashboard & Upload`: Master database metrics, CSV drag-and-drop, sample benchmark loader, configurable 80% default fuzzy threshold slider (50–100%), and ingestion validation preview.
  2. `Matching Results & Reviews`: 5 Summary Metric Cards, compact multi-filter row, search bar, authoritative candidate results grid, and a slide-over Evidence & Review Drawer with side-by-side comparison, deterministic rationale, append-only human review actions, review audit history, and optional AI verification panel.
  3. `Reports & Exports`: 3 distinct views from a single backend export service with formula injection protection and UTF-8 BOM encoding.

---

## 2. Invariant Verification

- **Master Database Size:** Exactly **10,000** synthetic master rows.
- **Intentional Duplicate Groups:** Exactly **200** intentional duplicate groups (each group has $\ge 2$ records, partitioned with ground truth labels isolated from runtime inference).
- **Deterministic Seeding:** Fixed seed (default 42). Database is never overwritten unless `--reset` is explicitly passed.
- **AI Verification Feature Flag:** `AI_VERIFICATION_ENABLED=false` by default. Core functionality runs completely offline with zero paid API keys, zero external network dependencies, and zero costs.

---

## 3. Quick Start & Local Run Commands

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Node.js 18+ (tested on Node.js v24.22) & npm

### Step 1: Backend Setup
```bash
# In project root:
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Database Migrations & Seeding
```bash
# Run Alembic migrations
alembic upgrade head

# Deterministic master database seeder (10,000 rows, 200 duplicate groups)
python -m database.seed_database --reset --seed 42 --rows 10000 --duplicate-groups 200
```

### Step 3: Start the Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```
- API Health Endpoint: `http://localhost:8000/api/health`
- Database Statistics: `http://localhost:8000/api/database/stats`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

### Step 4: Frontend Setup & Run (in a separate terminal)
```bash
cd frontend
npm install
npm run build   # Builds production bundle to frontend/dist (FastAPI serves this automatically)

# OR run in Vite dev mode:
npm run dev     # Starts dev server on http://localhost:5173 with proxy to port 8000
```

---

## 4. Matching & Scoring Business Rules (BR-01 to BR-15)

The matching engine applies the following authoritative decision matrix in strict priority:

| Rule | Website Match | LinkedIn Match | Other Condition | Classification | Evidence & Action |
|---|---|---|---|---|---|
| **BR-01** | `MATCH` | `MATCH` | — | High-confidence Candidate | Exact domain and LinkedIn matches recorded. |
| **BR-02** | `MATCH` | `UNAVAILABLE` | — | High-confidence Candidate | Exact domain recorded; LinkedIn unavailable. |
| **BR-03** | `UNAVAILABLE` | `MATCH` | — | High-confidence Candidate | Exact LinkedIn recorded; website unavailable. |
| **BR-04** | `MATCH` | `CONFLICT` | — | Needs Review | Identifier conflict overrides exact match. |
| **BR-05** | `CONFLICT` | `MATCH` | — | Needs Review | Identifier conflict overrides exact match. |
| **BR-06** | `CONFLICT` | `CONFLICT` | — | Not a Match / Related Lead | Identifiers conflict; surfaced as investigation lead if name look-alike. |
| **BR-07** | `UNAVAILABLE` | `UNAVAILABLE` | Master both unavailable & Legal Name similarity $\ge 80.0\%$ | Potential Duplicate | RapidFuzz unrounded ratio $\ge 80.0\%$. Exact 80 qualifies. |
| **BR-08** | `UNAVAILABLE` | `UNAVAILABLE` | Master both unavailable & Legal Name similarity $< 80.0\%$ | Not a Match | Below threshold under fuzzy rule. |
| **BR-09** | `UNAVAILABLE` | `UNAVAILABLE` | Master both unavailable & either legal name unusable | Insufficient Data | No fabricated score. |
| **BR-10** | `CONFLICT` | `UNAVAILABLE` | Master has $\ge 1$ identifier | Not a Match | No fuzzy fallback. Look-alike lead only. |
| **BR-11** | `UNAVAILABLE` | `CONFLICT` | Master has $\ge 1$ identifier | Not a Match | No fuzzy fallback. Look-alike lead only. |
| **BR-12** | `UNAVAILABLE` | `UNAVAILABLE` | Master has identifiers, upload has none | Insufficient Data | Insufficient comparable identifiers. |
| **BR-13** | Any | Any | One row matches multiple master entities | Keep All Unique Pairs | De-duplicate on `(run_id, upload_row_id, entity_id)`. |
| **BR-14** | Any | Any | Display & Export | Master Entity ID + Adjacent Legal Name | Real `entities.entity_id` and authoritative `legal_name`. Never `IMPORT_BATCH`. |
| **BR-15** | Any | Any | Human Review | Append-Only `duplicate_reviews` | Persist human decision; never mutate or delete master entity. |

---

## 5. Client Complaints Addressed & Acceptance Traceability

| ID | Issue Raised | Resolution & Measured Evidence |
|---|---|---|
| **AC-01** | Tool hangs / is slow | Core comparison runs in **0.123s** for 10 rows vs 10,000 SQLite master entities (target $\le 3.0$s). |
| **AC-02** | Trimark look-alikes missed | Separate related-name discovery surfaces Trimark look-alikes across industries (`Trimark Property` vs `Trimark Petroleum`) without falsely marking them duplicates. |
| **AC-03** | `IMPORT_BATCH` exported instead of Entity ID | Authoritative `entities.entity_id` is preserved and exported in every report. |
| **AC-04** | Legal Name missing beside Entity ID | Every export places authoritative `entities.legal_name` adjacent to `entity_id`. |
| **AC-05** | Potential Duplicate download repeats companies | `master_summary` export guarantees exactly one row per master `entity_id`. Zero repeats. |
| **AC-06** | URL vs web domain confusion | PSL-aware normalized registered domain (`tldextract`) matches `https://www.example.com/about` and `example.com`. |
| **AC-07** | Confirm accuracy percentage | Measured on held-out synthetic test partition: **Precision: 100.00%**, **Recall: 95.45%**, **F1: 97.67%**, **Candidate Recall: 100.00%**. |
| **AC-08** | Core matching logic | All BR-01–BR-15 rules implemented and verified by automated unit tests. |
| **AC-09** | Required columns & status | UI and exports present Company Name, Website Domain, LinkedIn, Status, and separate Name Similarity (%). |
| **AC-10** | Review safety | Reviews saved append-only in `duplicate_reviews`; source master records are never mutated or deleted. |

---

## 6. Export Contract (Three Distinct Views)

1. `uploaded_summary` (`GET /api/imports/{run_id}/export?type=uploaded_summary`):
   - Row grain: exactly one row per `(run_id, upload_record_id)`.
   - Accounts for all uploaded records, including those with zero candidate matches.
2. `master_summary` (`GET /api/imports/{run_id}/export?type=master_summary`):
   - Row grain: exactly one row per `(run_id, entity_id)`.
   - Displays `Matched Entity ID` and adjacent `Matched Legal Name`. Zero duplicate master companies.
3. `candidate_details` (`GET /api/imports/{run_id}/export?type=candidate_details`):
   - Row grain: exactly one row per candidate pair `(run_id, upload_record_id, entity_id)`.
   - Complete audit trail with exact match states, fuzzy similarity %, rationale, and latest human review decision.
- **Formula Injection Protection:** All exported text fields beginning with `=`, `+`, `-`, `@`, `\t`, `\r` are sanitized by prepending an apostrophe (`'`).

---

## 7. Open Business-Owner Decisions (Provisional Defaults)

| Decision ID | Point Under Confirmation | Provisional Demo Behavior Implemented |
|---|---|---|
| **DEC-01** | "Both identifiers blank" scope | Master record has both domain and LinkedIn missing/unusable; upload may have populated identifiers. |
| **DEC-02** | Legal Name scope for 80% threshold | Mandatory 80% threshold compares **Legal Name-to-Legal Name**. Other combinations are supplementary discovery only. |
| **DEC-03** | "Potential Duplicate" download grain | Provided both `master_summary` (1 row per master entity) and `uploaded_summary` (1 row per upload), plus `candidate_details`. |
| **Status %** | Percentage presentation in Status column | Distinct `Name Similarity (%)` column displayed alongside `Match Status` badge to avoid misrepresenting string similarity as calibrated probability. |

---

## 8. Executed Automated Tests & Quality Gates

Run the complete test suite:
```bash
pytest -v
```

All 33 automated tests pass:
- `test_normalization.py` (6 passed): Unicode NFKC, casefolding, protected words preservation, registered domains, LinkedIn canonicalization.
- `test_rules.py` (15 passed): BR-01 to BR-15, exact 80.0 threshold boundary, conflict precedence, Trimark hard negative.
- `test_dataset.py` (3 passed): 10,000 master entities, exactly 200 duplicate groups, seed=42 reproducibility.
- `test_api.py` (3 passed): CSV upload, compare execution, candidate retrieval, review submission, all 3 exports.
- `test_exports.py` (3 passed): formula injection sanitization, adjacent ID/Legal Name verification, error handling.
- `test_benchmarks.py` (2 passed): held-out partition evaluation, runtime latency benchmark.
- `test_e2e_smoke.py` (1 passed): complete end-to-end user journey smoke test.
