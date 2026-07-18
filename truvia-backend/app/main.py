from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.logging import logger
from app.api.v1 import auth, reports, chat, graph, entities, cases, alerts, dashboard
from sqlalchemy import text
from app.data.postgres_client import engine
from app.data.neo4j_client import neo4j_client
import redis.asyncio as aioredis
import logging

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0"
)

# CORS setup
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports Ingestion"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["AI Chat Assistant"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["Threat Graph Engine"])
app.include_router(entities.router, prefix="/api/v1/entities", tags=["Threat Entities Ledger"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["Cyber Investigation Cases"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Predictive Threats & Alerts"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Analytics Dashboard"])

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Truvia Digital Public Safety Platform API...")

    # Surface which AI credentials/services are configured vs. degraded (honest, no fabrication).
    try:
        from app.core.config_check import log_config_check
        log_config_check()
    except Exception as e:
        logger.error(f"Config check failed: {str(e)}")

    # Start Gemini key validation in the background on startup
    try:
        from app.core.config_check import verify_gemini_key_background
        import asyncio
        asyncio.create_task(verify_gemini_key_background())
    except Exception as e:
        logger.error(f"Failed to start Gemini key validation: {e}")

    # Warm the local OCR/STT engines in the background so the first citizen upload
    # (especially audio) doesn't pay one-time model load/download latency and time out
    # the frontend's result polling. Non-blocking — startup proceeds immediately.
    try:
        import asyncio
        from app.agents.input_processor import input_processor_agent
        asyncio.create_task(input_processor_agent.warm_engines())
    except Exception as e:
        logger.error(f"Could not schedule engine warmup: {str(e)}")

    # Auto-bootstrap SQLite tables if running in SQLite fallback mode
    from app.data.postgres_client import check_and_create_tables
    try:
        await check_and_create_tables()
    except Exception as e:
        logger.error(f"Error bootstrapping local database tables: {str(e)}")

    # Initialize Neo4j Client
    try:
        neo4j_client.connect()
    except Exception as e:
        logger.error(f"Could not connect to Neo4j on startup: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Truvia Digital Public Safety Platform API...")
    # Close Neo4j client connection
    await neo4j_client.close()

# Healthcheck endpoints
@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["System Health"])
async def healthz():
    return {"status": "healthy"}

@app.get("/api/v1/config-status", status_code=status.HTTP_200_OK, tags=["System Health"])
async def config_status():
    """Report which AI capabilities are configured vs. running in degraded/local mode."""
    from app.core.config_check import get_capability_report
    report = get_capability_report()
    return {
        "capabilities": report,
        "fully_degraded": not any(
            c["configured"] and c["provider"] not in (None, "local-rule-engine", "local-grounded-answers")
            for c in report.values()
        ),
    }

@app.get("/readyz", status_code=status.HTTP_200_OK, tags=["System Health"])
async def readyz():
    errors = {}
    
    # 1. Check PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        errors["postgres"] = f"Unhealthy: {str(e)}"
        
    # 2. Check Neo4j
    try:
        if not neo4j_client.driver:
            neo4j_client.connect()
        async with neo4j_client.driver.session() as session:
            await session.run("RETURN 1")
    except Exception as e:
        errors["neo4j"] = f"Unhealthy: {str(e)}"

    # 3. Check Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
    except Exception as e:
        errors["redis"] = f"Unhealthy: {str(e)}"
        
    if errors:
        return {"status": "degraded", "checks": errors}
        
    return {"status": "ready", "checks": {"postgres": "ok", "neo4j": "ok", "redis": "ok"}}
