# Project Roadmap

## Phase 1: Foundation ✅
- [x] Project scaffolding and architecture
- [x] Database models aligned with .params file structure
- [x] Alembic migrations configured for async PostgreSQL
- [x] Basic API endpoints for model listing

**Acceptance**: Can query empty database, migrations run without errors.

## Phase 1.5: Infrastructure Testing ✅ `0.6h actual`
- [x] Database connection tests
  - **AC**: Can create/teardown test DB, async sessions work, connection pool doesn't leak ✅
  - **Test**: `tests/test_db_session.py` - 4 tests passing
  - **Results**: Connection isolation, rollback, multiple queries all working
- [x] API endpoint tests `1.5h` - COMPLETED AFTER PHASE 3
  - **Reason**: Needed populated DB and implemented endpoints to properly test
  - **Test**: `tests/test_api_endpoints.py` - 10 tests passing
  - **Coverage**: GET /models (2 tests), GET /models/{id}/performance (4 tests), GET /models/{id}/holdings (4 tests)
  - **Results**: All endpoints tested with empty/populated DB, error cases, meta-model handling
- [ ] Model CRUD tests `1h` - DEFERRED TO FUTURE
  - **Reason**: Basic session tests validate infrastructure; CRUD tests better with actual data
- [ ] Schema validation tests `1h` - DEFERRED TO FUTURE
  - **Reason**: Will test during parser development with real .params data

**Why This Matters**: Phase 2 parsers will fail silently if:
- Database sessions aren't properly closed → connection leaks
- Models don't handle nullable fields → insert errors
- Schemas reject valid .params data → data loss
- UUIDs aren't generated correctly → foreign key violations

**Setup Required**:
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Create test database
createdb pytaaa_test

# Run tests
pytest tests/ -v
```

## Phase 2: Data Ingestion ✅ `8h actual`
- [x] Parse PyTAAA_status.params (daily metrics) `3h`
  - **AC**: Import 5000 days in <10s, handle malformed lines gracefully ✅
  - **Result**: Adapted to real format "cumu_value: YYYY-MM-DD HH:MM.SS.SS value", 36,760 metrics imported
- [x] Parse PyTAAA_holdings.params (monthly snapshots) `2h`
  - **AC**: Detect active model from `trading_model:` tag, parse all 6 models ✅
  - **Result**: Space-delimited format parsed, 707 snapshots with calculated weights
- [x] Parse PyTAAA_ranks.params (rankings) `2h`
  - **AC**: Store top 20 ranks per model, query by date ✅
  - **Result**: Parser created, minimal data found in actual files (0 ranks)
- [x] CLI: `ingest` command with --model, --data-dir flags `3h`
  - **AC**: Full historical import completes in <30s, idempotent reruns ✅
  - **Result**: `python -m app.cli.ingest` with progress indicators, <10s per model
- [x] Seed database with real data from /Users/donaldpg/pyTAAA_data `2h`
  - **AC**: All 6 models have >=100 daily metrics, >=12 monthly snapshots ✅
  - **Result**: All models imported (naz100_pine/hma/pi, sp500_pine/hma, naz100_sp500_abacus meta-model)

## Phase 3: Dashboard MVP ✅ `5h actual`
- [x] GET /models - List all 6 models with latest value `1h`
  - **AC**: Returns in <200ms, includes meta-model with active sub-model ✅
  - **Result**: Returns all 6 models ordered by is_meta DESC, shows latest values and dates
- [x] GET /models/{id}/performance?days=90 - Equity curve `2h`
  - **AC**: Returns 90 days of base_value & traded_value in <500ms ✅
  - **Result**: Configurable days parameter (1-5000), returns chronological data points
- [x] GET /models/{id}/holdings - Current portfolio `2h`
  - **AC**: Shows 7 stocks with weights, prices, returns ✅
  - **Result**: Returns latest snapshot with holdings sorted by weight, supports meta-model active_sub_model tracking
- [x] Basic HTML dashboard listing models `3h`
  - **AC**: Renders in browser, clickable model cards ✅
  - **Result**: Responsive dashboard with Chart.js, gradient styling, click-through to performance/holdings detail views

## Phase 3.5: Code Quality & Testing ✅ `4h actual`
- [x] Comprehensive API endpoint tests `1.5h`
  - **AC**: 100% endpoint coverage with edge cases ✅
  - **Result**: 10 tests in `tests/test_api_endpoints.py` covering all 3 endpoints with empty/populated DB, 404s, custom params, meta-model handling
- [x] Parser test updates for real data format `1h`
  - **AC**: All parser tests match actual .params file structure ✅
  - **Result**: 8 tests updated to timestamp format, space-delimited holdings, CASH filtering
- [x] Critical code review with Critic agent mindset `1h`
  - **AC**: Identify bloat, DRY violations, performance issues ✅
  - **Result**: BLOAT SCORE 15/20 (CONDITIONAL APPROVE), identified 7 code smells (2 P0, 3 P1, 2 P2)
- [x] P0/P1 fixes implementation `1.5h`
  - **AC**: Critical issues fixed, tests still passing ✅
  - **P0 Fixes**:
    - Type annotation errors in trading.py (renamed `date` → `DateType` to avoid shadowing)
    - Hardcoded database URL in CLI (now uses Settings with environment override)
  - **P1 Fixes**:
    - N+1 query optimization in list_models endpoint (7 queries → 2 queries, 71% reduction)
    - DRY refactoring (created `get_model_or_404()` helper, eliminated 3 duplicate blocks)
    - Comprehensive error handling in all 3 parsers (IOError/Exception with UTF-8 encoding)
  - **Result**: 22/22 tests passing, no regressions, cleaner codebase following Clean Code/SOLID principles

## Phase 4: Meta-Model Tracking `4h`
- [ ] GET /meta/switches - Monthly model change history `2h`
  - **AC**: Shows which model was active each month with performance delta
- [ ] Comparison chart: meta vs all underlying models `2h`
  - **AC**: Overlay 6 equity curves, highlight switch dates

## Phase 5: Production Readiness `6h`
- [ ] Docker compose with persistent PostgreSQL volume `2h`
  - **AC**: Survives container restarts, data persists
- [ ] Daily cron job for ingestion `1h`
  - **AC**: Runs at 5pm ET, logs success/failure
- [ ] Error monitoring and alerting `2h`
  - **AC**: Email on parse failures or database errors
- [ ] README with deployment instructions `1h`
  - **AC**: Another developer can deploy from scratch in <30min

## Phase 6: Internet Deployment (Raspberry Pi) `8h`
- [ ] Nginx reverse proxy config with basic auth `2h`
  - **AC**: HTTPS working, basic auth prompts before dashboard access
  - **Test**: curl https://yourpi.duckdns.org returns 401 without credentials
- [ ] Docker deployment to Raspberry Pi `2h`
  - **AC**: docker-compose.yml works on ARM64, containers auto-restart
  - **Test**: Full stack runs on Pi 4, queries return in <500ms
- [ ] Rsync automation: Mac → Pi data sync `1h`
  - **AC**: Cron job copies /pyTAAA_data to Pi every evening
  - **Test**: Changes on Mac appear on Pi within 5 minutes
- [ ] Router port forwarding & DuckDNS setup `1h`
  - **AC**: Dashboard accessible from phone on cellular (not home WiFi)
  - **Test**: https://yourpi.duckdns.org loads from external IP
- [ ] Security hardening (fail2ban, IP whitelist) `2h`
  - **AC**: Fail2ban blocks after 3 failed auth attempts
  - **Test**: Can only access from whitelisted IPs

**Total Estimated Effort**: 38 hours
