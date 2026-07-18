# Truvia

Digital Public Safety Platform — AI-assisted fraud triage (Citizen Fraud Shield),
officer investigation workflow, and a **Threat Intelligence Engine** (entity graph,
fraud-ring detection, and court-ready intelligence packages).

## Getting started

- **Backend** (FastAPI): setup, migrations, Neo4j graph schema, fraud-ring
  clustering, and the after-every-pull checklist are documented in
  [`truvia-backend/README.md`](truvia-backend/README.md).
- **Frontend** (Next.js): `cd truvia-frontend && npm install && npm run dev`.

One-command backing services (Postgres + pgvector, Redis, Neo4j + GDS/APOC):

```bash
cd truvia-backend
docker compose up -d
```

## Threat Intelligence Engine (Section 7)

Officer/admin-only surface under `/intelligence/*`:
- **Graph Home** — cluster-level fraud entity graph with search + entity preview.
- **Entity Explorer** — connections, complaints, risk history, risk network.
- **Fraud Rings** — Louvain-detected rings with scoped subgraphs and correlated complaints.
- **Intelligence Packages** — persisted, versioned, tamper-evident evidence bundles.

Resilient by design: Postgres is authoritative; Neo4j is a derived correlation
index. The engine works with or without Neo4j online (GDS Louvain when available,
`python-louvain` equivalent otherwise). See the backend README for details.
