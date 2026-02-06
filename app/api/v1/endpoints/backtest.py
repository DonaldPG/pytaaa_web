"""Backtest-related API endpoints."""
from typing import List
from datetime import timedelta, date as date_type
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.session import get_db
from app.models.trading import TradingModel, BacktestData
from app.schemas.trading import (
    BacktestResponse,
    BacktestDataPoint,
    BacktestComparisonResponse,
    BacktestModelSeries,
)
from app.api.v1.endpoints.models import get_model_or_404

router = APIRouter()


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
            new_lows=record.new_lows,
            selected_model=record.selected_model
        )
        for record in backtest_records
    ]
    
    return BacktestResponse(
        model_id=model.id,
        model_name=model.name,
        index_type=model.index_type,
        data_points=data_points
    )
