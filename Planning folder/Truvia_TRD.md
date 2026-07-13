# Truvia — Technical Requirements Document (TRD)
### Internal Engineering Documentation

**Companion to:** Truvia PRD v1.0
**Audience:** Engineering team (2 developers), technical judges/reviewers
**Status:** Build-Ready
**Scope of this document:** Technical implementation only. Product rationale, module UX, and business justification live in the PRD and are not repeated here.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Overall System Architecture](#2-overall-system-architecture)
3. [Technology Selection](#3-technology-selection)
4. [AI Architecture](#4-ai-architecture)
5. [Backend Architecture](#5-backend-architecture)
6. [Frontend Architecture](#6-frontend-architecture)
7. [API Design](#7-api-design)
8. [Security](#8-security)
9. [Database Architecture](#9-database-architecture)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Error Handling](#11-error-handling)
12. [Logging, Monitoring, Observability, Tracing](#12-logging-monitoring-observability-tracing)
13. [Performance: Caching, Queueing, Background Jobs, Scaling](#13-performance-caching-queueing-background-jobs-scaling)
14. [Technical Risks & Mitigation](#14-technical-risks--mitigation)

---

## 1. Executive Summary

Truvia is implemented as a **single deployable backend service exposing a modular, agent-oriented internal architecture**, fronted by one Next.js application serving three distinct experiences (Citizen Fraud Shield, Law Enforcement Dashboard, Threat Intelligence Engine). The technical thesis of this document is:

> **Build a monolith with microservice-shaped internal boundaries.** Two developers cannot operate real microservices (separate deploys, service discovery, distributed tracing overhead) in 18 days — but the six AI agents defined in the PRD *must* remain independently callable, independently testable, and independently failure-isolated, because that separation is the architectural proof-point of the product.

The technical approach rests on four pillars:

1. **A single FastAPI backend** organized into strictly-bounded internal modules (one per agent + shared core), each with its own request/response contract, so the codebase could be split into real microservices post-hackathon with minimal refactoring.
2. **Asynchronous, queue-mediated agent orchestration** — agents communicate through a task queue (Redis + a lightweight worker pool), not direct in-process function calls, so that a slow or failing agent (e.g., OCR timeout) never blocks the rest of the pipeline or the API's responsiveness.
3. **Polyglot persistence accessed through a single data-access layer** — PostgreSQL (system of record), Neo4j (graph correlation), pgvector (RAG retrieval) — each with one narrow internal client module, so the rest of the codebase never talks to a database driver directly.
4. **Contract-first API design** — every agent and every REST endpoint has an explicit, versioned JSON schema, enforced with Pydantic models, so integration bugs surface at request-validation time, not in production logs.

This document specifies exact endpoints, service boundaries, orchestration mechanics, security controls, and operational tooling required to build this system in an 18-day window while remaining structurally sound enough to scale toward a real government deployment.

---

## 2. Overall System Architecture

### 2.1 High-Level Component Diagram

```
                                   ┌─────────────────────────────┐
                                   │        CLIENT LAYER          │
                                   │  Next.js Web App (3 modules) │
                                   │  - Citizen Fraud Shield       │
                                   │  - LE Dashboard                │
                                   │  - Threat Intelligence Engine │
                                   └───────────────┬───────────────┘
                                                   │ HTTPS / JSON
                                                   ▼
                                   ┌─────────────────────────────┐
                                   │        API GATEWAY LAYER      │
                                   │  FastAPI app (single service)  │
                                   │  - Auth middleware             │
                                   │  - Rate limiting                │
                                   │  - Request validation (Pydantic)│
                                   │  - Routing to domain routers    │
                                   └───────────────┬───────────────┘
                                                   │
                        ┌──────────────────────────┼──────────────────────────┐
                        ▼                          ▼                          ▼
              ┌──────────────────┐      ┌────────────────────┐     ┌────────────────────┐
              │  SYNC DOMAIN APIs │      │  ORCHESTRATION LAYER │     │  READ-MODEL APIs     │
              │  (reports, cases, │      │  (Redis queue +       │     │  (dashboards, graph,  │
              │   users, alerts)  │      │   worker pool)        │     │   cached KPIs)        │
              └─────────┬────────┘      └──────────┬────────────┘     └──────────┬───────────┘
                        │                            │                            │
                        │                            ▼                            │
                        │              ┌─────────────────────────────┐            │
                        │              │        AGENT WORKERS          │            │
                        │              │ ┌───────────────────────────┐ │            │
                        │              │ │ Agent 1: Input Processing  │ │            │
                        │              │ ├───────────────────────────┤ │            │
                        │              │ │ Agent 2: Threat Detection  │ │            │
                        │              │ ├───────────────────────────┤ │            │
                        │              │ │ Agent 3: Knowledge (RAG)   │ │            │
                        │              │ ├───────────────────────────┤ │            │
                        │              │ │ Agent 4: Entity Intel      │ │            │
                        │              │ ├───────────────────────────┤ │            │
                        │              │ │ Agent 5: Threat Intel/Graph│ │            │
                        │              │ ├───────────────────────────┤ │            │
                        │              │ │ Agent 6: Alert/Investigate │ │            │
                        │              │ └───────────────────────────┘ │            │
                        │              └──────────────┬────────────────┘            │
                        │                              │                            │
                        ▼                              ▼                            ▼
              ┌────────────────────────────────────────────────────────────────────────┐
              │                          DATA ACCESS LAYER                                │
              │   PostgresClient   |   Neo4jClient   |   VectorStoreClient (pgvector)     │
              │                    |                 |   ObjectStorageClient (files)      │
              └───────────────────────────────┬────────────────────────────────────────────┘
                                               ▼
                     ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
                     │   PostgreSQL       │  │   Neo4j (Aura)     │  │  Object Storage    │
                     │  (system of record,│  │  (entity graph)     │  │  (raw uploads:      │
                     │   pgvector ext.)   │  │                     │  │   images/audio)     │
                     └───────────────────┘  └───────────────────┘  └───────────────────┘
```

### 2.2 Layer Responsibilities

| Layer | Responsibility | Implementation |
|---|---|---|
| Frontend | Renders 3 module UIs, manages client-side state, calls REST APIs, polls for async job status | Next.js (TypeScript) |
| API Gateway | Single entry point: auth, validation, rate limiting, routing | FastAPI, deployed as one process (multiple workers via Uvicorn/Gunicorn) |
| Sync Domain APIs | CRUD-style operations that don't require AI processing (fetch report, list complaints, manage cases) | FastAPI routers, direct DB reads/writes |
| Orchestration Layer | Sequences agent execution for a submitted report; manages retries, timeouts, partial-failure states | Redis-backed task queue (Celery or RQ) |
| Agent Workers | The 6 AI agents, each a discrete callable module with its own contract | Python modules under `app/agents/`, invoked by workers |
| Read-Model APIs | Serve dashboard/graph queries from precomputed or cached views, not live joins | FastAPI routers reading materialized views / cached Redis keys |
| Data Access Layer | Single point of contact per datastore; no other code imports a raw DB driver | `app/data/postgres_client.py`, `app/data/neo4j_client.py`, `app/data/vector_client.py`, `app/data/storage_client.py` |

### 2.3 Why This Shape (Monolith with Agent-Shaped Boundaries)

A **true microservice architecture** (one deployable per agent) is explicitly rejected for this build: it would require 6 separate deployment pipelines, service-to-service auth, and network-level failure handling — none of which two developers can responsibly operate in 18 days, and all of which add demo risk without adding demo-visible value. Instead, agent boundaries are enforced **at the code and queue level**: each agent is a stateless, independently invokable module with a strict input/output schema, called only through the orchestration queue — never via direct imports across agent modules. This means the migration to real microservices later is a deployment change (containerize each `app/agents/*` module separately, point the queue at network endpoints instead of in-process calls), not an architecture rewrite.

---

## 3. Technology Selection

*(Business/product-level justification for each technology lives in the PRD §14. This section adds the engineering-execution rationale specific to implementation.)*

| Component | Technology | Why Chosen (Engineering Lens) | Alternatives | Trade-off |
|---|---|---|---|---|
| API Framework | **FastAPI** | Native `async def` support lets the API accept a report upload and immediately hand off to the queue without blocking a worker thread; Pydantic-based request/response models double as the agent I/O contracts described in PRD §9, so there is exactly one schema definition per data shape, not two | Flask (sync-first, would need extra async plumbing), Django REST Framework (ORM/admin overhead not needed here) | FastAPI's async model requires discipline (don't block the event loop with sync DB calls) — mitigated by using async DB drivers (`asyncpg`) |
| Task Queue | **Celery + Redis** (or RQ + Redis for lower setup overhead — see decision note below) | Decouples the HTTP request/response cycle from potentially slow AI calls (OCR/ASR/LLM); gives per-task retry/backoff for free; Redis doubles as both queue broker and cache layer, reducing infra footprint | Direct `asyncio.create_task` background execution (no persistence — a server restart silently drops in-flight reports); AWS SQS/managed queue (more ops setup than needed) | Adds Redis as infra dependency, but it was already needed for caching, so marginal cost is near zero |
| Decision note | **RQ chosen over Celery for MVP** | RQ has a fraction of Celery's configuration surface (no separate beat scheduler, simpler worker model) — appropriate given the 18-day timeline; Celery remains the documented upgrade path if scheduled/periodic jobs (e.g., nightly trend recomputation) grow in complexity | Celery | RQ has weaker built-in support for complex workflows (chains/chords); acceptable since Truvia's pipeline is a simple linear sequence with fan-out only at Agent 5→6 |
| Relational DB Driver | **asyncpg** (via SQLAlchemy 2.0 async ORM) | True async DB access keeps the FastAPI event loop non-blocking; SQLAlchemy gives migration tooling (Alembic) for schema evolution during the build | Sync `psycopg2` (blocks event loop under load), raw `asyncpg` without ORM (faster but more boilerplate for 10+ tables) | Slightly more setup than raw SQL, worth it for migration safety across a 16-day build with an evolving schema |
| Graph DB Access | **Neo4j Python Driver (async)** + **Neo4j Graph Data Science (GDS) library** | GDS ships production-grade community-detection algorithms (Louvain) out of the box — avoids implementing clustering from scratch | Implementing Louvain manually over NetworkX in Python | NetworkX in-memory clustering doesn't scale and duplicates what the graph DB already does natively; GDS keeps clustering logic where the graph data lives |
| Vector Store | **pgvector on the existing PostgreSQL instance** | Avoids a 4th datastore; RAG corpus size (regulatory documents) is small enough (low thousands of chunks) that pgvector's exact/IVFFlat search is more than sufficient | Standalone Pinecone/Weaviate/Chroma | Would outperform pgvector at massive scale, which this MVP will never reach — added ops cost isn't justified |
| LLM SDK | **Anthropic Python SDK**, all calls routed through one internal `llm_client.py` wrapper | A single wrapper module enforces consistent structured-output parsing (JSON mode), consistent retry/timeout policy, and consistent token/cost logging across all 6 agents — no agent ever calls the SDK directly | Calling the SDK ad hoc from each agent | Ad hoc calls would duplicate retry/error-handling logic 6 times and make provider-swap (if ever needed) a 6-file change instead of a 1-file change |
| File Storage | **S3-compatible object storage** (e.g., AWS S3 or a compatible provider) | Raw uploads (screenshots, audio) must not be stored in the application database; object storage with signed URLs is the standard pattern and keeps Postgres lean | Storing files directly in Postgres as bytea | Bytea storage bloats the DB and complicates backups; object storage separates concerns correctly from day one |
| PDF Rendering | **Headless browser rendering (Playwright) of an HTML report template** | Lets the Intelligence Package (PRD §12) be styled with the exact same design tokens as the web dashboard, guaranteeing visual consistency between on-screen and exported evidence | `reportlab` (Python-native but verbose for complex multi-section layouts); `wkhtmltopdf` (unmaintained) | Playwright adds a heavier runtime dependency (headless Chromium) but produces materially better-looking output for a "court-ready" artifact, which is a judged differentiator |
| Frontend Framework | **Next.js 14 (App Router) + TypeScript** | File-based routing directly maps to the 3-module structure (`/citizen/*`, `/officer/*`, `/intelligence/*`); built-in API route capability used sparingly for BFF-style token refresh only | Vite + React Router | Next.js's opinionated structure reduces decisions two developers would otherwise have to make from scratch |
| State Management | **TanStack Query (React Query) for server state + Zustand for local UI state** | Report processing is inherently async/polling-based — React Query's built-in polling, caching, and stale-while-revalidate model fits the "processing… → result" flow natively | Redux Toolkit (more boilerplate for what is fundamentally server-state synchronization, not complex client state) | Two state libraries instead of one, but each is doing a genuinely different job (server cache vs. ephemeral UI state like graph zoom level) |

---

## 4. AI Architecture

### 4.1 Agent Orchestration Model

Every citizen report follows a **linear, queue-mediated pipeline** with one conditional fan-out point:

```
POST /reports
      │
      ▼
[enqueue: process_report(report_id)]
      │
      ▼
Agent 1 (Input Processing)  ──▶ writes CleanedInput to `reports.cleaned_text`
      │
      ▼
Agent 2 (Threat Detection)  ──▶ writes ThreatAssessment to `threat_scores`
      │
      ▼
Agent 4 (Entity Intelligence) ──▶ writes ExtractedEntities to `entities`/`report_entities`
      │
      ▼
Agent 5 (Threat Intelligence/Graph) ──▶ upserts graph nodes/edges in Neo4j, computes correlation
      │
      ▼
Agent 6 (Alert & Investigation) ──▶ generates CitizenAlert + updates dashboard cache
      │
      ▼
[mark report.status = 'complete'] ──▶ frontend polling picks up final state
```

Agent 3 (Knowledge Intelligence / RAG chat) is **not part of this pipeline** — it is invoked synchronously and independently whenever a user sends a chat message, since it must respond within a single request/response cycle for a usable chat UX.

### 4.2 Why Queue-Mediated, Not In-Process Chained Calls

If Agent 1→2→4→5→6 were chained as direct sequential function calls inside a single HTTP request handler, a slow OCR call or LLM timeout would hold an HTTP connection open for the full pipeline duration (potentially 15–20s), and any single agent failure would fail the entire request with no partial result saved. Instead:

- The initial `POST /reports` call does minimal work (validate + persist raw upload + enqueue job) and returns **immediately** with `202 Accepted` and a `report_id`.
- Each pipeline stage is a **separate queued task**, chained via the task queue's built-in task-chaining (each task enqueues the next on success).
- Each stage independently persists its output to the database **before** enqueuing the next stage, so a failure at Agent 5 still leaves the citizen with a valid, saved threat score and category from Agent 2 — the report is never "all or nothing."
- The frontend polls `GET /reports/{id}/status`, which reads the current `status` enum (`processing_input`, `scoring_threat`, `extracting_entities`, `updating_graph`, `finalizing`, `complete`, `failed_partial`) directly off the report row — this status field is also what powers the "processing stepper" UI described in PRD §8.1.

### 4.3 Prompt Strategy

- **One prompt template per agent**, version-controlled as a file (not inlined in Python strings), so prompt changes are reviewable diffs.
- All LLM-backed agents (2, 3, 6) use **structured output mode** (JSON schema-constrained generation) rather than free-text parsing — the Pydantic model for each agent's output *is* the schema passed to the LLM call, so parsing failures are caught at the schema-validation layer, not by regex-scraping free text.
- **System prompt layering**: a shared base system prompt (tone, "you are part of a public-safety intelligence system, not a general chatbot," output-format rules) is composed with an agent-specific task prompt at call time from a single `prompts/base_system.txt` + `prompts/agent_2_threat_detection.txt` pattern — avoids copy-pasted boilerplate drifting out of sync across 3 LLM-backed agents.
- **Few-shot examples** embedded in each agent's prompt file, drawn from the seeded synthetic dataset, to stabilize output format and category taxonomy adherence before any fine-tuning exists.

### 4.4 Structured Outputs & Context Management

- Every LLM call goes through `llm_client.generate_structured(prompt, response_model: Type[BaseModel])`, which: (1) constructs the schema-constrained request, (2) parses the response into the given Pydantic model, (3) retries once on schema-validation failure with an error-correction follow-up prompt, (4) raises a typed `AgentOutputError` if the second attempt also fails, which the calling agent module catches per its documented failure-handling behavior (PRD §9).
- **Context passed to each agent is explicitly scoped**, not the full conversation history: Agent 2 receives only the current report's cleaned text + a small "known pattern hints" context object from Agent 5 (top-3 similar historical categories, injected as extra context, not raw complaint text, to control token growth as the complaint corpus grows).
- **Chat context (Agent 3)** is scoped to the current report + the last N turns of the chat session (sliding window, N=6), rather than the entire chat history, to keep RAG prompts bounded regardless of session length.

### 4.5 RAG Workflow (Agent 3)

1. **Ingestion (offline/setup-time job):** regulatory documents (RBI/MHA/NCRP/CERT-In/NPCI advisories, curated scam-pattern notes) are chunked (~300–500 tokens, with overlap), embedded, and stored in the `knowledge_base` table with a `pgvector` embedding column.
2. **Query time:** user question is embedded → top-k (k=5) nearest chunks retrieved via cosine similarity → chunks + current report context assembled into a grounded prompt → LLM generates an answer **with inline citation markers referencing the specific retrieved chunk IDs**.
3. **Citation validation:** before returning to the client, the response is checked to confirm every citation marker maps to an actually-retrieved chunk ID (guards against the model inventing a citation) — any unmapped citation is stripped and logged as a quality-monitoring event.
4. **No-match handling:** if the top retrieved chunk's similarity score is below a configured threshold, the agent returns an explicit "not covered in current knowledge base" response rather than forcing a generation from irrelevant context.

### 4.6 Entity Extraction Pipeline (Agent 4)

- **Deterministic extractors first:** regex/format-validated extraction for phone numbers, UPI IDs, emails, URLs/domains, IFSC codes — these run with no LLM call, are near-zero-latency, and are treated as high-confidence by default.
- **NER pass second:** a named-entity-recognition model (LLM-based structured extraction, constrained to a fixed entity-type schema) identifies free-text entities that regex cannot catch — impersonated organization/government names, device references mentioned in speech.
- **Normalization layer:** all extracted values pass through per-type normalizers (e.g., phone numbers stripped of formatting/country-code variants unified) before being considered for deduplication against the existing entity table — critical, since ungnormalized duplicates would silently fragment the graph and break correlation.

### 4.7 Graph Update Pipeline (Agent 5)

1. For each normalized entity from Agent 4: `MERGE` (upsert) as a graph node keyed on `(type, normalized_value)`.
2. Create a `CO_OCCURRED_IN` edge from each entity to the current report node.
3. Query for existing entities that co-occurred with any of the current report's entities in prior reports → create/strengthen `LINKED_TO` edges (weight incremented on repeat co-occurrence).
4. Enqueue an **async, lower-priority task** to re-run community detection (Louvain via Neo4j GDS) — this does **not** block the main pipeline; ring membership updates are eventually consistent (target: within seconds for MVP scale, documented as a batch job at larger scale).
5. Recompute the risk score for all directly-touched nodes synchronously (cheap, local computation); recompute for the full affected cluster asynchronously (more expensive, graph-wide).

---

## 5. Backend Architecture

### 5.1 Monolith vs. Microservices — Decision

**Decision: Modular monolith**, single FastAPI application, single deployable artifact, single database connection pool — with internal module boundaries drawn exactly along the 6-agent + domain-API lines defined in the PRD. Justification: two developers, 18 days, one demo environment. Real microservices would multiply deployment surface area (6+ services × health checks × service-to-service auth × network failure modes) for zero judge-visible benefit, while a monolith with disciplined internal boundaries preserves the ability to physically split services later (each `app/agents/*` package already has zero direct imports from other agent packages — only through defined interfaces).

### 5.2 Folder Structure

```
truvia-backend/
├── app/
│   ├── main.py                      # FastAPI app instantiation, middleware registration
│   ├── config.py                    # Settings (env-driven, pydantic-settings)
│   ├── api/
│   │   ├── v1/
│   │   │   ├── reports.py           # Report intake & retrieval endpoints
│   │   │   ├── chat.py              # Agent 3 chat endpoint
│   │   │   ├── complaints.py        # LE dashboard complaint endpoints
│   │   │   ├── cases.py             # Case/investigation endpoints
│   │   │   ├── graph.py             # Threat Intelligence Engine endpoints
│   │   │   ├── alerts.py            # Public/officer alert endpoints
│   │   │   ├── dashboard.py         # KPI/trend/geo endpoints
│   │   │   └── auth.py              # Login/token endpoints
│   ├── agents/
│   │   ├── input_processing/        # Agent 1
│   │   ├── threat_detection/        # Agent 2
│   │   ├── knowledge_intelligence/  # Agent 3
│   │   ├── entity_intelligence/     # Agent 4
│   │   ├── threat_intelligence/     # Agent 5
│   │   └── alert_investigation/     # Agent 6
│   │       (each package: schemas.py, service.py, prompts/, tests/)
│   ├── orchestration/
│   │   ├── queue.py                 # Task queue setup (RQ)
│   │   ├── tasks.py                 # Task definitions chaining agent calls
│   │   └── status.py                # Report status state machine
│   ├── data/
│   │   ├── postgres_client.py
│   │   ├── neo4j_client.py
│   │   ├── vector_client.py
│   │   └── storage_client.py        # Object storage (S3-compatible)
│   ├── models/                      # SQLAlchemy ORM models
│   ├── schemas/                     # Shared Pydantic request/response schemas
│   ├── core/
│   │   ├── security.py              # JWT, password hashing
│   │   ├── rate_limit.py
│   │   ├── llm_client.py            # Single LLM SDK wrapper
│   │   └── logging.py
│   └── workers/
│       └── worker_entrypoint.py     # RQ worker process entrypoint
├── alembic/                          # DB migrations
├── tests/
└── local_setup.sh                    # Local dev: script to initialize local services (postgres, redis)
```

### 5.3 Services / Modules Breakdown

| Module | Responsibility | Depends On |
|---|---|---|
| `api/v1/*` | HTTP request handling, auth enforcement, request validation, response shaping | `data/*`, `orchestration/*` |
| `agents/*` | Pure business logic per agent — callable independently of HTTP or queue context (critical for unit testing) | `core/llm_client`, `data/*` |
| `orchestration/*` | Sequences agent calls, manages task state, handles retries | `agents/*`, `data/postgres_client` (for status writes) |
| `data/*` | Sole owners of their respective DB connections; expose typed methods only (no raw query leakage into API/agent code) | External DB drivers |
| `core/*` | Cross-cutting concerns (auth, rate limiting, LLM wrapper, logging config) | — |
| `workers/*` | Process entrypoint that runs the RQ worker loop, importing `orchestration.tasks` | `orchestration/*` |

### 5.4 API Gateway Behavior

The single FastAPI app **is** the API gateway (no separate gateway service, appropriate at this scale). It is responsible for:
- Terminating HTTPS (via the deployment platform's edge, e.g., managed load balancer/CDN)
- JWT validation middleware on all non-public routes
- Per-IP and per-user rate limiting middleware (see §8.4)
- Request-ID injection (for tracing — see §12)
- CORS policy enforcement (frontend origin allow-list)
- Global exception handler converting all uncaught exceptions into the standard error envelope (§11)

### 5.5 Background Workers

- A dedicated **worker process** (separate from the API process, same codebase, run via `python -m app.workers.worker_entrypoint`) consumes the RQ queue.
- Two logical queues: `pipeline` (report processing — Agents 1/2/4/5/6) and `graph_maintenance` (lower-priority async clustering recomputation), so a burst of new reports never starves the ring-detection batch job or vice versa.
- Workers are horizontally scalable (multiple worker processes can consume the same queue) — noted as the primary scale-out lever post-hackathon, requiring no code change, only additional worker instances.

---

## 6. Frontend Architecture

### 6.1 Folder Structure (Next.js App Router)

```
truvia-frontend/
├── app/
│   ├── (citizen)/
│   │   ├── fraud-shield/
│   │   │   ├── page.tsx              # Upload/home screen
│   │   │   ├── [reportId]/page.tsx   # Result + explainability screen
│   │   │   └── history/page.tsx
│   ├── (officer)/
│   │   ├── dashboard/page.tsx
│   │   ├── complaints/page.tsx
│   │   └── complaints/[id]/page.tsx  # Investigation view
│   ├── (intelligence)/
│   │   ├── graph/page.tsx            # Fraud graph canvas
│   │   └── entity/[id]/page.tsx      # Entity Explorer
│   ├── login/page.tsx
│   └── layout.tsx                    # Root layout, theme provider, auth provider
├── components/
│   ├── ui/                           # Design-system primitives (buttons, cards, badges)
│   ├── citizen/                      # Fraud Shield-specific components
│   ├── officer/                      # Dashboard-specific components
│   ├── graph/                        # Force-directed graph, entity panels
│   └── shared/                       # Cross-module (charts, tables, status stepper)
├── lib/
│   ├── api-client.ts                 # Typed fetch wrapper, base URL, auth header injection
│   ├── query-keys.ts                 # Centralized React Query key factory
│   └── auth.ts                       # Token storage/refresh helpers
├── hooks/                            # Custom hooks wrapping React Query calls per domain
├── store/                            # Zustand stores (UI-only state)
└── types/                            # Shared TypeScript types mirroring backend Pydantic schemas
```

### 6.2 Routing Strategy

Route groups (`(citizen)`, `(officer)`, `(intelligence)`) map directly to the three PRD modules and to distinct layout/theme contexts (light-mode citizen experience vs. dark-mode SOC-style dashboards), while sharing the same Next.js app and deployment — avoiding the operational overhead of 3 separate frontend deployments.

### 6.3 Component Hierarchy Pattern

Each screen follows a consistent three-layer composition: **Page component** (data-fetching via hooks, layout composition) → **Feature components** (e.g., `ThreatScoreGauge`, `ComplaintTable`, `FraudGraphCanvas` — domain-aware, still presentation-focused) → **UI primitives** (`Card`, `Badge`, `Button` — no domain awareness, fully reusable across all 3 modules). This ensures the severity-band badge, for instance, is one component styled once and reused identically across Citizen, Officer, and Intelligence views (design-system consistency, PRD §15).

### 6.4 State Management

- **Server state (reports, complaints, graph data):** TanStack Query exclusively. Report-processing screens use `refetchInterval` polling against `GET /reports/{id}/status` until `status === 'complete'`, then switch to the full result query — no manual polling/interval code written by hand.
- **Client/UI state (graph zoom/pan, active filters, modal open state):** Zustand, scoped per-module store — never mixed with server data to avoid stale-cache bugs.
- **No global Redux store** — deliberately avoided; the two state categories above cover all needs without a third abstraction layer.

### 6.5 Authentication Flow (Frontend)

1. User submits credentials to `POST /api/v1/auth/login`.
2. Backend returns a short-lived **access token** (JWT, ~15 min expiry) and a longer-lived **refresh token** (httpOnly cookie).
3. Access token stored in memory (not localStorage, to reduce XSS exposure) via an auth context provider; attached as `Authorization: Bearer` header by `api-client.ts` on every request.
4. On a `401` response, the API client automatically attempts a silent refresh via `POST /api/v1/auth/refresh` (using the httpOnly cookie) and retries the original request once; on refresh failure, redirects to `/login`.
5. Route-level guards (middleware in `app/layout.tsx` per route group) check the user's `role` claim (`citizen` / `officer` / `analyst`) and redirect unauthorized roles away from Officer/Intelligence route groups.

---

## 7. API Design

All endpoints are versioned under `/api/v1`. All authenticated endpoints require `Authorization: Bearer <access_token>` unless marked **Public**. All error responses follow the standard envelope defined in §11.

### 7.1 Authentication

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/register` | POST | Create a citizen account. **Request:** `{email, password, name}`. **Response:** `201 {user_id, email}`. **Auth:** Public. **Errors:** `400` (validation), `409` (email exists) |
| `/api/v1/auth/login` | POST | Authenticate. **Request:** `{email, password}`. **Response:** `200 {access_token, expires_in}` + refresh cookie set. **Auth:** Public. **Errors:** `401` (invalid credentials) |
| `/api/v1/auth/refresh` | POST | Refresh access token via cookie. **Request:** none (cookie-based). **Response:** `200 {access_token, expires_in}`. **Auth:** Refresh cookie required. **Errors:** `401` (expired/invalid refresh token) |
| `/api/v1/auth/logout` | POST | Invalidate refresh token. **Response:** `204`. **Auth:** Bearer. **Errors:** `401` |
| `/api/v1/auth/me` | GET | Current user profile + role. **Response:** `200 {id, email, name, role}`. **Auth:** Bearer. **Errors:** `401` |

### 7.2 Citizen Fraud Shield (Reports)

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/reports` | POST | Create a new report (multipart: `source_type`, `file` or `text_content`). **Response:** `202 {report_id, status: "queued"}`. **Auth:** Bearer (citizen). **Errors:** `400` (missing/invalid input type), `413` (file too large), `422` (validation) |
| `/api/v1/reports/{id}` | GET | Fetch full processed report (threat score, category, entities, explainability). **Response:** `200 {ReportDetail}` or `202 {status}` if still processing. **Auth:** Bearer (owner or officer role). **Errors:** `401`, `403`, `404` |
| `/api/v1/reports/{id}/status` | GET | Lightweight polling endpoint. **Response:** `200 {status, current_stage}`. **Auth:** Bearer (owner). **Errors:** `401`, `403`, `404` |
| `/api/v1/reports/{id}/chat` | POST | Ask the Knowledge Intelligence Agent a question in context of this report. **Request:** `{message, session_id}`. **Response:** `200 {answer, citations[]}`. **Auth:** Bearer (owner). **Errors:** `400`, `404`, `429` (rate limited), `503` (LLM unavailable) |
| `/api/v1/reports/{id}/download` | GET | Generate/download the PDF investigation report. **Response:** `200` (application/pdf stream) or `202` if package not yet generated (triggers generation). **Auth:** Bearer (owner or officer). **Errors:** `401`, `403`, `404` |
| `/api/v1/reports/{id}/escalate` | POST | Push report into officer complaint queue. **Response:** `200 {case_id, status: "escalated"}`. **Auth:** Bearer (owner). **Errors:** `404`, `409` (already escalated) |
| `/api/v1/reports/{id}/history` *(alias)* | — | *(see `/users/{id}/history` below — history is user-scoped, not report-scoped)* | |
| `/api/v1/users/{id}/history` | GET | Citizen's own report history, paginated. **Query:** `?page=&page_size=`. **Response:** `200 {items[], total, page}`. **Auth:** Bearer (self only). **Errors:** `401`, `403` |
| `/api/v1/alerts/public` | GET | Trending public scam alerts feed. **Query:** `?category=&limit=`. **Response:** `200 {alerts[]}`. **Auth:** Public. **Errors:** none expected (empty array on no data) |

### 7.3 Law Enforcement Dashboard

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/dashboard/kpis` | GET | Aggregate KPI cards (total complaints, active cases, high-risk entities, rings detected, avg. threat score trend). **Response:** `200 {KpiSummary}`. **Auth:** Bearer (officer/analyst). **Errors:** `401`, `403` |
| `/api/v1/dashboard/trends` | GET | Time-series complaint trend data. **Query:** `?range=7d|30d|90d&category=`. **Response:** `200 {series[]}`. **Auth:** Bearer (officer/analyst). **Errors:** `400` (invalid range), `401`, `403` |
| `/api/v1/dashboard/emerging-trends` | GET | Categories with abnormal velocity increase. **Response:** `200 {trends[]}`. **Auth:** Bearer (officer/analyst). **Errors:** `401`, `403` |
| `/api/v1/dashboard/geo-breakdown` | GET | City/district complaint counts. **Response:** `200 {regions[]}`. **Auth:** Bearer (officer/analyst). **Errors:** `401`, `403` |
| `/api/v1/complaints` | GET | Paginated, filterable complaint table. **Query:** `?category=&city=&score_min=&score_max=&status=&date_from=&date_to=&search=&page=`. **Response:** `200 {items[], total, page}`. **Auth:** Bearer (officer/analyst). **Errors:** `400` (invalid filter), `401`, `403` |
| `/api/v1/complaints/{id}` | GET | Full investigation view: AI summary, entities, evidence, linked complaints. **Response:** `200 {ComplaintDetail}`. **Auth:** Bearer (officer/analyst). **Errors:** `401`, `403`, `404` |
| `/api/v1/complaints/{id}/assign` | POST | Assign complaint to an officer. **Request:** `{officer_id}`. **Response:** `200 {case_id, assigned_officer_id}`. **Auth:** Bearer (officer with assign permission). **Errors:** `403`, `404`, `422` |
| `/api/v1/complaints/{id}/intelligence-package` | POST | Generate case-level Intelligence Package. **Response:** `201 {package_id}`. **Auth:** Bearer (officer/analyst). **Errors:** `404`, `409` (already generating), `500` (generation failure) |
| `/api/v1/complaints/{id}/export` | GET | Export complaint as PDF/CSV. **Query:** `?format=pdf|csv`. **Response:** `200` (file stream). **Auth:** Bearer (officer/analyst). **Errors:** `400` (invalid format), `404` |

### 7.4 Threat Intelligence Engine

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/graph/overview` | GET | Cluster-level graph snapshot for initial canvas render. **Query:** `?top_n_clusters=`. **Response:** `200 {nodes[], edges[]}`. **Auth:** Bearer (officer/analyst). **Errors:** `401`, `403` |
| `/api/v1/graph/entity/{id}` | GET | Entity profile + immediate neighbors. **Response:** `200 {EntityProfile}`. **Auth:** Bearer (officer/analyst). **Errors:** `404` |
| `/api/v1/graph/entity/{id}/subgraph` | GET | Expanded risk network. **Query:** `?depth=1|2|3`. **Response:** `200 {nodes[], edges[]}`. **Auth:** Bearer (officer/analyst). **Errors:** `400` (depth out of range), `404` |
| `/api/v1/graph/entity/{id}/risk-score` | GET | Current computed risk score + contributing factors. **Response:** `200 {risk_score, factors[]}`. **Auth:** Bearer (officer/analyst). **Errors:** `404` |
| `/api/v1/graph/correlate` | GET | Related historical complaints for a given report's entities. **Query:** `?report_id=`. **Response:** `200 {correlated_reports[]}`. **Auth:** Bearer (officer/analyst). **Errors:** `404` |
| `/api/v1/graph/rings` | GET | Detected fraud ring clusters, ranked. **Query:** `?limit=`. **Response:** `200 {rings[]}`. **Auth:** Bearer (officer/analyst). **Errors:** `401`, `403` |
| `/api/v1/graph/intelligence-package` | POST | Generate ring-level Intelligence Package. **Request:** `{ring_id}`. **Response:** `201 {package_id}`. **Auth:** Bearer (officer/analyst). **Errors:** `404`, `500` |

### 7.5 Standard Error Object

Every non-2xx response returns:

```json
{
  "error": {
    "code": "REPORT_NOT_FOUND",
    "message": "No report exists with the given ID.",
    "request_id": "req_9f1c...",
    "details": {}
  }
}
```

---

## 8. Security

### 8.1 Authentication
- **JWT access tokens** (short-lived, 15 min), signed with an asymmetric key pair (RS256) so token verification does not require access to the signing secret — relevant if/when the system splits into multiple services.
- **Refresh tokens** stored server-side (hashed) with a `revoked_at` field, delivered to the client only via `httpOnly`, `Secure`, `SameSite=Strict` cookies — never accessible to client-side JavaScript.
- Password storage via `bcrypt` (or `argon2id` if available in the chosen environment), never reversible encryption.

### 8.2 Authorization
- **Role-based access control (RBAC)** with three roles for MVP: `citizen`, `officer`, `analyst`. Role is embedded as a JWT claim and re-validated server-side on every request (never trusted from client state alone).
- **Resource-level ownership checks**: a citizen can only fetch/download/chat on their own reports (`report.user_id == current_user.id`); officers/analysts can access any complaint, but write actions (assign, generate package) are restricted to officer/analyst roles only.
- Authorization checks implemented as a reusable FastAPI dependency (`require_role(...)`, `require_ownership(...)`) applied per-route, not duplicated inline in handler bodies.

### 8.3 Encryption
- **In transit:** TLS terminated at the deployment platform's edge/load balancer; internal traffic between API and worker processes stays within a private network boundary.
- **At rest:** Database-provider-managed encryption at rest for PostgreSQL and Neo4j Aura; object storage bucket encryption enabled by default.
- **Sensitive fields:** entity values (phone numbers, UPI IDs, bank accounts) are stored as-is (required for correlation queries) but access to raw entity data is restricted to authenticated officer/analyst roles at the API layer — not publicly queryable even for the "public alerts" feed, which only surfaces aggregated categories/counts, never raw entity values.

### 8.4 Secrets Management
- All credentials (LLM API keys, DB connection strings, JWT signing keys, object storage keys) loaded exclusively from environment variables via `pydantic-settings`, never hardcoded or committed.
- Local development uses a `.env` file (git-ignored); deployed environments use the hosting platform's managed secrets/environment variable store.
- No secret values are ever logged — the logging module (§12) includes an explicit redaction filter for known secret-shaped keys.

### 8.5 Rate Limiting
- Per-IP rate limiting on public/unauthenticated endpoints (`/auth/login`, `/auth/register`, `/alerts/public`) to mitigate brute-force and scraping.
- Per-user rate limiting on expensive AI-backed endpoints (`/reports` creation, `/reports/{id}/chat`) to prevent quota exhaustion by a single account — implemented via a Redis-backed sliding-window counter (already have Redis for the task queue, reused here).
- Rate-limit violations return `429` with a `Retry-After` header.

### 8.6 Input Validation
- Every request body validated against a Pydantic model at the FastAPI routing layer — invalid payloads never reach business logic.
- File uploads validated for: MIME type allow-list (images: jpeg/png; audio: mp3/wav/m4a), maximum file size, and a basic content-sniffing check (not just trusting the file extension) before being handed to Agent 1.
- All user-supplied text is treated as untrusted when constructing LLM prompts — text is inserted into clearly delimited template slots (never string-concatenated into instruction-bearing positions) to reduce prompt-injection risk against the RAG/chat agent.

### 8.7 Logging & Audit Trail (Security-Relevant)
- All authentication events (login success/failure, token refresh, role-check denials) logged with user ID (where known), IP, and timestamp — feeding a basic audit trail appropriate for a public-safety system, expanded post-hackathon into a full immutable audit log.

---

## 9. Database Architecture

*(No schema definitions here — see PRD §13 for table-level schema. This section covers architectural role and access patterns only.)*

### 9.1 Relational Database (PostgreSQL) — System of Record

PostgreSQL holds all transactional, authoritative state: users, reports, threat scores, cases, evidence references, alerts, and knowledge base content (with the `pgvector` extension co-located rather than a separate vector store). It is the **source of truth** — any data present in the graph store is a derived/mirrored representation of relationships that ultimately trace back to rows in Postgres. All writes that must be durable and immediately consistent (report submission, case assignment, package generation) go through Postgres first.

**Access pattern:** accessed exclusively through `data/postgres_client.py`, using async SQLAlchemy sessions. Read-heavy dashboard queries (KPIs, trends) are served from **materialized views or scheduled aggregation tables** refreshed by a background job, not computed via live aggregate queries on every dashboard page load — keeping dashboard response times stable regardless of report volume growth.

### 9.2 Graph Database (Neo4j) — Correlation & Relationship Intelligence

Neo4j exists specifically because relational databases handle multi-hop relationship traversal ("entities within 2 hops of this UPI ID") poorly at scale — such queries require recursive CTEs that degrade quickly as the entity/relationship table grows. Neo4j is the **derived, specialized index** for exactly one class of query: graph traversal, correlation, and clustering. It is kept in sync with Postgres via the Agent 5 write path (every new report's extracted entities are written to both systems within the same pipeline stage) — Neo4j is never the sole holder of any fact that doesn't also exist in Postgres, so it can be rebuilt from Postgres if ever necessary.

**Access pattern:** accessed exclusively through `data/neo4j_client.py`, issuing parameterized Cypher queries. Community-detection (Louvain) runs via Neo4j's native Graph Data Science library, keeping the clustering computation co-located with the graph data rather than pulling the graph into application memory.

### 9.3 Vector Store (pgvector) — Retrieval for RAG

The vector store holds embeddings of the regulatory knowledge base only (not report content), used exclusively by Agent 3 for similarity search at chat time. Because it lives as an extension inside the same PostgreSQL instance, it requires no separate connection pool, no separate backup strategy, and no cross-database consistency concerns — a deliberate scope-reduction given the actual corpus size (regulatory documents, not millions of user-generated documents) does not require a dedicated vector database's specialized scaling characteristics.

### 9.4 Cross-Store Consistency Strategy

Since Postgres is authoritative and Neo4j is derived, the system tolerates **brief eventual consistency** between the two (target: sub-second in normal operation, since Agent 5's graph write happens synchronously within the same pipeline stage) rather than requiring distributed transactions across two different database technologies — a two-phase commit across Postgres and Neo4j would add complexity disproportionate to the actual consistency requirement (a graph correlation being a few seconds stale is operationally acceptable; a lost case record is not).

---

## 10. Deployment Architecture

### 10.1 Cloud & Hosting Strategy

- **Frontend:** deployed to a managed static/edge hosting platform (e.g., Vercel) with automatic preview deployments per pull request — zero server management, global CDN for asset delivery.
- **Backend (API + worker processes):** deployed as python processes running under a system manager (like systemd) directly on a managed virtual machine or cloud platform (e.g., Render, Railway, or a cloud VM running the Uvicorn server and python worker entrypoint) — chosen specifically to avoid containerization and Kubernetes overhead disproportionate to a 2-person, 18-day project.
- **PostgreSQL:** managed instance (e.g., the hosting platform's managed Postgres, or a provider like Neon/Supabase) with automated daily backups.
- **Neo4j:** Neo4j Aura (managed, free/professional tier) — avoids the team having to operate graph database infrastructure themselves.
- **Redis:** managed Redis instance (e.g., the hosting platform's managed Redis or Upstash) for both the task queue and rate-limit/cache storage.
- **Object storage:** S3-compatible bucket for raw uploads, accessed via signed URLs (uploads go client→signed-URL→bucket directly where feasible, to avoid routing large audio files through the API process itself).

### 10.2 Service Execution

The API and worker run directly in a python virtual environment on the host machine. The API runs using `uvicorn app.main:app` and the worker runs using `python -m app.workers.worker_entrypoint`. Both are managed as system services (e.g. systemd or PM2) to ensure automatic restarts on failure, guaranteeing both processes always run identical code/dependency versions.

### 10.3 CI/CD

- **CI (on every pull request):** lint (ruff/eslint), type-check (mypy/tsc), and unit tests (pytest/vitest) — must pass before merge.
- **CD:** merge to `main` triggers automatic deployment of the frontend (via the hosting platform's git integration) and a git-pull followed by a virtual environment reload and rolling restart of the API and worker processes on the backend server.
- Environment separation: a `staging` environment (separate DB instances, separate LLM API key with lower rate limits) mirrors `production` for pre-demo verification, given the criticality of a stable environment on judging day.

### 10.4 Scaling Strategy (Documented, Not Fully Exercised at Hackathon Scale)

- **API layer:** stateless by design (no in-memory session state — auth is JWT-based) — horizontally scalable by simply increasing the container replica count behind the load balancer.
- **Worker layer:** independently scalable from the API layer; additional worker replicas consume from the same Redis queue with no code change, directly addressing report-processing throughput under load.
- **Database layer:** vertical scaling (larger managed instance tier) is the first lever; read replicas for Postgres are the documented next step for dashboard-read-heavy scaling, not required at MVP data volumes.

### 10.5 Monitoring at the Deployment Layer

Health-check endpoints (`GET /healthz` — liveness; `GET /readyz` — checks DB/Redis/Neo4j connectivity) are exposed for the hosting platform's automated restart-on-failure behavior, and are the first thing verified in the deployment pipeline before traffic is routed to a new container revision.

---

## 11. Error Handling

### 11.1 System-Wide Principles

1. **Every error surfaced to the client uses the standard error envelope** (§7.5) — no raw stack traces, no unstructured error strings, ever reach the frontend.
2. **Partial success is preferred over total failure** wherever the pipeline allows it: as established in §4.2, a citizen report that succeeds through Agent 2 (threat score) but fails at Agent 5 (graph correlation) still returns a usable, complete-enough result to the citizen, marked with a `status: "complete_partial"` and a non-blocking `warnings[]` field — the user is never shown a dead end.
3. **Distinguish user errors from system errors** at the exception-handling layer: validation failures (`4xx`) are expected and handled gracefully with specific messages; unexpected exceptions (`5xx`) are caught by a global handler, logged with full context (§12), and returned to the client as a generic, non-leaky message plus a `request_id` the user/support can reference.

### 11.2 Agent-Level Failure Handling

Each agent's specific degraded-mode behavior is defined in the PRD (§9) — this section specifies the **mechanism**, not the per-agent policy:
- Every agent invocation is wrapped in a bounded retry (max 2 attempts, exponential backoff) at the orchestration layer for transient failures (timeouts, rate limits).
- Each agent module raises one of a small set of **typed exceptions** (`AgentTimeoutError`, `AgentOutputValidationError`, `AgentUpstreamServiceError`) rather than letting raw SDK/library exceptions propagate — the orchestration layer catches these typed exceptions specifically and applies the documented fallback behavior (e.g., degraded-mode scoring for Agent 2) rather than a blanket catch-all.
- A **dead-letter queue** captures any task that exhausts retries, for manual/automatted inspection — ensuring failed reports are never silently lost, only flagged for follow-up.

### 11.3 Frontend Error Handling

- React Query's built-in error boundaries surface API errors as inline, contextual UI states (e.g., "We couldn't process this file — try a clearer screenshot") rather than generic crash screens.
- A top-level error boundary catches any unhandled rendering exception and displays a recovery screen with a "reload" action, preventing a single component failure from blanking the entire dashboard during a live demo.

---

## 12. Logging, Monitoring, Observability, Tracing

### 12.1 Structured Logging

- All backend logs emitted as **structured JSON** (not free-text), including at minimum: timestamp, log level, `request_id`, `user_id` (if authenticated), module/agent name, and message.
- A single `core/logging.py` configures this globally — no module configures its own logger independently, ensuring consistent format across the API, orchestration layer, and all 6 agents.
- Secret-redaction filter (per §8.4) applied at the logging handler level, not left to individual call sites to remember.

### 12.2 Request Tracing

- Every incoming HTTP request is assigned a `request_id` (generated at the API gateway middleware layer if not already present in an `X-Request-ID` header) which is propagated through: the HTTP response, all log lines emitted during that request's lifecycle, and — critically — **through the task queue into the async agent pipeline**, so a single `request_id` (or a derived `pipeline_id`) can be used to trace a report's entire journey from upload through all 6 agents in the logs, even though execution spans multiple async task boundaries.

### 12.3 Monitoring & Metrics

- Key operational metrics exported (via a lightweight metrics endpoint or integration with the hosting platform's built-in metrics): request latency percentiles per endpoint, queue depth and task processing time per agent, LLM call latency/error rate per agent, and DB connection pool utilization.
- **Business-relevant metrics** (distinct from pure infra metrics) tracked for demo credibility: reports processed per hour, average end-to-end pipeline latency, current fraud-ring count, knowledge-base RAG hit rate (percentage of chat queries answered vs. "not covered") — these double as evidence, during judging, that the system is instrumented like a real intelligence platform, not a prototype.

### 12.4 Observability for AI-Specific Failure Modes

- Every LLM call logs: prompt template version used, token counts (input/output), latency, and whether structured-output parsing succeeded on the first attempt or required the error-correction retry (§4.4) — this data is what would drive prompt-iteration decisions post-hackathon and is valuable to show judges as evidence of AI-engineering maturity, not just AI-calling.
- RAG-specific observability: every chat query logs the retrieved chunk IDs and their similarity scores, enabling after-the-fact review of whether retrieval quality (not just generation quality) is the source of a bad answer.

### 12.5 Alerting

At MVP scale, alerting is manual (dashboard review), documented as a v2 requirement: threshold-based alerts on queue depth, error rate, and LLM cost spend, routed to a team notification channel.

---

## 13. Performance: Caching, Queueing, Background Jobs, Scaling

### 13.1 Caching Strategy

| What's Cached | Where | TTL / Invalidation |
|---|---|---|
| Dashboard KPIs (§7.3) | Redis | Refreshed by a scheduled background job every N minutes (not on every read); invalidated early on high-impact events (new report escalated) |
| Public alerts feed | Redis | Short TTL (a few minutes) — acceptable staleness for a "trending" feed |
| Graph overview snapshot (`/graph/overview`) | Redis | Refreshed after each graph-maintenance batch job (ring recomputation), not on every request — graph structure changes are inherently batched, not per-request |
| RAG embedding lookups | Not cached (query embeddings are cheap; pgvector index handles repeat-query performance natively) | — |
| JWT validation (public key) | In-memory, loaded once at process start | Process lifetime |

### 13.2 Queueing (Recap from §5.5/§4.2)

Two logical queues (`pipeline`, `graph_maintenance`) ensure the interactive report-processing path is never blocked by lower-priority background clustering work. Queue depth is a first-class monitored metric (§12.3) since it is the earliest indicator of the system falling behind under load — the single most important performance signal for a system whose core value proposition is *fast* threat scoring.

### 13.3 Background Jobs

| Job | Frequency | Purpose |
|---|---|---|
| Dashboard aggregate refresh | Every 2–5 minutes (configurable) | Keeps KPI/trend materialized views current without live-computing on every dashboard load |
| Graph clustering recomputation | Triggered after each new report's graph write, debounced/batched | Ring membership and risk scores stay current without recomputing the full graph on every single write |
| Knowledge base re-ingestion | Manual trigger (MVP); scheduled (v2) | Pulls in new regulatory advisories |
| Stale task cleanup | Hourly | Requeues or dead-letters any task stuck in a processing state beyond its expected max duration (guards against a crashed worker silently orphaning a task) |

### 13.4 Scaling Levers (Priority Order for Post-Hackathon Growth)

1. **Add worker replicas** — directly increases report-processing throughput, zero code change (§10.4).
2. **Add API replicas** — handles increased concurrent dashboard/citizen traffic, zero code change (stateless design).
3. **Move dashboard reads to a Postgres read replica** — isolates read-heavy officer dashboard traffic from write-heavy report intake.
4. **Split the monolith along agent boundaries into real services** — only justified once a specific agent (most likely Agent 5's graph clustering) becomes a demonstrated bottleneck under real load; the modular folder structure (§5.2) is designed specifically to make this split mechanical rather than a rewrite.

---

## 14. Technical Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Async task queue (RQ) proves too limited if pipeline branching grows more complex than the current linear+one-fanout shape | Low | Medium | Architecture already isolates orchestration logic in `orchestration/tasks.py`; migrating to Celery (which supports richer chains/chords) touches only this module, not agent internals |
| Neo4j Aura free-tier connection/resource limits hit during demo-day load testing | Medium | Medium | Load-test against Aura limits by Day 8 (per PRD roadmap); fall back plan is a paid tier bump (config-only change, no code change) |
| LLM structured-output parsing failures under edge-case inputs (garbled OCR text, code-mixed language) | Medium | Medium | Retry-with-correction mechanism (§4.4) plus deterministic regex extractors as a non-LLM fallback for the highest-value entity types (§4.6), so entity extraction degrades gracefully even if the LLM-based NER pass fails |
| Two-container deployment (API + worker from one image) drifts if environment variables differ between them | Low | Medium | Single shared `config.py` loaded identically by both entrypoints; CI includes a check that both entrypoints boot successfully against the same env file |
| pgvector performance degrades if the knowledge base grows unexpectedly large | Low | Low | Corpus size is bounded and known (regulatory documents, not user-generated content) — documented migration path to a dedicated vector DB exists (§3) if corpus scope changes |
| Signed-URL direct-to-storage uploads add frontend complexity under the 18-day deadline | Medium | Low | Fallback: route uploads through the API process directly for MVP (simpler, slightly less scalable) with the signed-URL pattern documented as the immediate post-hackathon optimization, not a blocking MVP requirement |
| Request tracing across async task boundaries (§12.2) is non-trivial to implement correctly under time pressure | Medium | Low | Scoped down for MVP to propagating `request_id` via task arguments/Redis job metadata (simple, manual) rather than a full distributed-tracing library integration (e.g., OpenTelemetry), which is documented as the v2 upgrade |

---

## Appendix: Cross-Reference to PRD

This TRD implements the modules, agents, and data model defined in the Truvia PRD v1.0. Specific cross-references:
- Agent responsibilities/contracts: PRD §9 (business behavior) ↔ TRD §4 (technical mechanics)
- Database tables: PRD §13 (schema) ↔ TRD §9 (architectural role, no schema repetition)
- Technology choices: PRD §14 (product-level justification) ↔ TRD §3 (engineering-execution rationale)
- Roadmap/timeline: PRD §16 (18-day plan) governs sequencing; this TRD specifies *what* is built at each milestone, not *when*
