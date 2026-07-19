import asyncio
from app.data.postgres_client import AsyncSessionLocal
from sqlalchemy import text


async def main():
    async with AsyncSessionLocal() as s:
        total = (await s.execute(text("SELECT count(*) FROM reports"))).scalar()
        non_null = (await s.execute(text("SELECT count(*) FROM reports WHERE city IS NOT NULL AND btrim(city) <> ''"))).scalar()
        print(f"reports total={total} with_city={non_null}")

        print("\n-- distinct city values (top 20 by count) --")
        rows = (await s.execute(text(
            "SELECT city, count(*) c FROM reports GROUP BY city ORDER BY c DESC LIMIT 20"
        ))).fetchall()
        for city, c in rows:
            print(f"  {city!r:30} {c}")

        print("\n-- created_at range --")
        r = (await s.execute(text("SELECT min(created_at), max(created_at) FROM reports"))).fetchone()
        print(f"  min={r[0]}  max={r[1]}")

        print("\n-- severity_band distribution (current threat scores) --")
        rows = (await s.execute(text(
            "SELECT ts.severity_band, count(*) c FROM threat_scores ts WHERE ts.is_current = true GROUP BY ts.severity_band ORDER BY c DESC"
        ))).fetchall()
        for band, c in rows:
            print(f"  {band!r:12} {c}")

        print("\n-- reports joined to a current threat score (join sanity) --")
        joined = (await s.execute(text(
            "SELECT count(*) FROM reports r JOIN threat_scores ts ON ts.report_id = r.id AND ts.is_current = true"
        ))).scalar()
        print(f"  reports_with_current_score={joined}")

        print("\n-- recent-window counts (last 30 / prior 30 days) --")
        r = (await s.execute(text(
            "SELECT "
            " count(*) FILTER (WHERE created_at >= now() - interval '30 days') last30, "
            " count(*) FILTER (WHERE created_at >= now() - interval '60 days' AND created_at < now() - interval '30 days') prev30 "
            "FROM reports"
        ))).fetchone()
        print(f"  last30={r[0]}  prev30={r[1]}")


asyncio.run(main())
