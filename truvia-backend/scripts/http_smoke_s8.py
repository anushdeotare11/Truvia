"""Authenticated HTTP smoke test for Section 8 admin endpoints (live server)."""
import asyncio
import sys

import httpx
from sqlalchemy import select

from app.core.security import create_access_token
from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User

BASE = "http://127.0.0.1:8000/api/v1"


async def main() -> int:
    async with AsyncSessionLocal() as db:
        admin = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        citizen = (await db.execute(select(User).where(User.role == "citizen"))).scalars().first()
    admin_tok = create_access_token(subject=str(admin.id), role="admin")
    ah = {"Authorization": f"Bearer {admin_tok}"}

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{BASE}/admin/users")
        print(f"[guard no-token] {r.status_code} (expect 401)")
        if citizen:
            ct = create_access_token(subject=str(citizen.id), role="citizen")
            r = await c.get(f"{BASE}/admin/users", headers={"Authorization": f"Bearer {ct}"})
            print(f"[guard citizen] {r.status_code} (expect 403)")

        checks = [
            ("users", f"{BASE}/admin/users?page=1&page_size=5"),
            ("users filter", f"{BASE}/admin/users?role=admin"),
            ("knowledge-base", f"{BASE}/admin/knowledge-base"),
            ("system-health", f"{BASE}/admin/system-health"),
        ]
        ok = True
        for name, url in checks:
            r = await c.get(url, headers=ah)
            ok = ok and r.status_code == 200
            extra = ""
            if r.status_code == 200:
                b = r.json()
                if name == "users":
                    extra = f"total={b['total']} items={len(b['items'])}"
                elif name == "knowledge-base":
                    extra = f"docs={len(b)}"
                elif name == "system-health":
                    extra = f"agents={len(b['agents'])} queue_avail={b['queue']['available']}"
            print(f"[{name}] {r.status_code} {extra}")

    print("HTTP_S8_OK" if ok else "HTTP_S8_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(asyncio.wait_for(main(), timeout=60)))
    except asyncio.TimeoutError:
        print("TIMEOUT", file=sys.stderr); sys.exit(2)
