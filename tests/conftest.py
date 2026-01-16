"""Pytest configuration and shared fixtures."""
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.db.session import get_db
from app.main import app
from app.models.base import Base
# Import all models so Base.metadata knows about them
from app.models.trading import TradingModel, PortfolioSnapshot, PortfolioHolding, PerformanceMetric

# Test database URL (override production database)
TEST_DATABASE_URL = "postgresql+asyncpg://pytaaa_user:pytaaa_pass@localhost:5432/pytaaa_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine with NullPool for test isolation."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,  # Avoid connection reuse between tests
        echo=False,  # Disable SQL logging
    )
    
    # Create all tables synchronously before yielding
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Clean slate
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup: drop all tables after test completes
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def override_get_db(db_session: AsyncSession):
    """Override the get_db dependency to use test database."""
    async def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()
