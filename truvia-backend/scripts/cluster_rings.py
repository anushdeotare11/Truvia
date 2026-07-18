"""CLI entrypoint for fraud-ring clustering (Backend_Schema §9.4).

Recomputes fraud rings (Louvain) from the authoritative Postgres graph and
persists them to `fraud_rings` / `fraud_ring_members` (and mirrors to Neo4j
when reachable). Safe to re-run; each run fully recomputes rings.

Run:
    .venv\\Scripts\\python.exe -m scripts.cluster_rings           (Windows)
    .venv/bin/python -m scripts.cluster_rings                     (macOS/Linux)

Intended to be run on a schedule (cron / task scheduler) or on demand after a
batch of new reports has been ingested.
"""
import asyncio
import sys

from app.agents.ring_clustering import detect_and_persist_rings


async def _main() -> int:
    result = await detect_and_persist_rings()
    print(
        f"Ring clustering finished — engine={result.get('algorithm')} "
        f"rings_persisted={result.get('rings')} "
        f"neo4j_rings_written={result.get('neo4j_rings_written')}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(asyncio.wait_for(_main(), timeout=120)))
    except asyncio.TimeoutError:
        print("TIMEOUT: clustering exceeded 120s", file=sys.stderr)
        sys.exit(2)
