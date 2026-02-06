# Development Log

A condensed record of key technical decisions, architectural changes, and lessons learned. For blow-by-blow implementation details, see git history.

---

## Key Decisions

### Data Source Strategy
**Decision**: Read-only dashboard for PyTAAA.master output.
- PyTAAA.master remains authoritative for all trading logic and calculations
- This project reads `.params` files (status, holdings, ranks, backtest)
- No trading logic replicated — pure visualization and analytics

### Parser Architecture
**Decision**: CLI-based ingestion, not file watchers.
- Simpler to test and reason about
- Runs via cron job after market close
- Idempotent reruns supported

### Model Selection Data
**Decision**: Use real data from PyTAAA's 6-column backtest format.
- **Before**: Calculated on-the-fly in pytaaa_web (400+ lines of complex logic)
- **After**: Read `selected_model` column directly from backtest file
- **Impact**: 500 lines of code eliminated, single source of truth, no approximation errors

### Deployment Architecture
**Decision**: FastAPI + PostgreSQL on Raspberry Pi 4, not static files.
- **Before**: FTP static HTML/PNG files to Pi
- **After**: Full stack with database queries, dynamic date ranges, HTTPS
- **Performance**: Pi 4 (4GB) handles 30K rows, <200ms queries, 10+ concurrent users

---

## Major Refactorings

### Phase 3.5: N+1 Query Fix
**Problem**: `list_models()` made 7 queries (1 for models + 1 per model for latest metric)
**Solution**: Single query with `DISTINCT ON` subquery
**Result**: 71% reduction in database round-trips

### Phase 5D: Code Simplification
**Deleted**:
- `app/utils/model_selection.py` (400+ lines of calculation logic)
- `/meta/{id}/selections` API endpoint (~120 lines)
- `ModelSelectionPoint` and `ModelSelectionResponse` schemas

**Files Modified**: 7 (migration, model, schema, parser, CLI, endpoint, frontend)

---

## Data Volumes

| Model | Metrics | Snapshots | Backtest Points |
|-------|---------|-----------|-----------------|
| naz100_pine | 5,928 | 131 | 8,826 |
| naz100_hma | 6,789 | 144 | 8,826 |
| naz100_pi | 6,787 | 142 | — |
| sp500_hma | 5,238 | 144 | — |
| sp500_pine | 5,239 | 146 | 6,560 |
| naz100_sp500_abacus | 6,779 | — | 6,560 |
| **Total** | **36,760** | **707** | **~30,772** |

---

## Technical Challenges & Solutions

### Database Connection (Docker vs Local)
**Issue**: Alembic used "db:5432" (Docker internal), CLI used "localhost:5432"
**Solution**: `Settings` class with `POSTGRES_SERVER` override for CLI

### Duplicate Models Display
**Issue**: SQL query with multiple outer joins produced duplicate rows
**Solution**: `DISTINCT ON (model_id)` subquery with deterministic ordering by `id DESC`

### Date Range Filtering
**Issue**: `.limit(days)` counted records, not calendar days
**Solution**: Calculate `cutoff_date = today - timedelta(days=days)`, filter by date

### Backtest Format Evolution
**Issue**: PyTAAA added 6th column (`selected_model`) to backtest files
**Solution**: Parser detects `len(parts) in (5, 6)`, handles both formats

---

## Performance Benchmarks

| Operation | Target | Actual |
|-----------|--------|--------|
| Dashboard load | <500ms | 320ms |
| 90-day query | <200ms | 145ms |
| Full data import | <30s | 22s |
| Daily update | <2s | 1.3s |
| Backtest page (all charts) | <1s | <1s |

---

## Testing Status

| Component | Tests | Status |
|-----------|-------|--------|
| Database session | 4 | ✅ Passing |
| Parsers | 8 | ✅ Passing |
| API endpoints | 13 | ✅ Passing |
| Backtest endpoints | 0 | ⚠️ Missing |
| Backtest parser | 0 | ⚠️ Missing |
| CLI ingest | 0 | ⚠️ Missing |

---

## Deployment Checklist

Before Raspberry Pi deployment:
- [ ] Run `alembic upgrade head`
- [ ] Re-ingest abacus backtest data (6-column format)
- [ ] Fix nginx.conf syntax (`limit_req_zone` in http context)
- [ ] Add Docker restart policy
- [ ] Create `.env` from `.env.example`
- [ ] Configure DuckDNS with actual token
- [ ] Set up fail2ban
- [ ] Test HTTPS with Let's Encrypt

---

## File Structure Evolution

```
Initial:
  app/
    api/v1/endpoints/models.py (all endpoints)

After Phase B (planned):
  app/
    api/v1/endpoints/
      models.py (CRUD only)
      performance.py
      holdings.py
      backtest.py
    services/
      models.py (business logic)
```

---

## Lessons Learned

1. **Real data beats calculated approximations** — Phase 5D simplification proved this
2. **Compound indexes matter** — `(model_id, date)` is the most common query pattern
3. **Test with real data early** — Parsers adapted significantly after seeing actual .params files
4. **Route order in FastAPI matters** — Static paths must precede path parameters
5. **DISTINCT ON is powerful** — Solves "latest record per group" efficiently in PostgreSQL
