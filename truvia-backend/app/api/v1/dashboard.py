from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case as sql_case
from app.data.postgres_client import get_db
from app.api import deps
from app.models.report import Report, ThreatScore
import logging

router = APIRouter()
logger = logging.getLogger("truvia.api.dashboard")


@router.get("/geo-breakdown", status_code=status.HTTP_200_OK)
async def get_geo_breakdown(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """
    Returns report counts grouped by city, sorted by count descending.
    Only includes reports where city is not null.
    """
    try:
        result = await db.execute(
            select(Report.city, func.count(Report.id).label("count"))
            .where(Report.city.isnot(None))
            .group_by(Report.city)
            .order_by(func.count(Report.id).desc())
        )
        rows = result.all()
        return [{"city": city, "count": int(count)} for city, count in rows]
    except Exception as e:
        logger.error(f"Failed to fetch geo breakdown: {str(e)}")
        raise HTTPException(status_code=500, detail="Geo breakdown query failed")


@router.get("/timeline", status_code=status.HTTP_200_OK)
async def get_timeline(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """
    Returns the last 50 reports with their current threat score info,
    ordered by created_at descending.
    """
    try:
        # Join reports with their current threat score
        stmt = (
            select(
                Report.id,
                Report.source_type,
                Report.created_at,
                ThreatScore.severity_band,
                ThreatScore.scam_category,
            )
            .outerjoin(
                ThreatScore,
                (ThreatScore.report_id == Report.id) & (ThreatScore.is_current == True),
            )
            .order_by(Report.created_at.desc())
            .limit(50)
        )
        result = await db.execute(stmt)
        rows = result.all()

        return [
            {
                "id": str(report_id),
                "source_type": source_type,
                "created_at": created_at.isoformat() if created_at else None,
                "severity": severity_band,
                "scam_category": scam_category,
                "event_type": "report_submitted",
            }
            for report_id, source_type, created_at, severity_band, scam_category in rows
        ]
    except Exception as e:
        logger.error(f"Failed to fetch timeline: {str(e)}")
        raise HTTPException(status_code=500, detail="Timeline query failed")


@router.get("/score-distribution", status_code=status.HTTP_200_OK)
async def get_score_distribution(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """
    Buckets all current threat scores into 5 ranges and returns counts per range.
    Ranges: 0-19, 20-39, 40-59, 60-79, 80-100
    """
    try:
        result = await db.execute(
            select(ThreatScore.threat_score).where(ThreatScore.is_current == True)
        )
        scores = [row[0] for row in result.all()]

        # Define buckets
        buckets = [
            ("0-19", 0, 19),
            ("20-39", 20, 39),
            ("40-59", 40, 59),
            ("60-79", 60, 79),
            ("80-100", 80, 100),
        ]

        distribution = []
        for label, low, high in buckets:
            count = sum(1 for s in scores if low <= s <= high)
            distribution.append({"range": label, "count": count})

        return distribution
    except Exception as e:
        logger.error(f"Failed to fetch score distribution: {str(e)}")
        raise HTTPException(status_code=500, detail="Score distribution query failed")
