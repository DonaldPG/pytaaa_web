"""Test database session management and connection handling."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_db_connection(db_session: AsyncSession):
    """Test that database connection is established and queries work."""
    result = await db_session.execute(text("SELECT 1 as value"))
    row = result.fetchone()
    assert row[0] == 1


@pytest.mark.asyncio
async def test_db_session_isolation(db_session: AsyncSession):
    """Test that database sessions are isolated between tests."""
    # This test should start with a clean database due to fixture scope
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM trading_models")
    )
    count = result.scalar()
    assert count == 0, "Database should be empty at test start"


@pytest.mark.asyncio
async def test_db_session_rollback(db_session: AsyncSession):
    """Test that sessions properly rollback uncommitted changes."""
    # Insert a record but don't commit
    await db_session.execute(
        text("INSERT INTO trading_models (id, name, description, index_type, is_meta) VALUES (gen_random_uuid(), 'test', 'test', 'NASDAQ_100', false)")
    )
    await db_session.rollback()
    
    # Verify the record was not persisted
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM trading_models")
    )
    count = result.scalar()
    assert count == 0, "Rolled back transaction should not persist data"


@pytest.mark.asyncio
async def test_multiple_queries(db_session: AsyncSession):
    """Test that multiple queries work in the same session."""
    queries = [
        "SELECT COUNT(*) FROM trading_models",
        "SELECT COUNT(*) FROM portfolio_snapshots",
        "SELECT COUNT(*) FROM portfolio_holdings",
        "SELECT COUNT(*) FROM performance_metrics",
    ]
    
    for query in queries:
        result = await db_session.execute(text(query))
        count = result.scalar()
        assert count == 0, f"Table should be empty: {query}"
