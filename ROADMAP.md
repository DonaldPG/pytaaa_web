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

## Phase 4: Model Comparison & Visualization ✅ `3h actual`
- [x] GET /models/compare - Multi-model performance comparison `1.5h`
  - **AC**: Returns all 6 models with configurable time period, meta-model first ✅
  - **Result**: Endpoint returns equity curves for all models (30-5000 days), orders by is_meta DESC, returns in <300ms
- [x] Comparison chart: All models overlaid with meta-model highlighting `1.5h`
  - **AC**: Overlay 6 equity curves, distinguish meta-model visually ✅
  - **Result**: Interactive Chart.js visualization with gold meta-model line (3px), dynamic time periods, performance stats grid
- [x] Comprehensive testing for comparison endpoint `0.5h`
  - **AC**: Test empty DB, populated data, custom parameters ✅
  - **Result**: 3 new tests added, 25/25 tests passing (13 API + 4 DB + 8 parser)
- **Note**: Model switching detection deferred - `active_sub_model_id` is NULL in all snapshots
  - Requires additional metadata source or inference logic
  - Current implementation focuses on performance visualization rather than switch detection

## Phase 4.5: Dashboard UX Improvements ✅ `2h actual`
- [x] Increased API validation limits for max period support `0.5h`
  - **AC**: All period selectors work correctly including "max" (13+ years) ✅
  - **Result**: Limits increased from 10K to 100K days in both `/performance` and `/compare` endpoints
- [x] Fixed date range filtering from record count to calendar days `0.5h`
  - **AC**: Period selectors show correct date ranges (2 years = data from 2024, not 2021) ✅
  - **Result**: Changed from `.limit(days)` to `cutoff_date = today - timedelta(days=days)`
- [x] Simplified detail chart visualization `0.5h`
  - **AC**: Clean single-line chart without redundant data or legend ✅
  - **Result**: Removed "Traded Value" line, disabled legend, kept only "Portfolio Value"
- [x] Added time-based x-axis formatting `0.5h`
  - **AC**: Monthly date labels matching comparison page, no date crowding ✅
  - **Result**: Chart.js time scale with monthly units, max 12 ticks, bold axis labels

## Phase 4.6: UI Polish & Layout ✅ `0.5h actual`
- [x] Card ordering optimization for visual alignment `0.2h`
  - **AC**: Model cards align vertically by strategy type ✅
  - **Result**: Swapped naz100_pi and naz100_pine positions, _pine and _hma cards now vertically aligned
- [x] Page zoom reduction for better content density `0.1h`
  - **AC**: More content visible without scrolling ✅
  - **Result**: Applied 85% zoom to both dashboard and comparison pages
- [x] Detail view header consolidation `0.2h`
  - **AC**: Single-row header with all controls accessible ✅
  - **Result**: Back button + Model name + Period selector on one row, more space for chart/table

## Phase 5A: Backtest Visualization MVP ✅ `8h actual`

### Overview
Add backtesting visualization showing model portfolio performance vs buy-and-hold baseline on a logarithmic scale. This MVP provides core portfolio value comparison without model selection timeline or breadth indicators (deferred to Phase 5B).

### Completed Features
- ✅ **Backend Data Models**: BacktestData table with migration applied
- ✅ **Parser**: `backtest_parser.py` handles space-delimited `.params` files (5 columns)
- ✅ **CLI Ingestion**: `--backtest` flag for importing pyTAAAweb_backtestPortfolioValue.params
- ✅ **API Endpoints**: GET `/models/{id}/backtest` returns chronological backtest data
- ✅ **Visualization Page**: `backtest.html` with Chart.js logarithmic scale chart
- ✅ **Logarithmic Y-Axis**: Powers of 10 from $10K to $100B with K/M/B label formatting
- ✅ **Model Selector**: Right-aligned dropdown in chart header
- ✅ **Legend**: Upper left inside chart with line-style indicators (60px × 1.5px)
- ✅ **Dashboard Button**: "📈 Backtest Results" link added to header
- ✅ **Data Ingested**: 3 models (naz100_hma, naz100_pine, sp500_pine) with 6,560-8,826 points each

### Deferred to Phase 5B
- Model selection timeline (Subplot 2 - "abacus" style dots)
- Market breadth indicators (Subplots 3-4 - new highs/lows)

---

## Phase 5B: Extended Backtest Features (Future) `4-6h`

### Overview
Extend backtest visualization with model selection timeline and market breadth indicators.

### Key Requirements Summary
1. **New Navigation Button**: Add "Backtests of models" button next to "Compare all models" on dashboard
2. **New Web Page**: Create `backtest.html` with interactive 4-subplot visualization
3. **Data Sources**: 
   - Recommendation plot: `/Users/donaldpg/pyTAAA_data/naz100_sp500_abacus/pyTAAA_web/recommendation_plot.png`
   - NASDAQ backtest data: `/Users/donaldpg/pyTAAA_data/naz100_pine/data_store/pyTAAAweb_backtestPortfolioValue.params`
   - S&P 500 backtest data: `/Users/donaldpg/pyTAAA_data/sp500_pine/data_store/pyTAAAweb_backtestPortfolioValue.params`
4. **Time Period Selector**: Same dropdown as comparison page (30d, 90d, 180d, YTD, 1y, 2y, 3y, 5y, 10y, max)

### Data Format Understanding
**File**: `pyTAAAweb_backtestPortfolioValue.params`
```
Column 1: Date (YYYY-MM-DD)
Column 2: Buy-and-hold portfolio value (float)
Column 3: Traded portfolio value (float)  
Column 4: New highs count (float with 1 decimal)
Column 5: New lows count (float with 1 decimal)
```

**Example lines**:
```
1991-01-02 10000.0 10000.0 0.0 0.0
1991-01-03 9965.284667169899 9965.284667169899 0.0 0.0
```

### Critical Assessment

**BLOAT SCORE**: 16/20 (CONDITIONAL APPROVE)
- ✅ Clear user value: Interactive backtest visualization
- ✅ Existing data sources confirmed
- ✅ Follows established patterns (parsers, API, Chart.js)
- ⚠️ Model selection logic adds complexity - needs verification it matches PyTAAA
- ⚠️ 8 lines on one chart may be cluttered - consider progressive disclosure

**MANDATORY IMPROVEMENTS**:
1. **Defer breadth indicators** (Subplots 3-4) to Phase 5B - reduces scope by 25%
2. **Simplify Subplot 1** - Start with model-switching + buy-and-hold only (6 fewer lines)
3. **Make model selection endpoint optional** - can launch without Subplot 2 initially
4. **Validate model selection logic** - Unit test against PyTAAA before frontend work

**REVISED SCOPE (Phase 5A - MVP)**:
- Subplot 1: Model-switching portfolio + 2 buy-and-hold lines (3 lines total)
- Skip Subplot 2 initially (model timeline) - defer to 5B
- Skip Subplots 3-4 (breadth) - defer to 5B
- **Estimated time**: 6-8h instead of 9-12h (33% reduction)

---

### Implementation Tasks

#### 5.1: Backend - Data Models & Parsers
**Solo with AI assistance:**
- Claude Sonnet 4.5: `2-3h` (excellent at patterns, follows existing model structure)
- Grok Code Fast 1: `2.5-3h` (fast generation but may need iteration) 💰 **RECOMMENDED**
- Claude Haiku 4.5: `3-3.5h` (faster but needs more guidance on complex relationships)

- [ ] Create `BacktestData` model in [app/models/trading.py](app/models/trading.py) `0.5-0.75h` 💰 **Grok/Haiku** 💰 **Grok/Haiku**
  - **Fields**: `id`, `model_id` (FK), `date`, `buy_hold_value`, `traded_value`, `new_highs_count`, `new_lows_count`
  - **Indexes**: compound index on (model_id, date)
  - **AC**: Model validates all field types, handles nullable counts
  - **AI tip**: Provide existing model as reference, AI generates boilerplate instantly
  - **Why Grok/Haiku**: Pure pattern replication from existing models, no complex logic
  
- [ ] Create Alembic migration for backtest tables `0.25h` 💰 **Haiku**
  - **AC**: Migration runs without errors, creates tables with proper constraints
  - **Command**: `alembic revision --autogenerate -m "add_backtest_data_table"`
  - **AI tip**: Auto-generated, just review and run
  - **Why Haiku**: Trivial auto-generation task

- [ ] Create backtest parser in [app/parsers/backtest_parser.py](app/parsers/backtest_parser.py) `0.75-1h` 💰 **Grok**
  - **Parse logic**: Read space-delimited `.params` files, handle float parsing
  - **Error handling**: Skip malformed lines, log warnings
  - **AC**: Parse 8000+ lines in <5s, handle edge cases gracefully
  - **Reference**: Similar to `status_parser.py` logic
  - **AI tip**: Point to existing parsers, AI adapts pattern quickly
  - **Why Grok**: Pattern matching from existing parsers, fast generation

- [ ] Extend CLI ingest command to handle backtest data `0.5h` 💰 **Grok**
  - **Update**: [app/cli/ingest.py](app/cli/ingest.py) to call backtest parser
  - **Flags**: `--backtest` flag to trigger backtest ingestion
  - **AC**: `python -m app.cli.ingest --backtest --model naz100_pine` imports successfully
  - **Paths**: Auto-detect `/data_store/pyTAAAweb_backtestPortfolioValue.params`
  - **AI tip**: Follows existing CLI pattern, minimal iteration
  - **Why Grok**: Straightforward pattern extension

- [ ] Write parser tests for backtest data `0.5-0.75h` 💰 **Grok**
  - **Test file**: [tests/test_backtest_parser.py](tests/test_backtest_parser.py)
  - **Coverage**: Empty file, malformed lines, valid data, date parsing
  - **AC**: 6-8 tests passing, 100% parser coverage
  - **AI tip**: Copy test structure from existing parser tests, AI generates variations
  - **Why Grok**: Test pattern replication, no novel logic

#### 5.2: Backend - API Endpoints
**Solo with AI assistance:**
- Claude Sonnet 4.5: `1.5-2h` (excellent at SQLAlchemy queries and FastAPI patterns) 💰 **RECOMMENDED**
- Grok Code Fast 1: `2-2.5h` (quick generation, may need query optimization)
- Claude Haiku 4.5: `2.5-3h` (needs more iteration on complex queries)

- [ ] Create GET `/api/v1/models/{id}/backtest` endpoint `0.75-1h` 💰 **Sonnet** ⚠️
  - **File**: [app/api/v1/endpoints/models.py](app/api/v1/endpoints/models.py)
  - **Query params**: `days` (default 365, max 100000)
  - **Response schema**: BacktestResponse with date, buy_hold_value, traded_value, new_highs, new_lows
  - **AC**: Returns chronological data, respects days filter, <500ms response time
  - **AI tip**: Similar to existing `/performance` endpoint, AI adapts pattern

- [ ] Create GET `/api/v1/models/backtest/compare` endpoint `0.5h`
  - **Purpose**: Return backtest data for both NASDAQ and S&P 500 models in single call
  - **Query params**: `days` (same as above)
  - **Response**: Map of model names to backtest series
  - **AC**: Returns 2 model series, aligned dates, handles missing data gracefully
  - **AI tip**: Similar to existing `/compare` e
**Solo with AI assistance:**
- Claude Sonnet 4.5: `4-5h` (excellent at Chart.js, complex logic porting)
- Grok Code Fast 1: `5-6h` (fast HTML/CSS, but model selection logic needs iteration)
- Claude Haiku 4.5: `6-7h` (struggles with complex model selection logic)

- [ ] Create [app/static/backtest.html](app/static/backtest.html) structure `0.5-0.75h` 💰 **Grok**
  - **Layout**: Header with back button, time period selector, 4 canvas elements for subplots
  - **Styling**: Match dashboard/comparison.html aesthetic (purple gradient, white cards)
  - **Grid**: Vertical stack layout (1 column, 4 rows) for subplots
  - **Subplot sizing**: Subplot 1 largest (portfolio curves), Subplot 2 smaller (model timeline), Subplots 3-4 medium (breadth)
  - **AC**: Page loads, shows placeholder canvases, selector works
  - **AI tip**: Copy structure from comparison.html, AI adapts quickly
  - **Why Grok**: HTML/CSS templating, fast generation

- [ ] **[MVP]** Implement Subplot 1: Combined portfolio performance curves `1.5-2h` 💰 **Sonnet** ⚠️
- [ ] Create [app/static/backtest.html](app/static/backtest.html) structure `1h`
  - **Layout**: Header with back button, time period selector, 4 canvas elements for subplots
  - **Styling**: Match dashboard/comparison.html aesthetic (purple gradient, white cards)
  - **Grid**: Vertical stack layout (1 column, 4 rows) for subplots
  - **Subplot sizing**: Subplot 1 largest (portfolio curves), Subplot 2 smaller (model timeline), Subplots 3-4 medium (breadth)
  - **AC**: Page loads, shows placeholder canvases, selector works
  - **AI tip**: Similar to comparison chart but with more datasets, AI handles config well

- [ ] Implement Subplot 2: Model selection timeline (abacus style) `1-1.5h`
  - **Subplot 2**: "Selected Model" timeline showing which model was active each period
  - **Chart type**: Scatter plot with categorical y-axis (model names)
  - **Visual style**: Colored dots matching the model colors from Subplot 1
  - **Data source**: Calculate using Option B approach - compute best model selection at each date
  - **Models shown**: cash, naz100_hma, naz100_pi, naz100_pine, sp500_hma, sp500_pine
  - **AC**: Dots show model switches over time, colors match subplot 1, looks like "abacus" with colored beads
  - **AI tip**: Chart.js scatter plot with categorical axis, may need manual tweaking

- [ ] Implement Subplots 3-4: Market breadth indicators `0.75-1
    - naz100_pine: medium (2px) blue line `rgb(0, 123, 255)`
    - sp500_hma: medium (2px) cyan line `rgb(0, 206, 209)`
    - sp500_pine: medium (2px) magenta line `rgb(199, 21, 133)`
  - **AC**: All 8 lines visible, log scale works, model-switching portfolio stands out as thick black line

- [ ] Implement Subplot 2: Model selection timeline (abacus style) `2h`
  - **Subplot 2**: "Selected Model" timeline showing which model was active each period
  - **Chart type**: Scatter plot with categorical y-axis (model names)
  - **Visual style**: Colored dots matching the model colors from Subplot 1
  - **Data source**: Calculate using Option B approach - compute best model selection at each date
  - **Models shown**: cash, naz100_hma, naz100_pi, naz100_pine, sp500_hma, sp500_pine
  - **AC**: Dots show model switches over time, colors match subplot 1, looks like "abacus" with colored beads

- [ ] Implement Subplots 3-4: Market breadth indicators `1.5h`
  - **Subplot 3 (NASDAQ)**: New highs (green) and new lows (red) counts for naz100_pine
  - **Subplot 4 (S&P 500)**: New highs (green) and new lows (red) counts for sp500_pine
  - **Chart type**: Line chart with shared x-axis
  - **AI tip**: Copy from comparison.html, minimal work

#### 5.4: Frontend - Dashboard Integration
**Solo with AI assistance:** `0.25-0.5h` (all models similar - trivial changes)

- [ ] Add "Backtests of models" button to [app/static/dashboard.html](app/static/dashboard.html) `0.15h` 💰 **Haiku**
  - **Location**: Header actions, next to "Compare all models" button
  - **Styling**: Match existing `.compare-button` class
  - **Link**: `/backtest.html`
  - **AC**: Button visible, clickable, navigates correctly
  - **AI tip**: One-line change, AI does instantly
  - **Why Haiku**: Trivial HTML change

- [ ] Update main.py to serve backtest.html static file `0.1-0.25h` 💰 **Haiku**
  - **File**: [app/main.py](app/main.py)
  - **Route**: Ensure `/backtest.html` is served from static directory
  - **AC**: Navigating to `/backtest.html` loads the page
  - **AI tip**: Verify static file serving config, usually already works
  - **Why Haiku**: Config verification only

#### 5.5: Data Ingestion & Testing
**Solo with AI assistance:**
- Claude Sonnet 4.5: `1-1.5h` (good at test generation)
  - **AI tip**: Run CLI commands, verify in DB

- [ ] Write API endpoint tests `0.5-0.75h`
  - **File**: [tests/test_api_endpoints.py](tests/test_api_endpoints.py)
  - **Tests**: Empty DB, populated data, days parameter, model not found
  - **AC**: 6 new tests passing, 31/31 total tests passing
  - **AI tip**: AI generates test boilerplate from existing tests quickly

- [ ] Manual end-to-end testing `0.25-0.5h`
  - **Flow**: Dashboard → Click "Backtests" → Select different time periods → Verify all 4 plots update
  - **Browser testing**: Chrome, Safari, Firefox
  - **AC**: No console errors, plots render correctly, data loads <1s
  - **AI tip**: Manual verification, debug any issue
  - **Link**: `/backtest.html`
  - **AC**: Button visible, clickable, navigates correctly

- [ ] Update main.py to serve backtest.html static file `0.5h`
  - **File**: [app/main.py](app/main.py)
  - **Route**: Ensure `/backtest.html` is served from static directory
  - **AC**: Navigating to `/backtest.html` loads the page

#### 5.5: Data Ingestion & Testing `2h`
- [ ] Ingest backtest data for NASDAQ and S&P 500 models `0.5h`
  - **Commands**: 
    ```bash
    python -m app.cli.ingest --backtest --model naz100_pine --data-dir /Users/donaldpg/pyTAAA_data/naz100_pine
    python -m app.cli.ingest --backtest --model sp500_pine --data-dir /Users/donaldpg/pyTAAA_data/sp500_pine
    ```
  - **AC**: 8000+ records per model ingested, no errors

- [ ] Write API endpoint tests `1h`
  - **File**: [tests/test_api_endpoints.py](tests/test_api_endpoints.py)
  - **Tests**: Empty DB, populated data, days parameter, model not found
  - **AC**: 6 new tests passing, 31/31 total tests passing

- [ ] Manual end-to-end testing `0.5h`
  - **Flow**: Dashboard → Click "Backtests" → Select different time periods → Verify all 4 plots update
  - **Browser testing**: Chrome, Safari, Firefox
  - **AC**: No console errors, plots render correctly, data loads <1s

### Technical Decisions & Considerations

#### Chart.js Configuration
- **Shared X-Axis**: Use Chart.js time scale with `adapter-date-fns`
- **Subplot Layout**: 4 separate canvas elements rather than single multi-axis chart (simpler)
- **Synchronization**: Ensure all 4 charts use identical `min` and `max` date values
- **Responsive Design**: Charts resize on window resize, maintain aspect ratio

#### Data Alignment Challenges
- **Date Mismatch**: NASDAQ starts 1991-01-02, S&P 500 starts 2000-01-03
  - **Solution**: Align x-axis to earliest common date in selected period
- **Missing Data**: Some dates may be missing in one series but not the other
  - **Solution**: Chart.js handles sparse data well, leave gaps

#### Performance Optimization
- **Data Volume**: ~8000 records per model × 5 columns = 40KB per model
  - **Frontend**: Fetch both models in single `/backtest/compare` call (80KB total)
  - **Backend**: Index on (model_id, date) for fast range queries
- **Rendering**: Chart.js can handle 8000 points, but may downsample for performance

#### Static Image Integration (Future Enhancement)
- **Recommendation Plot**: Current phase focuses on dynamic data visualization
- [ ] **Subplot 1**: All 8 portfolio curves (2 buy-and-hold + model-switching + 5 models), thick black line for model-switching stands out
- [ ] **Subplot 2**: Model selection timeline with colored dots (abacus style) showing which model was active
- [ ] **Subplots 3-4**: NASDAQ and S&P 500 new highs/lows indicators (green/red lines)
- [ ] All 4 subplots share synchronized x-axis (time)
- [ ] Time period selector changes all 4 charts simultaneously
- [ ] Log scale works on subplot 1 (portfolio curves)
- [ ] Model selection timeline correctly shows model switches matching the thick black line performance
- [ ] Dashboard has visible "Backtests of models" button
- [ ] Clicking button navigates to new backtest page
- [ ] Backtest page shows 4 subplots with correct data
- [ ] Top 2 subplots: NASDAQ and S&P 500 portfolio value curves (Buy-and-hold vs Trading)
- [ ] Bottom 2 subplots: NASDAQ and S&P 500 new highs/lows indicators
- [ ] All 4 subplots share synchronized x-axis (time)
- [ ] Time period selector changes all 4 charts simultaneously
- [ ] Log scale works on portfolio value charts
- [ ] No console errors, responsive on mobile
- [ ] 31+ tests passing (25 existing + 6 new)
- [ ] API responses <500ms for typical queries

### In Scope (Clarified)
- ✅ **Model switching timeline**: Bottom subplot from `recommendation_plot.png` showing which model was selected at each period
  - This data exists in the recommendation plot (colored dots: naz100_pine, sp500_pine, naz100_hma, sp500_hma, naz100_pi, cash)
  - Will need to either: (A) have PyTAAA save this to a `.params` file, OR (B) calculate on-the-fly in the backtest page
  - **Decision needed**: Which approach? See "Model Switching Data Generation" section below

### Non-Goals (Out of Scope)
- Static image integration (embedding the PNG directly - not needed if we recreate the plot)
- Export to PDF/PNG functionality (defer to Phase 8)
- Historical comparison of backtest runs (single snapshot only)

---

### Model Switching Data Generation Options

**CLARIFICATION**: The user wants the bottom subplot from `recommendation_plot.png` showing the model selection timeline (colored dots indicating which model was active: naz100_pine, sp500_pine, naz100_hma, sp500_hma, naz100_pi, cash). This IS in scope for Phase 5.

**Current State Assessment**:
- ✅ **Model switching logic exists** in `PyTAAA/functions/MonteCarloBacktest.py`
  - `_select_best_model(date_idx, lookbacks)` - Selects best model at any date
  - `_calculate_model_switching_portfolio(lookbacks)` - Simulates entire switching strategy
  - Uses multiple metrics: annual return, Sharpe ratio, max drawdown, Sortino ratio, Calmar ratio
  - Ranks models based on weighted performance across multiple lookback periods (e.g., [55, 157, 174] days as shown in plot)
  - Calculated dynamically during plot generation, stored in `self.best_model_selections`
  
- ❌ **No historical switching data is saved** to disk
  - Model selections are computed in memory during `create_monte_carlo_plot()`
  - Not persisted to any `.params` file currently
  - The recommendation plot shows this data exists but it's not in a parseable format

**Where to Generate**: Two options - decision needed

**Recommendation**: Implement in PyTAAA first, as that's where the model selection logic lives and backtests run.

**Implementation Approach** (if pursued):
Implementation Approaches**ate_model_switching_portfolio()` `1.5h`
  - Track model selections: `selections_history = {date: model_name}`
  - Calculate selection confidence (normalized score difference between 1st and 2nd place)
  - **File**: `/PyTAAA/functions/MonteCarloBacktest.py`
  A: Modify PyTAAA to Save Model Selection Data `3-4h PyTAAA + 2h pytaaa_web
- [ ] Add persistence method `save_model_selections()` `1h`
  - Create new `.params` file: `pyTAAAweb_modelSwitching.params`
  - Format: `YYYY-MM-DD model_name confidence_score rank1_score rank2_score rank3_score`
  - Write to `data_store/` directory alongside existing backtest files
  
- [ ] Call from backtest generation scripts `0.5h`
  - Update `recommend_model.py` to save selections when generating plots
  - Update `run_monte_carlo.py` if it runs backtests
  
- [ ] Test with existing data `1h`
  - Run backtest for naz100_sp500_abacus meta-model
  - Verify file generation and format
  - Spot-check model selections match expected logic

#### Option 2: Standalone Selection History Generator `2-3h`
- [ ] Create new script `generate_model_selection_history.py` `2h`
  - Read all model backtest data
  - Replay model selection logic for every date
  - Output `.params` file with complete history
  B: Calculate Model Selections in pytaaa_web Backend `4-5h pytaaa_web only`
- [ ] Port model selection logic from PyTAAA to pytaaa_web `2-3h`
  - Implement `compute_normalized_score()` for each performance metric
  - Implement ranking/weighting logic to select best model
  - **File**: New `app/utils/model_selection.py`
  
- [ ] Create API endpoint to calculate selections on-the-fly `1h`
  - GET `/api/v1/models/meta/{id}/selections?days=365&lookbacks=55,157,174`
  - Queries all sub-model performance data
  - Returns: `{date: model_name}` for each date in range
  
- [ ] No PyTAAA changes required ✅
  - Pure pytaaa_web implementation
  - Uses existing backtest data already ingested)"
- Subplot showing model selection confidence over time

**Estimated Effort**:
- Option A: 5-6h total (3-4h PyTAAA + 2h pytaaa_web)
- Option B: 4-5h total (pytaaa_web only)

**Recommendation**: **Option B - Calculate in pytaaa_web**
- ✅ No PyTAAA changes needed - stay in one codebase
- ✅ Simpler coordination - all work in Phase 5
- ✅ More flexible - can adjust lookback periods in UI without regenerating data
- ✅ Uses existing ingested backtest data
- ❌ Slightly more complex backend (need to port/implement selection logic)
 (Updated for Option B with 4 correct subplots)
- Backend (models, parsers, API): 6-8h
- Frontend (visualization page with model selection logic): 6-7h  
- Integration & testing: 2h
- **Total**: 14-17election logic stays in one place (PyTAAA)

**Decision needed**: Which option should Phase 5 use?
- **Suggested**: Option B to keep Phase 5 self-contained in pytaaa_web
- User preference if Option A desired (requires PyTAAA work first)

### Estimated Effort Summary (Solo with AI Assistance)

**With Claude Sonnet 4.5** (Recommended - best at complex logic):
- 5.1 Backend - Models & Parsers: 2-3h
- 5.2 Backend - API Endpoints: 1.5-2h
- 5.3 Frontend - Visualization: 4-5h
- 5.4 Dashboard Integration: 0.25-0.5h
- 5.5 Testing & Ingestion: 1-1.5h
- **Total: 9-12h** (38% time reduction from manual 14-17h)

**With Grok Code Fast 1** (Faster generation, needs more review):
- 5.1 Backend - Models & Parsers: 3-4h
- 5.2 Backend - API Endpoints: 2-2.5h
- 5.3 Frontend - Visualization: 5-6h
- 5.4 Dashboard Integration: 0.25-0.5h
- 5.5 Testing & Ingestion: 1.5-2h
- **Total: 12-15h** (18% time reduction from manual)

**With Claude Haiku 4.5** (Fastest but struggles with complex logic):
- 5.1 Backend - Models & Parsers: 3.5-4.5h
- 5.2 Backend - API Endpoints: 2.5-3h
- 5.3 Frontend - Visualization: 6-7h (model selection logic challenging)
- 5.4 Dashboard Integration: 0.25-0.5h
- 5.5 Testing & Ingestion: 1.5-2h
- **Total: 14-17h** (minimal time reduction, similar to manual)

**Key Differences:**
- **Sonnet 4.5**: Best for model selection logic porting (most complex task), excellent pattern recognition
- **Grok Code Fast 1**: Fast boilerplate, but needs human review on complex queries
- **Haiku 4.5**: Struggles with model selection logic (5.3), may need 2-3 iterations

**Recommendation**: Use **Claude Sonnet 4.5** for this phase - the model selection logic porting (task 5.3) is the critical path, and Sonnet handles it significantly better than other models.

---

### 💰 Lowest-Cost Model Quick Reference

| Task | Model | Why | Time |
|------|-------|-----|------|
| 5.1.1 BacktestData model | **Grok/Haiku** | Boilerplate replication | 0.5-0.75h |
| 5.1.2 Alembic migration | **Haiku** | Auto-generated | 0.25h |
| 5.1.3 Backtest parser | **Grok** | Pattern matching | 0.75-1h |
| 5.1.4 CLI extension | **Grok** | Simple pattern | 0.5h |
| 5.1.5 Parser tests | **Grok** | Test replication | 0.5-0.75h |
| 5.2.1 `/backtest` endpoint | **Sonnet** ⚠️ | SQLAlchemy optimization | 0.75-1h |
| 5.2.2 `/backtest/compare` endpoint | **Grok** | Simple aggregation | 0.5h |
| 5.2.3 Response schemas | **Haiku** | Pydantic boilerplate | 0.25-0.5h |
| 5.3.1 HTML structure | **Grok** | Template copy | 0.5-0.75h |
| 5.3.2 **[MVP]** Subplot 1 | **Sonnet** ⚠️ | Complex Chart.js | 1.5-2h |
| 5.3.3 **[OPTIONAL]** Subplot 2 | **Sonnet** ⚠️ | Custom scatter plot | 1-1.5h |
| 5.3.4 **[OPTIONAL]** Subplots 3-4 | **Grok** | Line chart pattern | 0.75-1h |
| 5.3.5 **[OPTIONAL]** Model selection logic | **Sonnet ONLY** 🚨 | Complex porting | 1.5-2.5h |
| 5.3.6 Time selector | **Haiku** | Copy existing | 0.25h |
| 5.4.1 Dashboard button | **Haiku** | One-line HTML | 0.15h |
| 5.4.2 Static file serving | **Haiku** | Config check | 0.1-0.25h |
| 5.5.1 Data ingestion | **Manual** | CLI commands | 0.25h |
| 5.5.2 API tests | **Grok** | Test patterns | 0.5-0.75h |
| 5.5.3 E2E testing | **Manual** | Browser testing | 0.25-0.5h |

**Legend**:
- 💰 = Lowest-cost option (Grok/Haiku)
- ⚠️ = Sonnet recommended for quality
- 🚨 = Sonnet REQUIRED (no alternatives)
- **[MVP]** = Essential for minimum viable product
- **[OPTIONAL]** = Can defer to Phase 5B

---

### Phase 5A MVP (Recommended) vs Phase 5 Full

| Aspect | Phase 5A MVP | Phase 5 Full |
|--------|-------------|--------------|
| **Scope** | Subplot 1 only (3 lines) | All 4 subplots (8+ lines, timeline, breadth) |
| **Time (Sonnet)** | **6-8h** | 9-12h |
| **Time (Grok)** | **8-10h** | 12-15h |
| **Value** | Core visualization + 2 buy-and-hold | Complete analysis dashboard |
| **Risk** | Low - proven patterns | Medium - model selection logic porting |
| **Defer** | Subplots 2,3,4 to Phase 5B | Nothing deferred |

**Critical Decision Point**: Start with Phase 5A MVP (6-8h) to validate the approach, then extend to Phase 5 Full (additional 3-4h) once proven.

### Dependencies
- Chart.js time scale adapter (already in use on comparison page)
- Backtest data files must exist at specified paths
- PostgreSQL with sufficient storage (~500MB for full dataset)

---

## Phase 6: Production Readiness `6h`
- [ ] Docker compose with persistent PostgreSQL volume `2h`
  - **AC**: Survives container restarts, data persists
- [ ] Daily cron job for ingestion `1h`
  - **AC**: Runs at 5pm ET, logs success/failure
- [ ] Error monitoring and alerting `2h`
  - **AC**: Email on parse failures or database errors
- [ ] README with deployment instructions `1h`
  - **AC**: Another developer can deploy from scratch in <30min

## Phase 7: Internet Deployment (Raspberry Pi) `8h`
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

---

**Total Estimated Effort (all phases)**: 50-53 hours
**Actual Effort to Date**: Phase 1-4 (20h) + Phase 5A (8h) = **28 hours completed**
