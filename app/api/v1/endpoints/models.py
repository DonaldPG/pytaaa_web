from typing import List
from datetime import timedelta, date as date_type
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from uuid import UUID
from app.db.session import get_db
from app.models.trading import TradingModel, PerformanceMetric, PortfolioSnapshot, PortfolioHolding, BacktestData
from app.schemas.trading import (
    TradingModel as TradingModelSchema,
    ModelWithLatestValue,
    PerformanceResponse,
    PerformanceDataPoint,
    HoldingsResponse,
    HoldingDetail,
    ComparisonResponse,
    ModelPerformanceSeries,
    BacktestResponse,
    BacktestDataPoint,
    BacktestComparisonResponse,
    BacktestModelSeries,
    ModelSelectionResponse,
    ModelSelectionPoint
)
from app.utils.model_selection import ModelSelection

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
    )
    
    # Collect all results
    all_results = []
    for model, metric in result:
        all_results.append((model, metric))
    
    # Custom sort: meta-model first, then swap naz100_pi and naz100_pine for vertical alignment
    def sort_key(item):
        model, _ = item
        if model.is_meta:
            return (0, model.name)
        # Swap naz100_pi and naz100_pine so _pine cards align vertically
        name = model.name
        if name == 'naz100_pi':
            name = 'naz100_pine_sort'
        elif name == 'naz100_pine':
            name = 'naz100_pi_sort'
        return (1, name)
    
    all_results.sort(key=sort_key)
    
    response = []
    for model, metric in all_results:
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


@router.get("/{model_id}/backtest", response_model=BacktestResponse)
async def get_backtest_data(
    model_id: UUID,
    days: int = Query(default=100000, ge=1, le=100000, description="Number of days to include"),
    db: AsyncSession = Depends(get_db)
):
    """Get backtest portfolio value data for a specific model.
    
    Returns historical backtest data with:
    - buy_hold_value: Buy-and-hold baseline
    - traded_value: Model-switched portfolio value
    - new_highs/new_lows: Market breadth indicators
    
    Args:
        model_id: UUID of the model
        days: Number of days of history to return (default: 100000 = all data)
    """
    # Validate model exists
    model = await get_model_or_404(model_id, db)
    
    # Calculate cutoff date
    today = date_type.today()
    cutoff_date = today - timedelta(days=days)
    
    # Get backtest data ordered by date, filtered by date range
    result = await db.execute(
        select(BacktestData)
        .where(BacktestData.model_id == model_id)
        .where(BacktestData.date >= cutoff_date)
        .order_by(BacktestData.date)
    )
    backtest_records = result.scalars().all()
    
    if not backtest_records:
        raise HTTPException(
            status_code=404,
            detail=f"No backtest data found for model {model.name}"
        )
    
    data_points = [
        BacktestDataPoint(
            date=record.date,
            buy_hold_value=record.buy_hold_value,
            traded_value=record.traded_value,
            new_highs=record.new_highs,
            new_lows=record.new_lows
        )
        for record in backtest_records
    ]
    
    return BacktestResponse(
        model_id=model.id,
        model_name=model.name,
        index_type=model.index_type,
        data_points=data_points
    )


@router.get("/backtest/compare", response_model=BacktestComparisonResponse)
async def compare_backtest_data(
    model_ids: List[UUID] = Query(..., description="List of model IDs to compare"),
    db: AsyncSession = Depends(get_db)
):
    """Compare backtest data across multiple models.
    
    Useful for visualizing how different models performed during backtesting.
    """
    if not model_ids:
        raise HTTPException(status_code=400, detail="At least one model_id required")
    
    model_series = []
    
    for model_id in model_ids:
        # Validate model exists
        model = await get_model_or_404(model_id, db)
        
        # Get backtest data
        result = await db.execute(
            select(BacktestData)
            .where(BacktestData.model_id == model_id)
            .order_by(BacktestData.date)
        )
        backtest_records = result.scalars().all()
        
        if not backtest_records:
            # Skip models without backtest data instead of failing
            continue
        
        data_points = [
            BacktestDataPoint(
                date=record.date,
                buy_hold_value=record.buy_hold_value,
                traded_value=record.traded_value,
                new_highs=record.new_highs,
                new_lows=record.new_lows
            )
            for record in backtest_records
        ]
        
        model_series.append(BacktestModelSeries(
            model_id=model.id,
            model_name=model.name,
            index_type=model.index_type,
            data_points=data_points
        ))
    
    if not model_series:
        raise HTTPException(
            status_code=404,
            detail="No backtest data found for any of the requested models"
        )
    
    return BacktestComparisonResponse(models=model_series)


@router.get("/meta/{meta_model_id}/selections", response_model=ModelSelectionResponse)
async def get_model_selections(
    meta_model_id: UUID,
    days: int = Query(default=365, ge=30, le=100000, description="Number of days to analyze"),
    lookbacks: str = Query(default="55,157,174", description="Comma-separated lookback periods"),
    sample_rate: int = Query(default=21, ge=1, le=252, description="Sample every N days (default: monthly)"),
    db: AsyncSession = Depends(get_db)
):
    """Calculate model selection decisions for a meta-model over time.
    
    This endpoint computes which sub-model the meta-model should have selected
    at different points in time based on historical performance analysis.
    
    Args:
        meta_model_id: UUID of the meta-model
        days: Number of days to analyze (default 365)
        lookbacks: Comma-separated lookback periods in days (default "55,157,174")
        sample_rate: Sample selections every N days (default 21 = monthly)
        db: Database session
        
    Returns:
        ModelSelectionResponse with selection history
    """
    # Validate meta-model exists and is actually a meta-model
    meta_model = await get_model_or_404(meta_model_id, db)
    if not meta_model.is_meta:
        raise HTTPException(
            status_code=400,
            detail=f"Model {meta_model.name} is not a meta-model"
        )
    
    # Parse lookback periods
    try:
        lookback_periods = [int(x.strip()) for x in lookbacks.split(',')]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid lookbacks format. Use comma-separated integers (e.g., '55,157,174')"
        )
    
    # Get all non-meta models (potential sub-models)
    models_result = await db.execute(
        select(TradingModel).where(TradingModel.is_meta == False)
    )
    models = models_result.scalars().all()
    
    if not models:
        raise HTTPException(
            status_code=404,
            detail="No sub-models found for selection"
        )
    
    # Calculate date range
    today = date_type.today()
    cutoff_date = today - timedelta(days=days)
    
    # Get backtest data for all models
    backtest_data_dict = {}
    
    for model in models:
        result = await db.execute(
            select(BacktestData)
            .where(BacktestData.model_id == model.id)
            .where(BacktestData.date >= cutoff_date - timedelta(days=max(lookback_periods)))
            .order_by(BacktestData.date)
        )
        records = result.scalars().all()
        
        if records:
            # Store as list of (date, traded_value) tuples
            backtest_data_dict[model.name] = [
                (record.date, record.traded_value) for record in records
            ]
    
    if not backtest_data_dict:
        raise HTTPException(
            status_code=404,
            detail="No backtest data found for any sub-models"
        )
    
    # Initialize model selection calculator
    selector = ModelSelection(lookback_periods=lookback_periods)
    
    # Get all unique dates in the range
    all_dates = set()
    for data_points in backtest_data_dict.values():
        all_dates.update(date for date, _ in data_points)
    
    # Filter to dates >= cutoff_date and sample at specified rate
    valid_dates = sorted([d for d in all_dates if d >= cutoff_date])
    
    # Sample dates (e.g., every 21 days for monthly)
    sampled_dates = valid_dates[::sample_rate]
    
    # Calculate selections for each sampled date
    selections = []
    
    for target_date in sampled_dates:
        best_model, confidence, all_ranks = selector.select_best_model(
            backtest_data_dict,
            target_date
        )
        
        selections.append(ModelSelectionPoint(
            date=target_date,
            selected_model=best_model,
            confidence=confidence,
            all_ranks=all_ranks
        ))
    
    return ModelSelectionResponse(
        selections=selections,
        lookback_periods=lookback_periods
    )

