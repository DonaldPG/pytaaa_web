from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(settings.get_database_url(), echo=settings.SQL_ECHO)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# Export async_session for use in health checks and other non-route contexts
async_session = SessionLocal

async def get_db():
    async with SessionLocal() as session:
        yield session
