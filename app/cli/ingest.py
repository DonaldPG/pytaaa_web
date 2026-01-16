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
from app.models.trading import TradingModel, PortfolioSnapshot, PortfolioHolding, PerformanceMetric
from app.parsers.status_parser import parse_status_file
from app.parsers.holdings_parser import parse_holdings_file
from app.parsers.ranks_parser import parse_ranks_file


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
            
            # Delete existing data
            print("🗑️  Deleting existing snapshots and metrics...")
            for snapshot in model.snapshots:
                await session.delete(snapshot)
            for metric in model.metrics:
                await session.delete(metric)
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
            for i, snapshot_dict in enumerate(holdings_data):
                snapshot = PortfolioSnapshot(
                    model_id=model.id,
                    date=snapshot_dict['date'],
                    total_value=snapshot_dict['total_value'],
                )
                session.add(snapshot)
                await session.flush()  # Get snapshot.id
                
                # Add holdings
                for holding_dict in snapshot_dict['holdings']:
                    holding = PortfolioHolding(
                        snapshot_id=snapshot.id,
                        ticker=holding_dict['ticker'],
                        shares=holding_dict['shares'],
                        purchase_price=holding_dict['purchase_price'],
                        current_price=holding_dict['current_price'],
                        weight=holding_dict['weight'],
                        rank=holding_dict['rank'],
                        buy_date=holding_dict['buy_date'],
                    )
                    session.add(holding)
                
                if (i + 1) % 100 == 0:
                    print(f"   Progress: {i + 1}/{len(holdings_data)}")
            
            await session.commit()
            print(f"✅ Inserted {len(holdings_data)} snapshots")
        
        print(f"✅ Successfully ingested model: {model_name}")
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
        "--index",
        type=str,
        choices=["NASDAQ_100", "SP_500"],
        default="NASDAQ_100",
        help="Index type (default: NASDAQ_100)",
    )
    parser.add_argument(
        "--description",
        type=str,
        help="Model description",
    )
    parser.add_argument(
        "--meta",
        action="store_true",
        help="Mark as meta-model",
    )
    
    args = parser.parse_args()
    
    # Validate data directory
    if not args.data_dir.exists():
        print(f"❌ Data directory not found: {args.data_dir}")
        sys.exit(1)
    
    # Run async ingestion
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
