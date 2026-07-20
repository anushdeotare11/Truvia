"""Module 6: Geospatial Crime Pattern Intelligence — aggregation layer (Spec §5/§6).

Pure SQL aggregation over existing tables (reports.city, reports.created_at,
threat_scores.severity_band/scam_category/is_current). No new tables, no LLM.

Priority score per city (Spec §6):
    priority_score_raw = complaint_density * avg_severity_weight * recency_factor
then normalized to 0-100 across the current result set. The three input
components are returned alongside the final score so the ranking is fully
explainable ("never just declare, always explain").

  * complaint_density  = count of complaints in the window (default 30 days)
  * avg_severity_weight = avg of severity mapped low=1, moderate=2, high=3, critical=4
  * recency_factor      = avg per-complaint half-life decay 0.5^(age_days / half_life),
                          half_life = days/2 (a complaint today counts ~1.0, older counts less)

Trend (Spec §6.5): compare this window's count to the equivalent prior window;
"rising" if up >15%, "falling" if down >15%, else "stable".
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("truvia.services.geo_intel")

RISING_FALLING_THRESHOLD = 0.15  # ±15% (Spec §6.5)

# Numeric severity weights (Spec §6.2) — reuses existing threat_scores bands.
_SEVERITY_CASE = (
    "CASE ts.severity_band "
    "WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'moderate' THEN 2 ELSE 1 END"
)


def _classify_trend(current: int, prior: int) -> str:
    """Rising/falling/stable from current vs prior window count (±15%)."""
    if prior == 0:
        return "rising" if current > 0 else "stable"
    change = (current - prior) / prior
    if change > RISING_FALLING_THRESHOLD:
        return "rising"
    if change < -RISING_FALLING_THRESHOLD:
        return "falling"
    return "stable"


async def get_priority_ranking(
    db: AsyncSession, category: str | None = None, days: int = 30
) -> list[dict]:
    """Ranked city priority list with score breakdown (Spec §5/§6)."""
    days = max(1, int(days))
    half_life = days / 2.0
    cat_filter = "AND ts.scam_category = :category" if category else ""

    # Current window aggregates per city.
    windowed_sql = f"""
        SELECT r.city AS city,
               count(*) AS complaint_count,
               avg({_SEVERITY_CASE})::float AS avg_severity_weight,
               avg(power(0.5, (EXTRACT(EPOCH FROM (now() - r.created_at)) / 86400.0) / :half_life))::float
                   AS recency_weight,
               mode() WITHIN GROUP (ORDER BY ts.scam_category) AS dominant_category
        FROM reports r
        JOIN threat_scores ts ON ts.report_id = r.id AND ts.is_current = true
        WHERE r.city IS NOT NULL AND btrim(r.city) <> ''
          AND r.created_at >= now() - make_interval(days => :days)
          {cat_filter}
        GROUP BY r.city
    """

    # Prior equivalent window (immediately before the current one) for trend.
    prior_sql = f"""
        SELECT r.city AS city, count(*) AS prev_count
        FROM reports r
        JOIN threat_scores ts ON ts.report_id = r.id AND ts.is_current = true
        WHERE r.city IS NOT NULL AND btrim(r.city) <> ''
          AND r.created_at >= now() - make_interval(days => :days2)
          AND r.created_at <  now() - make_interval(days => :days)
          {cat_filter}
        GROUP BY r.city
    """

    params = {"days": days, "days2": days * 2, "half_life": half_life}
    if category:
        params["category"] = category

    windowed = (await db.execute(text(windowed_sql), params)).mappings().all()
    prior = (await db.execute(text(prior_sql), params)).mappings().all()
    prior_counts = {row["city"]: row["prev_count"] for row in prior}

    # Raw score + normalization to 0-100 across the current result set.
    rows = []
    for w in windowed:
        raw = (
            float(w["complaint_count"])
            * float(w["avg_severity_weight"])
            * float(w["recency_weight"])
        )
        rows.append({**dict(w), "raw_score": raw})

    max_raw = max((r["raw_score"] for r in rows), default=0.0)

    result = []
    for r in rows:
        priority_score = round(100.0 * r["raw_score"] / max_raw) if max_raw > 0 else 0
        prev_count = int(prior_counts.get(r["city"], 0))
        result.append({
            "city": r["city"],
            "priority_score": priority_score,
            "complaint_count": int(r["complaint_count"]),
            "avg_severity_weight": round(float(r["avg_severity_weight"]), 3),
            "recency_weight": round(float(r["recency_weight"]), 3),
            "prior_window_count": prev_count,
            "trend": _classify_trend(int(r["complaint_count"]), prev_count),
            "dominant_category": r["dominant_category"],
        })

    # Rank by priority score (desc), then by raw complaint count as a tiebreak.
    result.sort(key=lambda x: (x["priority_score"], x["complaint_count"]), reverse=True)
    return result


async def get_city_trend(db: AsyncSession, city: str, weeks: int = 8) -> dict:
    """Weekly complaint volume + avg severity for one city, plus a trend label
    comparing the most recent `weeks` window to the prior `weeks` window."""
    weeks = max(1, int(weeks))

    series_sql = f"""
        SELECT date_trunc('week', r.created_at) AS week_start,
               count(*) AS complaint_count,
               avg({_SEVERITY_CASE})::float AS avg_severity
        FROM reports r
        JOIN threat_scores ts ON ts.report_id = r.id AND ts.is_current = true
        WHERE r.city = :city
          AND r.created_at >= now() - make_interval(weeks => :weeks)
        GROUP BY 1
        ORDER BY 1
    """
    rows = (await db.execute(text(series_sql), {"city": city, "weeks": weeks})).mappings().all()
    series = [
        {
            "week_start": row["week_start"].date().isoformat() if row["week_start"] else None,
            "complaint_count": int(row["complaint_count"]),
            "avg_severity": round(float(row["avg_severity"]), 3),
        }
        for row in rows
    ]

    # Trend: recent `weeks` window vs prior `weeks` window (±15%, Spec §6.5).
    window_sql = """
        SELECT
          count(*) FILTER (WHERE r.created_at >= now() - make_interval(weeks => :weeks)) AS cur,
          count(*) FILTER (
              WHERE r.created_at >= now() - make_interval(weeks => :weeks2)
                AND r.created_at <  now() - make_interval(weeks => :weeks)
          ) AS prev
        FROM reports r
        JOIN threat_scores ts ON ts.report_id = r.id AND ts.is_current = true
        WHERE r.city = :city
    """
    wr = (await db.execute(text(window_sql), {"city": city, "weeks": weeks, "weeks2": weeks * 2})).mappings().one()
    trend = _classify_trend(int(wr["cur"]), int(wr["prev"]))

    return {
        "city": city,
        "weeks": weeks,
        "series": series,
        "current_window_count": int(wr["cur"]),
        "prior_window_count": int(wr["prev"]),
        "trend": trend,
    }
