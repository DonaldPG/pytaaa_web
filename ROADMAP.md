# Project Roadmap

## Status Summary

| Phase | Status | Description |
|-------|--------|-------------|
| 1: Foundation | ✅ | Project scaffolding, database models, migrations |
| 1.5: Infrastructure Testing | ✅ | Database connection tests, API endpoint tests |
| 2: Data Ingestion | ✅ | Parsers for .params files, CLI ingest command |
| 3: Dashboard MVP | ✅ | API endpoints, basic HTML dashboard |
| 3.5: Code Quality | ✅ | N+1 query fixes, DRY refactoring, parser error handling |
| 4: Model Comparison | ✅ | Multi-model comparison endpoint and visualization |
| 4.5-4.6: UX Polish | ✅ | Period selectors, chart improvements, layout refinements |
| 5A: Backtest Visualization | ✅ | Log-scale portfolio charts, model selector |
| 5B: Market Breadth | ✅ | NASDAQ/S&P 500 new highs/lows indicators |
| 5C: Model Selection Timeline | ✅ | Abacus scatter plot with real PyTAAA data |
| 5D: Real Data Integration | ✅ | 6-column backtest format, eliminated 500 lines of calculation code |

**All core analytical features are complete!** The project now has:
- 6 trading models with 20+ years of historical data
- Dashboard with model cards and performance charts
- Comparison view with all models overlaid
- Backtest visualization with portfolio curves, market breadth, and model selection timeline

---

## What's Next

### Phase 6: Production Readiness `6h`
Prepare the system for reliable daily use with automation and monitoring.

- [ ] Docker volume persistence (keep data across restarts)
- [ ] Daily cron job for automatic data ingestion
- [ ] Error monitoring and health checks
- [ ] Comprehensive deployment documentation

**Why Now**: With all core features complete, production readiness ensures daily reliability without manual intervention.

### Phase 7: Internet Deployment (Raspberry Pi) `8h`
Deploy to internet-accessible Raspberry Pi for remote access.

- [ ] Nginx reverse proxy with HTTPS and basic auth
- [ ] Docker containers optimized for ARM64
- [ ] Automated rsync for Mac → Pi data synchronization
- [ ] Security hardening (fail2ban, IP whitelist)
- [ ] DuckDNS dynamic DNS setup

**Value**: Makes dashboard accessible from anywhere (phone, work, etc.)

---

## Recommendation

**Start with Phase 6 (Production Readiness)** — it provides immediate value by making the current features reliable and maintainable, without requiring hardware setup or networking knowledge. You can still use the dashboard daily while it's running reliably in Docker.

After Phase 6, proceed to Phase 7 for remote access capability.

---

## Completed Phase Details

See [`LOG.md`](LOG.md) for detailed implementation notes on completed phases.

### Key Technical Decisions

**Data Source**: PyTAAA.master remains authoritative. This dashboard reads `.params` files — it does NOT run trading logic.

**Parser Strategy**: CLI-based ingestion (not file watchers) — simpler, testable, runs via cron.

**Model Selection**: Uses real data from PyTAAA's 6-column backtest format. Previously calculated on-the-fly; now reads actual switching decisions from upstream.

**Deployment**: FastAPI + PostgreSQL in Docker on Raspberry Pi 4. Replaces old FTP static file approach with dynamic API queries.

### Performance Benchmarks

| Metric | Target | Actual |
|--------|--------|--------|
| Dashboard load | <500ms | 320ms |
| 90-day query | <200ms | 145ms |
| Full data import | <30s | 22s |
| Daily update | <2s | 1.3s |
| Concurrent users | 6 | 10+ |

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PyTAAA.master  │────▶│  .params files  │────▶│   CLI ingest    │
│   (Mac host)    │     │  (data_store/)  │     │  (app/cli/)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                              ┌──────────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   (Docker)      │
                    └────────┬────────┘
                              │
                              ▼
                    ┌─────────────────┐     ┌─────────────────┐
                    │    FastAPI      │────▶│  Static HTML    │
                    │    (Docker)     │     │  (dashboard)    │
                    └────────┬────────┘     └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  nginx (Pi)     │◀──── Internet (HTTPS)
                    │  reverse proxy  │
                    └─────────────────┘
```

---

## Deferred Items

These items were intentionally deferred and may be revisited in future phases:

- **Model CRUD tests** — Basic session tests validate infrastructure; full CRUD tests better with stable API
- **Schema validation tests** — Tested implicitly through parser development with real data
- **Historical model switching detection** — `active_sub_model_id` is NULL in all snapshots; requires additional metadata source
- **Export to PDF/PNG** — Deferred to Phase 8
- **Historical comparison of backtest runs** — Single snapshot only for now
