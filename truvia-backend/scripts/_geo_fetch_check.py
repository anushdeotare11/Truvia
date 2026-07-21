import asyncio, httpx
from datetime import timedelta
from sqlalchemy import select
from app.core.security import create_access_token
from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User


async def m():
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.role.in_(["officer", "admin"])))).scalars().first()
    tok = create_access_token(subject=str(u.id), role=u.role, expires_delta=timedelta(hours=1))
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("http://127.0.0.1:8000/api/v1/geo/priority?days=60",
                        headers={"Authorization": f"Bearer {tok}"})
        d = r.json()
        print("rows", len(d))
        for x in d[:14]:
            print(f"  {x['city']:14s} score={x['priority_score']:3d} trend={x['trend']:8s} "
                  f"cat={x['dominant_category']} n={x['complaint_count']}")


asyncio.run(m())
