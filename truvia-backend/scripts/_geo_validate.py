import asyncio
from app.data.postgres_client import AsyncSessionLocal
from app.services import geo_intel


async def main():
    async with AsyncSessionLocal() as db:
        ranking = await geo_intel.get_priority_ranking(db, days=30)
        print(f"cities ranked: {len(ranking)}")
        print(f"{'city':12} {'score':>5} {'count':>5} {'sev_wt':>6} {'rec_wt':>6} {'prev':>4} {'trend':>8}  dominant")
        for r in ranking:
            print(
                f"{r['city']:12} {r['priority_score']:5d} {r['complaint_count']:5d} "
                f"{r['avg_severity_weight']:6.2f} {r['recency_weight']:6.3f} {r['prior_window_count']:4d} "
                f"{r['trend']:>8}  {r['dominant_category']}"
            )

        scores = [r["priority_score"] for r in ranking]
        print("\ndistinct scores:", sorted(set(scores), reverse=True))
        print("scores differ across cities:", len(set(scores)) > 1)

        # Trend endpoint sample for the top city
        if ranking:
            top = ranking[0]["city"]
            trend = await geo_intel.get_city_trend(db, top, weeks=8)
            print(f"\ntrend for {top}: label={trend['trend']} cur={trend['current_window_count']} prev={trend['prior_window_count']}")
            for s in trend["series"]:
                print(f"   {s['week_start']}  count={s['complaint_count']}  avg_sev={s['avg_severity']}")

        # Category filter sanity
        cat_rank = await geo_intel.get_priority_ranking(db, category="Digital Arrest Scam", days=30)
        print(f"\ncategory-filtered (Digital Arrest Scam) cities: {len(cat_rank)}")


asyncio.run(main())
