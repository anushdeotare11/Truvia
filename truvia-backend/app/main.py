from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.logging import logger
from app.api.v1 import auth, reports, chat, graph, entities, cases, alerts
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

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Truvia Digital Public Safety Platform API...")
    
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
