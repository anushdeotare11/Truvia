"""One-shot response-time measurement against the running backend (read-only).

Mints an officer token and times each key endpoint once, printing time_total (ms).
Usage: .venv\\Scripts\\python.exe -m scripts._perf_measure
"""
import asyncio
import sys
import time
from datetime import timedelta

import httpx
from sqlalchemy import select

from app.core.security import create_access_token
from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User

BASE = "http://127.0.0.1:8000/api/v1"

ENDPOINTS = [
    ("GET", "/geo/priority?days=30"),
    ("GET", "/reports?limit=100"),
    ("GET", "/cases/stats"),
    ("GET", "/dashboard/geo-breakdown"),
    ("GET", "/dashboard/timeline"),
    ("GET", "/dashboard/score-distribution"),
    ("GET", "/graph/overview"),
]


async def _officer_token() -> str:
    async with AsyncSessionLocal() as db:
        u = (await db.execute(
            select(User).where(User.role.in_(["officer", "admin"]), User.status == "active")
        )).scalars().first()
    if not u:
        raise RuntimeError("no officer/admin account")
    return create_access_token(subject=str(u.id), role=u.role, expires_delta=timedelta(hours=1))


async def _main() -> int:
    tok = await _officer_token()
    h = {"Authorization": f"Bearer {tok}", "Connection": "close"}
    async with httpx.AsyncClient(timeout=60) as c:
        # one warm-up ping to establish keep-alive/pool (not measured)
        try:
            await c.get("http://127.0.0.1:8000/healthz")
        except Exception:
            pass
        print(f"{'endpoint':40s} {'status':>6s} {'time_ms':>10s}")
        print("-" * 60)
        for method, ep in ENDPOINTS:
            t0 = time.perf_counter()
            try:
                r = await c.request(method, f"{BASE}{ep}", headers=h)
                dt = (time.perf_counter() - t0) * 1000
                print(f"{ep:40s} {r.status_code:>6d} {dt:>10.1f}")
            except Exception as e:
                dt = (time.perf_counter() - t0) * 1000
                print(f"{ep:40s} {'ERR':>6s} {dt:>10.1f}  {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
