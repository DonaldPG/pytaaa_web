"""Performance-related API endpoints."""
from typing import List
from datetime import timedelta, date as date_type
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.db.session import get_db
from app.models.trading import TradingModel, PerformanceMetric
from app.schemas.trading import (
    PerformanceResponse,
    PerformanceDataPoint,
    ComparisonResponse,
    ModelPerformanceSeries,
)
from app.api.v1.endpoints.models import get_model_or_404

router = APIRouter()


@router.get("/compare", response_model=ComparisonResponse)
async def compare_models(
    days: int = Query(default=90, ge=1, le=100000, description="Number of days to compare"),
    db: AsyncSession = Depends(get_db)
):
    """Compare performance of all models over a specified time period.
    
    Returns equity curves for all models to enable overlay visualization.
    Useful for comparing meta-model performance against underlying models.
    
    Args:
        days: Number of most recent days to include (default 90, max 100000)
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
