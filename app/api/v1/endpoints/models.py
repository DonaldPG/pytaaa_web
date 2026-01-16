from typing import List
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
    HoldingDetail
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

@router.get("/{model_id}", response_model=TradingModelSchema)
async def get_model(model_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get details for a specific trading model."""
    return await get_model_or_404(model_id, db)

@router.get("/{model_id}/performance", response_model=PerformanceResponse)
async def get_model_performance(
    model_id: UUID,
    days: int = Query(default=90, ge=1, le=5000),
    db: AsyncSession = Depends(get_db)
):
    """Get performance data (equity curve) for a specific model."""
    # Verify model exists
    model = await get_model_or_404(model_id, db)
    
    # Get performance metrics
    metrics_result = await db.execute(
        select(PerformanceMetric)
        .where(PerformanceMetric.model_id == model_id)
        .order_by(desc(PerformanceMetric.date))
        .limit(days)
    )
    metrics = metrics_result.scalars().all()
    
    # Reverse to get chronological order
    metrics = list(reversed(metrics))
    
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
