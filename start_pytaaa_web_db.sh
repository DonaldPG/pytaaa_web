#!/bin/bash
#
# PyTAAA Web Database Setup and Ingestion Script
#
# This script re-ingests all trading models and backtest data,
# then starts the Docker containers.
#
# Usage: ./start_pytaaa_web_db.sh [DATA_DIR]
#   DATA_DIR: Path to pyTAAA_data directory (default: /Users/donaldpg/pyTAAA_data)
#

set -euo pipefail

# Configuration
DATA_DIR="${1:-/Users/donaldpg/pyTAAA_data}"

# Validate data directory exists
if [[ ! -d "$DATA_DIR" ]]; then
    echo "Error: Data directory not found: $DATA_DIR"
    echo "Usage: $0 [DATA_DIR]"
    exit 1
fi

echo "=========================================="
echo "PyTAAA Web Database Setup"
echo "Data directory: $DATA_DIR"
echo "=========================================="

# Function to ingest a model
ingest_model() {
    local model_dir="$1"
    local model_name="$2"
    local index_type="${3:-NASDAQ_100}"
    local is_meta="${4:-}"

    echo ""
    echo "Ingesting $model_name..."
    if [[ -n "$is_meta" ]]; then
        uv run python -m app.cli.ingest \
            --data-dir "$model_dir" \
            --model "$model_name" \
            --index "$index_type" \
            --meta
    else
        uv run python -m app.cli.ingest \
            --data-dir "$model_dir" \
            --model "$model_name" \
            --index "$index_type"
    fi
}

# Function to ingest backtest data
ingest_backtest() {
    local model_dir="$1"
    local model_name="$2"

    echo ""
    echo "Ingesting backtest data for $model_name..."
    uv run python -m app.cli.ingest \
        --backtest \
        --data-dir "$model_dir" \
        --model "$model_name"
}

echo ""
echo "Step 1: Ingesting NASDAQ 100 models..."
ingest_model "$DATA_DIR/naz100_hma/data_store" "naz100_hma"
ingest_model "$DATA_DIR/naz100_pi/data_store" "naz100_pi"
ingest_model "$DATA_DIR/naz100_pine/data_store" "naz100_pine"

echo ""
echo "Step 2: Ingesting S&P 500 models..."
ingest_model "$DATA_DIR/sp500_hma/data_store" "sp500_hma" "SP_500"
ingest_model "$DATA_DIR/sp500_pine/data_store" "sp500_pine" "SP_500"

echo ""
echo "Step 3: Ingesting meta-model..."
ingest_model "$DATA_DIR/naz100_sp500_abacus/data_store" "naz100_sp500_abacus" "NASDAQ_100" "--meta"

echo ""
echo "Step 4: Ingesting backtest data..."
ingest_backtest "$DATA_DIR/naz100_pine" "naz100_pine"
ingest_backtest "$DATA_DIR/naz100_hma" "naz100_hma"
ingest_backtest "$DATA_DIR/naz100_pi" "naz100_pi"
ingest_backtest "$DATA_DIR/sp500_hma" "sp500_hma"
ingest_backtest "$DATA_DIR/sp500_pine" "sp500_pine"
ingest_backtest "$DATA_DIR/naz100_sp500_abacus" "naz100_sp500_abacus"

echo ""
echo "Step 5: Starting Docker containers..."
docker-compose up -d

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Dashboard URLs:"
echo "  Main Dashboard:  http://localhost:8000/static/dashboard.html"
echo "  Model Comparison: http://localhost:8000/static/comparison.html"
echo "  API Docs:        http://localhost:8000/docs"
echo ""
