# REPORT 2: Remaining Implementation — Features Still Required

**Date:** July 15, 2026  
**Scope:** Features from PRD v1.0 that are NOT yet implemented or need significant completion  
**Priority:** Ranked by demo impact and hackathon judging criteria

---

## PRIORITY CLASSIFICATION

- **P0 (Critical for Demo):** Without this, judges will notice a gap during the live demo narrative
- **P1 (High Impact):** Directly maps to a hackathon judging criterion; would weaken the submission
- **P2 (Medium):** PRD specifies it for MVP, but the product still demos well without it
- **P3 (Nice-to-Have):** PRD labels as stretch or the existing partial implementation is acceptable

---

## P0 — CRITICAL FOR DEMO

### 1. Seeded Dataset (150–300 Synthetic Complaints)

| Aspect | Details |
|--------|---------|
| PRD Section | §6 MVP Scope |
| What's Needed | A script that populates the database with 150–300 realistic complaints across all scam categories (Digital Arrest, UPI Fraud, KYC Scam, Job Scam, Sextortion, etc.), spread across different dates and cities, with extracted entities and graph relationships already indexed |
| Why P0 | Without data, the Dashboard shows empty KPIs, the Threat Intel graph is blank, and Predictive Alerts returns nothing. Demo is dead on arrival. |
| Estimated Effort | 1–2 days (Python script + curated scam text templates) |
| Implementation Notes | Should: (a) create reports with cleaned_text, (b) run pipeline on them to generate threat_scores + entities + relationships, (c) seed knowledge_base with RBI/CERT-In advisory content for RAG, (d) create a few Cases with linked reports for the officer dashboard |

### 2. Live Processing States Stepper (Frontend)

| Aspect | Details |
|--------|---------|
| PRD Section | §8.1 User Flow, UI Components |
| What's Needed | Replace the current "ANALYZING FORENSICS..." spinner with a multi-step stepper showing: "Extracting text..." → "Analyzing threat patterns..." → "Cross-checking known fraud entities..." → "Complete" |
| Why P0 | The PRD explicitly states this is a key UX differentiator ("reinforces 'intelligence system' feel, not chatbot"). Judges will see a single spinner which makes it feel like any other AI wrapper. |
| Estimated Effort | 0.5 days (frontend only — backend already updates `report.status` through stages: submitted → processing → processed → scored) |
| Implementation Notes | Poll `GET /reports/{id}/status` and map status values to stepper stages. Can also add a `pipeline_stage` field if more granularity needed. |

---

## P1 — HIGH IMPACT (Judging Criteria)

### 3. City/District Geo Analysis

| Aspect | Details |
|--------|---------|
| PRD Section | §8.2 — City/District Analysis, `GET /api/v1/dashboard/geo-breakdown` |
| Hackathon Requirement | "Geospatial Intelligence" is an explicit judging criterion |
| What's Needed | (a) Add `city` or `district` field to the `reports` table, (b) Create `GET /api/v1/dashboard/geo-breakdown` endpoint aggregating complaint counts by city, (c) Build a bar chart / choropleth component on the dashboard |
| Estimated Effort | 1 day (schema migration + API + frontend chart) |
| Shortcut Option | For MVP, hardcode city options in the submission form (dropdown of 10–15 Indian cities) and aggregate from there. No real geocoding needed. |

### 4. Fraud Ring Listing Endpoint (`GET /graph/rings`)

| Aspect | Details |
|--------|---------|
| PRD Section | §8.3 — "Fraud Ring Detection" |
| Hackathon Requirement | "Graph Intelligence" judging criterion |
| What's Needed | An endpoint that runs community detection on the graph and returns a list of detected rings with: ring ID, member count, aggregate risk score, category affiliation, member entities |
| Estimated Effort | 0.5–1 day |
| Implementation Notes | Can use the existing `calculate_local_communities()` function and group nodes by community ID. If Neo4j GDS is available, use `gds.louvain.stream` for better clustering. |

### 5. Ring-Level Intelligence Package (`POST /graph/intelligence-package`)

| Aspect | Details |
|--------|---------|
| PRD Section | §8.3, §12 |
| Hackathon Requirement | "Court-admissible Intelligence" criterion |
| What's Needed | Generate a comprehensive PDF for an entire fraud ring (not just one case): all member entities, all linked complaints, aggregate timeline, total victims |
| Estimated Effort | 1 day |
| Implementation Notes | Extend existing package generation logic. Fetch all reports sharing entities in the same community cluster. Compose ring-level summary with Agent 6. |

### 6. Multi-Hop Subgraph Query (`GET /graph/entity/{id}/subgraph?depth=`)

| Aspect | Details |
|--------|---------|
| PRD Section | §8.3 — "expanded risk network" |
| Hackathon Requirement | Demonstrates graph traversal capability to judges |
| What's Needed | Endpoint that accepts a `depth` parameter (1–3) and returns all entities reachable within N hops |
| Estimated Effort | 0.5 day |
| Implementation Notes | Cypher: `MATCH path = (e:Entity {uid: $uid})-[*1..N]-(connected) RETURN path`. SQL fallback: recursive CTE or iterative BFS in Python. |

### 7. Report-Scoped Chat (`POST /reports/{id}/chat`)

| Aspect | Details |
|--------|---------|
| PRD Section | §8.1 — "RAG chat scoped to report context" |
| What's Needed | Modify the chat endpoint to accept a report_id, include the report's scam category and extracted entities in the RAG prompt for contextual answers |
| Estimated Effort | 0.5 day |
| Implementation Notes | Current chat endpoint at `POST /chat` works. Add an optional `report_id` parameter. Fetch the report's threat score + entities and prepend to the LLM prompt as context. |

### 8. Knowledge Base Seeding with RBI/CERT-In Advisories

| Aspect | Details |
|--------|---------|
| PRD Section | §9 Agent 3, §14 Knowledge Sources |
| Why P1 | Without knowledge base content, the RAG chat returns "not covered" for every query. This undermines the "grounded answers with citations" demo. |
| What's Needed | A seed script that ingests 15–30 official advisory documents (RBI fraud warnings, CERT-In alerts, MHA digital arrest guidance, NPCI UPI safety) into `knowledge_base` + `knowledge_base_chunks` tables with embeddings |
| Estimated Effort | 1 day |
| Implementation Notes | Collect public PDFs/text from rbi.org.in, cert-in.org.in. Chunk into ~500-token pieces. Embed (use dummy embedder for SQLite mode or real embedder with API key). Store with source metadata. |

---

## P2 — MEDIUM PRIORITY (MVP Completeness)

### 9. Entity Extraction: Missing Types (IFSC, IP, Device ID, Org/NER)

| Aspect | Details |
|--------|---------|
| PRD Section | §9 Agent 4 — "bank accounts, IFSC codes, device IDs, IP addresses, impersonated government/org names" |
| What's Needed | Add regex patterns for IFSC (`[A-Z]{4}0[A-Z0-9]{6}`), IP addresses, and optionally a lightweight NER pass for organization/government names |
| Estimated Effort | 0.5 day |

### 10. Threat Timeline (Real-Time Event Stream)

| Aspect | Details |
|--------|---------|
| PRD Section | §8.2 — "Threat Timeline (chronological event stream across all incoming reports)" |
| What's Needed | Endpoint returning the last N reports in chronological order with timestamps + type badges (new report, escalation, ring detection event). Frontend component showing vertical timeline. |
| Estimated Effort | 0.5 day |

### 11. Evidence Timeline (Per-Case)

| Aspect | Details |
|--------|---------|
| PRD Section | §8.2 — "Evidence Timeline (per-case chronological evidence chain)" |
| What's Needed | On the case detail page, show a timeline of: when each report was submitted, when entities were extracted, when the case was created, when it was assigned, when packages were generated |
| Estimated Effort | 0.5 day |
| Implementation Notes | Data exists in `audit_logs` + `report.created_at` + `case.created_at`. Need a frontend timeline component. |

### 12. Threat Score Distribution Histogram (Proper)

| Aspect | Details |
|--------|---------|
| PRD Section | §8.2 |
| What's Needed | Dedicated backend endpoint `GET /api/v1/dashboard/score-distribution` that buckets all threat scores into ranges (0-19, 20-39, 40-59, 60-79, 80-100) and returns counts. Frontend Recharts histogram. |
| Estimated Effort | 0.5 day |

### 13. Complaint Correlation from Graph (`GET /graph/correlate?report_id=`)

| Aspect | Details |
|--------|---------|
| PRD Section | §8.3 |
| What's Needed | Standalone API endpoint that, given a report_id, returns other reports sharing entities — accessible from Module 1's result screen (not just from case detail) |
| Estimated Effort | 0.5 day |
| Implementation Notes | Logic already exists in `cases.py` (correlated_reports section). Extract into a shared utility and expose at `/graph/correlate`. |

### 14. Export Evidence from Graph Module

| Aspect | Details |
|--------|---------|
| PRD Section | §8.3 — "Export Evidence (entity subgraph + supporting complaint IDs)" |
| What's Needed | Button on Threat Intel page to export the current entity's subgraph + linked report IDs as a JSON or PDF bundle |
| Estimated Effort | 0.5 day |

### 15. Full Court-Ready Intelligence Package Structure (§12 Compliance)

| Aspect | Details |
|--------|---------|
| PRD Section | §12 — Case Header, Timeline, Evidence, Extracted Entities, Threat Analysis, AI Explanation, Confidence Score, Linked Complaints, Related Fraud Ring, Officer Notes |
| What's Missing | Current package covers some sections but missing: separated "AI Explanation" section (currently merged with reasoning), "Related Fraud Ring" section, "Officer Notes" free-text field, explicit "Confidence Score" section, proper "Timeline" reconstruction |
| Estimated Effort | 1 day |

---

## P3 — NICE-TO-HAVE (Stretch / Acceptable As-Is)

### 16. Redis/RQ Pipeline (Replace BackgroundTasks)

| Details | Current: FastAPI BackgroundTasks. PRD §14 specifies "Redis-backed task queue." Working fine in demo but less resilient than queued architecture. |
| Effort | 0.5 day |
| Verdict | BackgroundTasks is acceptable for hackathon. Document as production upgrade. |

### 17. Real Embedding Model (Replace Dummy Embedder)

| Details | Current: deterministic dummy vector. Cosine similarity still works with keyword fallback. With a real embedding model (e.g., OpenAI `text-embedding-3-small`), RAG would be semantically accurate. |
| Effort | 0.5 day (add API call in `get_embedding()`) |
| Verdict | Works with keyword fallback for demo. Real embeddings would improve quality. |

### 18. Louvain Community Detection (Replace Connected Components)

| Details | Current: BFS connected components. PRD specifies Louvain clustering. Neo4j GDS plugin is configured in docker-compose but not called. |
| Effort | 0.5 day (Cypher GDS call) |
| Verdict | Connected components work for small demo datasets. Louvain would be more impressive under technical questioning. |

### 19. User History Endpoint (`GET /api/v1/users/{id}/history`)

| Details | Current: citizens see history via `GET /reports?limit=6` which auto-filters by user. No dedicated history endpoint. Functionally equivalent. |
| Effort | Minimal |
| Verdict | Acceptable as-is. |

### 20. Entity-Specific Risk Score Endpoint (`GET /graph/entity/{id}/risk-score`)

| Details | Risk score is already returned in the entity detail response. Dedicated endpoint is redundant but PRD lists it. |
| Effort | 10 minutes |
| Verdict | Trivial to add if needed for compliance. |

### 21. Notifications System

| Details | `notifications` table exists in schema. No API endpoint to list/mark notifications. No real-time push. |
| Effort | 1 day |
| Verdict | Not critical for demo. |

---

## IMPLEMENTATION PRIORITY ROADMAP

If continuing development, here's the recommended order:

| Day | Tasks | Impact |
|-----|-------|--------|
| Day 1 | #1 (Seed dataset) + #8 (Knowledge base seeding) | Dashboard/graph populated, RAG chat functional |
| Day 2 | #2 (Processing stepper) + #3 (Geo analysis) + #12 (Score histogram) | Module 2 dashboard complete, Module 1 UX polished |
| Day 3 | #4 (Ring listing) + #5 (Ring-level package) + #6 (Multi-hop subgraph) | Module 3 fully functional |
| Day 4 | #7 (Report-scoped chat) + #9 (Entity types) + #10 (Threat timeline) | Module 1 chat improved, Agent 4 complete |
| Day 5 | #11 (Evidence timeline) + #13 (Graph correlate) + #14 (Export evidence) + #15 (Full package structure) | All remaining PRD features |

**Total estimated remaining effort: ~7–8 developer-days**

---

## WHAT'S STRONG (No Work Needed)

These areas are production-quality and need no changes:

1. Authentication system (JWT + refresh + sessions + role-based)
2. Agent 1 Input Processing (real offline OCR + ASR)
3. Agent 2 Threat Detection (LLM + rule-engine fallback with proper degradation)
4. Entity extraction pipeline + relationship building
5. Neo4j graph indexing with graceful fallback
6. PDF report generation (professional styling)
7. Frontend Module 1 (Citizen Fraud Shield) — nearly complete UX
8. Frontend Module 2 (Officer Dashboard) — functional core
9. Frontend Module 3 (Threat Intel) — force-directed graph working
10. Database schema — comprehensive, matches PRD §13 closely
11. Docker infrastructure — all services defined
12. Error handling / graceful degradation pattern across all agents
