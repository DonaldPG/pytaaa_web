"""Database session management for CLI commands.

This module provides a factory function for creating database sessions
in CLI contexts where dependency injection is not available.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import Settings


def create_cli_session(server: str = "localhost") -> tuple[AsyncSession, str]:
    """Create a database session for CLI usage.
    
    Args:
        server: PostgreSQL server hostname (default: localhost for CLI,
                use "db" for Docker internal networking)
    
    Returns:
        Tuple of (async_session, database_url) where async_session is a
        sessionmaker that can be used in an async context manager.
    
    Example:
        >>> session, url = create_cli_session()
        >>> async with session() as db:
        ...     result = await db.execute(select(TradingModel))
    """
    settings = Settings(POSTGRES_SERVER=server)
    database_url = settings.get_database_url()
    engine = create_async_engine(database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    return async_session, database_url
