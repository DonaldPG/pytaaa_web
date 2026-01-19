# pytaaa_web

FastAPI web application for visualizing stock trading models and portfolio performance.

## What This Does
Dashboard for tracking 6 trading strategies:
- **5 base models**: naz100_pine, naz100_hma, naz100_pi, sp500_hma, sp500_pine
- **1 meta-model**: "Abacus" - monthly switches between the 5 based on performance

### Key Features
1. **Performance Tracking**: Daily equity curves for all models (20+ years of history)
2. **Portfolio View**: Current holdings (7 stocks per model, updated monthly)
3. **Meta-Model Logic**: See which model is active and when switches occurred
4. **Comparative Analysis**: Side-by-side performance of all strategies

## Data Source
Reads from `PyTAAA.master` output files (does NOT run trading logic):
- **PyTAAA_status.params**: Daily portfolio values
- **PyTAAA_holdings.params**: Current stock positions
- **PyTAAA_ranks.params**: Stock rankings
- **pyTAAAweb_backtestPortfolioValue.params**: Historical backtest data (optional, for visualization)
- **pytaaa_*.json**: Model configurations

**Example Status Line**:
```
cumu_value: 2025-01-15 16:00:00.000000 125432.15 1 126891.34
```
Means: On 2025-01-15, base value $125,432, signal=Long, traded value $126,891

**Example Backtest Line**:
```
1991-01-02 10000.0 10000.0 0.0 0.0
```
Means: Date, buy-and-hold value, traded value, new highs count, new lows count

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Access to `/Users/donaldpg/pyTAAA_data/` (model data files)

### Installation
```bash
# 1. Start database
docker-compose up -d db

# 2. Run migrations
source .venv/bin/activate
alembic upgrade head

# 3. Import historical data (one-time, ~2 minutes total)
# Import each model's performance/holdings data
python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/naz100_pine --model naz100_pine
python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/naz100_hma --model naz100_hma
python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/naz100_pi --model naz100_pi
python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/sp500_hma --model sp500_hma --index SP_500
python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/sp500_pine --model sp500_pine --index SP_500
python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/naz100_sp500_abacus --model naz100_sp500_abacus --meta

# 4. Import backtest data (optional, for backtesting visualization)
python -m app.cli.ingest --backtest --data-dir /Users/donaldpg/pyTAAA_data/naz100_hma --model naz100_hma
python -m app.cli.ingest --backtest --data-dir /Users/donaldpg/pyTAAA_data/naz100_pine --model naz100_pine
python -m app.cli.ingest --backtest --data-dir /Users/donaldpg/pyTAAA_data/sp500_pine --model sp500_pine

# 5. Start API server
uvicorn app.main:app --reload
```

API available at: http://localhost:8000  
Dashboard: http://localhost:8000/static/dashboard.html  
Docs: http://localhost:8000/docs

### Daily Updates
```bash
# Run after market close to sync latest data
python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/naz100_pine --model naz100_pine
```

**Performance Expectations**:
- Initial import (5000 days): <30s
- Daily update: <2s
- Dashboard load: <500ms
- Performance query (90 days): <200ms

## Internet Access (Raspberry Pi Deployment)

**Goal**: Access dashboard from anywhere, not just home network.

### Architecture
```
Your Phone/Laptop → https://yourpi.duckdns.org
                         ↓
                    Router (port 443)
                         ↓
                    Raspberry Pi
                         ├─ nginx (reverse proxy + HTTPS)
                         ├─ FastAPI (Docker container)
                         └─ PostgreSQL (Docker container)
```

### Quick Deploy to Raspberry Pi
```bash
# 1. On your Mac: Build ARM64 images
docker buildx build --platform linux/arm64 -t pytaaa-web:arm64 .

# 2. Copy to Pi
scp docker-compose.yml pi@raspberrypi:/home/pi/pytaaa_web/
scp -r app/ pi@raspberrypi:/home/pi/pytaaa_web/

# 3. On Pi: Start services
ssh pi@raspberrypi
cd /home/pi/pytaaa_web
docker-compose up -d

# 4. Setup nginx reverse proxy (see docs/nginx.conf)
sudo cp docs/nginx.conf /etc/nginx/sites-available/pytaaa
sudo ln -s /etc/nginx/sites-available/pytaaa /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# 5. Configure router port forwarding
#    External: 443 → Internal: raspberrypi:8000
```

### Security Setup
```bash
# Enable basic auth
sudo htpasswd -c /etc/nginx/.htpasswd yourusername

# Install fail2ban
sudo apt install fail2ban
sudo cp docs/fail2ban-pytaaa.conf /etc/fail2ban/jail.d/
```

**Access**: https://yourpi.duckdns.org (setup DuckDNS for free dynamic DNS)

### Data Sync from Mac
```bash
# Add to crontab: sync data every evening
0 17 * * * rsync -avz /Users/donaldpg/pyTAAA_data/ pi@raspberrypi:/home/pi/pyTAAA_data/
```

## Project Structure
- `app/api`: API route definitions.
- `app/models`: SQLAlchemy database models.
- `app/schemas`: Pydantic data schemas.
- `app/core`: Core configurations (settings, database setup).
- `app/db`: Database session management.

## Contributing
See `spec.md` for technical details and `refinement_guide.md` for coding standards.
