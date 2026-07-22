# Truvia — Project Understanding (Code-Grounded Source of Truth)

> **Purpose of this document.** This is the single, accurate reference for writing the
> presentation deck, the submission document, and the demo video script, and for preparing
> the team to answer judges' technical questions. Every claim below was verified against the
> actual code and runtime logs in this repository — **not** copied from the planning docs.
> Where the planning docs and the real implementation diverge, the divergence is called out
> explicitly. The whole value of this document is that it is *more accurate* than the original
> plan, not more impressive-sounding.
>
> **Verification basis:** backend source (`truvia-backend/app/**`), frontend source
> (`truvia-frontend/src/**`), the live Neon Postgres schema/row-count report (`report.md`),
> and runtime logs (`backend.out.log`, `cluster_rings.out.log`) dated 2026-07-21.

---

## 1. One-Paragraph Elevator Pitch

**Truvia is an AI-powered fraud-intelligence platform that turns scattered scam complaints
into connected, prosecutable intelligence — and warns people *before* they lose money.** A
citizen who receives a suspicious message, screenshot, or scam call can submit it and get an
instant, plain-language threat verdict ("this is a Digital Arrest Scam — 85/100, here's why,
here's what to do"). But unlike a simple "scam / not-scam" checker, every report is broken
down into its identifying details — phone numbers, UPI IDs, bank accounts, domains — which
are stored in a growing graph. When the same phone number or UPI ID shows up across many
victims, Truvia automatically detects the *fraud ring* behind them and hands cybercrime
officers a ready-made, court-style evidence package. It works for three audiences at once:
**citizens** (self-defense and live, mid-call warnings), **police officers** (investigation
dashboard, fraud-ring graph, geographic priority map), and **admins** (knowledge base and
system health). In one line a non-technical judge can repeat: *"Truvia protects the next
victim using what it learned from the last one."*

---

## 2. Problem Statement Alignment

### 2.1 The hackathon problem statement chosen

- **Event:** ET AI Hackathon 2026
- **Track (verbatim from the PRD):** *"AI for Digital Public Safety — Defeating
  Counterfeiting, Fraud & Digital Arrest Scams."*
- **Core insight the product attacks:** today every scam complaint is siloed (bank vs. police
  vs. CERT-In vs. telecom), fraud is caught only *after* money moves, and existing "AI scam
  checkers" output a binary label with no investigative or evidentiary value. Truvia's answer
  is a **persistent, correlating fraud-intelligence layer** that connects complaints into
  rings and shifts intervention to *before* the transfer.

### 2.2 What the official brief asked for vs. what was actually built

The PRD's own "Hackathon Requirement Mapping" table lists the capabilities the brief
rewards. Verified against code, here is the honest built-vs-substituted mapping:

| Brief capability | Built? | Where it lives in the code (verified) |
|---|---|---|
| Digital Arrest Scam detection | ✅ Built | `threat_evaluator.py` — dedicated "Digital Arrest Scam" category with law-enforcement-impersonation keyword rules |
| Fraud Intelligence (entity graph, correlation, rings) | ✅ Built | `entity_extractor.py`, `graph.py`, `ring_clustering.py`, `fraud_rings`/`relationships` tables |
| AI Agents | ✅ Built (6 agents) | `app/agents/*` — all real, orchestrated in `orchestration/pipeline.py` |
| Multi-source intelligence (image / audio / text / KB) | ✅ Built | `input_processor.py` (OCR + ASR + text), `knowledge_agent.py` (RBI/NCRP KB) |
| Explainable AI | ✅ Built | every `threat_scores` row stores `reasoning_json` = key_indicators + victim_instructions + risk_explanation |
| Graph Intelligence | ✅ Built | Threat Intelligence Engine (`graph.py`) — overview, entity explorer, ring subgraphs |
| Geospatial Intelligence | ✅ Built as **city/district-level** (Module 6) | `geo_intel.py` — ranked-city priority score; **not** street-level GPS (honest granularity) |
| Predictive Threat Detection | ⚠️ Partial | rising/falling/stable trends (`geo_intel.py`), high-risk-entity ranking, auto-alerts ≥75 — heuristic, not a trained forecaster |
| Court-admissible Intelligence | ✅ Built (structure) | `intelligence_packages` — versioned, SHA-256 content hash, PDF export; legal certification itself out of scope |

### 2.3 The team's own innovations (added beyond the original 3-module PRD)

The original PRD (dated Jul 13) scoped **three** modules. Two additional modules were
designed and built late in the cycle (specs dated Jul 19) as the team's own extensions:

- **Module 5 — Live Scam Interceptor** (`live_session_scorer.py`, `live_sessions.py`,
  `live-shield/page.tsx`). **Why added:** the brief explicitly rewards *"flags active scam
  sessions before financial transfer occurs."* The original Fraud Shield is stateless
  (one submission → one verdict). This module is **stateful**: it scores a conversation
  turn-by-turn as it unfolds and fires a proactive warning the moment cumulative risk crosses
  "high" — a genuinely different problem shape (incremental re-scoring of an escalating
  sequence, not one-shot classification).
- **Module 6 — Geospatial Crime Pattern Intelligence** (`geo_intel.py`, `geo.py`,
  `geo-priority/page.tsx`). **Why added:** the brief rewards *"enforcement intelligence and
  prioritisation."* The existing complaint table can *filter* by city but cannot *rank* cities
  against each other or show trend direction. This module adds an explainable per-city
  Priority Score. **Honest scoping (from the spec itself):** it works at city/district
  granularity because that is the granularity the seeded `reports.city` data actually
  supports — it deliberately does **not** claim street-level GPS precision.

---

## 3. Module-by-Module Breakdown

> Roles are enforced in `app/api/deps.py` (`require_citizen`, `require_officer` = officer+admin,
> `require_admin`) and mirrored in the frontend nav (`src/lib/nav.ts`). Landing route per role
> (`homeForRole`): citizen → `/fraud-shield`, officer → `/dashboard`, admin → `/admin/users`.

### 3.1 Citizen Fraud Shield (`/fraud-shield`) — citizen role

**What it does (plain language):** A citizen submits a suspicious **text message, screenshot,
or audio recording**. Truvia extracts the text, scores how dangerous it is (0–100), classifies
the scam type, lists the red flags it found, tells the citizen exactly what to do, and lets
them either escalate it to police or download a PDF. A cited RAG chat assistant ("Vigil")
answers follow-up questions from official guidance.

**Actual user flow, screen by screen (from `fraud-shield/page.tsx`):**
1. Pick a source tab (`text` / `screenshot` / `audio`); paste text or upload a file.
2. Click **Run AI Analysis** → `POST /reports/submit` (multipart). A report row is created and
   the analysis pipeline is scheduled as a background task.
3. The UI polls `GET /reports/{id}/status` (drives the `ProcessingStepper`: ingesting →
   extracting_text → evaluating_threat → extracting_entities → indexing_graph → completed) and
   `GET /reports/{id}` until a threat score is attached (~up to 90s window for slow audio).
4. Result panel renders: `RiskGauge` (score + severity band), confidence %, scam category,
   **Detected Red Flags** (`reasoning_json.key_indicators`), **Recommended Response**
   (`reasoning_json.victim_instructions`), and a low-confidence caveat banner if OCR/ASR was weak.
5. Actions: **Report to Cyber Cell** (`POST /reports/{id}/escalate`, behind a JS `confirm()`),
   **Export Report** (`GET /reports/{id}/pdf`), **Mark as Reviewed** (`POST /reports/{id}/dismiss`).
6. **Vigil chat** (`POST /chat`) returns an answer + citations. **Recent Scans** table lists the
   citizen's last reports (clickable to re-open a verdict).

**Working end-to-end:** submission → extraction → scoring → entity extraction → escalation →
PDF, all persisted to Neon Postgres (202 reports, 196 threat scores live). Escalation creates a
real `cases` row and, if the report shares entities with an existing case's reports, auto-links
to it.

**Known limitations:** the threat score and OCR currently come from the **local rule-based /
RapidOCR fallbacks**, not Gemini (see §6). If extraction yields no text, the pipeline returns an
explicit honest "Insufficient Content" verdict (score 0) rather than a fabricated result.

**Most demo-worthy thing:** the **explainability contract** — every verdict ships with concrete
red flags *and* actionable victim instructions, not just a number, and it is honest about low
confidence instead of bluffing.

### 3.2 Live Scam Interceptor / "Live Shield" (`/live-shield`) — citizen role

**What it does:** Mid-call or mid-chat, the citizen types in **what the scammer just said**,
turn by turn. After each turn Truvia re-scores the *whole conversation as an escalating
sequence* and, the moment risk crosses "high," pops a proactive, scam-specific warning banner —
before any money moves.

**Actual user flow (from `live-shield/page.tsx`), three phases:**
- **idle:** "Start Live Session" → `POST /live-sessions` (creates an `active` session).
- **active:** type a turn → `POST /live-sessions/{id}/turns`. Each turn shows its own severity
  dot + running cumulative risk; a live `RiskGauge` tracks the trajectory. When cumulative
  crosses 70, an intervention banner appears once with category-specific guidance.
- **summary:** "End Session" → `GET /live-sessions/{id}` renders a **Recharts** risk-trajectory
  line with a dashed reference line at 70, the full turn timeline, final verdict, and actions:
  **Report to Cyber Cell** (`/escalate` → creates a case), **Download Report** (PDF), **Restart**.

**Working end-to-end:** real turn-by-turn scoring, cumulative trajectory, one-time intervention,
escalation-to-case, and PDF — persisted in `live_sessions` (7 live) and `live_session_turns`
(22 live).

**Known limitations:** it is **text-turn**, not streaming audio — the citizen types what they
hear (this matches the spec; true streaming STT is v2). The frontend is intentionally
"functional-but-plain" per the spec (UI polish deferred). Per-turn scoring is rule-based; the
optional LLM enrichment pass is currently inactive because Gemini is disabled (§6).

**Most demo-worthy thing:** the **cumulative trajectory scoring** — see §5.1. Watching the gauge
climb turn-over-turn and the warning fire *during* the "call" is the single most visceral moment
in the whole demo.

### 3.3 Officer Dashboard & Investigations (`/dashboard`, `/investigations`, `/my-cases`, `/reports`) — officer/admin

**What it does:** Gives cybercrime officers KPIs, a filterable complaint feed, case detail with
an AI-written summary, correlated-complaint discovery, case assignment, and a court-style dossier
PDF.

**Actual flow (from `cases.py` + frontend):**
- **Dashboard** (`GET /cases/stats`): real KPIs — total reports, total cases, high-risk entities
  (`risk_score ≥ 65`), average current threat score, and a **real** zero-filled 7-day complaint
  volume series.
- **Reports Feed** (`GET /reports` with server-side filters: search, status, source_type,
  category, score range, date range, and `city` for the geo drill-through) + CSV export
  (`GET /reports/export` streams the *currently filtered* set).
- **Case detail** (`GET /cases/{id}`): linked reports, extracted entities, audit logs, AI summary,
  and **correlated complaints** — other reports that share ≥1 extracted entity, ranked by shared-
  entity count (real Postgres correlation via `report_entities`).
- **Assign** (`POST /cases/{id}/assign`): sets `assigned_officer_id`, writes a durable
  `officer_assignments` history row (closing any open one), logs to `audit_logs`, then triggers
  Agent 6 to (re)summarize the case.
- **Dossier** (`GET /cases/{id}/package`): persists an `intelligence_packages` row (SHA-256 hash)
  and streams a multi-page ReportLab **"Court Evidence Dossier"** PDF.

**Working end-to-end:** stats, filtering, CSV, case detail, correlation, assignment, dossier PDF
(live data: 23 cases, 62 case-report links, 6 intelligence packages).

**Known limitations:** Agent 6 summaries are the deterministic local variant while Gemini is
disabled (§6). Officer assignment history shows only 1 row live (feature works; lightly exercised).

**Most demo-worthy thing:** the **auto-correlation** — opening one complaint and instantly seeing
"3 other complaints share this UPI ID" is the payoff of the entity graph.

### 3.4 Threat Intelligence Engine (`/intelligence/graph`, `/intelligence/rings`, `/intelligence/entity/[id]`) — officer/admin

**What it does:** The centerpiece. A force-directed **fraud graph**, an **entity explorer**, a
**fraud-ring list**, and **versioned court-ready intelligence packages**. This is what makes
Truvia "fraud intelligence" rather than "fraud classification."

**Actual flow (from `graph.py` + `intelligence/graph/page.tsx`):**
- **Graph Home** (`GET /graph/overview?top_n_clusters=8`): capped top-N highest-risk ring
  subgraph (nodes = ring members, edges = their relationships), plus a top-10 high-risk entity
  sidebar and the algorithm label. Payload is capped for performance.
- **Search** (`GET /graph/search?q=`): entity autocomplete over normalized/raw values.
- **Entity Explorer** (`GET /graph/entity/{id}`, `/subgraph?depth=1..3`, `/risk-score`): identity,
  risk tier, connection & complaint counts, ring membership, an N-hop BFS neighbourhood over the
  Postgres `relationships` table, and a risk breakdown with contributing **factors** + a risk
  **history** sparkline.
- **Rings** (`GET /graph/rings`, `/rings/{id}`): ranked ring list and full ring detail (member
  subgraph + correlated complaints). Export bundle (`/rings/{id}/export`) = JSON of subgraph +
  complaint IDs.
- **Intelligence Package** (`POST /graph/intelligence-package`): assembles a ring/entity package,
  auto-creates/links a `ring_level` case, stores it **immutably and versioned** with a SHA-256
  `content_hash`; `GET .../download` renders the snapshot as PDF.

**Working end-to-end:** all served from **authoritative Postgres** (9 fraud rings, 62 entities,
63 relationships, 34 ring memberships live). Works with or without Neo4j online.

**Known limitations:** rings were detected by the **python-louvain fallback**, not Neo4j GDS
(§6). "Risk score history" uses each linked report's current threat score, not a full temporal
snapshot chain.

**Most demo-worthy thing:** the **tamper-evident, versioned intelligence package** — a
content-hashed, immutable evidence bundle auto-tied to a case is the "court-ready" story judges
remember.

### 3.5 Geospatial Crime Pattern Intelligence (`/geo-priority`) — officer/admin

**What it does:** Ranks **cities/districts** by recent, severity-weighted fraud activity so
patrol/investigation resources can be pointed somewhere specific, with a visible trend arrow.

**Actual flow (from `geo.py`, `geo_intel.py`, `geo-priority/page.tsx`):**
- `GET /geo/priority?category=&days=30` → ranked-city table: Priority Score (0–100 bar), trend
  (rising/falling/stable arrow), dominant category, complaint count. Window (7/14/30/60/90 days)
  and category filters.
- Optional **Leaflet map** view (client-only, `GeoMap.tsx` + `cityCoords.ts`) plotting the same
  ranking.
- Click a city → drill through to `/reports?city=<city>` (reuses the complaint feed's `city` filter).
- `GET /geo/priority/{city}/trend?weeks=8` → weekly volume + severity series for one city.

**Working end-to-end:** pure SQL aggregation over existing `reports.city` + `threat_scores`; no
new tables, no LLM. The scoring is fully explainable (see §5.4).

**Known limitations:** **city-level, not GPS/street-level** (honest and by design). Depends on
`reports.city` being populated. Table is the primary view; the map is a secondary nicety.

**Most demo-worthy thing:** the **explainable Priority Score** — it never "just declares" a
ranking; it returns the three components (density × severity × recency) behind every number.

### 3.6 Admin (`/admin/users`, `/admin/knowledge-base`, `/admin/system-health`) — admin role

**What it does:** User management, the RAG knowledge base (ingest RBI/NCRP/CERT-In guidance),
and a live **System Health** console.

**Actual flow:** System Health (`GET /admin/system-health`, from `metrics.py` telemetry
installed at startup) shows per-agent cards (provider, avg latency, runs/errors in the last hour),
task-queue depth, and recent failed tasks with a **Retry** button. Knowledge Base drives
`knowledge_base` (21 docs) + `knowledge_base_chunks` (42 chunks) that feed Vigil's RAG.

**Most demo-worthy thing:** System Health is where the platform's **honesty** shows — it displays
each agent's *actual* provider (e.g. `local-rule-engine`) rather than pretending everything is
LLM-powered.

---

## 4. Technical Architecture — Explained Simply, Then Precisely

### 4.1 Request lifecycle, in words (a citizen submits a scam screenshot)

1. **Frontend** (`fraud-shield/page.tsx`) builds a `FormData` with the image and
   `POST`s it to `/api/v1/reports/submit` with a JWT bearer token (`lib/api.ts`).
2. **API** (`reports.py`) authenticates the user (`deps.get_current_user`), saves the file to
   **Cloudinary** (`storage_client`), creates a `reports` row (`status="submitted"`) and an
   `evidence` row (with a SHA-256 file hash), and schedules `run_pipeline(report_id)` as a
   **FastAPI background task** — then immediately returns the report object.
3. The **frontend polls** `/reports/{id}/status` and `/reports/{id}` while the pipeline runs.
4. **Pipeline** (`orchestration/pipeline.py`) updates `pipeline_stage` at each step and runs the
   agents in order (see §4.3): Agent 1 (extract text) → Agent 2 (score) → Agent 4 (entities) →
   auto-alert if ≥75 → Agent 5 (graph sync).
5. Results are written to **Neon Postgres** (`threat_scores`, `entities`, `report_entities`,
   `relationships`); Agent 5 best-effort mirrors into **Neo4j**.
6. The frontend's next poll sees `status="scored"` + an attached `threat_scores` row and renders
   the verdict.

### 4.2 Why the architecture is what it is (defensible under questioning)

- **Modular monolith, not microservices.** One FastAPI app (`main.py`) mounts all routers;
  agents are Python modules orchestrated in-process. For a 2-person, 18-day build this maximizes
  velocity and keeps transactions simple, while the agent boundaries keep clear seams to split
  into services later. There is no premature distributed-systems complexity.
- **Async queue = FastAPI `BackgroundTasks`, in-process (not Redis/RQ).** The pipeline runs
  after the HTTP response returns, so the citizen gets an instant `201` and polls for the
  verdict. **Divergence from the plan:** the PRD/TRD implied a Redis worker; the real system does
  **not** require one — Redis appears only in an optional `/readyz` health check. This is simpler
  and has one fewer moving part to fail in a demo. (Trade-off: work is lost if the process
  restarts mid-pipeline; acceptable at this scale.)
- **Three data stores, each for a different shape of data:**
  - **Postgres (Neon) + pgvector** — the *authoritative* relational store for everything
    (reports, scores, entities, relationships, cases, rings, KB embeddings). pgvector lets
    embeddings live next to the relational data (no separate vector DB).
  - **Neo4j** — a *derived* correlation/visualization index for the entity graph. **It is
    explicitly non-authoritative**: `graph.py` and `ring_clustering.py` compute everything from
    Postgres and treat Neo4j as best-effort. The whole graph can be rebuilt from Postgres, so
    the engine works with Neo4j offline.
  - **Cloudinary** — evidence blob storage (images/audio) out of the relational DB.
  - Defensible answer to *"why not one DB?"*: relational integrity + vector search + native graph
    traversal are three different access patterns; Postgres is the source of truth and the other
    two are optimizations, not parallel sources of truth.
- **Graceful degradation is a first-class design principle** (`config_check.py`): missing/invalid
  credentials degrade a *capability* (rule engine, lexical retrieval, local OCR/ASR) rather than
  crashing — and the system refuses to fabricate results (empty extraction → explicit
  "Insufficient Content" verdict).

### 4.3 The 6 AI agents (verified against agent code, not the PRD)

| # | Agent (file) | Runs when | Input → Output | Primary vs. fallback |
|---|---|---|---|---|
| 1 | **Input Processor** (`input_processor.py`) | Pipeline step 1 | evidence files → `cleaned_text`, language, `input_confidence`, `low_confidence_flag` | OCR: Gemini-vision → **local RapidOCR**; ASR: OpenAI Whisper → **local faster-whisper**; text: direct |
| 2 | **Threat Evaluator** (`threat_evaluator.py`) | Pipeline step 2 | text → `threat_score` 0–100, `severity_band`, `scam_category`, `confidence`, `reasoning_json` | Gemini 2.0 Flash structured JSON → **local rule-based keyword engine** |
| 3 | **Knowledge Agent** (`knowledge_agent.py`) | Vigil chat (`/chat`) | query (+optional report context) → grounded answer + citations | retrieval via pgvector/lexical; answer via Gemini → **local grounded (cited excerpts) composer** |
| 4 | **Entity Extractor** (`entity_extractor.py`) | Pipeline step 3 | text → entities (phone/upi/email/domain/ifsc/ip/bank_account/org) + co-occurrence relationships | **Regex + normalization** (no LLM) — deterministic by design |
| 5 | **Threat Intel** (`threat_intel.py`) | Pipeline step 4 | report + entities → Neo4j `:Entity`/`:Report`/`CO_OCCURRED_IN`/`LINKED_TO` mirror | Neo4j when reachable → **degraded_mode no-op** (Postgres already authoritative) |
| 6 | **Investigation** (`investigation.py`) | On escalate/assign | case/ring reports → `summary`, `primary_patterns`, `estimated_losses` | Gemini narrative → **deterministic local summary** (patterns + amounts extracted from real text) |

Pipeline order (`run_pipeline`): **1 → 2 → 4 → auto-alert(≥75) → 5**. Agent 3 (chat) and Agent 6
(investigation) run on demand, not in the intake pipeline. The Live Scam Interceptor
(`live_session_scorer.py`) **reuses Agent 2** per turn (`rule_based_analyze`) plus a conditional
Agent 2 LLM pass — it is not a separate seventh agent.

### 4.4 Key data-model decisions worth explaining

- **Entities are de-duplicated via `(type, normalized_value)`** (unique key
  `entities_type_normalized_value_key`). A phone number is normalized to its last 10 digits, a UPI
  ID lowercased, a URL reduced to its domain. This is the linchpin of correlation: the *same*
  scammer identifier from two different complaints resolves to *one* entity row whose
  `occurrence_count` and `risk_score` grow — which is exactly what makes ring detection possible.
- **Threat scores are versioned, not overwritten.** `threat_scores` keeps every score with an
  `is_current` boolean (old rows flipped to `false`, new row inserted `true`). This preserves an
  audit trail (crucial for "court-ready"), lets a re-analyzed report keep its history, and stores
  `degraded_mode` + `model_version` so you can always tell *which engine* produced a given score.
- **Co-occurrence relationships** — Agent 4 links every pair of entities found in the same report
  (`relationship_type="co_occurred_in_report"`, strength 1.0). This edge set is what Louvain
  clusters into rings.
- **Fraud rings are persisted in Postgres** (`fraud_rings` + `fraud_ring_members`) even though the
  schema models Ring as a Neo4j node — a deliberate, documented deviation so ring endpoints and
  intelligence packages remain queryable with Neo4j offline. `neo4j_ring_id` is a stable
  content-hash key shared across both stores.
- **Live sessions** (`live_sessions` + `live_session_turns`) store the denormalized current score
  on the session and the cumulative score per turn — the per-turn `cumulative_score` is precisely
  what the trajectory chart plots.

---

## 5. What Makes This Technically Interesting (for judges)

Honest, non-trivial engineering — each explained precisely enough to survive a follow-up.

### 5.1 Turn-by-turn cumulative scoring (Live Scam Interceptor)
The formula (`live_session_scorer.py`) is deliberately simple and *explainable* — no black-box
sequence model:
```
cumulative = 0.4 * previous_cumulative + 0.6 * current_turn_score
```
Recent turns are weighted heavier (0.6). On top of that, a flat **+15 escalation bonus** (capped
at 100) fires when the **last 3 consecutive turns each individually exceed the "moderate"
threshold (≥40)** — rewarding *sustained* escalation, which is itself a strong scam signal. The
"high" intervention (≥70) fires **once per session** (tracked via `intervention_shown_at`). Cost/
latency-aware: the expensive LLM reasoning pass is only invoked once cumulative ≥ moderate, never
on every turn. Defensible because every number is traceable to the formula, not a model you can't
explain in court.

### 5.2 Louvain fraud-ring clustering with a Postgres fallback
`ring_clustering.py` is dual-path: **primary** is Neo4j GDS `gds.louvain.stream`; **equivalent
fallback** is `python-louvain` (`community.best_partition`) over a NetworkX graph built from the
authoritative Postgres `relationships` table. Rings (≥3 members) are enriched with real
complaint counts, dominant category, and activity dates, then written to Postgres and mirrored to
Neo4j when available. **Verified runtime fact:** GDS is not installed, so the system ran the
`python_louvain` path and still produced real rings (e.g. a 22-member, 14-complaint "UPI Refund
Scam" ring). The community-key is a content hash of the sorted member set, so the same ring keeps
a stable ID across re-runs.

### 5.3 Graceful degradation (LLM-optional by design)
Every LLM-backed agent checks `is_gemini_enabled()` and falls back to a deterministic local path;
a `401 Unauthenticated` at call time triggers `disable_gemini()` globally so the app stops
retrying a blocked key. Critically, the fallbacks **never fabricate**: empty OCR/ASR → honest
zero-confidence "Insufficient Content" verdict; no KB match → "I don't have an official advisory
for that." This is the difference between a demo that fails loudly and one that degrades honestly.

### 5.4 Explainable geospatial priority score
`geo_intel.py`, pure SQL:
```
raw = complaint_density * avg_severity_weight * recency_factor      (then normalized 0–100)
  complaint_density  = count of complaints in the window
  avg_severity_weight = avg(low=1, moderate=2, high=3, critical=4)
  recency_factor      = avg( 0.5 ^ (age_days / half_life) ),  half_life = window/2
```
Trend = current vs. prior equal window, ±15% → rising/falling/stable. Every component is returned
alongside the final score ("never just declare, always explain").

### 5.5 Versioned, tamper-evident intelligence packages
`graph.py` assembles a ring/entity package, serializes it deterministically
(`json.dumps(..., sort_keys=True)`), and stores a **SHA-256 `content_hash`** with an
auto-incrementing `version` per case. Packages are immutable snapshots — a defensible chain-of-
custody *structure* for evidence (full cryptographic signing is documented as v2).

### 5.6 Entity de-duplication + N-hop graph traversal in Postgres
The `(type, normalized_value)` unique constraint plus a BFS over the `relationships` table
(`_bfs_subgraph`, depth 1–3) gives real graph traversal on the relational store — the reason the
Threat Intelligence Engine works even with Neo4j offline.

### 5.7 RAG chat — grounded and honestly lexical (see caveat in §6)
Retrieval returns cited passages from the KB; when the LLM is unavailable the answer is composed
*only* from the actually-retrieved passages with inline `[RBI]`/`[CERT-In]` source tags — no
canned advice, and an explicit "no advisory found" when retrieval is empty.

---

## 6. Known Limitations & Honest Caveats

This section is deliberately undefensive. Judges respect honesty about scope far more than an
inflated claim that collapses under one follow-up question.

### 6.1 🔴 The single biggest one: Gemini is DISABLED at runtime right now
- **Verified fact (`backend.out.log`, 2026-07-21):** the configured `GOOGLE_API_KEY` (which
  starts with `AQ.`) fails Google's background validation with **`401 Unauthenticated —
  API_KEY_SERVICE_BLOCKED`**, so `disable_gemini()` runs at startup and **all Gemini integrations
  are turned off globally.**
- **Consequence — what is actually running:**
  - `llm_threat_reasoning` → **`local-rule-engine`** (keyword rules), not Gemini
  - `rag_chat_llm` → **`local-grounded-answers`** (cited-excerpt composer), not Gemini
  - `image_ocr` → **`local-rapidocr`** (Gemini vision blocked)
  - `audio_asr` → **`local-faster-whisper`** (OpenAI key is empty anyway)
  - Agent 6 case/ring summaries → **deterministic local** variant
- **Why this is OK to present:** the platform was *designed* to degrade this way and still runs
  end-to-end on real data. But you must not claim "LLM-powered reasoning" in the live demo unless
  a valid key is added first. The most powerful honest framing: *"the intelligence layer is
  LLM-optional by design — here it's running on the deterministic fallback and still produces a
  full verdict."* If you want the LLM path live, **replace `GOOGLE_API_KEY` with a valid,
  unrestricted Gemini key before the demo.**
- **Note:** the stale audit report (`Truvia_Implementation_Audit_Report.md`) claims Gemini is
  *"Fully functional!"* — that claim is **incorrect** as of the current runtime.

### 6.2 The "RAG" is grounded lexical retrieval, not semantic vector search
`vector_client.get_embedding` returns a **deterministic dummy vector derived from a character sum**
— it is *not* a semantic embedding. In Postgres it's stored in pgvector and queried with cosine
distance, but since the vectors aren't semantic, retrieval effectively behaves like keyword
matching (and in SQLite mode it is *explicitly* lexical token-overlap). It retrieves genuinely
relevant guideline passages for keyword-overlapping queries, but it will not do true semantic
"understands-a-paraphrase" retrieval. Call it "grounded, cited retrieval," not "semantic RAG."

### 6.3 Neo4j GDS is not installed → python-louvain fallback
The Neo4j driver connects, but Graph Data Science isn't present, so ring detection ran on the
`python_louvain` equivalent (verified). Rings are real and correct; just not GDS-computed.

### 6.4 Other honest caveats
- **Provider divergence from the PRD:** the PRD specified **Anthropic Claude**; the code uses
  **Google Gemini 2.0 Flash** (+ OpenAI Whisper for ASR). Both are currently unkeyed/blocked.
- **No async worker:** the pipeline is an in-process background task, not a Redis/RQ worker
  (simpler, but work is lost on restart mid-pipeline).
- **Predictive layer is heuristic**, not a trained forecaster (trend deltas, risk ranking,
  auto-alert ≥75).
- **Geospatial is city-level, not GPS** (by design, honest).
- **Live Shield is text-turn, not streaming audio** (citizen types what they hear).
- **Modules 5 & 6 frontends are intentionally "functional-but-plain"** (UI polish deferred per
  their specs) — backends are fully real.
- **Data is synthetic/seeded** (~202 reports) to make the graph meaningful on day one.
- **Court-admissibility** = structure + hashing only; legal certification is out of scope.

### 6.5 v2 priorities (in order)
1. Add a valid Gemini key (or self-host an LLM) to light up real reasoning + summaries.
2. Real semantic embeddings (e.g. a sentence-transformer) behind the existing pgvector schema.
3. Install Neo4j GDS (or keep python-louvain — it works) + move clustering to a schedule.
4. Streaming STT for true live-call interception.
5. Durable job queue (Redis/RQ) for pipeline resilience at scale.

---

## 7. Suggested Demo Script Flow

A coherent story: **prevention (citizen) → live prevention → investigation → intelligence →
prioritization → honesty.** Log in with three pre-seeded accounts (citizen, officer, admin).

1. **Open on the citizen problem (Fraud Shield, ~90s).** As a citizen, paste a classic Digital
   Arrest message ("This is CBI, a warrant is issued, pay to avoid arrest…"). Run analysis. Show
   the gauge hit High/Critical, the **red flags**, the **recommended actions**, and the scam
   category. Ask Vigil one question and show the **cited** answer. *Message: instant, explainable
   self-defense.*
2. **Escalate that report to police (~15s).** Click **Report to Cyber Cell** → note the case
   reference. This is the hand-off from citizen to officer.
3. **Live Scam Interceptor (the showstopper, ~90s).** Switch to **Live Shield**. Start a session
   and add 3–4 escalating turns ("I'm from your bank" → "your account is compromised" → "share the
   OTP now" → "pay via this UPI to secure it"). Show the gauge climbing turn-over-turn and the
   **intervention banner firing** as it crosses High. End → show the **Recharts trajectory** with
   the 70 reference line. *Message: we warn before the money moves.*
4. **Officer investigation (~90s).** Log in as officer → **Dashboard** KPIs → open the escalated
   **case** → show the AI summary and, crucially, **correlated complaints** ("these other reports
   share this UPI ID"). Generate the **Court Evidence Dossier** PDF.
5. **Threat Intelligence Engine (~90s).** Go to **Intelligence → Graph**. Show the fraud graph,
   click a high-risk entity → **Entity Explorer** (connections, risk factors, ring membership).
   Open the **fraud ring** it belongs to (e.g. the 22-member UPI ring). Generate a **versioned
   intelligence package** and show the **SHA-256 content hash**. *Message: connected, court-ready
   intelligence.*
6. **Geospatial priority (~45s).** Open **Geo Priority** → show cities ranked by Priority Score
   with trend arrows; click a rising city to **drill through** to its complaints.
7. **Close on honesty (Admin System Health, ~30s).** Show the per-agent providers and say the line:
   *"Every agent degrades gracefully — right now it's running on the local engines and still
   produced everything you just saw. Add an LLM key and the same pipeline gets richer, without a
   rewrite."*

**If time is tight:** do 1 → 3 → 4 → 5 (citizen verdict, live interception, correlation, ring +
package). That's the whole thesis in ~4 minutes.

---

## 8. Anticipated Judge Questions & Grounded Answers

1. **"Why not just use one big LLM prompt for everything?"**
   Because the value isn't the classification — it's the *persistent, correlating graph*. A single
   prompt is stateless and dies when the response returns; it can't tell you a UPI ID appeared in
   40 other complaints or cluster them into a ring. Truvia decomposes each report into
   de-duplicated entities (`(type, normalized_value)`), links co-occurrences, and runs Louvain
   clustering — that's graph engineering, not prompting. Also: separate agents let each piece
   degrade independently and stay auditable (versioned scores, content-hashed packages).

2. **"What happens if the LLM API is down during your demo?"**
   It already is — and the demo still works. The Gemini key is currently blocked (§6.1), so the
   platform is running on its rule-based/local engines *right now*. Every agent has a deterministic
   fallback and refuses to fabricate; missing extraction returns an honest "Insufficient Content"
   verdict. Adding a valid key upgrades the reasoning without any code change.

3. **"How do you avoid false positives?"**
   Scores are banded (low/moderate/high/critical) with actions scaled to severity; low OCR/ASR
   confidence is surfaced as a caveat rather than hidden; the rule engine requires *multiple*
   phishing signals (bank + identity + urgency + link) before it escalates to a high KYC-scam
   score. And a citizen can escalate or dismiss — a human is always in the loop. We'd reduce them
   further in v2 with real semantic scoring and precision/recall tuning on labeled data.

4. **"How does this scale beyond a hackathon demo?"**
   The store is cloud Postgres (Neon) + pgvector, already handling ~200 reports/62 entities. It's a
   modular monolith with clean agent seams to peel into services; the in-process background task
   would become a durable queue (Redis/RQ). Neo4j is a *derived* index, so the authoritative store
   stays single and consistent. Ring clustering is a batch job that can move to a schedule.

5. **"How is this different from Truecaller / existing scam checkers?"**
   Truecaller identifies a *caller*; scam checkers output a *label*. Truvia produces
   *intelligence*: who else this identifier hit, which ring it belongs to, an explainable score
   with cited guidance, a live mid-call trajectory warning, and a court-ready evidence package for
   police. It's built for the *investigation and prevention* workflow, not just caller ID.

6. **"Is this legally admissible? How would police actually adopt it?"**
   We build the *structure* for admissibility — immutable, versioned intelligence packages with
   SHA-256 content hashes, full audit logs, and officer-assignment history — not a legal
   certification (explicitly out of scope). Adoption path: it ingests the unstructured complaints
   police already receive and outputs the correlation + dossier work they currently do by hand.
   The officer role, case assignment, and dossier PDF exist today.

7. **"Your graph DB — is it really a graph, or SQL pretending?"**
   Both, intentionally. Postgres is authoritative and we do real BFS traversal (1–3 hops) and
   Louvain community detection over the `relationships` table. Neo4j mirrors it as a native graph
   index for visualization/GDS *when available*. We decoupled them so the engine never hard-depends
   on Neo4j — the whole graph is rebuildable from Postgres.

8. **"Is your RAG real?"**
   Honestly: it's *grounded, cited retrieval*, and right now the embeddings are a deterministic
   placeholder, so retrieval behaves lexically (keyword overlap) rather than semantically (§6.2).
   Answers are composed only from actually-retrieved official passages with inline citations, and
   it says "no advisory found" rather than inventing guidance. The pgvector schema is already in
   place, so swapping in real embeddings is a drop-in v2 change.

9. **"Why Gemini in the code when the PRD said Claude?"**
   A pragmatic provider switch (Gemini 2.0 Flash has a free tier); the agent interfaces are
   provider-agnostic behind `genai_helper`. Neither is active right now due to the blocked key.

10. **"What's genuinely novel here vs. assembled from libraries?"**
    The cumulative turn-trajectory scoring formula with the consecutive-escalation bonus (§5.1),
    the Postgres-authoritative/Neo4j-derived graph design with a python-louvain fallback (§5.2),
    the LLM-optional graceful-degradation contract that never fabricates (§5.3), the explainable
    geospatial priority score (§5.4), and the versioned content-hashed intelligence packages
    (§5.5). The plumbing uses standard libraries; the *design decisions* are the work.

---

## 9. Glossary of Terms Used in This Project

- **Agent** — a single-responsibility backend module in `app/agents/` (there are 6) that performs
  one step of analysis (extract text, score threat, extract entities, etc.).
- **Pipeline** — the orchestrated sequence (`orchestration/pipeline.py`) that runs the agents in
  order after a report is submitted; runs as an in-process FastAPI background task.
- **Threat score / severity band** — a 0–100 danger rating and its bucket: low (0–39),
  moderate (40–69), high (70–89), critical (90–100). Stored versioned in `threat_scores`.
- **Scam category** — the classified type (Digital Arrest Scam, UPI Refund Scam, KYC Verification
  Scam, Lottery/Job Scam, etc.).
- **Entity** — a fraud identifier extracted from a report: phone, UPI ID, email, domain, IFSC,
  IP, bank account, or impersonated org.
- **Normalized value / de-duplication** — the canonical form of an entity (last 10 phone digits,
  lowercased UPI, URL→domain). The `(type, normalized_value)` unique key merges the *same*
  identifier across reports into one row — the basis of correlation.
- **Entity correlation** — discovering that different reports share the same entity, which links
  otherwise-siloed complaints together.
- **Relationship / co-occurrence edge** — a link (`relationships` table) between two entities that
  appeared in the same report; the edge set Louvain clusters into rings.
- **Fraud ring** — a cluster of ≥3 correlated entities (and their complaints) detected by Louvain
  community detection; stored in `fraud_rings` / `fraud_ring_members`.
- **Louvain clustering** — a community-detection algorithm that groups densely-connected nodes.
  Primary path = Neo4j GDS; fallback = `python-louvain` over Postgres data.
- **RAG (Retrieval-Augmented Generation)** — answering a question using retrieved source passages
  so the answer is grounded and citable. Here it's grounded *lexical* retrieval (see §6.2).
- **pgvector** — a Postgres extension storing vector embeddings for similarity search, used for KB
  chunk retrieval.
- **Knowledge base (KB)** — ingested official guidance (RBI/NCRP/CERT-In/MHA/NPCI) chunked and
  embedded; the source Vigil cites.
- **Degraded / fallback mode** — running a capability on a local/deterministic engine because the
  cloud LLM credential is missing or blocked; recorded per score via `degraded_mode` +
  `model_version`.
- **Cumulative / trajectory score** — the running Live-Session risk `0.4*prev + 0.6*turn`, plotted
  turn-by-turn to show whether a conversation is escalating.
- **Intervention** — the one-time proactive warning banner shown mid-session when cumulative risk
  crosses "high" (70).
- **Priority score (geospatial)** — a per-city 0–100 rank = normalized (complaint density ×
  avg severity × recency decay); the "where to focus" signal.
- **Recency factor / half-life decay** — weights recent complaints higher via
  `0.5^(age_days / half_life)`.
- **Intelligence package** — a versioned, SHA-256-hashed, immutable evidence bundle (ring or entity
  focused) tied to a case; the "court-ready" export.
- **Escalation** — a citizen (or officer) turning a report/session into a real `cases` row for
  investigation.
- **Case / dossier** — an investigation record (`cases`) and its multi-page ReportLab PDF summary.
- **Threat Intelligence Engine** — the officer/admin graph surface (`/intelligence/*`): graph home,
  entity explorer, fraud rings, intelligence packages.
- **Explainability contract** — the rule that every verdict ships with `key_indicators`,
  `victim_instructions`, and a `risk_explanation` (`reasoning_json`), never a bare number.
- **Modular monolith** — one deployable app with clear internal module boundaries (as opposed to
  many independently-deployed microservices).

