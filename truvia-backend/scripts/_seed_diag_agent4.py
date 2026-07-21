"""Diagnostic: run entity extraction in-process on the most-recent report to see
if Agent 4 raises (code/data bug) or works (server background-task issue)."""
import asyncio, sys, traceback
from sqlalchemy import select, desc
from app.data.postgres_client import AsyncSessionLocal
from app.models.report import Report
from app.agents.entity_extractor import entity_extractor_agent


async def _main() -> int:
    async with AsyncSessionLocal() as db:
        r = (await db.execute(
            select(Report).where(Report.cleaned_text.ilike("PROBE-A%"))
            .order_by(desc(Report.created_at)).limit(1)
        )).scalar_one_or_none()
        if not r:
            r = (await db.execute(select(Report).order_by(desc(Report.created_at)).limit(1))).scalar_one()
    print(f"Testing Agent 4 on report {r.id} stage={r.pipeline_stage}")
    print(f"  text={r.cleaned_text!r}")
    try:
        res = await entity_extractor_agent.extract_entities(str(r.id))
        print(f"  Agent4 OK -> {res}")
    except Exception as e:
        print(f"  Agent4 RAISED: {type(e).__name__}: {e}")
        traceback.print_exc()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
