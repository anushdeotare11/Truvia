"""Section 9.3: deliberate before/after trend change, verified then ROLLED BACK.
Lightweight (few inserts) so it fits comfortably in one command window."""
import asyncio
import sys
import uuid
import logging

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
from sqlalchemy import select, text
from app.data.postgres_client import AsyncSessionLocal, engine as _engine
_engine.echo = False
from app.models.user import User
from app.services import geo_intel


async def insert_report(db, uid, city, days_ago):
    rid = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO reports (id, user_id, source_type, raw_input_ref, city, status, created_at, updated_at) "
        "VALUES (:id, :uid, 'text', 'test', :city, 'scored', now() - make_interval(days => :d), now())"
    ), {"id": rid, "uid": uid, "city": city, "d": days_ago})
    await db.execute(text(
        "INSERT INTO threat_scores (id, report_id, threat_score, severity_band, scam_category, confidence_score, reasoning_json, degraded_mode, model_version, is_current, created_at) "
        "VALUES (:id, :rid, 80, 'high', 'UPI Refund Scam', 0.9, '{}'::jsonb, false, 'test', true, now())"
    ), {"id": uuid.uuid4(), "rid": rid})


async def main() -> int:
    ok = True
    async with AsyncSessionLocal() as db:
        citizen = (await db.execute(select(User).where(User.role == "citizen"))).scalars().first()
        uid = citizen.id
        city = f"ZZTEST_{uuid.uuid4().hex[:6]}"

        # RISING: 1 prior week, 4 recent week
        await insert_report(db, uid, city, 10)
        for _ in range(4):
            await insert_report(db, uid, city, 2)
        t = await geo_intel.get_city_trend(db, city, weeks=1)
        print(f"rising  : cur={t['current_window_count']} prev={t['prior_window_count']} -> {t['trend']} (expect rising)")
        ok = ok and t["trend"] == "rising"
        await db.rollback()

        # FALLING: 5 prior week, 1 recent week
        for _ in range(5):
            await insert_report(db, uid, city, 10)
        await insert_report(db, uid, city, 2)
        t = await geo_intel.get_city_trend(db, city, weeks=1)
        print(f"falling : cur={t['current_window_count']} prev={t['prior_window_count']} -> {t['trend']} (expect falling)")
        ok = ok and t["trend"] == "falling"
        await db.rollback()

    # classifier unit checks (±15%)
    assert geo_intel._classify_trend(100, 100) == "stable"
    assert geo_intel._classify_trend(120, 100) == "rising"
    assert geo_intel._classify_trend(80, 100) == "falling"
    assert geo_intel._classify_trend(110, 100) == "stable"
    assert geo_intel._classify_trend(5, 0) == "rising"
    print("classifier: stable/rising/falling/+10%=stable/prev0=rising all OK")

    async with AsyncSessionLocal() as db:
        leftover = (await db.execute(text("SELECT count(*) FROM reports WHERE city LIKE 'ZZTEST_%'"))).scalar()
    print(f"leftover synthetic rows after rollback: {leftover} (expect 0)")
    ok = ok and leftover == 0
    print("TREND_CHECK_OK" if ok else "TREND_CHECK_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(asyncio.wait_for(main(), timeout=25)))
