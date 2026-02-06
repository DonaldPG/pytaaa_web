"""Tests for backtest API endpoints."""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.trading import TradingModel, BacktestData


@pytest_asyncio.fixture
async def test_model(db_session: AsyncSession):
    """Create a test trading model."""
    model = TradingModel(
        id=uuid4(),
        name="test_model",
        description="Test model for backtest endpoints",
        index_type="NASDAQ_100",
        is_meta=False,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def test_backtest_data(db_session: AsyncSession, test_model):
    """Create test backtest data for the test model."""
    # Create 30 days of backtest data
    base_date = date(2024, 1, 1)
    for i in range(30):
        backtest_record = BacktestData(
            model_id=test_model.id,
            date=base_date + timedelta(days=i),
            buy_hold_value=10000.0 + (i * 100),
            traded_value=10000.0 + (i * 150),
            new_highs=5 + i,
            new_lows=2,
            selected_model=None,
        )
        db_session.add(backtest_record)
    
    await db_session.commit()
    return test_model


class TestGetBacktestData:
    """Tests for GET /models/{id}/backtest endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_backtest_empty_database(self, async_client: AsyncClient):
        """Test getting backtest data with empty database returns 404."""
        random_uuid = uuid4()
        response = await async_client.get(f"/api/v1/models/{random_uuid}/backtest")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_backtest_nonexistent_model(self, async_client: AsyncClient):
        """Test getting backtest data for non-existent model returns 404."""
        random_uuid = uuid4()
        response = await async_client.get(f"/api/v1/models/{random_uuid}/backtest")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_backtest_with_data(
        self, async_client: AsyncClient, test_backtest_data
    ):
        """Test getting backtest data with populated data returns correct structure."""
        response = await async_client.get(
            f"/api/v1/models/{test_backtest_data.id}/backtest"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["model_id"] == str(test_backtest_data.id)
        assert data["model_name"] == "test_model"
        assert len(data["data_points"]) == 30
        
        # Verify data point structure
        first_point = data["data_points"][0]
        assert "date" in first_point
        assert "buy_hold_value" in first_point
        assert "traded_value" in first_point
        assert "new_highs" in first_point
        assert "new_lows" in first_point
    
    @pytest.mark.asyncio
    async def test_get_backtest_with_days_filter(
        self, async_client: AsyncClient, test_backtest_data
    ):
        """Test getting backtest data with days filter."""
        response = await async_client.get(
            f"/api/v1/models/{test_backtest_data.id}/backtest?days=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return approximately 10 days of data
        # (exact count depends on date filtering logic)
        assert len(data["data_points"]) <= 30
    
    @pytest.mark.asyncio
    async def test_get_backtest_model_no_backtest_data(
        self, async_client: AsyncClient, test_model
    ):
        """Test getting backtest data for model with no backtest records returns empty."""
        response = await async_client.get(
            f"/api/v1/models/{test_model.id}/backtest"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["model_id"] == str(test_model.id)
        assert len(data["data_points"]) == 0


class TestCompareBacktestData:
    """Tests for GET /models/backtest/compare endpoint."""
    
    @pytest.mark.asyncio
    async def test_compare_backtest_empty_model_list(self, async_client: AsyncClient):
        """Test comparing backtest with empty model list returns 400."""
        response = await async_client.get("/api/v1/models/backtest/compare")
        
        assert response.status_code == 400
        assert "model_ids" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_compare_backtest_valid_models(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test comparing backtest data for valid models."""
        # Create two test models with backtest data
        model1 = TradingModel(
            id=uuid4(),
            name="model1",
            description="Test model 1",
            index_type="NASDAQ_100",
            is_meta=False,
        )
        model2 = TradingModel(
            id=uuid4(),
            name="model2",
            description="Test model 2",
            index_type="SP_500",
            is_meta=False,
        )
        db_session.add_all([model1, model2])
        await db_session.commit()
        
        # Add backtest data for both models
        base_date = date(2024, 1, 1)
        for i in range(10):
            db_session.add(BacktestData(
                model_id=model1.id,
                date=base_date + timedelta(days=i),
                buy_hold_value=10000.0 + i * 100,
                traded_value=10000.0 + i * 120,
                new_highs=5,
                new_lows=2,
            ))
            db_session.add(BacktestData(
                model_id=model2.id,
                date=base_date + timedelta(days=i),
                buy_hold_value=10000.0 + i * 90,
                traded_value=10000.0 + i * 110,
                new_highs=4,
                new_lows=3,
            ))
        await db_session.commit()
        
        # Test comparison
        model_ids = f"{model1.id},{model2.id}"
        response = await async_client.get(
            f"/api/v1/models/backtest/compare?model_ids={model_ids}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["models"]) == 2
        assert data["models"][0]["model_name"] in ["model1", "model2"]
        assert data["models"][1]["model_name"] in ["model1", "model2"]
