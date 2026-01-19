

### re-ingest all models with the corrected purchase date logic, run these commands:
# NASDAQ 100 models
uv run python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/naz100_hma/data_store --model naz100_hma
uv run python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/naz100_pi/data_store --model naz100_pi
uv run python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/naz100_pine/data_store --model naz100_pine

# S&P 500 models
uv run python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/sp500_hma/data_store --model sp500_hma --index SP_500
uv run python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/sp500_pine/data_store --model sp500_pine --index SP_500

# Meta-model
uv run python -m app.cli.ingest --data-dir /Users/donaldpg/pyTAAA_data/naz100_sp500_abacus/data_store --model naz100_sp500_abacus --meta

### re-ingest backtest data
uv run python -m app.cli.ingest --backtest --data-dir /Users/donaldpg/pyTAAA_data/naz100_pine --model naz100_pine
uv run python -m app.cli.ingest --backtest --data-dir /Users/donaldpg/pyTAAA_data/naz100_hma --model naz100_hma
uv run python -m app.cli.ingest --backtest --data-dir /Users/donaldpg/pyTAAA_data/naz100_pi --model naz100_pi
uv run python -m app.cli.ingest --backtest --data-dir /Users/donaldpg/pyTAAA_data/sp500_hma --model sp500_hma
uv run python -m app.cli.ingest --backtest --data-dir /Users/donaldpg/pyTAAA_data/sp500_pine --model sp500_pine
uv run python -m app.cli.ingest --backtest --data-dir /Users/donaldpg/pyTAAA_data/naz100_sp500_abacus --model naz100_sp500_abacus

### restart docker and display web page

docker-compose up -d
# Main Dashboard:
http://localhost:8000/static/dashboard.html

# Model Comparison:
http://localhost:8000/static/comparison.html

# API Documentation:
http://localhost:8000/docs