"""Portfolio holdings-related API endpoints."""
from typing import List
from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from uuid import UUID

from app.db.session import get_db
from app.models.trading import TradingModel, PortfolioSnapshot, PortfolioHolding
from app.schemas.trading import (
    HoldingsResponse,
    HoldingDetail,
)
from app.api.v1.endpoints.models import get_model_or_404

router = APIRouter()


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
