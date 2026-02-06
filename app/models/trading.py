import uuid
from datetime import date as DateType
from enum import Enum as PyEnum
from sqlalchemy import String, Text, Boolean, Float, Integer, Date, ForeignKey, Enum, UUID, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from app.models.base import Base

class IndexType(PyEnum):
    NASDAQ_100 = "NASDAQ_100"
    SP_500 = "SP_500"

class TradingModel(Base):
    __tablename__ = "trading_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    index_type: Mapped[IndexType] = mapped_column(Enum(IndexType))
    is_meta: Mapped[bool] = mapped_column(Boolean, default=False)
    config_json_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    snapshots: Mapped[List["PortfolioSnapshot"]] = relationship("PortfolioSnapshot", back_populates="model", foreign_keys="[PortfolioSnapshot.model_id]")
    metrics: Mapped[List["PerformanceMetric"]] = relationship(back_populates="model", cascade="all, delete-orphan")
    backtest_data: Mapped[List["BacktestData"]] = relationship(back_populates="model", cascade="all, delete-orphan")

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trading_models.id"))
    date: Mapped[DateType] = mapped_column(Date)
    total_value: Mapped[float] = mapped_column(Float, default=0.0)
    
    # For meta-model, track which sub-model was active at this snapshot
    active_sub_model_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("trading_models.id"), nullable=True)

    model: Mapped["TradingModel"] = relationship("TradingModel", foreign_keys=[model_id], back_populates="snapshots")
    holdings: Mapped[List["PortfolioHolding"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    
    # Compound index for efficient model + date queries
    __table_args__ = (
        Index('ix_portfolio_snapshots_model_id_date', 'model_id', 'date'),
    )

class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portfolio_snapshots.id"))
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    shares: Mapped[float] = mapped_column(Float)
    purchase_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight: Mapped[float] = mapped_column(Float)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    buy_date: Mapped[Optional[DateType]] = mapped_column(Date, nullable=True)

    snapshot: Mapped["PortfolioSnapshot"] = relationship(back_populates="holdings")

class PerformanceMetric(Base):
    """Daily performance records for each model."""
    __tablename__ = "performance_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trading_models.id"))
    date: Mapped[DateType] = mapped_column(Date)
    
    # Values from PyTAAA_status.params
    base_value: Mapped[float] = mapped_column(Float)  # cumu_value (long only/original)
    signal: Mapped[int] = mapped_column(Integer)      # 1 or 0
    traded_value: Mapped[float] = mapped_column(Float) # value after signal
    
    daily_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    model: Mapped["TradingModel"] = relationship(back_populates="metrics")
    
    # Compound index for efficient model + date queries
    __table_args__ = (
        Index('ix_performance_metrics_model_id_date', 'model_id', 'date'),
    )

class BacktestData(Base):
    """Backtest portfolio value data from pyTAAAweb_backtestPortfolioValue.params files."""
    __tablename__ = "backtest_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trading_models.id"), index=True)
    date: Mapped[DateType] = mapped_column(Date, index=True)
    
    # Values from pyTAAAweb_backtestPortfolioValue.params
    buy_hold_value: Mapped[float] = mapped_column(Float)      # Column 2: buy-and-hold baseline
    traded_value: Mapped[float] = mapped_column(Float)        # Column 3: model-switched portfolio
    new_highs: Mapped[int] = mapped_column(Integer)           # Column 4: market breadth indicator
    new_lows: Mapped[int] = mapped_column(Integer)            # Column 5: market breadth indicator
    selected_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Column 6 (abacus only): model selection

    model: Mapped["TradingModel"] = relationship(back_populates="backtest_data")

    __table_args__ = (
        {"comment": "Daily backtest portfolio values for visualization"}
    )
