"""Tests for Phase 3 API endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from datetime import date, timedelta
from uuid import uuid4

from app.main import app
from app.models.trading import TradingModel, PerformanceMetric, PortfolioSnapshot, PortfolioHolding, IndexType


@pytest.mark.asyncio
async def test_list_models_empty(override_get_db):
    """Test GET /models with empty database."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/models/")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_models_with_data(db_session, override_get_db):
    """Test GET /models returns all models with latest values."""
    # Create test models
    base_model = TradingModel(
        id=uuid4(),
        name="test_base_model",
        description="Test base model",
        index_type=IndexType.NASDAQ_100,
        is_meta=False
    )
    meta_model = TradingModel(
        id=uuid4(),
        name="test_meta_model",
        description="Test meta model",
        index_type=IndexType.SP_500,
        is_meta=True
    )
    
    db_session.add_all([base_model, meta_model])
    
    # Add performance metrics
    metric1 = PerformanceMetric(
        id=uuid4(),
        model_id=base_model.id,
        date=date.today(),
        base_value=10000.0,
        signal=1,
        traded_value=10500.0
    )
    metric2 = PerformanceMetric(
        id=uuid4(),
        model_id=meta_model.id,
        date=date.today(),
        base_value=20000.0,
        signal=1,
        traded_value=21000.0
    )
    
    db_session.add_all([metric1, metric2])
    await db_session.commit()
    
    # Test endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/models/")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Meta-model should be first (ordered by is_meta DESC)
    assert data[0]["name"] == "test_meta_model"
    assert data[0]["is_meta"] is True
    assert data[0]["latest_value"] == 21000.0
    assert data[0]["latest_date"] == str(date.today())
    
    # Base model should be second
    assert data[1]["name"] == "test_base_model"
    assert data[1]["is_meta"] is False
    assert data[1]["latest_value"] == 10500.0


@pytest.mark.asyncio
async def test_get_model_not_found(override_get_db):
    """Test GET /models/{id} with non-existent model."""
    fake_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/models/{fake_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_model_performance(db_session, override_get_db):
    """Test GET /models/{id}/performance returns equity curve data."""
    # Create test model
    model = TradingModel(
        id=uuid4(),
        name="test_performance_model",
        description="Test model",
        index_type=IndexType.NASDAQ_100,
        is_meta=False
    )
    db_session.add(model)
    
    # Add 100 days of performance metrics
    today = date.today()
    metrics = []
    for i in range(100):
        metric = PerformanceMetric(
            id=uuid4(),
            model_id=model.id,
            date=today - timedelta(days=99-i),
            base_value=10000.0 + (i * 10),
            signal=1 if i % 2 == 0 else 0,
            traded_value=10000.0 + (i * 15),
            daily_return=0.001 * i
        )
        metrics.append(metric)
    
    db_session.add_all(metrics)
    await db_session.commit()
    
    # Test default (90 days)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/models/{model.id}/performance")
    
    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == str(model.id)
    assert data["model_name"] == "test_performance_model"
    assert data["days"] == 90
    assert len(data["data_points"]) == 90
    
    # Verify chronological order
    dates = [point["date"] for point in data["data_points"]]
    assert dates == sorted(dates)
    
    # Verify first and last data points
    assert data["data_points"][0]["base_value"] == 10100.0  # Day 10 (100 - 90)
    assert data["data_points"][-1]["base_value"] == 10990.0  # Day 99


@pytest.mark.asyncio
async def test_get_model_performance_custom_days(db_session, override_get_db):
    """Test GET /models/{id}/performance with custom days parameter."""
    # Create test model with 30 metrics
    model = TradingModel(
        id=uuid4(),
        name="test_custom_days",
        description="Test model",
        index_type=IndexType.SP_500,
        is_meta=False
    )
    db_session.add(model)
    
    today = date.today()
    for i in range(30):
        metric = PerformanceMetric(
            id=uuid4(),
            model_id=model.id,
            date=today - timedelta(days=29-i),
            base_value=10000.0 + i,
            signal=1,
            traded_value=10000.0 + i
        )
        db_session.add(metric)
    
    await db_session.commit()
    
    # Request only 10 days
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/models/{model.id}/performance?days=10")
    
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 10
    assert len(data["data_points"]) == 10


@pytest.mark.asyncio
async def test_get_model_performance_not_found(override_get_db):
    """Test GET /models/{id}/performance with non-existent model."""
    fake_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/models/{fake_id}/performance")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_model_holdings(db_session, override_get_db):
    """Test GET /models/{id}/holdings returns current portfolio."""
    # Create test model
    model = TradingModel(
        id=uuid4(),
        name="test_holdings_model",
        description="Test model",
        index_type=IndexType.NASDAQ_100,
        is_meta=False
    )
    db_session.add(model)
    
    # Create portfolio snapshots (older and newer)
    old_snapshot = PortfolioSnapshot(
        id=uuid4(),
        model_id=model.id,
        date=date.today() - timedelta(days=30),
        total_value=50000.0
    )
    latest_snapshot = PortfolioSnapshot(
        id=uuid4(),
        model_id=model.id,
        date=date.today(),
        total_value=100000.0
    )
    
    db_session.add_all([old_snapshot, latest_snapshot])
    
    # Add holdings to latest snapshot
    holdings = [
        PortfolioHolding(
            id=uuid4(),
            snapshot_id=latest_snapshot.id,
            ticker="AAPL",
            shares=100.0,
            purchase_price=150.0,
            current_price=160.0,
            weight=0.40,
            rank=1,
            buy_date=date.today() - timedelta(days=5)
        ),
        PortfolioHolding(
            id=uuid4(),
            snapshot_id=latest_snapshot.id,
            ticker="MSFT",
            shares=80.0,
            purchase_price=300.0,
            current_price=310.0,
            weight=0.35,
            rank=2,
            buy_date=date.today() - timedelta(days=3)
        ),
        PortfolioHolding(
            id=uuid4(),
            snapshot_id=latest_snapshot.id,
            ticker="GOOGL",
            shares=50.0,
            purchase_price=140.0,
            current_price=145.0,
            weight=0.25,
            rank=3,
            buy_date=date.today() - timedelta(days=1)
        )
    ]
    
    db_session.add_all(holdings)
    await db_session.commit()
    
    # Test endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/models/{model.id}/holdings")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["model_id"] == str(model.id)
    assert data["model_name"] == "test_holdings_model"
    assert data["snapshot_date"] == str(date.today())
    assert data["total_value"] == 100000.0
    assert data["active_sub_model_name"] is None
    
    # Verify holdings are sorted by weight (descending)
    assert len(data["holdings"]) == 3
    assert data["holdings"][0]["ticker"] == "AAPL"
    assert data["holdings"][0]["weight"] == 0.40
    assert data["holdings"][1]["ticker"] == "MSFT"
    assert data["holdings"][1]["weight"] == 0.35
    assert data["holdings"][2]["ticker"] == "GOOGL"
    assert data["holdings"][2]["weight"] == 0.25


@pytest.mark.asyncio
async def test_get_model_holdings_with_meta_model(db_session, override_get_db):
    """Test GET /models/{id}/holdings for meta-model shows active sub-model."""
    # Create meta-model and sub-model
    sub_model = TradingModel(
        id=uuid4(),
        name="active_sub_model",
        description="Active sub model",
        index_type=IndexType.NASDAQ_100,
        is_meta=False
    )
    meta_model = TradingModel(
        id=uuid4(),
        name="meta_model",
        description="Meta model",
        index_type=IndexType.SP_500,
        is_meta=True
    )
    
    db_session.add_all([sub_model, meta_model])
    
    # Create snapshot with active_sub_model_id
    snapshot = PortfolioSnapshot(
        id=uuid4(),
        model_id=meta_model.id,
        date=date.today(),
        total_value=200000.0,
        active_sub_model_id=sub_model.id
    )
    
    db_session.add(snapshot)
    
    # Add a holding
    holding = PortfolioHolding(
        id=uuid4(),
        snapshot_id=snapshot.id,
        ticker="TSLA",
        shares=100.0,
        purchase_price=200.0,
        weight=1.0
    )
    
    db_session.add(holding)
    await db_session.commit()
    
    # Test endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/models/{meta_model.id}/holdings")
    
    assert response.status_code == 200
    data = response.json()
    assert data["active_sub_model_name"] == "active_sub_model"


@pytest.mark.asyncio
async def test_get_model_holdings_not_found(override_get_db):
    """Test GET /models/{id}/holdings with non-existent model."""
    fake_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/models/{fake_id}/holdings")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_model_holdings_no_snapshots(db_session, override_get_db):
    """Test GET /models/{id}/holdings when model has no snapshots."""
    # Create model with no snapshots
    model = TradingModel(
        id=uuid4(),
        name="empty_model",
        description="Model with no data",
        index_type=IndexType.NASDAQ_100,
        is_meta=False
    )
    db_session.add(model)
    await db_session.commit()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/models/{model.id}/holdings")
    
    assert response.status_code == 404
    assert "no portfolio snapshots" in response.json()["detail"].lower()
