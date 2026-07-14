from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.data.postgres_client import get_db
from app.api import deps
from app.models.report import Report, ThreatScore
from app.models.alert import Alert
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

router = APIRouter()
logger = logging.getLogger("truvia.api.alerts")

@router.get("/predictive", status_code=status.HTTP_200_OK)
async def get_predictive_alerts(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.require_officer)
):
    """
    Analyzes real complaint velocity per scam category by comparing the last 7 days
    against the prior 7 days, and flags categories that are trending. All numbers are
    computed from stored data — no hardcoded/seeded fallback.
    """
    try:
        now = datetime.now()
        cur_start = now - timedelta(days=7)
        prev_start = now - timedelta(days=14)

        async def counts_between(start, end):
            q = (
                select(ThreatScore.scam_category, func.count(ThreatScore.id))
                .join(Report, Report.id == ThreatScore.report_id)
                .where(and_(Report.created_at >= start, Report.created_at < end))
                .group_by(ThreatScore.scam_category)
            )
            rows = await db.execute(q)
            return {cat: int(cnt) for cat, cnt in rows.all() if cat}

        current = await counts_between(cur_start, now)
        prior = await counts_between(prev_start, cur_start)

        alerts = []
        for category, cur_count in current.items():
            prev_count = prior.get(category, 0)
            # Real week-over-week change. New-this-week categories count as a full surge.
            if prev_count == 0:
                trend_pct = 100 if cur_count > 0 else 0
            else:
                trend_pct = int(round((cur_count - prev_count) / prev_count * 100))

            # Only surface categories with meaningful current volume (real signal).
            if cur_count < 3:
                continue

            # Severity derived from real current volume, not a fixed label.
            if cur_count >= 25:
                severity = "critical"
            elif cur_count >= 12:
                severity = "high"
            else:
                severity = "moderate"

            direction = "up" if trend_pct > 0 else ("down" if trend_pct < 0 else "flat")
            alerts.append({
                "title": f"Velocity Surge: {category}",
                "severity": severity,
                "description": (
                    f"{cur_count} {category} report(s) in the last 7 days "
                    f"vs {prev_count} in the prior 7 days "
                    f"({'+' if trend_pct >= 0 else ''}{trend_pct}% {direction})."
                ),
                "velocity_metric": {
                    "count_14d": cur_count + prev_count,
                    "trend_percentage": trend_pct,
                },
            })

        # Highest current volume / most severe first. Empty list is a valid, honest state
        # (the dashboard renders "No predictive signals today").
        alerts.sort(key=lambda a: (a["velocity_metric"]["count_14d"], a["velocity_metric"]["trend_percentage"]), reverse=True)
        return alerts
    except Exception as e:
        logger.error(f"Failed to calculate predictive alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Velocity calculation failed")

@router.get("/public", status_code=status.HTTP_200_OK)
async def get_public_safety_warnings(
    category: Optional[str] = None,
    limit: int = 12,
    db: AsyncSession = Depends(get_db)
):
    """
    Anonymized, trending public scam-pattern feed for citizens (§5.5).
    Computed from REAL stored data: groups the last 7 days of scored reports by
    scam category and ranks them by a recency-weighted velocity (recent reports
    count more). Exposes ONLY aggregate category/count/trend — never entity- or
    complaint-level detail (privacy intent, PRD §8.1). Returns [] (→ genuine
    "No trending alerts right now" empty state) when there is no recent data.
    """
    try:
        now = datetime.now()
        cur_start = now - timedelta(days=7)
        prev_start = now - timedelta(days=14)

        # Pull last 14 days of (category, created_at) once; weight in Python.
        rows = await db.execute(
            select(ThreatScore.scam_category, Report.created_at, ThreatScore.severity_band)
            .join(Report, Report.id == ThreatScore.report_id)
            .where(and_(Report.created_at >= prev_start, ThreatScore.is_current == True))
        )
        cur_counts: Dict[str, float] = {}
        cur_raw: Dict[str, int] = {}
        prev_raw: Dict[str, int] = {}
        worst_band: Dict[str, str] = {}
        band_rank = {"low": 0, "moderate": 1, "high": 2, "critical": 3}

        for cat, created_at, band in rows.all():
            if not cat:
                continue
            if category and cat.lower() != category.lower():
                continue
            if created_at is None:
                continue
            # Normalize possibly-naive/aware datetimes for comparison.
            ts = created_at.replace(tzinfo=None) if getattr(created_at, "tzinfo", None) else created_at
            if ts >= cur_start.replace(tzinfo=None):
                # Recency weight: newer reports (closer to now) weigh up to ~2x.
                age_days = max(0.0, (now.replace(tzinfo=None) - ts).total_seconds() / 86400.0)
                weight = 1.0 + max(0.0, (7.0 - age_days) / 7.0)
                cur_counts[cat] = cur_counts.get(cat, 0.0) + weight
                cur_raw[cat] = cur_raw.get(cat, 0) + 1
                if band_rank.get(band, 0) >= band_rank.get(worst_band.get(cat, "low"), 0):
                    worst_band[cat] = band or "low"
            else:
                prev_raw[cat] = prev_raw.get(cat, 0) + 1

        alerts = []
        for cat, weighted in sorted(cur_counts.items(), key=lambda kv: kv[1], reverse=True):
            cur_n = cur_raw.get(cat, 0)
            prev_n = prev_raw.get(cat, 0)
            if prev_n == 0:
                trend_pct = 100 if cur_n > 0 else 0
            else:
                trend_pct = int(round((cur_n - prev_n) / prev_n * 100))
            band = worst_band.get(cat, "moderate")
            trend_word = "rising" if trend_pct > 0 else ("easing" if trend_pct < 0 else "steady")
            alerts.append({
                "id": f"trend-{cat.lower().replace(' ', '-').replace('/', '-')}",
                "title": f"Trending: {cat}",
                "description": (
                    f"{cur_n} report(s) of {cat} in the last 7 days "
                    f"({'+' if trend_pct >= 0 else ''}{trend_pct}% vs prior week, {trend_word}). "
                    "Stay alert to messages matching this pattern."
                ),
                "severity": band,
                "date": now.strftime("%d %b %Y"),
            })

        return alerts[:limit]
    except Exception as e:
        logger.error(f"Failed to compute public alerts: {str(e)}")
        # Non-critical page: fail soft to an empty feed rather than erroring.
        return []
