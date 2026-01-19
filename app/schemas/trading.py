from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date
from typing import List, Optional
from app.models.trading import IndexType

class TradingModelBase(BaseModel):
    name: str
    description: Optional[str] = None
    index_type: IndexType
    is_meta: bool = False
    config_json_path: Optional[str] = None

class TradingModelCreate(TradingModelBase):
    pass

class TradingModel(TradingModelBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class PortfolioHoldingBase(BaseModel):
    ticker: str
    shares: float
    purchase_price: float
    current_price: Optional[float] = None
    weight: float
    rank: Optional[int] = None
    buy_date: Optional[date] = None

class PortfolioHolding(PortfolioHoldingBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class PortfolioSnapshotBase(BaseModel):
    date: date
    total_value: float
    active_sub_model_id: Optional[UUID] = None

class PortfolioSnapshot(PortfolioSnapshotBase):
    id: UUID
    model_id: UUID
    holdings: List[PortfolioHolding]
    model_config = ConfigDict(from_attributes=True)

class PerformanceMetricBase(BaseModel):
    date: date
    base_value: float
    signal: int
    traded_value: float
    daily_return: Optional[float] = None

class PerformanceMetric(PerformanceMetricBase):
    id: UUID
    model_id: UUID
    model_config = ConfigDict(from_attributes=True)

# Response schemas for API endpoints
class ModelWithLatestValue(BaseModel):
    """Model summary with latest performance value"""
    id: UUID
    name: str
    description: Optional[str] = None
    index_type: IndexType
    is_meta: bool
    latest_value: Optional[float] = None
    latest_date: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)

class PerformanceDataPoint(BaseModel):
    """Single point in equity curve"""
    date: date
    base_value: float
    traded_value: float
    signal: int
    daily_return: Optional[float] = None

class PerformanceResponse(BaseModel):
    """Performance data for a model over time"""
    model_id: UUID
    model_name: str
    days: int
    data_points: List[PerformanceDataPoint]
    model_config = ConfigDict(protected_namespaces=())

class HoldingDetail(BaseModel):
    """Detailed holding information"""
    ticker: str
    shares: float
    purchase_price: float
    current_price: Optional[float] = None
    weight: float
    rank: Optional[int] = None
    buy_date: Optional[date] = None

class HoldingsResponse(BaseModel):
    """Current portfolio holdings for a model"""
    model_id: UUID
    model_name: str
    snapshot_date: date
    total_value: float
    holdings: List[HoldingDetail]
    active_sub_model_name: Optional[str] = None
    model_config = ConfigDict(protected_namespaces=())

class ModelPerformanceSeries(BaseModel):
    """Performance time series for a single model"""
    model_id: UUID
    model_name: str
    is_meta: bool
    index_type: IndexType
    data_points: List[PerformanceDataPoint]

class ComparisonResponse(BaseModel):
    """Performance comparison of all models"""
    days: int
    models: List[ModelPerformanceSeries]
    model_config = ConfigDict(protected_namespaces=())

# Backtest schemas
class BacktestDataPoint(BaseModel):
    """Single backtest data point"""
    date: date
    buy_hold_value: float
    traded_value: float
    new_highs: int
    new_lows: int

class BacktestResponse(BaseModel):
    """Backtest data for a single model"""
    model_id: UUID
    model_name: str
    index_type: IndexType
    data_points: List[BacktestDataPoint]
    model_config = ConfigDict(protected_namespaces=())

class BacktestModelSeries(BaseModel):
    """Backtest series for one model"""
    model_id: UUID
    model_name: str
    index_type: IndexType
    data_points: List[BacktestDataPoint]

class BacktestComparisonResponse(BaseModel):
    """Backtest comparison of multiple models"""
    models: List[BacktestModelSeries]
    model_config = ConfigDict(protected_namespaces=())


class ModelSelectionPoint(BaseModel):
    """Model selection at a specific date"""
    date: date
    selected_model: str
    confidence: float
    all_ranks: dict  # {model_name: rank_score}

class ModelSelectionResponse(BaseModel):
    """Model selection history over time"""
    selections: List[ModelSelectionPoint]
    lookback_periods: List[int]
    model_config = ConfigDict(protected_namespaces=())
