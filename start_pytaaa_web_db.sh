

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

