from typing import List
from datetime import timedelta, date as date_type
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from uuid import UUID
from app.db.session import get_db
from app.models.trading import TradingModel, PerformanceMetric, PortfolioSnapshot, PortfolioHolding
from app.schemas.trading import (
    TradingModel as TradingModelSchema,
    ModelWithLatestValue,
    PerformanceResponse,
    PerformanceDataPoint,
    HoldingsResponse,
    HoldingDetail,
    ComparisonResponse,
    ModelPerformanceSeries
)

router = APIRouter()


async def get_model_or_404(model_id: UUID, db: AsyncSession) -> TradingModel:
    """Get a model by ID or raise 404.
    
    DRY helper to avoid duplicate model validation across endpoints.
    """
    result = await db.execute(select(TradingModel).where(TradingModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.get("/", response_model=List[ModelWithLatestValue])
async def list_models(db: AsyncSession = Depends(get_db)):
    """List all available trading models with their latest performance values.
    
    Optimized to avoid N+1 queries using a subquery for latest metrics.
    """
    # Subquery to get latest metric date per model
    latest_metric_subquery = (
        select(
            PerformanceMetric.model_id,
            func.max(PerformanceMetric.date).label('max_date')
        )
        .group_by(PerformanceMetric.model_id)
        .subquery()
    )
    
    # Join models with their latest metrics in a single query
    result = await db.execute(
        select(TradingModel, PerformanceMetric)
        .outerjoin(
            latest_metric_subquery,
            TradingModel.id == latest_metric_subquery.c.model_id
        )
        .outerjoin(
            PerformanceMetric,
            (PerformanceMetric.model_id == TradingModel.id) &
            (PerformanceMetric.date == latest_metric_subquery.c.max_date)
        )
        .order_by(TradingModel.is_meta.desc(), TradingModel.name)
    )
    
    response = []
    for model, metric in result:
        response.append(ModelWithLatestValue(
            id=model.id,
            name=model.name,
            description=model.description,
            index_type=model.index_type,
            is_meta=model.is_meta,
            latest_value=metric.traded_value if metric else None,
            latest_date=metric.date if metric else None
        ))
    
    return response


@router.get("/compare", response_model=ComparisonResponse)
async def compare_models(
    days: int = Query(default=90, ge=1, le=100000, description="Number of days to compare"),
    db: AsyncSession = Depends(get_db)
):
    """Compare performance of all models over a specified time period.
    
    Returns equity curves for all models to enable overlay visualization.
    Useful for comparing meta-model performance against underlying models.
    
    Args:
        days: Number of most recent days to include (default 90, max 5000)
        db: Database session
        
    Returns:
        ComparisonResponse with performance data for all models
    """
    # Get all models
    models_result = await db.execute(
        select(TradingModel).order_by(TradingModel.is_meta.desc(), TradingModel.name)
    )
    models = models_result.scalars().all()
    
    if not models:
        return ComparisonResponse(days=days, models=[])
    
    # Use absolute calendar dates: today (or latest data date) minus N days
    # This ensures consistent date ranges regardless of data frequency
    latest_date_result = await db.execute(
        select(func.max(PerformanceMetric.date))
    )
    latest_date = latest_date_result.scalar()
    
    if not latest_date:
        return ComparisonResponse(days=days, models=[])
    
    # Calculate the earliest date as exactly N calendar days before the latest date
    earliest_date = latest_date - timedelta(days=days)
    
    model_series = []
    
    for model in models:
        # Get performance metrics for this model within the absolute calendar date range
        metrics_result = await db.execute(
            select(PerformanceMetric)
            .where(
                PerformanceMetric.model_id == model.id,
                PerformanceMetric.date >= earliest_date,
                PerformanceMetric.date <= latest_date
            )
            .order_by(PerformanceMetric.date)
        )
        metrics = metrics_result.scalars().all()
        
        data_points = [
            PerformanceDataPoint(
                date=m.date,
                base_value=m.base_value,
                traded_value=m.traded_value,
                signal=m.signal,
                daily_return=m.daily_return
            )
            for m in metrics
        ]
        
        model_series.append(
            ModelPerformanceSeries(
                model_id=model.id,
                model_name=model.name,
                is_meta=model.is_meta,
                index_type=model.index_type,
                data_points=data_points
            )
        )
    
    return ComparisonResponse(days=days, models=model_series)


@router.get("/{model_id}", response_model=TradingModelSchema)
async def get_model(model_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get details for a specific trading model."""
    return await get_model_or_404(model_id, db)

@router.get("/{model_id}/performance", response_model=PerformanceResponse)
async def get_model_performance(
    model_id: UUID,
    days: int = Query(default=90, ge=1, le=100000),
    db: AsyncSession = Depends(get_db)
):
    """Get performance data (equity curve) for a specific model."""
    # Verify model exists
    model = await get_model_or_404(model_id, db)
    
    # Calculate date cutoff (calendar days, not record count)
    cutoff_date = date_type.today() - timedelta(days=days)
    
    # Get performance metrics within the date range
    metrics_result = await db.execute(
        select(PerformanceMetric)
        .where(PerformanceMetric.model_id == model_id)
        .where(PerformanceMetric.date >= cutoff_date)
        .order_by(PerformanceMetric.date)
    )
    metrics = metrics_result.scalars().all()
    
    data_points = [
        PerformanceDataPoint(
            date=m.date,
            base_value=m.base_value,
            traded_value=m.traded_value,
            signal=m.signal,
            daily_return=m.daily_return
        )
        for m in metrics
    ]
    
    return PerformanceResponse(
        model_id=model.id,
        model_name=model.name,
        days=len(data_points),
        data_points=data_points
    )

@router.get("/{model_id}/holdings", response_model=HoldingsResponse)
async def get_model_holdings(model_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get current portfolio holdings for a specific model."""
    # Verify model exists
    model = await get_model_or_404(model_id, db)
    
    # Get latest snapshot
    snapshot_result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.model_id == model_id)
        .order_by(desc(PortfolioSnapshot.date))
        .limit(1)
    )
    snapshot = snapshot_result.scalar_one_or_none()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="No portfolio snapshots found for this model")
    
    # Get holdings for this snapshot
    holdings_result = await db.execute(
        select(PortfolioHolding)
        .where(PortfolioHolding.snapshot_id == snapshot.id)
        .order_by(desc(PortfolioHolding.weight))
    )
    holdings = holdings_result.scalars().all()
    
    # Get active sub-model name if meta-model
    active_sub_model_name = None
    if snapshot.active_sub_model_id:
        sub_model_result = await db.execute(
            select(TradingModel).where(TradingModel.id == snapshot.active_sub_model_id)
        )
        sub_model = sub_model_result.scalar_one_or_none()
        if sub_model:
            active_sub_model_name = sub_model.name
    
    holding_details = [
        HoldingDetail(
            ticker=h.ticker,
            shares=h.shares,
            purchase_price=h.purchase_price,
            current_price=h.current_price,
            weight=h.weight,
            rank=h.rank,
            buy_date=h.buy_date
        )
        for h in holdings
    ]
    
    return HoldingsResponse(
        model_id=model.id,
        model_name=model.name,
        snapshot_date=snapshot.date,
        total_value=snapshot.total_value,
        holdings=holding_details,
        active_sub_model_name=active_sub_model_name
    )

@router.get("/{model_id}/snapshots", response_model=List[date_type])
async def get_model_snapshot_dates(model_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all available snapshot dates for a specific model."""
    # Verify model exists
    await get_model_or_404(model_id, db)
    
    # Get all snapshot dates
    snapshots_result = await db.execute(
        select(PortfolioSnapshot.date)
        .where(PortfolioSnapshot.model_id == model_id)
        .order_by(desc(PortfolioSnapshot.date))
    )
    dates = snapshots_result.scalars().all()
    
    return dates

@router.get("/{model_id}/holdings/{snapshot_date}", response_model=HoldingsResponse)
async def get_model_holdings_by_date(
    model_id: UUID, 
    snapshot_date: date_type,
    db: AsyncSession = Depends(get_db)
):
    """Get portfolio holdings for a specific model at a specific date."""
    # Verify model exists
    model = await get_model_or_404(model_id, db)
    
    # Get snapshot for the specific date
    snapshot_result = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.model_id == model_id,
            PortfolioSnapshot.date == snapshot_date
        )
        .limit(1)
    )
    snapshot = snapshot_result.scalar_one_or_none()
    
    if not snapshot:
        raise HTTPException(
            status_code=404, 
            detail=f"No portfolio snapshot found for date {snapshot_date}"
        )
    
    # Get holdings for this snapshot
    holdings_result = await db.execute(
        select(PortfolioHolding)
        .where(PortfolioHolding.snapshot_id == snapshot.id)
        .order_by(desc(PortfolioHolding.weight))
    )
    holdings = holdings_result.scalars().all()
    
    # Get active sub-model name if meta-model
    active_sub_model_name = None
    if snapshot.active_sub_model_id:
        sub_model_result = await db.execute(
            select(TradingModel).where(TradingModel.id == snapshot.active_sub_model_id)
        )
        sub_model = sub_model_result.scalar_one_or_none()
        if sub_model:
            active_sub_model_name = sub_model.name
    
    holding_details = [
        HoldingDetail(
            ticker=h.ticker,
            shares=h.shares,
            purchase_price=h.purchase_price,
            current_price=h.current_price,
            weight=h.weight,
            rank=h.rank,
            buy_date=h.buy_date
        )
        for h in holdings
    ]
    
    return HoldingsResponse(
        model_id=model.id,
        model_name=model.name,
        snapshot_date=snapshot.date,
        total_value=snapshot.total_value,
        holdings=holding_details,
        active_sub_model_name=active_sub_model_name
    )
