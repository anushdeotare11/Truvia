"""Show the most recent reports + their pipeline outputs (read-only)."""
import asyncio, sys
from sqlalchemy import select, func, desc
from app.data.postgres_client import AsyncSessionLocal
from app.models.report import Report, ThreatScore, ReportEntity


async def _main() -> int:
    async with AsyncSessionLocal() as db:
        reps = (await db.execute(
            select(Report).order_by(desc(Report.created_at)).limit(8)
        )).scalars().all()
        for r in reps:
            ns = (await db.execute(select(func.count()).select_from(ThreatScore)
                                   .where(ThreatScore.report_id == r.id))).scalar()
            ne = (await db.execute(select(func.count()).select_from(ReportEntity)
                                   .where(ReportEntity.report_id == r.id))).scalar()
            print(f"  {str(r.id)[:8]} status={r.status:10s} stage={str(r.pipeline_stage):16s} "
                  f"scores={ns} entities={ne} created={r.created_at} "
                  f"text={ (r.cleaned_text or '')[:45]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
