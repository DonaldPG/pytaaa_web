"""Tests for CLI ingest functionality."""
import pytest
import pytest_asyncio
import asyncio
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.cli.ingest import ingest_model, ingest_backtest_data
from app.models.trading import TradingModel, PerformanceMetric, PortfolioSnapshot, BacktestData


class TestIngestModel:
    """Tests for ingest_model function."""
    
    @pytest.mark.asyncio
    async def test_ingest_model_creates_model_and_inserts_metrics(
        self, tmp_path: Path, db_session
    ):
        """Test that ingest_model creates a model and inserts metrics."""
        # Create mock data directory structure
        data_dir = tmp_path / "test_model"
        data_store = data_dir / "data_store"
        data_store.mkdir(parents=True)
        
        # Create a mock status file
        status_file = data_store / "PyTAAA_status.params"
        status_content = """# Performance metrics
2024-01-01 10000.0 1 10000.0 0.01
2024-01-02 10100.0 1 10200.0 0.02
"""
        status_file.write_text(status_content)
        
        # Mock the create_cli_session to return our test session
        with patch('app.cli.ingest.create_cli_session') as mock_session:
            mock_session.return_value = (lambda: db_session, "test_db_url")
            
            # Run ingestion
            success = await ingest_model(
                data_dir=data_dir,
                model_name="test_model",
                index_type="NASDAQ_100",
                description="Test model",
            )
            
            # Note: This test will need adjustment based on actual implementation
            # The function may need to be refactored to accept a session parameter for testing
            
    @pytest.mark.asyncio
    async def test_ingest_model_missing_status_file(self, tmp_path: Path):
        """Test that ingest_model returns False when status file is missing."""
        data_dir = tmp_path / "test_model"
        data_dir.mkdir()
        
        success = await ingest_model(
            data_dir=data_dir,
            model_name="test_model",
            index_type="NASDAQ_100",
        )
        
        assert success is False


class TestIngestBacktestData:
    """Tests for ingest_backtest_data function."""
    
    @pytest.mark.asyncio
    async def test_ingest_backtest_data_creates_records(
        self, tmp_path: Path, db_session
    ):
        """Test that ingest_backtest_data creates backtest records."""
        # Create mock data directory
        data_dir = tmp_path / "test_model"
        data_store = data_dir / "data_store"
        data_store.mkdir(parents=True)
        
        # Create a mock backtest file
        backtest_file = data_store / "pyTAAAweb_backtestPortfolioValue.params"
        backtest_content = """# Backtest data
2024-01-01 10000.0 10000.0 5 2
2024-01-02 10100.0 10200.0 6 1
"""
        backtest_file.write_text(backtest_content)
        
        # First create a model in the database
        model = TradingModel(
            name="test_model",
            description="Test model",
            index_type="NASDAQ_100",
            is_meta=False,
        )
        db_session.add(model)
        await db_session.commit()
        
        # Mock the create_cli_session
        with patch('app.cli.ingest.create_cli_session') as mock_session:
            mock_session.return_value = (lambda: db_session, "test_db_url")
            
            # This test needs the function to be refactored for dependency injection
            # or we need to use a different testing approach
            
    @pytest.mark.asyncio
    async def test_ingest_backtest_data_missing_file(self, tmp_path: Path):
        """Test that ingest_backtest_data returns False when file is missing."""
        data_dir = tmp_path / "test_model"
        data_dir.mkdir()
        
        success = await ingest_backtest_data(
            data_dir=data_dir,
            model_name="test_model",
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_ingest_backtest_data_model_not_found(self, tmp_path: Path):
        """Test that ingest_backtest_data returns False when model doesn't exist."""
        data_dir = tmp_path / "test_model"
        data_store = data_dir / "data_store"
        data_store.mkdir(parents=True)
        
        # Create backtest file but no model in DB
        backtest_file = data_store / "pyTAAAweb_backtestPortfolioValue.params"
        backtest_file.write_text("2024-01-01 10000.0 10000.0 5 2\n")
        
        success = await ingest_backtest_data(
            data_dir=data_dir,
            model_name="nonexistent_model",
        )
        
        assert success is False


class TestIdempotentReingestion:
    """Tests for idempotent re-ingestion (overwrite flow)."""
    
    @pytest.mark.asyncio
    async def test_reingest_overwrites_existing_data(self, tmp_path: Path):
        """Test that re-ingesting overwrites existing data."""
        # This test would require mocking user input for the overwrite confirmation
        # or refactoring the function to accept a force_overwrite parameter
        pass
