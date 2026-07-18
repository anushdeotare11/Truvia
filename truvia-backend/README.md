# Truvia Backend — Setup & Deployment

FastAPI backend for the Truvia Digital Public Safety Platform. This document is
the single source of truth for bringing the stack up from a fresh clone, and the
**"after every pull"** checklist the team follows to avoid environment drift.

---

## 1. Prerequisites

- Python 3.12
- (Recommended) Docker + Docker Compose — brings up Postgres (pgvector), Redis,
  and Neo4j (with the GDS + APOC plugins) in one command.
- A `.env` file created from `.env.example` (see below).

The platform is **resilient by design**: it runs even when optional services are
down. Postgres is the single authoritative store; Neo4j is a *derived*
correlation index. If Neo4j is offline, the Threat Intelligence Engine
(Section 7) automatically falls back to computing everything from Postgres, so
no screen is ever blank for lack of a graph database.

---

## 2. First-time setup (fresh clone)

```bash
# 1. Create and fill your env file
cp .env.example .env          # (Windows: copy .env.example .env)
#    -> set DATABASE_URL, and (optionally) GOOGLE_API_KEY / OPENAI_API_KEY,
#       NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD.

# 2. Create a virtualenv and install deps
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt

# 3. (Optional but recommended) Bring up backing services
docker compose up -d           # postgres + redis + neo4j (GDS/APOC)

# 4. Apply database migrations (Postgres)
alembic upgrade head

# 5. Set up the Neo4j graph schema (idempotent; safe to re-run).
#    Soft-fails and exits 0 if Neo4j is offline — run again once it's up.
python -m scripts.neo4j_schema

# 6. Detect fraud rings (Louvain). Populates fraud_rings/fraud_ring_members.
python -m scripts.cluster_rings

# 7. Run the API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend: see `../truvia-frontend` (`npm install && npm run dev`). It talks to
this API at `http://127.0.0.1:8000` (proxied via `/api/*`).

---

## 3. Environment variables

All variables are documented with placeholders in **`.env.example`**. The ones
relevant to the Threat Intelligence Engine (Section 7):

| Var | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | Postgres (authoritative store). Falls back to local SQLite only if a localhost Postgres is unreachable. | local pg |
| `NEO4J_URI` | Bolt URI for the graph correlation index. | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j username. | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password (matches `docker-compose.yml`). | `password` |

No new environment variables were introduced by Section 7 — it reuses the
existing `NEO4J_*` settings. Ring detection sensitivity is a code-level constant
(`MIN_RING_SIZE` in `app/agents/ring_clustering.py`).

---

## 4. Threat Intelligence Engine (Section 7) — operational notes

- **Graph sync** happens automatically inside the report pipeline (Agent 5,
  `app/agents/threat_intel.py`): every processed report mirrors its entities,
  `CO_OCCURRED_IN` and `LINKED_TO` edges into Neo4j when it's reachable
  (Backend_Schema §9.2). This is best-effort and never blocks ingestion.
- **Ring clustering** (`scripts/cluster_rings.py`) is a real, re-runnable job:
  - Uses **Neo4j GDS Louvain** when Neo4j + GDS are available;
  - otherwise uses the **equivalent `python-louvain`** engine over the Postgres
    relationship graph (Backend_Schema §9.4).
  - Results are written to Postgres (`fraud_rings`, `fraud_ring_members`) and
    mirrored to Neo4j (`:Ring` + `:MEMBER_OF`) when reachable.
  - Run it on a schedule (cron / Task Scheduler) or after a batch of ingests.
- **Neo4j schema** (`scripts/neo4j_schema.py`) applies the constraints/indexes
  from Backend_Schema §9.3. Idempotent (`CREATE ... IF NOT EXISTS`).

> **Documented deviation from Backend_Schema:** rings are persisted to Postgres
> (`fraud_rings` / `fraud_ring_members`, migration `0003`) in addition to the
> Neo4j `:Ring` nodes the schema describes. This keeps Section 7 fully queryable
> and the graph rebuildable from Postgres (§9.5) even when Neo4j is offline.
> `neo4j_ring_id` is the shared key across both stores and on `cases.neo4j_ring_id`.

---

## 5. After every pull (checklist)

Run these every time you pull changes, to stay in sync:

```bash
pip install -r requirements.txt      # 1. new/updated dependencies
alembic upgrade head                 # 2. new database migrations (Postgres)
python -m scripts.neo4j_schema       # 3. ensure Neo4j constraints/indexes exist
python -m scripts.cluster_rings      # 4. (if reports changed) refresh fraud rings
```

Everything above is idempotent and safe to re-run.

---

## 6. Migrations

Migrations live in `alembic/versions/` and are always committed:

- `0001_initial` — full baseline schema
- `0002_add_city_pipeline_stage` — report columns
- `0003_add_fraud_rings` — `fraud_rings` + `fraud_ring_members` (Section 7)

Never hand-edit the database schema; add a new Alembic revision instead.
