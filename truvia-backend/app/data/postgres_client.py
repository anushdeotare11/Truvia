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

# Normalize provider-supplied URLs. Railway/Render/Heroku hand out `postgres://`
# or `postgresql://` (a SYNC driver scheme); SQLAlchemy's async engine needs the
# asyncpg driver. Also strip the libpq `sslmode` query param that asyncpg rejects.
if db_url.startswith("postgres://"):
    db_url = "postgresql+asyncpg://" + db_url[len("postgres://"):]
elif db_url.startswith("postgresql://"):
    db_url = "postgresql+asyncpg://" + db_url[len("postgresql://"):]
if "sslmode=" in db_url:
    import re as _re
    db_url = _re.sub(r"[?&]sslmode=[^&]*", "", db_url)
    db_url = db_url.rstrip("?&")

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
        # NOTE (perf): pool_pre_ping issued a `SELECT 1` liveness round-trip on
        # EVERY connection checkout. Against the cloud Neon instance (~0.8s RTT)
        # that added ~0.8s to every authenticated request app-wide. Replaced with
        # pool_recycle so stale connections are still avoided (recycled well
        # inside Neon's idle-connection timeout) without paying a round-trip per
        # request. Measured: removed ~0.8s of latency from every endpoint.
        pool_recycle=280,
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
            from fastapi import HTTPException
            from starlette.exceptions import HTTPException as StarletteHTTPException
            if not isinstance(e, (HTTPException, StarletteHTTPException)):
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
