"""One-shot Section 7 audit: Neo4j reachability + GDS, and Postgres data counts.
Run: .venv\\Scripts\\python.exe -m scripts.audit_s7
Prints a compact JSON-ish report and never hangs (short timeouts)."""
import asyncio
import sys


async def check_postgres():
    from sqlalchemy import text
    from app.data.postgres_client import engine, is_sqlite
    out = {"dialect": "sqlite" if is_sqlite else "postgres/neon"}
    tables = [
        "reports", "entities", "report_entities", "relationships",
        "threat_scores", "cases", "intelligence_packages", "case_reports",
    ]
    try:
        async with engine.connect() as conn:
            for t in tables:
                try:
                    r = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                    out[t] = r.scalar()
                except Exception as e:
                    out[t] = f"ERR: {type(e).__name__}: {str(e)[:80]}"
    except Exception as e:
        out["_connect_error"] = f"{type(e).__name__}: {str(e)[:120]}"
    return out


def check_neo4j():
    from neo4j import GraphDatabase
    from app.config import settings
    out = {"uri": settings.NEO4J_URI}
    try:
        drv = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            connection_timeout=5,
        )
        with drv.session() as s:
            out["ping"] = s.run("RETURN 1 AS ok").single()["ok"]
            # node/edge counts
            try:
                out["nodes"] = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
                out["rels"] = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
                labels = s.run("CALL db.labels() YIELD label RETURN collect(label) AS l").single()["l"]
                out["labels"] = labels
                rtypes = s.run(
                    "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS l"
                ).single()["l"]
                out["rel_types"] = rtypes
            except Exception as e:
                out["counts_error"] = str(e)[:120]
            # GDS availability
            try:
                ver = s.run("RETURN gds.version() AS v").single()["v"]
                out["gds_version"] = ver
            except Exception as e:
                out["gds"] = f"UNAVAILABLE: {type(e).__name__}: {str(e)[:80]}"
            # APOC availability
            try:
                s.run("RETURN apoc.version() AS v").single()
                out["apoc"] = "available"
            except Exception as e:
                out["apoc"] = f"UNAVAILABLE: {str(e)[:60]}"
        drv.close()
    except Exception as e:
        out["_connect_error"] = f"{type(e).__name__}: {str(e)[:160]}"
    return out


async def main():
    print("=== NEO4J ===")
    neo = await asyncio.to_thread(check_neo4j)
    for k, v in neo.items():
        print(f"  {k}: {v}")
    print("=== POSTGRES ===")
    pg = await check_postgres()
    for k, v in pg.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    try:
        asyncio.run(asyncio.wait_for(main(), timeout=40))
    except asyncio.TimeoutError:
        print("TIMEOUT: audit exceeded 40s", file=sys.stderr)
        sys.exit(2)
