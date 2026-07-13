import pytest
import asyncio
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.data.postgres_client import Base
import app.models  # Register all models on Base.metadata

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Creates an in-memory SQLite async engine and bootstraps all tables.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def override_db(test_engine):
    """
    Auto-monkeypatches AsyncSessionLocal in postgres_client and agent modules
    to bind to the test_engine in-memory SQLite database, ensuring test isolation.
    """
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    import app.data.postgres_client
    app.data.postgres_client.AsyncSessionLocal = TestSessionLocal
    
    import app.agents.input_processor
    import app.agents.threat_evaluator
    import app.agents.entity_extractor
    import app.agents.threat_intel
    import app.agents.investigation
    
    app.agents.input_processor.AsyncSessionLocal = TestSessionLocal
    app.agents.threat_evaluator.AsyncSessionLocal = TestSessionLocal
    app.agents.entity_extractor.AsyncSessionLocal = TestSessionLocal
    app.agents.threat_intel.AsyncSessionLocal = TestSessionLocal
    app.agents.investigation.AsyncSessionLocal = TestSessionLocal
    
    # Overwrite storage_client.get_file to return dummy text bytes for test evidence processing
    async def mock_get_file(file_ref: str) -> bytes:
        return b"mock text from evidence file containing scam indicators like UPI collect request and QR code scan."
        
    app.agents.input_processor.storage_client.get_file = mock_get_file
    
    yield

@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    Yields an isolated async session for database queries, rolling back at the end of each test.
    """
    AsyncSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
