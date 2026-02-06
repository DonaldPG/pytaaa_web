# Fix: Duplicate Models on Dashboard

**Date:** February 6, 2026  
**Issue:** Trading models displayed multiple times (2x or 3x) on the main dashboard  
**Root Cause:** SQL query producing duplicate rows due to multiple outer joins  
**Files Modified:** `app/api/v1/endpoints/models.py`

## Problem Description

The dashboard was showing each trading model multiple times:
- Regular models (naz100_hma, naz100_pi, etc.) appeared twice
- The meta-model (naz100_sp500_abacus) appeared three times

This occurred because the `/api/v1/models/` endpoint's SQL query had a flawed join strategy:

```python
# PROBLEMATIC: Two outer joins creating duplicates
latest_metric_subquery = (
    select(
        PerformanceMetric.model_id,
        func.max(PerformanceMetric.date).label('max_date')
    )
    .group_by(PerformanceMetric.model_id)
    .subquery()
)

result = await db.execute(
    select(TradingModel, PerformanceMetric)
    .outerjoin(latest_metric_subquery, ...)
    .outerjoin(PerformanceMetric, ...)  # Second join creates duplicates
)
```

When multiple `PerformanceMetric` records existed with the same max date (common with daily ingestion), the second outer join would return one row per matching metric, creating duplicates.

## Solution

Replaced the two-step join approach with a `DISTINCT ON` subquery that guarantees exactly one metric per model:

```python
# FIXED: Single join with DISTINCT ON
latest_metric_subquery = (
    select(PerformanceMetric)
    .distinct(PerformanceMetric.model_id)
    .order_by(
        PerformanceMetric.model_id,
        PerformanceMetric.date.desc(),
        PerformanceMetric.id.desc()  # Deterministic when multiple entries per date
    )
    .subquery()
)

result = await db.execute(
    select(TradingModel, latest_metric_subquery.c.traded_value, latest_metric_subquery.c.date)
    .outerjoin(latest_metric_subquery, TradingModel.id == latest_metric_subquery.c.model_id)
)
```

### Key Improvements

1. **Guaranteed Uniqueness**: `DISTINCT ON (model_id)` ensures exactly one row per model
2. **Deterministic Selection**: When multiple metrics exist for the same date, ordering by `id DESC` picks the most recently inserted one (highest id)
3. **Cleaner Code**: Single outer join instead of two cascading joins
4. **Better Performance**: Reduced join complexity and intermediate result size

## Verification

After the fix:
- Each model appears exactly once on the dashboard
- The most recent metric value is displayed for each model
- When multiple metrics exist for the same date (e.g., from re-ingestion), the last inserted one is used

## Related Context

This fix was implemented as part of a database reset and re-ingestion workflow. The user cleared the database using:

```bash
docker-compose down -v
docker-compose up -d
docker-compose exec app alembic upgrade head
```

Then re-ingested all models, which revealed the duplicate display issue.
