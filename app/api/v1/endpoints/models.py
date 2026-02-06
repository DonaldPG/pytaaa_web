"""Trading model CRUD endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.db.session import get_db
from app.models.trading import TradingModel, PerformanceMetric
from app.schemas.trading import (
    TradingModel as TradingModelSchema,
    ModelWithLatestValue,
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
    
    Optimized to avoid N+1 queries and duplicates using a subquery for latest metrics.
    """
    # Subquery to get the latest metric (by date, then by id for determinism) per model
    latest_metric_subquery = (
        select(PerformanceMetric)
        .distinct(PerformanceMetric.model_id)
        .order_by(PerformanceMetric.model_id, PerformanceMetric.date.desc(), PerformanceMetric.id.desc())
        .subquery()
    )
    
    # Get all models and join with their latest metrics (at most one per model)
    result = await db.execute(
        select(TradingModel, latest_metric_subquery.c.traded_value, latest_metric_subquery.c.date)
        .outerjoin(
            latest_metric_subquery,
            TradingModel.id == latest_metric_subquery.c.model_id
        )
        .order_by(TradingModel.is_meta.desc(), TradingModel.name)
    )
    
    # Collect all results
    all_results = []
    for model, traded_value, metric_date in result:
        all_results.append((model, traded_value, metric_date))
    
    # Custom sort: meta-model first, then swap naz100_pi and naz100_pine for vertical alignment
    def sort_key(item):
        model, _, _ = item
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
    for model, traded_value, metric_date in all_results:
        response.append(ModelWithLatestValue(
            id=model.id,
            name=model.name,
            description=model.description,
            index_type=model.index_type,
            is_meta=model.is_meta,
            latest_value=traded_value,
            latest_date=metric_date
        ))
    
    return response


@router.get("/{model_id}", response_model=TradingModelSchema)
async def get_model(model_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get details for a specific trading model."""
    return await get_model_or_404(model_id, db)
