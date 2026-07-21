"""Tiny probe: submit 3 entity-rich reports through the live endpoint, time the
pipeline to 'completed', and confirm threat_scores + entities were produced.
These 3 rows are real seed data (kept). Read-only verification via DB afterwards."""
import asyncio
import sys
import time
from datetime import timedelta

import httpx
from sqlalchemy import select, func

from app.core.security import create_access_token
from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User
from app.models.report import ThreatScore, ReportEntity
import uuid

BASE = "http://127.0.0.1:8000/api/v1"

PROBE_TEXTS = [
    "PROBE-A CBI digital arrest: transfer Rs 50000 to probealpha123@okaxis now or warrant issued. Call +91 9812000001. Notice http://probe-cbi.top",
    "PROBE-B SBI KYC expired, account blocked today. Verify at http://probe-kyc.xyz. Helpline +91 9812000002.",
    "PROBE-C Accept the UPI refund request of Rs 4999 from probecharlie77@okhdfc and enter PIN. Support +91 9812000003.",
]


async def _main() -> int:
    async with AsyncSessionLocal() as db:
        citizen = (await db.execute(select(User).where(User.role == "citizen"))).scalars().first()
    assert citizen, "no citizen"
    tok = create_access_token(subject=str(citizen.id), role="citizen", expires_delta=timedelta(hours=1))
    h = {"Authorization": f"Bearer {tok}"}
    ids = []
    async with httpx.AsyncClient(timeout=60) as c:
        for txt in PROBE_TEXTS:
            t0 = time.monotonic()
            r = await c.post(f"{BASE}/reports/submit", headers=h,
                             data={"source_type": "text", "text_content": txt})
            assert r.status_code == 201, f"submit {r.status_code}: {r.text[:200]}"
            rid = r.json()["id"]
            ids.append(rid)
            # poll
            stage = None
            while time.monotonic() - t0 < 60:
                await asyncio.sleep(1.0)
                s = await c.get(f"{BASE}/reports/{rid}/status", headers=h)
                body = s.json()
                stage = body.get("pipeline_stage")
                if stage == "completed" or body.get("status") == "failed":
                    break
            dt = time.monotonic() - t0
            print(f"  {rid} stage={stage} status={body.get('status')} took={dt:.1f}s", flush=True)

    # verify scores + entities exist for these 3
    async with AsyncSessionLocal() as db:
        for rid in ids:
            ru = uuid.UUID(rid)
            ns = (await db.execute(select(func.count()).select_from(ThreatScore)
                                   .where(ThreatScore.report_id == ru))).scalar()
            ne = (await db.execute(select(func.count()).select_from(ReportEntity)
                                   .where(ReportEntity.report_id == ru))).scalar()
            print(f"  verify {rid}: threat_scores={ns} report_entities={ne}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
