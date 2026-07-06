import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy import UUID

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "TEXT"

@compiles(INET, "sqlite")
def compile_inet_sqlite(element, compiler, **kw):
    return "VARCHAR(50)"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"

logger = logging.getLogger("truvia.data.postgres")

# Check if we should fallback to SQLite (e.g. if postgres is not reachable)
db_url = settings.DATABASE_URL
is_sqlite = False

if "localhost" in db_url or "127.0.0.1" in db_url:
    import socket
    try:
        # Quick socket check on port 5432
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(("127.0.0.1", 5432))
        s.close()
        logger.info("Authoritative PostgreSQL instance detected on port 5432.")
    except Exception:
        logger.warning("Local PostgreSQL on port 5432 is unreachable. Falling back to SQLite file database.")
        db_url = "sqlite+aiosqlite:///./truvia.db"
        is_sqlite = True

# Create async engine with dialect-specific options
if is_sqlite:
    engine = create_async_engine(
        db_url,
        echo=False
    )
else:
    engine = create_async_engine(
        db_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    """
    Dependency to get DB session in FastAPI endpoints.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

async def check_and_create_tables():
    """
    Auto-bootstrapping utility for SQLite fallback during hackathon runs.
    """
    if is_sqlite:
        async with engine.begin() as conn:
            # Importing models here registers them on Base.metadata
            import app.models
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Verified and bootstrapped SQLite database tables successfully.")
