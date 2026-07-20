"""Module 6: Geospatial Crime Pattern Intelligence — API (Spec §5).

Two officer/admin-only endpoints over the existing complaint data:
  * GET /api/v1/geo/priority?category=&days=     — ranked city priority list
  * GET /api/v1/geo/priority/{city}/trend?weeks=  — weekly trend for one city

Pure SQL aggregation (app/services/geo_intel.py); no new tables, no LLM.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.data.postgres_client import get_db
from app.models.user import User
from app.services import geo_intel

logger = logging.getLogger("truvia.api.geo")
router = APIRouter()


@router.get("/priority")
async def geo_priority(
    category: Optional[str] = Query(None, description="Optional scam-category filter"),
    days: int = Query(30, ge=1, le=365, description="Look-back window in days (default 30)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_officer),
):
    """Ranked city priority list with full score breakdown (Spec §5/§6)."""
    return await geo_intel.get_priority_ranking(db, category=category, days=days)


@router.get("/priority/{city}/trend")
async def geo_city_trend(
    city: str,
    weeks: int = Query(8, ge=1, le=52, description="Number of recent weeks (default 8)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_officer),
):
    """Weekly complaint volume + avg severity for one city, with a trend label
    (rising/falling/stable) comparing the recent window to the prior one."""
    return await geo_intel.get_city_trend(db, city=city, weeks=weeks)
