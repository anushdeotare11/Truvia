"""Authenticated HTTP smoke test against the LIVE backend (port 8000).
Mints an officer/admin access token, then exercises the Section 7 routes over
real HTTP to validate routing, the officer guard, and JSON serialization.
Run: .venv\\Scripts\\python.exe -m scripts.http_smoke_s7
"""
import asyncio
import sys

import httpx
from sqlalchemy import select

from app.core.security import create_access_token
from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User
from app.models.ring import FraudRing, FraudRingMember

BASE = "http://127.0.0.1:8000/api/v1"


async def main() -> int:
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.role.in_(["officer", "admin"])))).scalars().first()
        ring = (await db.execute(select(FraudRing).order_by(FraudRing.member_count.desc()))).scalars().first()
        member = (await db.execute(select(FraudRingMember).where(FraudRingMember.ring_id == ring.id))).scalars().first()
    token = create_access_token(subject=str(user.id), role=user.role)
    h = {"Authorization": f"Bearer {token}"}
    ring_id = ring.neo4j_ring_id
    entity_id = str(member.entity_id)

    async with httpx.AsyncClient(timeout=30) as c:
        # unauth guard check
        r = await c.get(f"{BASE}/graph/overview")
        print(f"[guard] overview no-token -> {r.status_code} (expect 401)")

        checks = [
            ("overview", f"{BASE}/graph/overview?top_n_clusters=8"),
            ("search", f"{BASE}/graph/search?q={entity_id[:3]}"),
            ("rings", f"{BASE}/graph/rings?sort=risk&limit=50"),
            ("ring detail", f"{BASE}/graph/rings/{ring_id}"),
            ("ring export", f"{BASE}/graph/rings/{ring_id}/export"),
            ("entity", f"{BASE}/graph/entity/{entity_id}"),
            ("subgraph d2", f"{BASE}/graph/entity/{entity_id}/subgraph?depth=2"),
            ("risk-score", f"{BASE}/graph/entity/{entity_id}/risk-score"),
        ]
        ok = True
        for name, url in checks:
            r = await c.get(url, headers=h)
            good = r.status_code == 200
            ok = ok and good
            extra = ""
            if good and r.headers.get("content-type", "").startswith("application/json"):
                body = r.json()
                if isinstance(body, list):
                    extra = f"len={len(body)}"
                elif isinstance(body, dict):
                    extra = ",".join(list(body.keys())[:5])
            print(f"[{name}] {r.status_code} {extra}")

        # POST package (ring)
        r = await c.post(f"{BASE}/graph/intelligence-package", json={"ring_id": ring_id}, headers=h)
        print(f"[package ring] {r.status_code} -> {r.json().get('case_number') if r.status_code in (200,201) else r.text[:120]}")
        pkg_ok = r.status_code in (200, 201)
        if pkg_ok:
            pid = r.json()["id"]
            r2 = await c.get(f"{BASE}/graph/intelligence-package/{pid}/download", headers=h)
            print(f"[package download] {r2.status_code} {r2.headers.get('content-type')}")
            pkg_ok = pkg_ok and r2.status_code == 200

    if ok and pkg_ok:
        print("HTTP_S7_OK")
        return 0
    print("HTTP_S7_FAILED")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(asyncio.wait_for(main(), timeout=80)))
    except asyncio.TimeoutError:
        print("TIMEOUT", file=sys.stderr)
        sys.exit(2)
