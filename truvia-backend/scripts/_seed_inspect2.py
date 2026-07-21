"""Supplemental read-only inspection: category, degraded_mode, entity reuse."""
import asyncio
import sys
from sqlalchemy import select, func, desc

from app.data.postgres_client import AsyncSessionLocal
from app.models.report import Report, ThreatScore, Entity, ReportEntity


async def _main() -> int:
    async with AsyncSessionLocal() as db:
        print("=== current threat_scores.scam_category (is_current) ===")
        rows = (await db.execute(
            select(ThreatScore.scam_category, func.count())
            .where(ThreatScore.is_current == True)
            .group_by(ThreatScore.scam_category)
            .order_by(desc(func.count()))
        )).all()
        for cat, c in rows:
            print(f"  {str(cat):28s} {c}")

        print("\n=== degraded_mode dist (is_current) ===")
        rows = (await db.execute(
            select(ThreatScore.degraded_mode, ThreatScore.model_version, func.count())
            .where(ThreatScore.is_current == True)
            .group_by(ThreatScore.degraded_mode, ThreatScore.model_version)
        )).all()
        for dm, mv, c in rows:
            print(f"  degraded={dm} model={mv!r} -> {c}")

        print("\n=== severity_band dist (is_current) ===")
        rows = (await db.execute(
            select(ThreatScore.severity_band, func.count())
            .where(ThreatScore.is_current == True)
            .group_by(ThreatScore.severity_band)
        )).all()
        for b, c in rows:
            print(f"  {str(b):12s} {c}")

        print("\n=== top entities by occurrence_count ===")
        rows = (await db.execute(
            select(Entity.type, Entity.raw_value, Entity.occurrence_count)
            .order_by(desc(Entity.occurrence_count)).limit(20)
        )).all()
        for t, rv, oc in rows:
            print(f"  {t:14s} {rv[:40]:40s} occ={oc}")

        # entity appearance depth: how many entities appear in >1 report
        appear = (await db.execute(
            select(ReportEntity.entity_id, func.count().label("n"))
            .group_by(ReportEntity.entity_id)
        )).all()
        multi = [a for a in appear if a[1] > 1]
        print(f"\n=== entity reuse: {len(appear)} entities have appearances; "
              f"{len(multi)} appear in >1 report ===")

        # how many reports have >=1 entity
        rep_with_ent = (await db.execute(
            select(func.count(func.distinct(ReportEntity.report_id)))
        )).scalar()
        total_rep = (await db.execute(select(func.count()).select_from(Report))).scalar()
        print(f"  reports with >=1 entity: {rep_with_ent}/{total_rep}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
