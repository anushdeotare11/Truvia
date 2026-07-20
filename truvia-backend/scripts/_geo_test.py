"""Module 6 Geospatial Intelligence — Section 9 checklist test.

HTTP checks against the live server + a controlled, rolled-back before/after
trend verification (inserts synthetic rows in a transaction, asserts, then
ROLLS BACK — nothing persists to the shared DB).
"""
import asyncio
import sys
import uuid
import logging

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

import httpx
from sqlalchemy import select, text

from app.core.security import create_access_token
from app.data.postgres_client import AsyncSessionLocal
from app.data.postgres_client import engine as _engine
_engine.echo = False
from app.models.user import User
from app.services import geo_intel

BASE = "http://127.0.0.1:8000/api/v1"


async def http_checks():
    async with AsyncSessionLocal() as db:
        officer = (await db.execute(select(User).where(User.role == "officer"))).scalars().first()
        citizen = (await db.execute(select(User).where(User.role == "citizen"))).scalars().first()
    otok = create_access_token(subject=str(officer.id), role="officer")
    oh = {"Authorization": f"Bearer {otok}"}
    ok = True

    async with httpx.AsyncClient(timeout=30) as c:
        # Guard: no token -> 401; citizen -> 403
        r = await c.get(f"{BASE}/geo/priority")
        print(f"[guard no-token] {r.status_code} (expect 401)")
        ok = ok and r.status_code == 401
        if citizen:
            ct = create_access_token(subject=str(citizen.id), role="citizen")
            r = await c.get(f"{BASE}/geo/priority", headers={"Authorization": f"Bearer {ct}"})
            print(f"[guard citizen] {r.status_code} (expect 403)")
            ok = ok and r.status_code == 403

        # Ranking
        r = await c.get(f"{BASE}/geo/priority?days=30", headers=oh)
        ok = ok and r.status_code == 200
        ranking = r.json()
        scores = [row["priority_score"] for row in ranking]
        print(f"[ranking] {r.status_code} cities={len(ranking)} distinct_scores={sorted(set(scores), reverse=True)}")
        # Section 9.1: scores differ across cities
        differ = len(set(scores)) > 1
        # Section 9.2: weighting != pure count — a lower-count city outranks a higher-count one
        by_rank = ranking  # already sorted desc by score
        weighting_effect = any(
            by_rank[i]["complaint_count"] < by_rank[j]["complaint_count"]
            for i in range(len(by_rank)) for j in range(i + 1, len(by_rank))
        )
        print(f"  scores_differ={differ}  weighting_beats_count={weighting_effect}")
        # each row carries the full breakdown
        keys_ok = all(
            k in ranking[0]
            for k in ("city", "priority_score", "complaint_count", "avg_severity_weight", "recency_weight", "trend", "dominant_category")
        ) if ranking else False
        print(f"  breakdown_keys_present={keys_ok}")
        ok = ok and differ and weighting_effect and keys_ok

        # Trend endpoint for top city
        top = ranking[0]["city"]
        r = await c.get(f"{BASE}/geo/priority/{top}/trend?weeks=8", headers=oh)
        tb = r.json()
        print(f"[trend {top}] {r.status_code} label={tb['trend']} series_weeks={len(tb['series'])}")
        ok = ok and r.status_code == 200 and "series" in tb

        # Section 9.5: a genuinely zero-complaint city doesn't break ranking/trend
        r = await c.get(f"{BASE}/geo/priority/NoSuchCity/trend?weeks=8", headers=oh)
        zb = r.json()
        zero_ok = r.status_code == 200 and zb["series"] == [] and zb["trend"] == "stable"
        print(f"[zero-city trend] {r.status_code} series={zb['series']} trend={zb['trend']} -> ok={zero_ok}")
        ok = ok and zero_ok

    return ok


async def rollback_trend_check():
    """Section 9.3: deliberate before/after data change, verified then rolled back."""
    print("\n[before/after trend check — transaction, rolled back]")
    ok = True
    async with AsyncSessionLocal() as db:
        citizen = (await db.execute(select(User).where(User.role == "citizen"))).scalars().first()
        uid = citizen.id
        test_city = f"ZZTEST_{uuid.uuid4().hex[:6]}"

        async def insert_report(days_ago: int):
            rid = uuid.uuid4()
            await db.execute(text(
                "INSERT INTO reports (id, user_id, source_type, raw_input_ref, city, status, created_at, updated_at) "
                "VALUES (:id, :uid, 'text', 'test', :city, 'scored', now() - make_interval(days => :d), now())"
            ), {"id": rid, "uid": uid, "city": test_city, "d": days_ago})
            await db.execute(text(
                "INSERT INTO threat_scores (id, report_id, threat_score, severity_band, scam_category, confidence_score, reasoning_json, degraded_mode, model_version, is_current, created_at) "
                "VALUES (:id, :rid, 80, 'high', 'UPI Refund Scam', 0.9, '{}'::jsonb, false, 'test', true, now())"
            ), {"id": uuid.uuid4(), "rid": rid})

        # RISING: 2 in prior 7 days, 6 in recent 7 days
        for _ in range(2):
            await insert_report(days_ago=10)   # prior window (8-14 days ago)
        for _ in range(6):
            await insert_report(days_ago=2)    # recent window (0-7 days ago)
        rising = await geo_intel.get_city_trend(db, test_city, weeks=1)
        print(f"  rising case: cur={rising['current_window_count']} prev={rising['prior_window_count']} -> {rising['trend']} (expect rising)")
        ok = ok and rising["trend"] == "rising"

        await db.rollback()  # discard synthetic rows

        # FALLING: 8 in prior window, 1 in recent window
        for _ in range(8):
            await insert_report(days_ago=10)
        for _ in range(1):
            await insert_report(days_ago=2)
        falling = await geo_intel.get_city_trend(db, test_city, weeks=1)
        print(f"  falling case: cur={falling['current_window_count']} prev={falling['prior_window_count']} -> {falling['trend']} (expect falling)")
        ok = ok and falling["trend"] == "falling"

        await db.rollback()  # discard synthetic rows

    # unit checks on the threshold classifier
    assert geo_intel._classify_trend(100, 100) == "stable"
    assert geo_intel._classify_trend(120, 100) == "rising"   # +20% > 15%
    assert geo_intel._classify_trend(80, 100) == "falling"   # -20% > 15%
    assert geo_intel._classify_trend(110, 100) == "stable"   # +10% < 15%
    assert geo_intel._classify_trend(5, 0) == "rising"
    print("  threshold classifier unit checks passed (stable/rising/falling/prev=0)")
    return ok


async def main() -> int:
    ok1 = await http_checks()
    ok2 = await rollback_trend_check()
    # confirm rollback left nothing behind
    async with AsyncSessionLocal() as db:
        leftover = (await db.execute(text("SELECT count(*) FROM reports WHERE city LIKE 'ZZTEST_%'"))).scalar()
    print(f"\nleftover synthetic rows after rollback: {leftover} (expect 0)")
    ok = ok1 and ok2 and leftover == 0
    print("\nGEO_TEST_OK" if ok else "\nGEO_TEST_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(asyncio.wait_for(main(), timeout=120)))
    except asyncio.TimeoutError:
        print("TIMEOUT", file=sys.stderr)
        sys.exit(2)
