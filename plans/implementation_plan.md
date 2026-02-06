# Implementation Plan: Codebase Cleanup & Deployment Readiness

**Created:** 2026-02-06  
**Source:** [`plans/codebase_analysis.md`](plans/codebase_analysis.md)  
**Goal:** Clean up structural debt, improve maintainability, and prepare for Raspberry Pi deployment

---

## Phase A: Documentation Cleanup

Quick wins that make everything else easier to reason about.

### A1: Trim ROADMAP.md to Future Work Only ✅
- [x] Remove all completed phase details (Phases 1–5D) — keep only the phase title and "✅" marker as a one-liner
- [x] Remove duplicate task lists (lines 385–426 vs 559–576)
- [x] Remove AI model cost comparison tables (lines 714–778)
- [x] Remove abandoned Option A/B model selection discussions (lines 632–712)
- [x] Remove stale unchecked items for work completed in earlier phases (lines 503–616)
- [x] Add a clean "Status Summary" section at the top showing what's done vs what's next
- [x] Keep only Phase 6 and Phase 7 task details as the active roadmap

### A2: Clean Up LOG.md ✅
- [x] Condense each phase entry to: key decisions made, problems encountered, lessons learned
- [x] Remove blow-by-blow implementation details that duplicate ROADMAP.md
- [x] Target: reduce from 649 lines to ~150 lines of high-value content

### A3: Fix start_pytaaa_web_db.sh ✅
- [x] Add `#!/bin/bash` shebang line
- [x] Add `set -euo pipefail` for error handling
- [x] Remove bare URLs — move to comments
- [x] Add command-line argument for data directory path instead of hardcoding
- [x] Make it actually executable: `chmod +x start_pytaaa_web_db.sh`

### A4: Create .env.example ✅
- [x] Create `.env.example` with all required environment variables
- [x] Include: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_SERVER`, `DATABASE_URL`
- [x] Add comments explaining each variable
- [x] Add deployment notes for local dev vs Raspberry Pi

### A5: Fix Stale Docstrings ✅
- [x] Fix `compare_models()` docstring — says "max 5000" but allows 100,000
- [x] Review all endpoint docstrings for accuracy

---

## Phase B: Code Structure Refactoring

The biggest phase — split the god endpoint file and add a service layer.

### B1: Split Endpoint File into Domain-Specific Modules ✅
- [x] Create `app/api/v1/endpoints/performance.py` — move `get_model_performance()` and `compare_models()`
- [x] Create `app/api/v1/endpoints/holdings.py` — move `get_model_holdings()`, `get_model_holdings_by_date()`, `get_model_snapshot_dates()`
- [x] Create `app/api/v1/endpoints/backtest.py` — move `get_backtest_data()` and `compare_backtest_data()`
- [x] Keep `app/api/v1/endpoints/models.py` with only: `list_models()`, `get_model()`, and `get_model_or_404()` helper
- [x] Update `app/api/v1/api.py` to register all new routers with appropriate prefixes
- [x] Verify all routes still work with correct URL paths

**Results:**
- `models.py`: 477 lines → 85 lines
- `performance.py`: 115 lines (new)
- `holdings.py`: 115 lines (new)
- `backtest.py`: 110 lines (new)

### B2: Fix Route Ordering Bug ✅
- [x] Ensure `/backtest/compare` is registered before `/{model_id}/backtest` in the router
- [x] Comment added in `api.py` explaining the registration order
- [x] **ADDITIONAL FIX:** Reordered router registration in `api.py` — `performance.router` now registered before `models.router` to prevent `/{model_id}` from intercepting `/compare`
- [x] Moved `/compare` endpoint before `/{model_id}/performance` within `performance.py`

### B3: Extract Shared Database Factory for CLI ✅
- [x] Create `app/db/cli_session.py` with a `create_cli_session()` factory function
- [x] Accept optional `server` parameter, default to "localhost"
- [x] Replace duplicate engine creation in `ingest_model()` and `ingest_backtest_data()`
- [x] Both functions now call the shared factory

### B4: Remove Empty Utils Package ✅
- [x] Delete `app/utils/__init__.py`
- [x] Delete `app/utils/` directory
- [x] Verified no imports reference `app.utils` anywhere

### B5: Extract Shared Frontend Assets ✅
- [x] Create `app/static/shared.css` with common styles (layout, cards, buttons, charts, responsive)
- [x] Create `app/static/shared.js` with common constants (API_BASE, COLORS, PERIOD_OPTIONS, CHART_DEFAULTS, utilities)
- [ ] Update `dashboard.html` to use shared assets via `<link>` and `<script>` tags — **DEFERRED**
- [ ] Update `comparison.html` to use shared assets — **DEFERRED**
- [ ] Update `backtest.html` to use shared assets — **DEFERRED**

**Note:** HTML file updates deferred to avoid breaking existing functionality. The shared assets are created and ready for future integration.

---

## Phase C: Database & Performance

Quick wins for query performance and correctness.

### C1: Add Compound Indexes ✅
- [x] Add compound index `(model_id, date)` to `PerformanceMetric` in `app/models/trading.py`
- [x] Add compound index `(model_id, date)` to `PortfolioSnapshot` in `app/models/trading.py`
- [x] Generate Alembic migration: `alembic revision --autogenerate -m "add_compound_indexes"`
- [x] Review and apply migration: `alembic upgrade head`
- [ ] Verify query performance improvement with `EXPLAIN ANALYZE` — **PENDING**

### C2: Fix migrations/env.py ✅
- [x] Add `BacktestData` to the import line in `migrations/env.py`
- [ ] Verify autogenerate detects no pending changes: `alembic revision --autogenerate -m "test"` should produce empty migration — **PENDING**

### C3: Make SQL Echo Configurable ✅
- [x] Add `SQL_ECHO: bool = False` to `Settings` class in `app/core/config.py`
- [x] Update `app/db/session.py` to use `settings.SQL_ECHO` instead of hardcoded `True`
- [x] `.env.example` already includes `SQL_ECHO` with comment

### C4: Remove Unused Dependencies ✅
- [x] Remove `pandas==2.2.1` from `requirements.txt`
- [x] Verified no `import pandas` exists in the codebase
- [x] Rebuild Docker image to verify no import errors — **COMPLETED**

---

## Phase D: Error Handling & Robustness

### D1: Fix Bare Except in Holdings Parser ✅
- [x] Replaced bare `except:` on line 80 of `app/parsers/holdings_parser.py` with `except (ValueError, IndexError):`
- [x] Added comment explaining what exceptions are being caught

### D2: Add Health Check Endpoint ✅
- [x] Added `GET /health` endpoint to `app/main.py`
- [x] Returns `{"status": "ok", "database": "connected"}` after a simple DB ping
- [x] Returns 503 if database is unreachable
- [ ] Add health check to `docker-compose.yml` for the app service — **PENDING**

### D3: Implement --all-models CLI Flag ✅
- [x] Added `--all-models` argument to CLI parser in `app/cli/ingest.py`
- [x] Defined `ALL_MODELS` constant with all 6 models and their configurations
- [x] When `--all-models` is passed, iterates through all models and ingests each
- [x] Supports `--all-models --backtest` to ingest all backtest data
- [ ] Update deployment docs to reference the working flag — **PENDING**

### D4: Replace Print Statements with Logging ✅
- [x] Added `import logging` and `logger = logging.getLogger(__name__)` to `app/cli/ingest.py`
- [x] Replaced all `print()` calls with appropriate `logger.info()`, `logger.warning()`, `logger.error()`
- [x] Configured basic logging format at module level
- [x] Kept emoji prefixes in log messages for readability

---

## Phase E: Test Coverage

### E1: Fix Test Configuration
- [ ] Add `BacktestData` to imports in `tests/conftest.py`
- [ ] Verify test database creates `backtest_data` table

### E2: Write Backtest Endpoint Tests
- [ ] Test `GET /models/{id}/backtest` with empty database — expect 404
- [ ] Test `GET /models/{id}/backtest` with populated data — verify response structure
- [ ] Test `GET /models/{id}/backtest?days=30` — verify date filtering
- [ ] Test `GET /models/{id}/backtest` with non-existent model — expect 404
- [ ] Test `GET /models/backtest/compare` with valid model IDs
- [ ] Test `GET /models/backtest/compare` with empty model list — expect 400

### E3: Write Backtest Parser Tests
- [ ] Test parsing valid 5-column file — verify all fields
- [ ] Test parsing valid 6-column file — verify `selected_model` field
- [ ] Test parsing file with malformed lines — expect `BacktestParseError`
- [ ] Test parsing empty file — expect `BacktestParseError`
- [ ] Test parsing file with invalid values below -99999 — verify cleanup to 0
- [ ] Test file not found — expect `BacktestParseError`

### E4: Write CLI Ingest Tests
- [ ] Create mock .params files in a temp directory
- [ ] Test `ingest_model()` creates model and inserts metrics
- [ ] Test `ingest_backtest_data()` creates backtest records
- [ ] Test idempotent re-ingestion (overwrite flow)
- [ ] Test missing status file returns False

---

## Phase F: Deployment Hardening

### F1: Fix nginx.conf
- [ ] Move `limit_req_zone` directive from `server` block to a comment noting it must be in `http` context
- [ ] Add a note in the file explaining where to place it in the actual nginx config
- [ ] Or restructure the file to show both `http` and `server` blocks

### F2: Add Docker Restart Policy
- [ ] Add `restart: unless-stopped` to both `db` and `app` services in `docker-compose.yml`
- [ ] Verify containers restart after `docker-compose restart`

### F3: Fix Dockerfile for Production
- [ ] Remove `--reload` from CMD in `Dockerfile`
- [ ] Use environment variable to control reload: `CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 ${UVICORN_RELOAD:+--reload}"]`
- [ ] Or create separate `Dockerfile.dev` with `--reload`

### F4: Create Production Docker Compose
- [ ] Create `docker-compose.prod.yml` without volume mounts to source code
- [ ] Remove `--reload` from app command
- [ ] Add health checks for both services
- [ ] Add resource limits appropriate for Raspberry Pi 4
- [ ] Add persistent volume for PostgreSQL data

### F5: Add Docker Health Check
- [ ] Add `healthcheck` section to app service in `docker-compose.yml`
- [ ] Use `curl -f http://localhost:8000/health || exit 1`
- [ ] Set interval: 30s, timeout: 10s, retries: 3

---

## Execution Order

**Start here → Phase A** (documentation) → then **Phase C** (quick DB wins) → then **Phase D** (error handling) → then **Phase B** (big refactor) → then **Phase E** (tests) → then **Phase F** (deployment)

Phase A is the recommended starting point because:
1. It's low-risk — only markdown and shell script changes
2. It clears mental clutter so the code refactoring phases are easier to reason about
3. It produces immediate value — cleaner docs for daily reference
