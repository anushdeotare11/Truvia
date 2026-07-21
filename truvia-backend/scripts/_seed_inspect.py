"""One-shot inspection of current DB volume + demo citizen accounts (read-only)."""
import asyncio
import sys
from sqlalchemy import select, func

from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User
from app.models.report import Report, ThreatScore, Entity, ReportEntity, Relationship
from app.models.ring import FraudRing, FraudRingMember


async def _main() -> int:
    async with AsyncSessionLocal() as db:
        async def count(model):
            return (await db.execute(select(func.count()).select_from(model))).scalar()

        print("=== Current DB volume ===")
        for name, model in [
            ("users", User), ("reports", Report), ("threat_scores", ThreatScore),
            ("entities", Entity), ("report_entities", ReportEntity),
            ("relationships", Relationship), ("fraud_rings", FraudRing),
            ("fraud_ring_members", FraudRingMember),
        ]:
            print(f"  {name:20s} {await count(model)}")

        # reports with non-null city
        city_rows = (await db.execute(
            select(Report.city, func.count()).group_by(Report.city)
        )).all()
        print("\n=== reports.city distribution ===")
        for city, c in city_rows:
            print(f"  {str(city):20s} {c}")

        # citizen users
        citizens = (await db.execute(
            select(User).where(User.role == "citizen")
        )).scalars().all()
        print(f"\n=== citizen users ({len(citizens)}) ===")
        for u in citizens[:30]:
            print(f"  {str(u.id)}  {u.email:35s} {u.name!r} status={u.status}")

        # report status distribution
        st_rows = (await db.execute(
            select(Report.status, func.count()).group_by(Report.status)
        )).all()
        print("\n=== reports.status distribution ===")
        for s, c in st_rows:
            print(f"  {str(s):15s} {c}")

        # created_at range
        rng = (await db.execute(
            select(func.min(Report.created_at), func.max(Report.created_at))
        )).one()
        print(f"\n=== reports.created_at range ===\n  min={rng[0]}  max={rng[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
