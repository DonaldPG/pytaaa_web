"""Data ingestion CLI command.

Usage:
    python -m app.cli.ingest --data-dir /path/to/pyTAAA_data --model naz100_pine
"""
import asyncio
import argparse
from pathlib import Path
from typing import Optional
import sys

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import Settings
from app.models.trading import TradingModel, PortfolioSnapshot, PortfolioHolding, PerformanceMetric, BacktestData
from app.parsers.status_parser import parse_status_file
from app.parsers.holdings_parser import parse_holdings_file
from app.parsers.ranks_parser import parse_ranks_file
from app.parsers.backtest_parser import parse_backtest_file


async def ingest_model(
    data_dir: Path,
    model_name: str,
    index_type: str = "NASDAQ_100",
    description: Optional[str] = None,
    is_meta: bool = False,
):
    """Ingest data for a trading model from .params files.
    
    Args:
        data_dir: Path to data directory (e.g., /Users/donaldpg/pyTAAA_data/naz100_pine)
        model_name: Name of the model (e.g., "naz100_pine")
        index_type: Index type (NASDAQ_100 or SP_500)
        description: Optional description
        is_meta: Whether this is a meta-model
    """
    # Use localhost for CLI (not Docker internal 'db')
    settings = Settings(POSTGRES_SERVER="localhost")
    database_url = settings.get_database_url()
    engine = create_async_engine(database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    # Locate .params files (in data_store subdirectory)
    data_store = data_dir / "data_store"
    if not data_store.exists():
        data_store = data_dir  # Fallback to data_dir itself
    
    status_file = data_store / "PyTAAA_status.params"
    holdings_file = data_store / "PyTAAA_holdings.params"
    ranks_file = data_store / "PyTAAA_ranks.params"
    
    if not status_file.exists():
        print(f"❌ Status file not found: {status_file}")
        return False
    
    print(f"📂 Ingesting model: {model_name}")
    print(f"   Data directory: {data_dir}")
    
    # Parse files
    print("📊 Parsing status file...")
    metrics_data = parse_status_file(status_file)
    print(f"   Found {len(metrics_data)} performance metrics")
    
    holdings_data = []
    active_sub_model = None
    if holdings_file.exists():
        print("📊 Parsing holdings file...")
        holdings_data, active_sub_model = parse_holdings_file(holdings_file)
        print(f"   Found {len(holdings_data)} portfolio snapshots")
        if active_sub_model:
            print(f"   Active sub-model detected: {active_sub_model}")
    
    ranks_data = []
    if ranks_file.exists():
        print("📊 Parsing ranks file...")
        ranks_data = parse_ranks_file(ranks_file)
        print(f"   Found {len(ranks_data)} stock rankings")
    
    # Create database session
    async with async_session() as session:
        # Create or get trading model
        result = await session.execute(
            select(TradingModel).where(TradingModel.name == model_name)
        )
        model = result.scalar_one_or_none()
        
        if model:
            print(f"⚠️  Model '{model_name}' already exists (ID: {model.id})")
            overwrite = input("   Overwrite existing data? [y/N]: ")
            if overwrite.lower() != 'y':
                print("❌ Ingestion cancelled")
                return False
            
            # Delete existing data using direct queries (not lazy-loaded relationships)
            print("🗑️  Deleting existing snapshots and metrics...")
            
            # First get snapshot IDs
            from sqlalchemy import delete
            snapshot_ids_result = await session.execute(
                select(PortfolioSnapshot.id).where(PortfolioSnapshot.model_id == model.id)
            )
            snapshot_ids = [row[0] for row in snapshot_ids_result.fetchall()]
            
            # Delete holdings first (foreign key constraint)
            if snapshot_ids:
                await session.execute(
                    delete(PortfolioHolding).where(PortfolioHolding.snapshot_id.in_(snapshot_ids))
                )
            
            # Delete snapshots
            await session.execute(
                delete(PortfolioSnapshot).where(PortfolioSnapshot.model_id == model.id)
            )
            
            # Delete metrics
            await session.execute(
                delete(PerformanceMetric).where(PerformanceMetric.model_id == model.id)
            )
            
            await session.commit()
        else:
            print(f"✨ Creating new model: {model_name}")
            model = TradingModel(
                name=model_name,
                description=description or f"Trading model: {model_name}",
                index_type=index_type,
                is_meta=is_meta,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
        
        # Insert performance metrics
        print(f"💾 Inserting {len(metrics_data)} performance metrics...")
        for i, metric_dict in enumerate(metrics_data):
            metric = PerformanceMetric(
                model_id=model.id,
                date=metric_dict['date'],
                base_value=metric_dict['base_value'],
                signal=metric_dict['signal'],
                traded_value=metric_dict['traded_value'],
            )
            session.add(metric)
            
            if (i + 1) % 1000 == 0:
                print(f"   Progress: {i + 1}/{len(metrics_data)}")
        
        await session.commit()
        print(f"✅ Inserted {len(metrics_data)} metrics")
        
        # Insert portfolio snapshots and holdings
        if holdings_data:
            print(f"💾 Inserting {len(holdings_data)} portfolio snapshots...")
            
            # Sort snapshots by date to process chronologically
            holdings_data_sorted = sorted(holdings_data, key=lambda x: x['date'])
            
            # Build a cache of model name -> model ID for meta-models
            model_id_cache = {}
            if model.is_meta:
                print("   Building sub-model ID cache for meta-model...")
                # Get all potential sub-models
                all_models_result = await session.execute(select(TradingModel))
                all_models = all_models_result.scalars().all()
                for m in all_models:
                    model_id_cache[m.name] = m.id
                print(f"   Cached {len(model_id_cache)} model IDs")
            
            # Track previous holdings to determine actual purchase dates
            previous_holdings = {}  # {(ticker, purchase_price): buy_date}
            
            for i, snapshot_dict in enumerate(holdings_data_sorted):
                # Determine active sub-model ID for this specific snapshot
                snapshot_active_sub_model_id = None
                if model.is_meta and 'active_model' in snapshot_dict:
                    active_model_name = snapshot_dict['active_model']
                    snapshot_active_sub_model_id = model_id_cache.get(active_model_name)
                    if not snapshot_active_sub_model_id:
                        print(f"   ⚠️  Warning: Active model '{active_model_name}' not found for snapshot {snapshot_dict['date']}")
                
                snapshot = PortfolioSnapshot(
                    model_id=model.id,
                    date=snapshot_dict['date'],
                    total_value=snapshot_dict['total_value'],
                    active_sub_model_id=snapshot_active_sub_model_id,
                )
                session.add(snapshot)
                await session.flush()  # Get snapshot.id
                
                current_holdings_set = {}  # For tracking this month's holdings
                
                # Add holdings with corrected buy_date
                for holding_dict in snapshot_dict['holdings']:
                    ticker = holding_dict['ticker']
                    purchase_price = holding_dict['purchase_price']
                    shares = holding_dict['shares']
                    
                    # Check if this holding existed in previous month with same purchase price
                    holding_key = (ticker, purchase_price)
                    
                    if holding_key in previous_holdings:
                        # This holding existed before - use the original buy_date
                        buy_date = previous_holdings[holding_key]
                    else:
                        # New holding - use current snapshot date as buy_date
                        buy_date = snapshot_dict['date']
                    
                    holding = PortfolioHolding(
                        snapshot_id=snapshot.id,
                        ticker=ticker,
                        shares=shares,
                        purchase_price=purchase_price,
                        current_price=holding_dict.get('current_price', purchase_price),
                        weight=holding_dict['weight'],
                        rank=holding_dict.get('rank'),
                        buy_date=buy_date,
                    )
                    session.add(holding)
                    
                    # Track for next iteration
                    current_holdings_set[holding_key] = buy_date
                
                # Update previous_holdings for next iteration
                previous_holdings = current_holdings_set
                
                if (i + 1) % 50 == 0:
                    print(f"   Progress: {i + 1}/{len(holdings_data_sorted)}")
            
            await session.commit()
            print(f"✅ Inserted {len(holdings_data)} snapshots with corrected purchase dates")
        
        print(f"✅ Successfully ingested model: {model_name}")
        return True


async def ingest_backtest_data(
    data_dir: Path,
    model_name: str,
):
    """Ingest backtest data for a trading model from pyTAAAweb_backtestPortfolioValue.params.
    
    Args:
        data_dir: Path to data directory (e.g., /Users/donaldpg/pyTAAA_data/naz100_pine)
        model_name: Name of the model to associate backtest data with
    """
    # Use localhost for CLI (not Docker internal 'db')
    settings = Settings(POSTGRES_SERVER="localhost")
    database_url = settings.get_database_url()
    engine = create_async_engine(database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    # Locate backtest file (in data_store subdirectory)
    data_store = data_dir / "data_store"
    if not data_store.exists():
        data_store = data_dir  # Fallback to data_dir itself
    
    backtest_file = data_store / "pyTAAAweb_backtestPortfolioValue.params"
    
    if not backtest_file.exists():
        print(f"❌ Backtest file not found: {backtest_file}")
        return False
    
    print(f"📂 Ingesting backtest data for model: {model_name}")
    print(f"   Data file: {backtest_file}")
    
    # Parse backtest file
    print("📊 Parsing backtest file...")
    backtest_data = parse_backtest_file(backtest_file)
    print(f"   Found {len(backtest_data)} backtest data points")
    
    # Create database session
    async with async_session() as session:
        # Get trading model
        result = await session.execute(
            select(TradingModel).where(TradingModel.name == model_name)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            print(f"❌ Model '{model_name}' not found. Please ingest model data first.")
            return False
        
        print(f"✅ Found model '{model_name}' (ID: {model.id})")
        
        # Check if backtest data already exists
        existing_result = await session.execute(
            select(BacktestData).where(BacktestData.model_id == model.id).limit(1)
        )
        if existing_result.scalar_one_or_none():
            overwrite = input("   Backtest data already exists. Overwrite? [y/N]: ")
            if overwrite.lower() != 'y':
                print("❌ Ingestion cancelled")
                return False
            
            # Delete existing backtest data
            print("🗑️  Deleting existing backtest data...")
            from sqlalchemy import delete
            await session.execute(
                delete(BacktestData).where(BacktestData.model_id == model.id)
            )
            await session.commit()
        
        # Insert backtest data
        print(f"💾 Inserting {len(backtest_data)} backtest data points...")
        for i, data_dict in enumerate(backtest_data):
            backtest_record = BacktestData(
                model_id=model.id,
                date=data_dict['date'],
                buy_hold_value=data_dict['buy_hold_value'],
                traded_value=data_dict['traded_value'],
                new_highs=data_dict['new_highs'],
                new_lows=data_dict['new_lows'],
                selected_model=data_dict.get('selected_model'),  # Optional: only for abacus
            )
            session.add(backtest_record)
            
            if (i + 1) % 1000 == 0:
                print(f"   Progress: {i + 1}/{len(backtest_data)}")
        
        await session.commit()
        print(f"✅ Successfully inserted {len(backtest_data)} backtest data points")
        return True


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest PyTAAA trading model data into database"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to model data directory (e.g., /Users/donaldpg/pyTAAA_data/naz100_pine)",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Model name (e.g., naz100_pine)",
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Ingest backtest data only (pyTAAAweb_backtestPortfolioValue.params)",
    )
    parser.add_argument(
        "--index",
        type=str,
        choices=["NASDAQ_100", "SP_500"],
        default="NASDAQ_100",
        help="Index type (default: NASDAQ_100) - ignored for backtest-only",
    )
    parser.add_argument(
        "--description",
        type=str,
        help="Model description - ignored for backtest-only",
    )
    parser.add_argument(
        "--meta",
        action="store_true",
        help="Mark as meta-model - ignored for backtest-only",
    )
    
    args = parser.parse_args()
    
    # Validate data directory
    if not args.data_dir.exists():
        print(f"❌ Data directory not found: {args.data_dir}")
        sys.exit(1)
    
    # Run appropriate ingestion
    if args.backtest:
        success = asyncio.run(ingest_backtest_data(
            data_dir=args.data_dir,
            model_name=args.model,
        ))
    else:
        success = asyncio.run(ingest_model(
            data_dir=args.data_dir,
            model_name=args.model,
            index_type=args.index,
            description=args.description,
            is_meta=args.meta,
        ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
