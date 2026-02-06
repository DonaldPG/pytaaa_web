from fastapi import APIRouter
from app.api.v1.endpoints import models, performance, holdings, backtest

api_router = APIRouter()

# Performance endpoints (includes /compare and /{id}/performance)
# Note: Must be registered before models router to avoid /compare being matched by /{model_id}
api_router.include_router(performance.router, prefix="/models", tags=["performance"])

# Model CRUD endpoints
api_router.include_router(models.router, prefix="/models", tags=["models"])

# Holdings endpoints (includes /{id}/holdings, /{id}/snapshots, /{id}/holdings/{date})
api_router.include_router(holdings.router, prefix="/models", tags=["holdings"])

# Backtest endpoints (includes /backtest/compare and /{id}/backtest)
# Note: /backtest/compare is registered before /{id}/backtest to avoid route conflicts
api_router.include_router(backtest.router, prefix="/models", tags=["backtest"])
