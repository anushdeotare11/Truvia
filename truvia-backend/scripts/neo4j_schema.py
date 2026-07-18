"""Idempotent Neo4j schema setup for the Truvia Threat Intelligence Engine.

Creates the constraints and indexes defined in Backend_Schema §9.3. Every
statement uses `IF NOT EXISTS`, so this script is safe to re-run any number of
times (e.g. on every deploy / after every pull).

Run:
    # with Neo4j up (see docker-compose.yml — service `neo4j`):
    .venv\\Scripts\\python.exe -m scripts.neo4j_schema        (Windows)
    .venv/bin/python -m scripts.neo4j_schema                  (macOS/Linux)

Connection settings come from .env (NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD).
If Neo4j is unreachable the script prints a clear warning and exits 0 in
--soft mode (default) so it never breaks an automated setup step; pass
--strict to make an unreachable Neo4j a hard failure (exit 1).
"""
import sys

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

from app.config import settings

# Backend_Schema §9.3 — uniqueness constraints (auto-create a backing index).
CONSTRAINTS = [
    ("entity_id_unique",
     "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
     "FOR (e:Entity) REQUIRE e.id IS UNIQUE"),
    ("report_id_unique",
     "CREATE CONSTRAINT report_id_unique IF NOT EXISTS "
     "FOR (r:Report) REQUIRE r.id IS UNIQUE"),
    ("ring_id_unique",
     "CREATE CONSTRAINT ring_id_unique IF NOT EXISTS "
     "FOR (g:Ring) REQUIRE g.id IS UNIQUE"),
]

# Property indexes for common filter/lookup paths.
INDEXES = [
    ("entity_normalized_value",
     "CREATE INDEX entity_normalized_value IF NOT EXISTS "
     "FOR (e:Entity) ON (e.normalized_value)"),
    ("entity_risk_tier",
     "CREATE INDEX entity_risk_tier IF NOT EXISTS "
     "FOR (e:Entity) ON (e.risk_tier)"),
    ("report_created_at",
     "CREATE INDEX report_created_at IF NOT EXISTS "
     "FOR (r:Report) ON (r.created_at)"),
]

# Full-text index backing the global entity search bar.
FULLTEXT = [
    ("entity_search",
     "CREATE FULLTEXT INDEX entity_search IF NOT EXISTS "
     "FOR (e:Entity) ON EACH [e.normalized_value]"),
]


def apply_schema() -> int:
    applied = 0
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        connection_timeout=5,
    )
    try:
        with driver.session() as session:
            for group_name, statements in (
                ("constraints", CONSTRAINTS),
                ("indexes", INDEXES),
                ("fulltext", FULLTEXT),
            ):
                print(f"-- {group_name} --")
                for name, cypher in statements:
                    try:
                        session.run(cypher).consume()
                        print(f"  [ok] {name}")
                        applied += 1
                    except Neo4jError as e:
                        print(f"  [warn] {name}: {e.code} {e.message}")
    finally:
        driver.close()
    return applied


def main() -> int:
    strict = "--strict" in sys.argv
    print(f"Applying Neo4j schema to {settings.NEO4J_URI} ...")
    try:
        count = apply_schema()
    except Exception as e:  # connection / auth errors
        msg = f"Neo4j unreachable ({type(e).__name__}: {str(e)[:120]})."
        if strict:
            print(f"ERROR: {msg}", file=sys.stderr)
            return 1
        print(
            f"WARNING: {msg}\n"
            "Skipping graph schema setup. The Threat Intelligence Engine will run "
            "in Postgres-only mode until Neo4j is available. Re-run this command "
            "once Neo4j is up (docker compose up -d neo4j).",
            file=sys.stderr,
        )
        return 0
    print(f"Neo4j schema applied ({count} statements). Idempotent — safe to re-run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
