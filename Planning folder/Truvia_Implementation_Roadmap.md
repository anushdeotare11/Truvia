# Truvia
## Implementation Roadmap
### v1.0 — 18-Day Build Plan for a 2-Developer Team

**Prepared by:** Senior Engineering Manager
**References used as source of truth:** PRD v1.0, TRD v1.0, App Flow v1.0, UI/UX Design Brief v1.0, Backend Schema v1.0
**Objective:** Ship a feature-complete, deployed, demo-hardened MVP that maximizes score against the hackathon's judging rubric (PRD §18: Technical Depth, Innovation, Real-World Feasibility, Design & UX, Problem-Statement Alignment, Presentation-Readiness) — not maximum feature count.

---

## Table of Contents

1. Team & Operating Model
2. Git Strategy, Branching, Folder Structure
3. Coding Standards
4. Documentation Strategy
5. Definition of Done
6. Development Phases & Milestones
7. Critical Path
8. Daily Breakdown (Day 1–18) — full task tables
9. Testing Strategy & Checklist
10. Deployment Plan
11. Risk Management
12. Day-by-Day Checklist
13. Sprint Board
14. Final Submission Checklist
15. Demo Readiness Checklist
16. Bug Triage Checklist

---

## 1. Team & Operating Model

**Dev A — Backend/AI/Data.** Owns: FastAPI app, all 6 agents, PostgreSQL schema + migrations, Neo4j, pgvector, background workers, deployment of backend services.
**Dev B — Frontend/UX/Integration.** Owns: Next.js app, design system/component library, all three modules' UI, charts, graph canvas, frontend deployment, demo video/deck.

**Why this split, not a vertical-slice split:** the PRD's own 18-day table already uses this backend/frontend split (§16), and the TRD's modular-monolith architecture (§5.1) draws internal boundaries that map cleanly to it — `agents/*`, `data/*`, `orchestration/*` are Dev A's world; `app/(citizen|officer|intelligence)/*`, `components/*` are Dev B's. A vertical split (each dev owns one full module end-to-end) would force both developers to context-switch between Python and TypeScript daily, which costs more time than it saves for a 2-person team.

**Daily sync:** one 15-minute EOD sync (per PRD §17 risk mitigation), same time every day, covering: what shipped, what's blocked, tomorrow's plan, any API-contract change. Contract changes (request/response shape) are the #1 cross-dev risk — any change to a `schemas/` Pydantic model or a documented endpoint contract is called out explicitly in this sync, not discovered via a broken frontend build the next day.

**Communication artifact:** the API contract table in TRD §7 is the single shared source of truth for request/response shapes. Neither dev "just wires it up" from memory — any change gets a one-line update to that table before either side writes code against it.

---

## 2. Git Strategy, Branch Strategy, Folder Structure

### 2.1 Repository Structure

Two repositories, matching the TRD's two deployables (`truvia-backend`, `truvia-frontend`) rather than a monorepo — chosen because the two apps have entirely disjoint toolchains (Python/FastAPI vs. TypeScript/Next.js), disjoint CI pipelines, and disjoint deployment targets; a monorepo would add tooling overhead (path-based CI triggers, shared lockfile concerns) with no benefit for a 2-person team where Dev A and Dev B rarely touch the other's repo.

```
truvia-backend/        (per TRD §5.2 — full structure already specified there)
truvia-frontend/       (per TRD §6.1 — full structure already specified there)
truvia-docs/           (this roadmap, PRD, TRD, App Flow, Design Brief, Schema — versioned docs, not code)
```

### 2.2 Branching Model

**Trunk-based development with short-lived feature branches** — not GitFlow. GitFlow's release/hotfix branch ceremony is built for teams cutting periodic releases; Truvia ships continuously to one demo environment for 18 days, so the overhead is pure waste.

```
main                      ← always deployable; every merge triggers CI + auto-deploy to demo env
├── feat/agent-1-ocr-stt          (Dev A)
├── feat/fraud-shield-upload-ui   (Dev B)
├── feat/graph-canvas             (Dev B)
├── fix/threat-score-rounding     (either)
```

- Branch naming: `feat/<short-description>`, `fix/<short-description>`, `chore/<short-description>`.
- **One branch = one PR = one reviewable unit**, target: mergeable within a day. No branch survives more than ~2 days — given the timeline, a stale branch is a bigger risk than an imperfect PR.
- Every PR requires **one review from the other developer** before merge, even under time pressure — this is the cheapest possible defect-catching mechanism available to a 2-person team and should not be skipped even on Day 17. Reviews should take under 10 minutes; if a PR is too large to review in 10 minutes, it should have been split.
- `main` is protected: no direct pushes, CI must pass (lint + type-check + unit tests) before merge.
- Merge strategy: **squash merge** — keeps `main`'s history one commit per feature, readable for anyone (including judges, if the repo is shown) skimming commit history.

### 2.3 Commit Message Convention

Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`) — lightweight enough to not slow anyone down, but produces a commit log that itself demonstrates engineering discipline to judges reviewing the repo.

### 2.4 Folder Structure

Both folder structures are already fully specified and are **not repeated here** — see:
- Backend: TRD §5.2 (`truvia-backend/` tree — `app/api`, `app/agents`, `app/orchestration`, `app/data`, `app/models`, `app/schemas`, `app/core`, `app/workers`, `alembic/`, `tests/`)
- Frontend: TRD §6.1 (`truvia-frontend/` tree — `app/(citizen)`, `app/(officer)`, `app/(intelligence)`, `components/ui`, `lib/`, `hooks/`, `store/`, `types/`)

This roadmap's task tables (§8) reference these paths directly so both developers know exactly where each day's work lands.

---

## 3. Coding Standards

### 3.1 Backend (Python/FastAPI)

- **Formatting/linting:** `ruff` (format + lint in one tool, fast enough to run on every save) — configured as a pre-commit hook, not just a CI check, so style debates never happen in review.
- **Type checking:** full type hints on every function signature; `mypy` run in CI (non-blocking warning-only for Days 1–14 to avoid slowing early velocity, **blocking** from Day 15 onward during the hardening phase).
- **Pydantic schemas** are the single source of truth for request/response shapes — never hand-write a dict and hope it matches; every endpoint's response model is declared on the route decorator (`response_model=...`) so FastAPI's auto-generated OpenAPI docs (TRD §14's stated benefit) stay accurate for free.
- **Agent code is framework-agnostic** (TRD §5.3) — every `agents/*/service.py` function must be callable and unit-testable with a plain Python call, no FastAPI request object, no queue context. This is a hard rule, not a preference: it's what makes Day 3's "first end-to-end score demo" milestone testable in isolation before the queue/API wiring exists.
- **No bare `except:`** — every exception handler catches a specific exception type; PRD's agent-level failure-handling contracts (e.g., Agent 1's `low_confidence` flag, Agent 2's `degraded_mode` flag) are implemented as explicit typed exceptions/results, never silent swallowing.

### 3.2 Frontend (TypeScript/Next.js)

- **Formatting/linting:** `eslint` + `prettier`, pre-commit hook, same rationale as backend.
- **No `any`** — every API response is typed via the shared `types/` directory, hand-mirrored from the backend's Pydantic schemas (TRD §6.1 already specifies this file exists; keeping it hand-synced, not codegen'd, is the right call for 18 days — codegen tooling setup costs more time than it saves at this scale).
- **Component conventions:** every component follows the three-layer pattern from TRD §6.3 (Page → Feature → UI primitive) — a new component's first question is always "which layer does this belong in," preventing the common hackathon anti-pattern of one giant page component doing everything.
- **No inline hex colors** — every color reference goes through the design-token system (Design Brief §3); this is what keeps severity-badge colors consistent across all three modules without manual re-checking.
- **Server state only via TanStack Query, UI state only via Zustand** (TRD §6.4) — no component reaches for `useState` to cache server data.

### 3.3 Shared Standards

- Every PR description answers three questions: *What changed? Why? How was it tested?* — even a one-line answer to each is enough; the point is forcing a 30-second self-review before requesting the other dev's time.
- No commented-out code merged to `main` — delete it (git history preserves it if ever needed).
- No `TODO` comments without a linked issue/task reference — an untracked TODO is how scope quietly creeps past the PRD's strict MVP boundary (PRD §17 risk register explicitly calls scope creep the highest-likelihood, highest-impact risk).

---

## 4. Documentation Strategy

- **Living documents, not a Day-18 scramble:** the PRD, TRD, App Flow, Design Brief, Backend Schema, and this Roadmap are the documentation — no separate "documentation phase" exists in the schedule because none is needed if these stay current. Any deviation from a documented contract (an API shape change, a new table, a schema tweak) gets a one-line edit to the relevant doc in the same PR that makes the change, not a "we'll write it up later."
- **Auto-generated API docs:** FastAPI's OpenAPI/Swagger UI (free, from `response_model` typing per §3.1) serves as the always-current API reference — judges or teammates can hit `/docs` on the deployed backend and see the real, live contract, which is itself a small "technical depth" signal (PRD §18).
- **README per repo:** each of `truvia-backend`/`truvia-frontend` gets a README covering: local setup (env vars, local DB initialization, migration command), how to run tests, how to run the app — written on Day 1 as part of scaffolding, not retrofitted.
- **Inline code comments:** reserved for *why*, never *what* — a comment explaining why Agent 2 merges rule-based and LLM signals with a specific weighting is valuable; a comment restating `# increment counter` is noise and is not written.
- **Demo narrative doc:** a living one-page doc (owned jointly, updated as features land) tracking the exact demo script beats from PRD Appendix B — this becomes the literal presentation-day script, so it's written incrementally as each piece becomes demoable, not authored cold on Day 18.

---

## 5. Definition of Done

A task is **Done** only when all of the following are true — this checklist is the actual gate used in the daily sync, not aspirational:

- [ ] Code merged to `main` via a reviewed, squash-merged PR
- [ ] CI green (lint, type-check, relevant tests)
- [ ] Matches the documented contract (API shape per TRD §7, schema per Backend Schema doc, visual spec per Design Brief) — no silent deviation
- [ ] Manually exercised in the deployed demo environment at least once (not just `localhost`) once daily deploys are live (from Day 2 onward)
- [ ] Loading, error, and empty states implemented for anything that fetches data (Design Brief §10) — not deferred as "polish," since these are cheap to build alongside the happy path and expensive to retrofit
- [ ] No new `console.log`/`print` debug statements left in the diff
- [ ] Relevant doc updated if behavior deviates from what PRD/TRD/Schema/Design Brief currently say

---

## 6. Development Phases & Milestones

| Phase | Days | Goal |
|---|---|---|
| **Phase 0 — Setup & Foundations** | 1 | Architecture locked, repos scaffolded, both devs unblocked to build in parallel |
| **Phase 1 — Module 1 Core Loop** | 2–4 | Citizen Fraud Shield functional end-to-end on live backend |
| **Phase 2 — Knowledge & Graph Foundations** | 5–6 | RAG chat live, Neo4j online, graph writes flowing |
| **Phase 3 — Module 3 Core Loop** | 7–8 | Threat Intelligence Engine graph visualization + entity explorer functional |
| **Phase 4 — Module 2 Core Loop** | 9–11 | Officer Dashboard shell, complaint table, investigation view functional |
| **Phase 5 — Data & Intelligence Depth** | 12–14 | Realistic seeded dataset live, intelligence packages, predictive layer |
| **Phase 6 — Integration Hardening** | 15–16 | Cross-module navigation, full failure-handling, full polish/accessibility pass |
| **Phase 7 — Deployment & Submission Prep** | 17–18 | Deployed, QA'd, demo rehearsed, submission assets finalized |

Each phase ends on a **named milestone** (matching PRD §16) that is independently demoable — so a slip anywhere doesn't block showing the rest, which is itself a resilience story worth mentioning to judges under technical questioning.

---

## 7. Critical Path

The single chain of dependencies that, if delayed, delays the whole project:

```
Day 1: DB schema finalized
   → Day 2: Agent 1 (OCR/STT) built
      → Day 3: Agent 2 (Threat Detection) built, first score demo
         → Day 4: Module 1 wired to live backend (MILESTONE)
            → Day 5: Neo4j online, Agent 5 entity linking
               → Day 7: Fraud-ring clustering built
                  → Day 8: Module 3 core loop (MILESTONE)
                     → Day 12: Synthetic dataset seeded (unblocks realistic Module 2/3 demo visuals)
                        → Day 13: Intelligence Package generation (both case- and ring-level)
                           → Day 16: Feature-complete
                              → Day 17-18: Deploy, rehearse, submit
```

**Everything else is parallelizable around this spine.** Notably: Module 2's dashboard shell (Day 9) does **not** block on Module 3 — it's on the critical path only insofar as it needs the seeded dataset (Day 12) to look convincing, which is why Day 12's data seeding is deliberately scheduled mid-timeline rather than last (PRD §16 risk mitigation, carried forward unchanged here because it's correct). Authentication (built Day 1–2, see §8) is a **cross-cutting dependency** for every role-gated screen from Day 4 onward — it is treated as part of Phase 0/1, not a separate late phase, precisely because everything downstream needs it.

---

## 8. Daily Breakdown

Each day's table lists every task with **Owner, Estimated Hours, Dependencies, Output, Priority** (P0 = blocks the day's milestone / critical path, P1 = important but not blocking, P2 = nice-to-have/stretch).

### Day 1 — Architecture Locked

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Finalize Postgres schema (all 18 tables per Backend Schema doc); write Alembic initial migration | Dev A | 5 | Backend Schema doc | `alembic/versions/0001_initial.py`, migrated local DB | P0 |
| Provision Postgres (local installation + cloud dev instance); provision Neo4j Aura Free tier account | Dev A | 2 | — | Running DB instances, connection strings in `.env.example` | P0 |
| Scaffold `truvia-backend` repo: folder structure (TRD §5.2), `main.py`, `config.py`, CI pipeline (lint+test on PR) | Dev A | 2 | Repo created | CI green on empty scaffold | P0 |
| Build `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, JWT issuance (`core/security.py`) | Dev A | 3 | Users table migrated | Working auth endpoints, testable via curl | P0 |
| Scaffold `truvia-frontend` repo: Next.js App Router, route groups `(citizen)/(officer)/(intelligence)`, CI pipeline | Dev B | 2 | Repo created | CI green on empty scaffold | P0 |
| Build design tokens as Tailwind config + CSS variables (Design Brief §3), both theme modes | Dev B | 3 | Design Brief | `tailwind.config.ts`, `globals.css` with light/dark tokens | P0 |
| Build component-library skeleton: Button, Card, Badge, Input (Design Brief §6.1–6.4), Storybook or a bare `/dev/components` preview page | Dev B | 3 | Design tokens | First 4 reusable components, visually matching brief | P0 |
| Build auth pages (`/login`, `/register`) + `lib/auth.ts` token handling (TRD §6.5) | Dev B | 2 | Auth endpoints contract (can build against mocked response) | Working login form, stores token in memory | P1 |
| **EOD sync:** confirm API contract table (TRD §7) is the agreed shared reference | Both | 0.5 | — | Shared understanding, any Day-1 contract gaps resolved | P0 |

**Milestone: Architecture Locked.** ✅ if both repos build, CI is green, auth endpoints respond, and the DB schema is migrated.

---

### Day 2 — Input Pipeline Online

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build Agent 1 (Input Processing): OCR integration (managed Vision API), ASR integration (managed STT API), language detection, `CleanedInput` schema | Dev A | 5 | Day 1 scaffolding | `app/agents/input_processing/service.py`, unit-testable in isolation | P0 |
| Implement `low_confidence` flagging + graceful-degradation contract (PRD Agent 1 failure handling) | Dev A | 1.5 | Agent 1 core | Typed result object with `warnings[]` | P0 |
| Build `POST /api/v1/reports` (multipart upload) + object storage client (`data/storage_client.py`) | Dev A | 3 | Agent 1, evidence table migrated | Endpoint accepts screenshot/audio/text, returns `202 {report_id, status: queued}` | P0 |
| Build `evidence` table writes + file hash computation (chain-of-custody, Backend Schema §4.4) | Dev A | 1 | reports/evidence tables | Evidence rows created on upload | P1 |
| Build Citizen Fraud Shield upload UI: multi-modal dropzone with type auto-detection (Design Brief §14.1) | Dev B | 4 | Component library (Day 1) | Working dropzone UI, calls `POST /reports` | P0 |
| Build the live processing stepper component (Design Brief §9.3) — visual only, polling wired once status endpoint exists | Dev B | 3 | — | `ProcessingStepper` component with pending/active/complete states | P0 |
| Build `GET /api/v1/reports/{id}/status` polling endpoint | Dev A | 1 | reports table | Status endpoint live | P1 |
| Wire stepper to real polling via TanStack Query `refetchInterval` (TRD §6.4) | Dev B | 1.5 | Status endpoint | Stepper reflects real backend state | P1 |

**Milestone: Input Pipeline Online.** ✅ if a real screenshot/audio/text submission produces a `CleanedInput` object and the UI shows live processing stages.

---

### Day 3 — First End-to-End Score Demo

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build Agent 2 (Threat Detection): rule-based red-flag feature extractor + LLM structured-reasoning pass + weighted score merge | Dev A | 5 | Agent 1 output (`CleanedInput`) | `app/agents/threat_detection/service.py`, returns `ThreatAssessment` | P0 |
| Implement `degraded_mode` fallback (LLM failure → rule-based-only scoring) | Dev A | 1.5 | Agent 2 core | Typed fallback path, unit-tested | P0 |
| Write `threat_scores` table writes with `is_current` versioning logic (Backend Schema §4.5) | Dev A | 1.5 | threat_scores table, Agent 2 | Score persisted, versioned correctly | P0 |
| Wire orchestration: `reports` → Agent 1 → Agent 2 as a chained RQ task (`orchestration/tasks.py`) | Dev A | 2 | Agents 1+2, Redis queue set up | Full pipeline runs async end-to-end | P0 |
| Build `GET /api/v1/reports/{id}` full result endpoint | Dev A | 1 | threat_scores populated | Returns score, category, confidence, reasoning | P0 |
| Build Threat Score result screen: radial gauge (Design Brief §7.2), severity badge, category label, confidence meter | Dev B | 4 | Design tokens, chart lib (Recharts) installed | `ThreatScoreGauge` + result page layout | P0 |
| Build Explainability accordion (flagged phrases + reasoning, default-expanded per Design Brief §14.3) | Dev B | 2.5 | Result endpoint contract | Explainability panel component | P0 |
| Build Recommended Actions checklist card component | Dev B | 1.5 | — | Static/contract-driven action list UI | P1 |

**Milestone: First End-to-End Score Demo.** ✅ if a real upload flows through Agents 1→2 and renders a real threat score with explanation on screen — this is the demo's core "wow" moment and should be screen-recorded today as an early fallback asset (PRD §17 risk mitigation).

---

### Day 4 — Module 1 Core Loop Functional (MILESTONE)

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build Agent 4 (Entity Intelligence): NER/entity extraction from cleaned text, normalization logic (Backend Schema §4.6) | Dev A | 4 | Agent 1 output | `app/agents/entity_intelligence/service.py` | P0 |
| Wire Agent 4 into the orchestration chain (Agent 1 → 2 → 4), write to `entities`/`report_entities` tables | Dev A | 2 | Agent 4, entities tables | Entities persisted per report, silently feeding Module 3 (PRD §8.1) | P0 |
| Add role-guard middleware (citizen/officer/admin route protection, TRD §5.4) | Dev A | 1.5 | Auth (Day 1) | 403 responses for unauthorized role access | P0 |
| Full wiring pass: connect all Module 1 frontend screens to the live backend (remove any mocked data) | Dev B | 3 | Days 2–3 backend endpoints | Fully functional upload→process→result loop against real API | P0 |
| Build route-group guards on the frontend (redirect citizen away from `/officer/*`, `/intelligence/*`) per App Flow §2.5 | Dev B | 1.5 | Auth role claim | Working 403 redirect behavior | P0 |
| Build `/403` error page | Dev B | 0.5 | — | Error page matching Design Brief §10.2 | P1 |
| End-to-end manual test pass on the full Module 1 loop (upload each of 3 input types) | Both | 1.5 | All above | Bug list for any breaks, triaged immediately | P0 |

**Milestone: Module 1 Core Loop Functional.** This is PRD's own stated Day-4 milestone — confirmed unchanged. ✅ criteria: a citizen can upload any of the 3 input types and see a real, explained threat score, with entities silently extracted in the background.

---

### Day 5 — Graph Writes Live

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Set up Neo4j schema: constraints + indexes (Backend Schema §9.3) | Dev A | 1.5 | Neo4j Aura provisioned (Day 1) | Constraints/indexes applied | P0 |
| Build Agent 5 core: entity-linking logic, `Entity`/`Report` node writes, `CO_OCCURRED_IN`/`LINKED_TO` edge writes | Dev A | 5 | entities/report_entities tables, Neo4j schema | `app/agents/threat_intelligence/service.py` writing to Neo4j on every new report | P0 |
| Wire Agent 5 into the orchestration chain (async, non-blocking per PRD Agent 2's "historical-pattern boost" call) | Dev A | 2 | Agent 5 core | Graph writes happen within the same pipeline run | P0 |
| Build Recommended Actions → Report download (PDF) endpoint (`GET /reports/{id}/download`) | Dev A | 2 | Agent 6 not yet built — build a minimal HTML-to-PDF render of existing report data as a placeholder template | Downloadable PDF | P1 |
| Build the Recommended Actions UI final polish + wire Report Download button | Dev B | 2 | Download endpoint | Working download button | P1 |
| Build `POST /reports/{id}/escalate` + wire "Report to Police" confirmation dialog (App Flow §10.1) | Dev A / Dev B | 2 / 2 | cases table, case_reports table | Working escalation flow with confirmation modal | P1 |
| Start Threat Intelligence Engine scaffolding: install `react-force-graph`/Cytoscape.js, build empty canvas shell | Dev B | 2 | — | Blank but themeable graph canvas component | P1 |

**Milestone: Graph Writes Live.** ✅ if every new report visibly creates/updates nodes and edges in Neo4j (verifiable via Neo4j Browser query).

---

### Day 6 — RAG Chat Functional

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Ingest knowledge base documents: source RBI/CERT-In/NCRP/MHA/NPCI public advisories, populate `knowledge_base` table | Dev A | 3 | knowledge_base table | 15–30 seeded source documents | P0 |
| Build chunking pipeline (Backend Schema §10.3): paragraph-aware chunking, `knowledge_base_chunks` writes | Dev A | 2 | knowledge_base seeded | Chunked rows ready for embedding | P0 |
| Build embedding pipeline + pgvector HNSW index (Backend Schema §10.4), embed all chunks | Dev A | 2 | Chunking pipeline | Populated `embedding` column, index built | P0 |
| Build Agent 3 (Knowledge Intelligence / RAG): similarity search + LLM answer generation with citations | Dev A | 4 | Embeddings live | `app/agents/knowledge_intelligence/service.py` | P0 |
| Build `POST /reports/{id}/chat` endpoint | Dev A | 1 | Agent 3 | Chat endpoint live | P0 |
| Build AI Chat Assistant drawer UI (Design Brief §18.4): message bubbles, citation chips | Dev B | 4 | Chat endpoint contract | Working chat drawer, right-side desktop / full-screen mobile | P0 |
| Wire citation chips to show source name on hover/tap (Design Brief §14.4) | Dev B | 1.5 | Agent 3 citation format | Citation chip interaction | P1 |
| Build `/fraud-shield/history` and `/fraud-shield/alerts` screens (basic version) | Dev B | 2.5 | `GET /users/{id}/history`, `GET /alerts/public` (build minimal versions on Dev A side, 1 hr) | Working history + alerts screens | P1 |

**Milestone: RAG Chat Functional.** ✅ if the chat assistant answers a citizen's follow-up question with an accurate, cited response grounded in real regulatory text.

---

### Day 7 — Graph Visualization Online

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build fraud-ring clustering: Louvain community detection via Neo4j GDS library (Backend Schema §9.4) | Dev A | 4 | Graph writes live (Day 5) | `Ring` nodes + `MEMBER_OF` edges created by a scheduled/triggerable job | P0 |
| Build `GET /api/v1/graph/overview` (cluster-level snapshot, capped top-N per PRD's performance risk mitigation) | Dev A | 2.5 | Clustering job | Endpoint returns nodes/edges for canvas render | P0 |
| Build `GET /api/v1/graph/rings` | Dev A | 1 | Ring nodes | Ring list endpoint | P1 |
| Build the full force-directed graph canvas: node/edge rendering, entity-type color coding, risk-tier ring overlay, cluster hull rendering (Design Brief §8.1–8.2) | Dev B | 6 | Graph overview endpoint contract, canvas shell (Day 5) | Working `/intelligence/graph` page rendering real data | P0 |
| Build zoom/pan/click interactions + legend (Design Brief §8.3) | Dev B | 1.5 | Canvas rendering | Interactive canvas | P0 |

**Milestone: Graph Visualization Online.** ✅ if `/intelligence/graph` renders real clustered entity data from the seeded/live reports with correct color coding.

---

### Day 8 — Module 3 Core Loop Functional (MILESTONE)

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build correlation query API: `GET /graph/correlate?report_id=` (N-hop entity correlation, Backend Schema §9.4) | Dev A | 2.5 | Graph online | Correlation endpoint | P0 |
| Build `GET /graph/entity/{id}` and `GET /graph/entity/{id}/subgraph` | Dev A | 2.5 | Entities in graph | Entity profile + expanded neighbor endpoints | P0 |
| Build `GET /graph/entity/{id}/risk-score` (risk scoring logic — combination of occurrence count, ring membership, category severity) | Dev A | 2 | Entities/rings | Risk score endpoint | P1 |
| Build Entity Explorer full-page UI: header, tabs (Overview/Connections/Complaints/Risk History), local subgraph mini-view (Design Brief §16.2) | Dev B | 5 | Entity endpoints | Working `/intelligence/entity/[id]` page | P0 |
| Build Risk Network subgraph view + Entity Explorer Side Panel Overlay (lightweight preview from graph clicks, App Flow §10.10) | Dev B | 3 | Subgraph endpoint | Working side-panel preview + full profile navigation | P0 |
| Manual end-to-end test: click a node → preview panel → full profile → connections subgraph | Both | 1 | All above | Bug list, triaged | P0 |

**Milestone: Module 3 Core Loop Functional.** PRD's own stated Day-8 milestone, confirmed. ✅ criteria: an officer/analyst can land on the graph, click into any entity, and explore its connections and risk profile.

---

### Day 9 — Dashboard Shell Live

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build Agent 6 (Alert & Investigation): case/report summarization, package-generation templating groundwork | Dev A | 4 | Agents 1/2/4/5 outputs | `app/agents/alert_investigation/service.py` | P0 |
| Build `GET /api/v1/dashboard/kpis` (backed by a materialized view stub, Backend Schema §11.1) | Dev A | 2.5 | reports/cases/entities tables | KPI endpoint | P0 |
| Build `cases` table write paths: case creation on escalation, `case_reports` linking | Dev A | 2 | cases/case_reports tables | Escalated reports become real cases | P0 |
| Build Officer Dashboard shell: header, sidebar (per Design Brief §17.1–17.2), KPI card row layout | Dev B | 4 | Component library, KPI endpoint contract | Working `/officer/dashboard` shell | P0 |
| Build officer-role route guards + `/officer/dashboard` as officer landing page (App Flow §2.5) | Dev B | 1 | Auth roles | Correct role-based redirect | P0 |
| Build sidebar collapse behavior (tablet breakpoint, Design Brief §13.2) | Dev B | 1.5 | Sidebar built | Responsive sidebar | P1 |

**Milestone: Dashboard Shell Live.** ✅ if an officer logging in lands on a real dashboard shell with live KPI numbers (even if trends/tables aren't built yet).

---

### Day 10 — Officer Triage View Functional

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build `GET /api/v1/dashboard/trends`, `GET /api/v1/dashboard/emerging-trends` | Dev A | 3 | reports/threat_scores data | Trend + emerging-trend endpoints | P0 |
| Build `GET /api/v1/complaints` (paginated, filterable — category/city/score-range/date/status/search) | Dev A | 3.5 | reports/cases/threat_scores | Filterable complaint list endpoint | P0 |
| Add supporting indexes for filter columns (Backend Schema §11.1) | Dev A | 1 | Complaints endpoint | Query performance verified against seeded-scale data | P1 |
| Build Complaint Trends time-series chart + Emerging Scam Trends panel (Design Brief §7.2, §15.1) | Dev B | 3 | Trend endpoints | Dashboard home fully populated (minus geo/histogram) | P0 |
| Build Complaint Table with filter bar (chips, search, filters per Design Brief §15.2) | Dev B | 4 | Complaints endpoint | Working `/officer/complaints` screen | P0 |
| Build empty/loading/error states for the table (Design Brief §10) | Dev B | 1 | Table built | Full state coverage, not deferred | P1 |

**Milestone: Officer Triage View Functional.** ✅ if an officer can scan the dashboard, click an emerging trend, and see a correctly filtered complaint table.

---

### Day 11 — Module 2 Core Loop Functional (MILESTONE)

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build `GET /api/v1/complaints/{id}` (full investigation view: AI summary, entities, evidence, linked complaints) | Dev A | 3.5 | Agent 6, entities/evidence tables | Investigation detail endpoint | P0 |
| Build `POST /complaints/{id}/assign` + `officer_assignments` history writes | Dev A | 2 | cases/officer_assignments tables | Assignment endpoint with full history | P0 |
| Wire Agent 6's summarization into the investigation endpoint (real AI Summary, not placeholder) | Dev A | 2 | Agent 6 | Real LLM-generated case briefs | P0 |
| Build Investigation View UI: tabbed panel (Summary/Entities/Evidence/Timeline), context rail (Design Brief §15.3) | Dev B | 5 | Investigation endpoint contract | Working `/officer/complaints/[id]` page | P0 |
| Build Case Assignment modal (App Flow §10.2) | Dev B | 1.5 | Assign endpoint | Working assignment flow | P0 |
| Build cross-module deep link: "View in Graph" from Investigation View to Threat Intelligence Engine | Dev B | 1 | Entity Explorer (Day 8) | Working navigation link with entity context passed | P1 |

**Milestone: Module 2 Core Loop Functional.** PRD's own stated Day-11 milestone, confirmed. ✅ criteria: an officer can triage, open a full investigation view with a real AI summary, assign it, and jump into the graph.

---

### Day 12 — Populated Demo Data Live

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build/curate the synthetic dataset: 150–300 realistic complaints across categories/cities, grounded in real RBI/CERT-In advisory patterns (PRD §17 risk mitigation) | Dev A | 5 | All ingestion pipeline pieces working | Seed script + seeded demo database | P0 |
| Run the full pipeline against the seeded dataset (batch mode) to populate threat_scores/entities/graph/rings at realistic scale | Dev A | 2 | Seed data, full pipeline | Populated Neo4j graph with real multi-report rings | P0 |
| Spot-check clustering quality on seeded data; tune Louvain resolution parameter (PRD Appendix C open question, resolved here) | Dev A | 1.5 | Seeded graph | Tuned clustering parameter documented in `settings` | P1 |
| Build City/District Analysis chart + Threat Score Distribution histogram (Design Brief §7.2, §15.4) | Dev B | 3.5 | Seeded data available to demo against, geo-breakdown endpoint (Dev A, 1.5 hrs) | Working analytics charts | P0 |
| Visual QA pass across Modules 2 & 3 now that real, populated data is visible — catch any layout issues that only appear at realistic data volume | Both | 1.5 | Seeded data live | Bug list, triaged | P0 |

**Milestone: Populated Demo Data Live.** PRD's own stated Day-12 milestone, confirmed. ✅ criteria: every dashboard, table, and graph view looks like a real, populated production system, not an empty shell.

---

### Day 13 — Court-Ready Packages Functional

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build Intelligence Package generation (case-level): `POST /complaints/{id}/intelligence-package`, `package_json` assembly, content hash, PDF render | Dev A | 4.5 | Agent 6, intelligence_packages table | Case-level package generation working | P0 |
| Build Intelligence Package generation (ring-level): `POST /graph/intelligence-package` | Dev A | 3 | Ring/graph data, case-level package logic reused | Ring-level package generation working | P0 |
| Build Package Generation preview modal (App Flow §10.3, Design Brief §16.4) | Dev B | 3 | Package endpoints contract | Working preview modal, both entry points (Investigation View, Ring Detail) | P0 |
| Build Intelligence Package preview/export UI (rendered document view + download) | Dev B | 3 | Package generation live | Working preview + export | P0 |

**Milestone: Court-Ready Packages Functional.** ✅ if a real case and a real ring can each produce a downloadable, structured intelligence package.

---

### Day 14 — Predictive Layer Live

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Build predictive intelligence heuristics: trend-velocity calculation feeding `alerts` table, high-risk entity ranking | Dev A | 4 | Seeded data, entities/rings | Emerging-trend alerts generated from real velocity signals, not hardcoded | P0 |
| Build/finalize `GET /alerts/public` with real velocity-based trending data | Dev A | 1.5 | Alerts generation | Public alerts feed backed by real signal | P0 |
| Build notification writes for key events (package ready, case assigned, emerging trend) — `notifications` table | Dev A | 2 | notifications table | Backend notification records created | P1 |
| Build Public Scam Alerts feed UI (card grid, Design Brief §14.5) | Dev B | 2.5 | Alerts endpoint | Working alerts feed | P0 |
| Build Scam History UI polish (final pass) | Dev B | 1.5 | History endpoint (Day 6) | Polished history screen | P1 |
| Build header notification bell + dropdown (Design Brief §17.1) | Dev B | 2 | Notifications data | Working notification bell | P1 |
| Fraud Ring List & Detail screens (Design Brief §16.3) | Dev B | 3 | Rings endpoint (Day 7) | Working `/intelligence/rings` and detail pages | P0 |

**Milestone: Predictive Layer Live.** PRD's own stated Day-14 milestone, confirmed. ✅ criteria: emerging trends are computed from real data velocity, not hardcoded demo values.

---

### Day 15 — Full Pipeline Stress-Tested

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Integration hardening: failure handling across all 6 agents — verify every documented fallback path (OCR low-confidence, LLM timeout/degraded_mode, graph write failure retry) actually triggers correctly | Dev A | 5 | All agents built | Verified failure-handling matrix, bugs fixed | P0 |
| Load-test the seeded-scale complaint table / graph queries; add any missing indexes surfaced (Backend Schema §11) | Dev A | 2 | Seeded data | Verified acceptable query latency at demo scale | P1 |
| Enable `mypy` as a blocking CI check (§3.1) | Dev A | 1 | — | Type-check gate active for remaining days | P1 |
| Cross-module navigation polish: Module 2 ↔ 3 deep links, breadcrumbs, consistent back-navigation | Dev B | 3 | All modules built | Smooth cross-module flow | P0 |
| Full responsive QA pass: desktop/tablet/mobile per Design Brief §13, starting with Citizen Fraud Shield (must be fully mobile-functional per PRD scope) | Dev B | 4 | All Module 1 screens | Verified responsive behavior, bugs fixed | P0 |
| Toast/dialog/drawer consistency pass across all modules (Design Brief §18) | Dev B | 1.5 | — | Consistent interaction patterns everywhere | P1 |

**Milestone: Full Pipeline Stress-Tested.** PRD's own stated Day-15 milestone, confirmed.

---

### Day 16 — MVP Feature-Complete (MILESTONE)

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Bug fixes from Day 15's stress test | Dev A | 3 | Day 15 bug list | Resolved backend bugs | P0 |
| Performance pass on graph queries specifically (PRD §17 named risk) | Dev A | 2 | — | Verified graph query performance at capped top-N scale | P0 |
| Admin console minimum-viable build: `/admin/users`, `/admin/knowledge-base`, `/admin/system-health` (basic versions — App Flow §8, not previously scheduled but required for role-completeness) | Dev A / Dev B | 3 / 3 | users/knowledge_base tables | Functional admin screens (can be visually simpler than Modules 1–3) | P1 |
| Full UI polish pass: spacing, motion timing (Design Brief §9), empty/loading/error state final check across every screen | Dev B | 4 | All screens built | Polished, consistent UI | P0 |
| Full accessibility pass: contrast check, keyboard nav on Module 1 (PRD explicit requirement), focus states, `aria-label`s on icon buttons (Design Brief §12) | Dev B | 3 | All screens built | Verified WCAG AA compliance | P0 |
| Full manual regression pass: walk every screen in the sitemap (App Flow §1) as each of the 3 roles | Both | 2 | All above | Final bug list before deployment hardening | P0 |

**Milestone: MVP Feature-Complete.** PRD's own stated Day-16 milestone, confirmed. No new features are built after this point — Days 17–18 are buffer/hardening only, per PRD's explicit risk-mitigation philosophy (§16), carried forward unchanged.

---

### Day 17 — Deployed & Stable

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Deploy backend to production environment (managed host per TRD §10.1); configure production env vars/secrets | Dev A | 3 | Feature-complete backend | Live production backend URL | P0 |
| Environment hardening: rate limiting active, CORS locked to production frontend origin, secrets rotated from dev values | Dev A | 2 | Deployed backend | Hardened production config | P0 |
| Final data seeding pass on production DB (fresh, clean seeded dataset for demo day, not accumulated test cruft from development) | Dev A | 2 | Production DB live | Clean, demo-ready dataset | P0 |
| Deploy frontend to production (Vercel or equivalent); point at production backend URL | Dev B | 2 | Deployed backend | Live production frontend URL | P0 |
| Cross-browser QA (Chrome, Safari, Firefox at minimum) on the deployed production build | Dev B | 2.5 | Deployed frontend | Verified cross-browser behavior | P0 |
| Demo script rehearsal — full walkthrough of PRD Appendix B's demo narrative against the live production deployment | Both | 2 | Full deployment | Timed rehearsal, gaps identified | P0 |
| Record a full backup demo video (PRD §17 named risk mitigation for LLM API issues during live judging) | Both | 1.5 | Rehearsal complete | Backup video asset saved | P0 |

**Milestone: Deployed & Stable.** PRD's own stated Day-17 milestone, confirmed.

---

### Day 18 — Submission Ready (BUFFER DAY)

| Task | Owner | Hrs | Dependencies | Output | Priority |
|---|---|---|---|---|---|
| Fix any deployment issues surfaced during Day 17 rehearsal | Dev A | 2 | Day 17 bug list | Stable production deployment | P0 |
| Final data/config check on production (no stale test accounts, no debug flags left on) | Dev A | 1 | — | Clean production state | P0 |
| Final polish pass on any visual issues found during rehearsal | Dev B | 2 | Day 17 bug list | Polished final build | P0 |
| Finalize presentation deck (mapping directly to PRD §18 judging-criteria table, so every slide ties to a specific rubric line) | Both | 3 | — | Submission-ready deck | P0 |
| Finalize/re-record demo video if needed | Both | 2 | Deck finalized | Final video asset | P0 |
| Submission checklist walkthrough (§14 below) | Both | 1 | Everything above | Confirmed submission-ready | P0 |
| **Buffer/slack time** — reserved, not pre-assigned (PRD §16 explicit philosophy: Days 16–18 are hardening, not new-feature days) | Both | remaining | — | Absorbs any overrun from earlier days | — |

**Milestone: Submission Ready.** PRD's own stated Day-18 milestone, confirmed.

---

## 9. Testing Strategy & Checklist

### 9.1 Testing Philosophy

Given 18 days and 2 developers, **manual, scenario-driven testing is the primary QA mechanism** — a full automated test pyramid (unit + integration + E2E) is not achievable at this scale without cannibalizing feature-build time, and a hackathon judge evaluates a working demo, not a coverage percentage. That said, a **minimum automated floor** is non-negotiable because it protects the specific things that are expensive to catch manually and catastrophic to get wrong in front of judges:

- **Unit tests are mandatory** for: every agent's core logic (`agents/*/service.py` — testable in isolation per §3.1's framework-agnostic rule), the threat-score weighting/merge logic, the entity normalization/de-duplication logic, and the severity-band bucketing logic. These are the pieces where a silent logic bug produces a *plausible-looking but wrong* number — the worst possible failure mode during live judging.
- **Manual scenario testing** covers everything else: every screen in the App Flow sitemap, walked as each of the 3 roles, on each of the 3 breakpoints (Design Brief §13) — this is what Day 16's "full manual regression pass" and Day 4/8/11's milestone-gate manual tests are for.

### 9.2 Testing Checklist (run at every milestone gate, and again on Day 16)

**Module 1 — Citizen Fraud Shield**
- [ ] Upload each of 3 input types (screenshot, audio, paste-text) — each produces a correct threat score
- [ ] Low-confidence OCR/ASR input shows the degraded-mode banner, not a hard failure
- [ ] Explainability panel cites specific flagged phrases from the actual input, not generic boilerplate
- [ ] Recommended actions are category-appropriate (a "Digital Arrest" scam gets different guidance than a "Job Scam")
- [ ] AI Chat Assistant answers cite a real, correct source document
- [ ] Report download produces a valid, readable PDF
- [ ] "Report to Police" escalation correctly creates a `cases` row and is visible in the officer's Complaint Table
- [ ] Full flow works on a 375px-width mobile viewport with keyboard-only navigation

**Module 2 — Officer Dashboard**
- [ ] KPI numbers match a manual count against the seeded dataset (sanity check, not just "a number renders")
- [ ] Complaint Table filters (category/city/score/date/status/search) each independently narrow results correctly
- [ ] Investigation View's AI Summary is coherent and references the actual report content, not hallucinated detail
- [ ] Case assignment updates both `cases.assigned_officer_id` and creates an `officer_assignments` history row
- [ ] Intelligence Package generation produces a package whose entity/complaint counts match what's actually linked

**Module 3 — Threat Intelligence Engine**
- [ ] Graph canvas renders without performance degradation at the seeded dataset's scale
- [ ] Clicking a node opens the correct preview panel; "View Full Profile" navigates to the matching Entity Explorer
- [ ] A known-planted fraud ring in the seed data is actually detected as a cluster (not just "some cluster exists")
- [ ] Correlation search for a report's entities returns the actually-related historical complaints
- [ ] Ring-level Intelligence Package generation includes every report actually linked to that ring

**Cross-Cutting**
- [ ] Role guards correctly block citizen access to `/officer/*` and `/intelligence/*` (and vice versa where applicable)
- [ ] Every list/table screen's empty state renders correctly (test by filtering to zero results)
- [ ] Every screen's error-banner-with-retry works (test by temporarily killing a backend dependency)
- [ ] Dark/light theme renders correctly on every screen in its assigned theme, with WCAG AA contrast verified

---

## 10. Deployment Plan

| Step | When | Detail |
|---|---|---|
| Local dev environment | Day 1 | Local system services — Postgres, Redis; Neo4j via Aura Free tier (cloud, even in "local" dev, since Aura has no convenient local equivalent) |
| Continuous deploy to a shared demo environment | From Day 2 onward | Every merge to `main` auto-deploys (backend to managed host, frontend to Vercel) — per TRD §10.1; this is what makes the Day 4/8/11 milestone demos and the Definition of Done's "exercised in the deployed environment" gate possible |
| Production environment provisioning | Day 17 | Separate from the rolling demo environment — a clean production deploy with its own secrets, its own seeded dataset, hardened per §8's Day 17 tasks |
| Final production freeze | End of Day 17 rehearsal | No further feature changes to production after rehearsal passes; Day 18 touches production only for verified bug fixes |

**Rollback plan:** since deploys are continuous from Day 2, a bad merge is caught same-day by the Definition of Done's live-environment check — the rollback mechanism is simply reverting the offending PR and letting CI redeploy, not a manual production rollback procedure (unnecessary complexity at this scale, per TRD §10's stated philosophy of matching ops complexity to actual team size and timeline).

---

## 11. Risk Management

This roadmap inherits PRD §17's risk register in full and adds roadmap-specific mitigations:

| Risk | Roadmap-Level Mitigation |
|---|---|
| OCR/ASR accuracy on messy inputs | Day 12's seeded dataset deliberately includes a few "known-good" curated inputs alongside realistic messy ones, so the demo path always has a reliable primary example, with degraded-mode shown as a secondary, intentional example (not hidden) |
| Neo4j operational complexity | Day 5 is scoped tightly (schema + Agent 5 core only); if Neo4j setup itself stalls past Day 5's allotted hours, the documented fallback (PRD §17: Postgres recursive-CTE 1-hop correlation) is invoked immediately rather than let it eat into Day 6–7 |
| LLM API cost/rate limits during demo | Day 17 explicitly includes pre-warming/caching demo-path responses and recording a full backup video — both scheduled tasks, not "if we have time" |
| Scope creep across 3 modules | Every day's task table above is scoped directly from the PRD's MVP table (§6) — no task in this roadmap exists outside that scope; any new idea during build goes to a shared "Future Scope" note, never onto a day's task list |
| Two-person team illness/unavailability | The API contract table (TRD §7) and this roadmap's daily task breakdown together mean either developer has a written spec of what the other was building — sufficient for either to pick up the other's in-flight task, per PRD §17 |
| Synthetic dataset looking unconvincing | Day 12 explicitly grounds synthetic complaints in real, publicly reported RBI/CERT-In advisory patterns, per PRD §17, not fabricated from scratch |
| Graph visualization performance | Day 7's `graph/overview` endpoint is built with the top-N cap from day one, not retrofitted under time pressure later |
| **New — cross-dev contract drift** | Any API/schema contract change is called out explicitly in the daily EOD sync (§1) and reflected in TRD §7's table same-day — this is the roadmap's own addition, addressing the specific 2-person-team risk of silent contract mismatch |
| **New — Day 16 feature-freeze discipline** | Explicitly no new-feature tasks scheduled Days 17–18 (matches PRD philosophy) — the temptation to squeeze in "one more feature" on Day 17 is the single most common way hackathon teams destroy their own stability right before judging; this roadmap treats the freeze as a hard rule, not a suggestion |

---

## 12. Day-by-Day Checklist

- [ ] **Day 1:** Architecture locked — both repos scaffolded, CI green, auth endpoints live, DB migrated
- [ ] **Day 2:** Input pipeline online — Agent 1 working, upload UI + stepper live
- [ ] **Day 3:** First end-to-end score demo — Agent 2 working, result screen renders a real score
- [ ] **Day 4:** ✅ MILESTONE — Module 1 core loop functional
- [ ] **Day 5:** Graph writes live — Agent 5 core, Neo4j populated on every new report
- [ ] **Day 6:** RAG chat functional — Agent 3 working, chat drawer live with citations
- [ ] **Day 7:** Graph visualization online — clustering built, canvas renders real data
- [ ] **Day 8:** ✅ MILESTONE — Module 3 core loop functional
- [ ] **Day 9:** Dashboard shell live — Agent 6 started, KPI cards populated
- [ ] **Day 10:** Officer triage view functional — trends, emerging trends, complaint table live
- [ ] **Day 11:** ✅ MILESTONE — Module 2 core loop functional
- [ ] **Day 12:** ✅ MILESTONE — populated demo data live (150–300 seeded complaints)
- [ ] **Day 13:** Court-ready packages functional — both case- and ring-level generation working
- [ ] **Day 14:** ✅ MILESTONE — predictive layer live, real velocity-based alerts
- [ ] **Day 15:** ✅ MILESTONE — full pipeline stress-tested, failure handling verified
- [ ] **Day 16:** ✅ MILESTONE — MVP feature-complete, no new features after this point
- [ ] **Day 17:** ✅ MILESTONE — deployed & stable, demo rehearsed, backup video recorded
- [ ] **Day 18:** ✅ MILESTONE — submission ready

---

## 13. Sprint Board

A simple 4-column board (To Do / In Progress / In Review / Done), organized by phase — recommended as a physical or digital (Trello/Linear/GitHub Projects) board, refreshed at each EOD sync.

| Phase | To Do (upcoming) | In Progress | In Review | Done |
|---|---|---|---|---|
| **Phase 0 (Day 1)** | — | Repo scaffolding, DB schema, auth | — | *(populate daily)* |
| **Phase 1 (Days 2–4)** | Agent 1, Agent 2, Agent 4, upload UI, result UI | *(populate daily)* | *(populate daily)* | *(populate daily)* |
| **Phase 2 (Days 5–6)** | Neo4j schema, Agent 5, Agent 3, RAG chat UI | | | |
| **Phase 3 (Days 7–8)** | Clustering, graph canvas, Entity Explorer | | | |
| **Phase 4 (Days 9–11)** | Agent 6, dashboard, complaint table, investigation view | | | |
| **Phase 5 (Days 12–14)** | Data seeding, intelligence packages, predictive alerts | | | |
| **Phase 6 (Days 15–16)** | Hardening, cross-module nav, full polish/a11y pass | | | |
| **Phase 7 (Days 17–18)** | Deploy, rehearse, submission assets | | | |

**Board discipline:** a card only moves to "Done" when it satisfies §5's Definition of Done — not merely "code written." Each day's task table (§8) is the literal source of the cards for that day; nothing goes on the board that isn't traceable to a task row above (this is the mechanism that actually enforces the "no scope creep" rule from §11, not just a stated intention).

---

## 14. Final Submission Checklist

- [ ] Production backend URL live and responding
- [ ] Production frontend URL live and responding
- [ ] Demo account credentials prepared for all 3 roles (citizen, officer, admin), documented in a private note for the team (never committed to the repo)
- [ ] Seeded dataset is clean, realistic, and free of leftover test/debug artifacts
- [ ] All 6 agents functioning on the production deployment (not just locally)
- [ ] PDF export (citizen report + intelligence packages) verified working on production
- [ ] Repository READMEs are current and accurate (setup instructions actually work if someone follows them fresh)
- [ ] PRD, TRD, App Flow, Design Brief, Backend Schema, and this Roadmap are all included in the submission materials
- [ ] Presentation deck finalized, each slide traceable to a PRD §18 judging criterion
- [ ] Demo video recorded and uploaded (backup asset, per risk mitigation)
- [ ] Demo script (PRD Appendix B narrative) rehearsed at least twice against the live production deployment
- [ ] Submission form/portal fields (team name, project name, links, category) filled and double-checked well before the deadline, not in the final minutes

---

## 15. Demo Readiness Checklist

- [ ] Demo narrative rehearsed start-to-finish in under the judging panel's allotted time (rehearse the *tight* version, not just the full walkthrough)
- [ ] Primary demo path uses **curated, known-good inputs** (per §11's risk mitigation) — the degraded-mode/low-confidence example is shown *deliberately* as a secondary beat, not stumbled into by accident
- [ ] Internet connectivity at the venue verified in advance where possible; backup video ready as a true fallback, not an afterthought
- [ ] Both developers know how to answer "why not just one LLM prompt" (PRD §5) and "why 3 databases, not 1" (PRD §13.4/Backend Schema §1) — these are the two most likely pointed technical questions
- [ ] Browser tabs/windows pre-arranged for smooth screen-sharing (citizen view, officer view, graph view each ready in a separate tab, logged in as the correct role)
- [ ] Laptop fully charged, backup charger present, screen-recording software pre-tested if recording live
- [ ] A one-page printed/digital cheat-sheet of the PRD §18 judging-criteria mapping, for quick reference during Q&A

---

## 16. Bug Triage Checklist

Applied at every milestone gate (Days 4, 8, 11, 12, 14, 15, 16) and continuously during Days 17–18:

1. **Reproduce** — confirm the bug on the deployed demo environment, not just localhost (environment-specific bugs are common and easy to miss otherwise).
2. **Classify severity:**
   - **P0 — Demo-breaking:** blocks the core demo narrative (PRD Appendix B) or a milestone's stated ✅ criteria. Fixed immediately, same day, before any new feature work continues.
   - **P1 — Visible but non-blocking:** a real bug, visible in the UI or data, but doesn't break the demo path. Scheduled into the next available slot (the task tables above intentionally leave some slack for this).
   - **P2 — Cosmetic/edge-case:** unlikely to surface during a judged demo. Logged, addressed only if Day 17–18 buffer time allows; explicitly *not* worth risking a late-stage regression to fix.
3. **Assign owner** — whichever developer owns the affected module/layer per §1's allocation; cross-cutting bugs (contract mismatches) are fixed jointly in the same sync.
4. **Fix on a branch, PR, review, merge** — even under time pressure on Day 17–18, the review step is not skipped (§2.2) — a rushed direct-to-`main` fix is exactly how new bugs get introduced 6 hours before judging.
5. **Verify on the deployed environment**, not just in the PR diff, before marking resolved.
6. **Log a one-line note** in the shared demo-narrative doc if the bug or its fix changes anything about how the demo should be presented (e.g., "avoid uploading audio files over 2 min — known latency issue, not a blocking bug but avoid in the live demo").

---

*End of Implementation Roadmap. Together with the PRD, TRD, App Flow, UI/UX Design Brief, and Backend Schema documents, this roadmap should let both developers start coding on Day 1 with zero ambiguity about what to build, in what order, owned by whom, and judged against what standard of done.*
