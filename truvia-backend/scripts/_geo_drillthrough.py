import asyncio
import sys
import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
import httpx
from sqlalchemy import select
from app.core.security import create_access_token
from app.data.postgres_client import AsyncSessionLocal, engine as _e
_e.echo = False
from app.models.user import User

BASE = "http://127.0.0.1:8000/api/v1"


async def main():
    async with AsyncSessionLocal() as db:
        officer = (await db.execute(select(User).where(User.role == "officer"))).scalars().first()
    h = {"Authorization": f"Bearer {create_access_token(subject=str(officer.id), role='officer')}"}
    async with httpx.AsyncClient(timeout=25) as c:
        pune = (await c.get(f"{BASE}/reports?city=Pune&limit=50", headers=h)).json()
        other = (await c.get(f"{BASE}/reports?city=Delhi&limit=50", headers=h)).json()
    pcities = {r.get("city") for r in pune}
    dcities = {r.get("city") for r in other}
    print(f"city=Pune  -> {len(pune)} rows, distinct cities={pcities}")
    print(f"city=Delhi -> {len(other)} rows, distinct cities={dcities}")
    ok = len(pune) > 0 and pcities == {"Pune"} and len(other) > 0 and dcities == {"Delhi"}
    print("DRILLTHROUGH_OK" if ok else "DRILLTHROUGH_FAILED")
    return 0 if ok else 1


sys.exit(asyncio.run(asyncio.wait_for(main(), timeout=28)))
