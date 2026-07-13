# Truvia
## AI Public Safety Intelligence Platform
### Product Requirements Document — ET AI Hackathon 2026

**Track:** AI for Digital Public Safety — Defeating Counterfeiting, Fraud & Digital Arrest Scams
**Document Owner:** Product & Engineering
**Version:** 1.0
**Status:** Build-Ready

---

## Table of Contents

1. [Product Identity](#1-product-identity)
2. [Executive Summary](#2-executive-summary)
3. [Problem Statement & Why Existing Solutions Fail](#3-problem-statement--why-existing-solutions-fail)
4. [Product Vision & Goal](#4-product-vision--goal)
5. [Why Truvia Is Not "Another Scam Detector"](#5-why-truvia-is-not-another-scam-detector)
6. [Scope: MVP vs. Stretch Goals](#6-scope-mvp-vs-stretch-goals)
7. [Hackathon Requirement Mapping](#7-hackathon-requirement-mapping)
8. [Core User Modules](#8-core-user-modules)
   - 8.1 [Module 1 — Citizen Fraud Shield](#81-module-1--citizen-fraud-shield)
   - 8.2 [Module 2 — Law Enforcement Intelligence Dashboard](#82-module-2--law-enforcement-intelligence-dashboard)
   - 8.3 [Module 3 — Threat Intelligence Engine](#83-module-3--threat-intelligence-engine)
9. [Agentic AI Architecture](#9-agentic-ai-architecture)
10. [System Architecture & Data Flow](#10-system-architecture--data-flow)
11. [Predictive Intelligence Layer](#11-predictive-intelligence-layer)
12. [Court-Ready Intelligence Packages](#12-court-ready-intelligence-packages)
13. [Data Architecture & Database Schema](#13-data-architecture--database-schema)
14. [Technology Stack & Justification](#14-technology-stack--justification)
15. [Design System](#15-design-system)
16. [18-Day Build Roadmap](#16-18-day-build-roadmap)
17. [Risk Register & Mitigation](#17-risk-register--mitigation)
18. [Success Metrics & Judging Alignment](#18-success-metrics--judging-alignment)
19. [Appendix](#19-appendix)

---

## 1. Product Identity

### Name
**Truvia**

### Etymology
A fusion of **"Truth"** and **"Via"** (Latin for *way/path*) — "the path to truth." The name signals the product's core function: not just flagging suspicious content, but illuminating the verified path of an investigation, from a citizen's report to a prosecutable case.

### Mission Statement
> To give every citizen, bank, and law enforcement officer the same intelligence advantage that organized fraud networks already have — and to stop fraud before the money moves.

### Vision Statement
> A connected national fraud-intelligence layer where every complaint, screenshot, and phone call makes the entire system smarter — so that the 10,000th victim is protected by the intelligence extracted from the first.

### Tagline
> **"Truvia — See the Fraud Before It Sees You."**

### Product Positioning Statement
For citizens who are targeted by digital arrest scams, phishing, and fraud, and for law enforcement agencies who investigate them, **Truvia** is an AI-powered public-safety intelligence platform that transforms unstructured complaints into structured, explainable, court-ready intelligence — unlike point-solution "scam checkers," Truvia builds a continuously-learning threat graph that connects individual complaints into fraud rings, enabling **pre-transaction prevention**, not just post-incident reporting.

---

## 2. Executive Summary

Digital arrest scams, UPI fraud, and impersonation scams in India (and globally) share a common weakness in the current response system: **every complaint is treated as an isolated event.** A citizen reports a scam call to a bank; a different citizen reports a similar call to the police; a third reports a phishing SMS to CERT-In. None of these systems talk to each other. The fraud ring behind all three complaints is never identified, and the scam script keeps working on victim #4, #5, and #500.

**Truvia** closes this gap. It is a three-module intelligence platform, powered by six coordinated AI agents, that:

1. **Ingests** citizen-submitted evidence (screenshots, call recordings, chat text) and extracts structured signal from unstructured noise using OCR, Speech-to-Text, and NLP.
2. **Scores and explains** the threat in real time, in language a non-technical citizen understands, backed by cited regulatory guidance (RBI, NCRP, CERT-In, MHA, NPCI).
3. **Extracts entities** (phone numbers, UPI IDs, bank accounts, domains, device fingerprints) from every report and feeds them into a **persistent, continuously-growing fraud graph**.
4. **Correlates** new complaints against this graph in real time to detect fraud rings, repeat offenders, and emerging scam patterns — often before a victim has transferred money.
5. **Packages** the resulting intelligence into a dashboard for cybercrime officers and a structured, evidentiary report suitable for case escalation.

The MVP, buildable by a two-person team in 18 days, demonstrates this full pipeline end-to-end on a curated but realistic dataset, with an architecture explicitly designed to scale to national deployment.

---

## 3. Problem Statement & Why Existing Solutions Fail

| Failure Mode in Existing Systems | Consequence | How Truvia Addresses It |
|---|---|---|
| Every complaint is siloed (bank, police station, CERT-In portal, telecom) | Fraud rings using the same script across hundreds of victims go undetected | Central entity graph correlates complaints across all intake channels |
| Fraud detection happens *after* money has moved | Recovery rates are extremely low (single digits in most jurisdictions) | Real-time threat scoring during an active call/chat, before transfer |
| Existing "AI scam checkers" output a binary label (Scam / Not Scam) | No investigative value; officers still start from zero | Truvia outputs structured, explainable intelligence packages, not labels |
| Officers manually cross-reference phone numbers/UPI IDs across cases | Extremely slow, error-prone, doesn't scale past a handful of cases | Automated entity-linking + graph-based fraud ring detection |
| Reports rarely translate into usable legal evidence | Cases stall for lack of admissible, structured documentation | Auto-generated court-ready intelligence packages with timeline & evidence chain |
| No feedback loop — the system doesn't get smarter | Same scam scripts recycle for years | Every new report strengthens the graph and retrains detection heuristics |

---

## 4. Product Vision & Goal

Truvia operates as an **intelligence layer** connecting four stakeholders that currently do not share data:

```
   CITIZENS
      │  (reports, screenshots, calls)
      ▼
   ┌─────────────────────────┐
   │        TRUVIA            │
   │  (Intelligence Layer)    │
   └─────────────────────────┘
      │            │            │
      ▼            ▼            ▼
   BANKS      LAW ENFORCEMENT   GOVT / THREAT INTEL
 (fraud alerts) (case packages)  (CERT-In, NCRP feeds)
```

**Primary Goal:** Shift the intervention point from *after* the transfer (reporting) to *before* the transfer (prevention), by giving citizens a real-time threat score during an ongoing scam interaction and giving officers early warning of emerging fraud rings.

**Secondary Goal:** Every unit of data ingested — a screenshot, a recording, a complaint — must permanently increase the intelligence value of the system for all future users. Truvia is designed as a compounding intelligence asset, not a stateless classifier.

---

## 5. Why Truvia Is Not "Another Scam Detector"

Most hackathon submissions in this space stop at classification: *"Upload a message, get a scam/not-scam label."* This has limited real-world value because:

- Cybercrime officers don't need a label — they need **who, how many others, and how connected.**
- A single classification has no persistence — it dies the moment the API call returns.
- It offers no path to prosecution.

**Truvia's differentiator is the Threat Intelligence Engine (Module 3).** Every report submitted through the Citizen Fraud Shield doesn't just get scored — it is decomposed into entities (phone numbers, UPI IDs, domains, device signals) that are inserted into a **persistent graph database**. This graph is queried on every new report to answer questions no single-report classifier ever could:

- *Has this phone number appeared in other complaints?*
- *Is this UPI ID part of a cluster of 40 other complaints filed in the last 10 days?*
- *Does this scam script match a known "digital arrest" pattern used by a specific ring active in 3 states?*

This reframes the product from **"fraud classification"** to **"fraud intelligence generation"** — directly matching the hackathon's emphasis on Graph Intelligence, Multi-source Intelligence, and Predictive Threat Detection, and giving judges a technically defensible reason the product could not be built as a weekend wrapper around an LLM prompt.

---

## 6. Scope: MVP vs. Stretch Goals

Given 2 developers and 18 days, the MVP is deliberately scoped to demonstrate the **full pipeline at small but real scale**, rather than a subset of features at large scale.

### MVP (Must Build — Days 1–16)

| Area | MVP Scope |
|---|---|
| Citizen Fraud Shield | Screenshot upload + OCR, audio upload + STT, paste-text, threat scoring, explainability, chat assistant (RAG), report download, scam history (seeded + user-generated) |
| Law Enforcement Dashboard | KPI cards, complaint table with filters/search, investigation view with AI summary, threat score distribution, city-level breakdown (static geo boundaries), export to PDF |
| Threat Intelligence Engine | Entity extraction, graph construction (Neo4j), interactive fraud graph visualization, fraud-ring clustering (rule-based + community detection), entity explorer, correlation search |
| Agents | All 6 agents implemented as real orchestrated services (not mocked), with clear input/output contracts |
| Data | Seeded dataset of ~150–300 synthetic-but-realistic complaints to make the graph and dashboard meaningfully populated on Day 1 of demo |

### Stretch Goals (Days 17–18 or "Future Scope" slides if time runs out)

| Area | Stretch Scope |
|---|---|
| Live phone-call threat scoring (streaming STT) | Architected, not fully real-time in demo |
| True geospatial heatmaps (lat/long clustering) | Static/mock district map acceptable for MVP |
| Multi-language OCR/STT (Hindi, regional languages) | English + one regional language demo, rest documented as roadmap |
| Officer case assignment workflows (multi-user RBAC) | Single-role dashboard for MVP; RBAC documented as v2 |
| Production-grade court-package digital signing / chain-of-custody hashing | Report structure built; cryptographic chain-of-custody documented as v2 |
| National integration with actual NCRP/CERT-In APIs | Simulated knowledge base ingestion from public RBI/CERT-In advisories |

### Explicitly Out of Scope for Hackathon
- Real bank transaction blocking/API integration
- Legal admissibility certification (only structure/format is demonstrated)
- Multi-tenant government SSO/auth integration

---

## 7. Hackathon Requirement Mapping

| Official Requirement | Satisfied By |
|---|---|
| Digital Arrest Scam Detection | Threat Detection Agent + scam-category taxonomy including "Digital Arrest" pattern class |
| Fraud Intelligence | Threat Intelligence Engine (Module 3) — entity graph, correlation, ring detection |
| AI Agents | 6-agent orchestrated pipeline (Section 9) |
| Multi-source Intelligence | Ingests screenshot (vision/OCR), audio (speech), text, and structured knowledge base (RBI/NCRP/CERT-In) |
| Explainable AI | Every threat score ships with a natural-language reasoning trace + cited evidence (Threat Detection Agent output contract) |
| Graph Intelligence | Neo4j-backed fraud graph, Entity Explorer, Fraud Ring Detection |
| Geospatial Intelligence | City/District Analysis dashboard panel; architecture supports full lat/long heatmaps in v2 |
| Public Safety | Citizen Fraud Shield — real-time prevention guidance before money transfer |
| Law Enforcement | Module 2 — full investigation dashboard, case summaries, evidence export |
| Predictive Threat Detection | Section 11 — emerging scam trend detection, high-risk entity ranking |
| Court-admissible Intelligence | Section 12 — structured Intelligence Package generation |

---

## 8. Core User Modules

### 8.1 Module 1 — Citizen Fraud Shield

**Objective:** Give any citizen, in under 60 seconds, a clear, explainable threat verdict on a suspicious call, message, or screenshot — and a concrete next action — before they act on the scammer's instructions.

**Features**
- Upload Screenshot (image → OCR)
- Upload Audio (call/voice note → Speech-to-Text)
- Paste Text (SMS/WhatsApp/email body)
- Automated OCR & Speech-to-Text pipeline with language detection
- Threat Analysis with Scam Category (e.g., Digital Arrest, UPI Refund Scam, Loan App Harassment, Investment/Trading Fraud, Impersonation — Police/CBI/Customs, Job Scam, Sextortion, KYC Update Fraud)
- Threat Intelligence Score (0–100) with severity band (Low / Moderate / High / Critical)
- Confidence Score (model certainty, shown separately from threat score)
- Explainable AI panel — plain-language reasoning: which phrases, patterns, or entities drove the score
- Recommended Actions (contextual: "Do not share OTP," "This is not how CBI operates," "Block and report this UPI ID")
- Download Investigation Report (PDF, individual case)
- Report to Police (pre-filled structured complaint, exportable/submittable)
- AI Chat Assistant (RAG-grounded, cites RBI/NCRP/CERT-In guidance — not a generic chatbot persona)
- Scam History (citizen's own past submissions)
- Recent Public Scam Alerts (aggregated, anonymized feed of trending scam patterns detected system-wide)

**User Flow**
1. Citizen lands on Fraud Shield home → chooses input type (screenshot / audio / text).
2. Uploads evidence → sees live processing states ("Extracting text…", "Analyzing threat patterns…", "Cross-checking known fraud entities…").
3. Result screen: Threat Score, Category, Confidence, Explainability panel, Recommended Actions.
4. Citizen can ask follow-up questions to the AI Chat Assistant ("Is this how the CBI actually contacts people?").
5. Citizen downloads report and/or submits to police queue.
6. Citizen browses Recent Public Scam Alerts to see if others reported similar patterns.

**UI Components**
- Multi-modal upload dropzone with type auto-detection
- Processing/status stepper (mirrors backend agent pipeline stages — reinforces "intelligence system" feel, not "chatbot")
- Threat Score gauge (radial, color-coded by severity band)
- Explainability accordion (evidence-by-evidence breakdown)
- Action checklist cards
- Chat panel with citation chips linking to source guideline
- History table with status badges
- Public alert feed (card grid)

**Backend APIs**
- `POST /api/v1/reports` — create report (multipart: image/audio/text)
- `GET /api/v1/reports/{id}` — fetch processed result
- `GET /api/v1/reports/{id}/status` — poll pipeline stage (for live stepper)
- `POST /api/v1/reports/{id}/chat` — RAG chat scoped to report context
- `GET /api/v1/reports/{id}/download` — generate/download PDF
- `POST /api/v1/reports/{id}/escalate` — push to police queue
- `GET /api/v1/alerts/public` — trending public alerts feed
- `GET /api/v1/users/{id}/history` — citizen's report history

**AI Used**
- OCR (vision-language extraction)
- Speech-to-Text (ASR)
- LLM-based threat classification & reasoning (Threat Detection Agent)
- RAG pipeline over regulatory knowledge base (Knowledge Intelligence Agent)
- NER/entity extraction (Entity Intelligence Agent, silently feeds Module 3)

**Database Tables Touched:** `reports`, `entities`, `threat_scores`, `evidence`, `users`, `knowledge_base` (read), `alerts`

**Future Scope**
- Real-time in-call threat scoring via streaming ASR during an active phone call
- Browser/SMS-app plugin for automatic flagging before the citizen even opens Truvia
- WhatsApp Business API bot for zero-friction reporting

---

### 8.2 Module 2 — Law Enforcement Intelligence Dashboard

**Objective:** Give a cybercrime officer, in one screen, a command-center view of complaint volume, emerging patterns, and individual case depth — replacing manual spreadsheet triage.

**Features**
- Dashboard home with KPI Cards (Total Complaints, Active Cases, High-Risk Entities, Fraud Rings Detected, Avg. Threat Score Trend)
- Complaint Trends (time-series chart, filterable by category/city)
- Emerging Scam Trends panel (patterns gaining velocity in last 7/30 days)
- Threat Timeline (chronological event stream across all incoming reports)
- Complaint Table with Search & Filters (category, city, score range, date, status)
- Investigation View (single-case deep dive): AI Summary, extracted entities, linked complaints, evidence
- Case Assignment (assign complaint to officer/team — MVP: single-tenant status field; v2: full RBAC)
- Intelligence Package generation button (produces Section 12 output)
- Evidence Timeline (per-case chronological evidence chain)
- Threat Score Distribution (histogram across all complaints)
- City/District Analysis (bar/choropleth-style breakdown)
- Recent Reports feed
- Export Report (PDF/CSV)

**User Flow**
1. Officer logs in → lands on Dashboard with KPI overview.
2. Scans Emerging Scam Trends panel → clicks into a trending pattern.
3. Views filtered Complaint Table of matching cases.
4. Opens Investigation View on a specific complaint → reviews AI Summary + linked entities.
5. Clicks "Generate Intelligence Package" → reviews and exports structured case file.
6. Optionally jumps into Module 3 (Threat Intelligence Engine) directly from the Investigation View to explore the entity's graph neighborhood.

**UI Components**
- KPI card row (dense, data-forward, dark-mode-friendly)
- Time-series line/area chart (complaint trends)
- Sortable/filterable data table (virtualized for scale)
- Case detail drawer/panel with tabs (Summary / Entities / Evidence / Timeline)
- Histogram component (threat score distribution)
- District bar chart (Recharts) with map-style color legend
- Export/print-friendly report layout

**Backend APIs**
- `GET /api/v1/dashboard/kpis`
- `GET /api/v1/dashboard/trends?range=`
- `GET /api/v1/complaints?filters...`
- `GET /api/v1/complaints/{id}`
- `POST /api/v1/complaints/{id}/assign`
- `POST /api/v1/complaints/{id}/intelligence-package`
- `GET /api/v1/dashboard/geo-breakdown`
- `GET /api/v1/dashboard/emerging-trends`
- `GET /api/v1/complaints/{id}/export`

**AI Used**
- Alert & Investigation Agent (AI Summary, Case Summary generation)
- Threat Intelligence Agent (feeds emerging trend detection, linked-complaint suggestions)
- LLM summarization for natural-language case briefs

**Database Tables Touched:** `cases`, `reports`, `entities`, `relationships`, `threat_scores`, `evidence`, `users` (officer roles)

**Future Scope**
- Multi-officer collaborative case notes
- Automated case routing based on jurisdiction/entity geolocation
- Integration with actual NCRP case-ID system for bidirectional sync

---

### 8.3 Module 3 — Threat Intelligence Engine

**Objective:** Maintain a continuously-growing, queryable knowledge graph of fraud entities and their relationships, enabling correlation, ring detection, and predictive risk-ranking that no single complaint could reveal alone.

**Features**
- Interactive Fraud Graph (force-directed visualization of entities & relationships)
- Fraud Ring Detection (community-detection clustering over the graph)
- Entity Explorer (search any phone/UPI/email/domain/device/IP, see full profile + connections)
- Complaint Correlation (given a new report, instantly surface related historical complaints)
- Phone Number Intelligence (frequency, associated categories, risk tier)
- UPI Intelligence (linked accounts, transaction-pattern flags, associated complaints)
- Email Intelligence
- Website/Domain Intelligence (registration age proxy, associated scam categories)
- Device Intelligence (device fingerprint reappearance across complaints)
- IP Intelligence (IP reappearance, geolocation clustering)
- Risk Network view (subgraph centered on a high-risk entity)
- Cluster Detection (algorithmic grouping of tightly-connected entities = probable fraud ring)
- Threat Relationships (typed edges: "same phone used in," "same UPI linked to," "same script pattern as")
- Investigation Timeline (graph-driven chronological reconstruction of a ring's activity)
- Generate Intelligence Package (from graph context — richer than the single-case version in Module 2)
- Export Evidence (entity subgraph + supporting complaint IDs)

**User Flow**
1. User (officer or analyst) lands on Threat Intelligence Engine home → sees the full graph at a zoomed-out cluster level.
2. Searches or clicks a specific entity (e.g., a UPI ID) → Entity Explorer opens with full profile.
3. Views the Risk Network subgraph centered on that entity → identifies a Fraud Ring cluster.
4. Reviews Complaint Correlation list — all complaints touching this ring.
5. Generates an Intelligence Package for the entire ring (not just one complaint).
6. Exports evidence bundle for law enforcement escalation.

**UI Components**
- Force-directed graph canvas (zoom/pan/click-to-expand nodes)
- Entity profile side panel (tabs: Overview / Connections / Complaints / Risk History)
- Cluster highlight overlay (color-coded ring groupings)
- Correlation results list (ranked by relevance)
- Risk tier badges (Low/Medium/High/Critical) on every entity
- Package generation modal with preview

**Backend APIs**
- `GET /api/v1/graph/overview` — cluster-level graph snapshot
- `GET /api/v1/graph/entity/{id}` — entity profile + immediate neighbors
- `GET /api/v1/graph/entity/{id}/subgraph?depth=` — expanded risk network
- `GET /api/v1/graph/correlate?report_id=` — related complaints for a new report
- `GET /api/v1/graph/rings` — detected fraud ring clusters
- `POST /api/v1/graph/intelligence-package` — generate ring-level package
- `GET /api/v1/graph/entity/{id}/risk-score`

**AI Used**
- Entity Intelligence Agent (extraction feeding the graph)
- Threat Intelligence Agent (graph construction, entity linking, ring detection, risk ranking)
- Graph algorithms: connected-components / Louvain community detection for clustering
- Alert & Investigation Agent (package generation from graph context)

**Database Tables Touched:** `entities`, `relationships` (graph store: Neo4j), mirrored/synced from `reports` and `evidence` in the relational store

**Future Scope**
- Temporal graph analysis (how a ring's structure evolves week over week)
- Cross-border entity correlation (international phone/UPI equivalents)
- Graph neural network (GNN) based risk propagation instead of rule-based clustering
- Automated new-ring alerting the moment a cluster crosses a size/velocity threshold

---

## 9. Agentic AI Architecture

Truvia's backend is not a single LLM prompt — it is a coordinated pipeline of six specialized agents, each with a narrow responsibility, explicit input/output contracts, and independent failure handling. This mirrors how real cybercrime intelligence units divide labor (intake → triage → research → forensics → investigation).

### Agent 1 — Input Processing Agent

| Field | Detail |
|---|---|
| Responsibility | OCR, Speech-to-Text, text cleaning, input validation, language detection |
| Inputs | Raw upload (image / audio file / pasted text) |
| Outputs | Normalized `CleanedInput` object: `{ raw_text, source_type, detected_language, confidence, warnings[] }` |
| Internal Workflow | 1) Detect input type → 2) route to OCR or ASR engine → 3) run language detection → 4) sanitize/normalize text (strip artifacts, fix encoding) → 5) validate non-empty/non-corrupt → 6) emit `CleanedInput` |
| Models Used | Vision-language OCR model (screenshot text extraction); ASR model for speech-to-text; lightweight language-ID classifier |
| APIs Used | Internal `/agents/input-processing/process` |
| Failure Handling | If OCR/ASR confidence < threshold, flag `low_confidence: true` and pass through to Threat Detection Agent with a caveat banner shown to the user rather than hard-failing; corrupt/unsupported files return a clear user-facing error with retry guidance |
| Future Improvements | Multi-language OCR/ASR (regional Indian languages), video call frame extraction, noise-robust ASR for poor call quality |

### Agent 2 — Threat Detection Agent

| Field | Detail |
|---|---|
| Responsibility | Scam detection, threat scoring, scam category classification, confidence scoring, explainability/reasoning |
| Inputs | `CleanedInput` from Agent 1, plus historical pattern context from Agent 5 (if available) |
| Outputs | `ThreatAssessment`: `{ threat_score, severity_band, scam_category, confidence_score, reasoning[], flagged_phrases[] }` |
| Internal Workflow | 1) Pattern-match against known scam-script taxonomy → 2) LLM structured-reasoning pass over the cleaned text → 3) merge rule-based signals (urgency language, authority impersonation, payment requests, OTP requests) with LLM judgment → 4) compute weighted threat score → 5) generate plain-language explanation citing exact flagged phrases |
| Models Used | LLM (structured JSON output mode) for classification + reasoning; rule-based feature extractor for known red-flag phrase patterns |
| APIs Used | Internal `/agents/threat-detection/analyze`; calls Agent 5 for historical-pattern boost (async, non-blocking) |
| Failure Handling | If LLM call fails/times out, fall back to rule-based-only scoring with `degraded_mode: true` flag so the UI can show reduced-confidence messaging instead of failing the request |
| Future Improvements | Fine-tuned classifier trained on growing Truvia complaint corpus; multi-turn conversation threat tracking (not just single message) |

### Agent 3 — Knowledge Intelligence Agent

| Field | Detail |
|---|---|
| Responsibility | RAG-based question answering grounded in official guidance, with citations |
| Inputs | User chat query, current report context (scam category, entities) |
| Outputs | `GroundedAnswer`: `{ answer_text, citations[] }` where each citation references a source document/section |
| Internal Workflow | 1) Embed query → 2) retrieve top-k relevant chunks from vector store of ingested knowledge base → 3) construct grounded prompt with retrieved chunks → 4) generate answer with inline citation markers → 5) validate citations map to real retrieved chunks before returning |
| Models Used | Embedding model + LLM generation with retrieval-augmented prompting |
| Knowledge Sources | RBI advisories, MHA guidelines, NCRP procedures, CERT-In alerts, NPCI UPI safety guidance, curated scam-pattern knowledge base |
| APIs Used | Internal `/agents/knowledge/query`; vector store query API |
| Failure Handling | If retrieval returns no relevant chunks above similarity threshold, respond with an honest "not covered in current knowledge base" message rather than an ungrounded hallucinated answer |
| Future Improvements | Auto-ingest new RBI/CERT-In advisories via scheduled scraping; multi-hop reasoning across documents |

### Agent 4 — Entity Intelligence Agent

| Field | Detail |
|---|---|
| Responsibility | Extract structured entities from cleaned input for graph intelligence |
| Inputs | `CleanedInput` (Agent 1) + `ThreatAssessment` (Agent 2) |
| Outputs | `ExtractedEntities[]`: typed list — phone numbers, emails, URLs/domains, UPI IDs, bank accounts, IFSC codes, device IDs, IP addresses, impersonated government/org names |
| Internal Workflow | 1) Run regex/pattern extractors for structured formats (phone, UPI, IFSC, email, URL) → 2) run NER pass for named entities (org/government impersonation names) → 3) normalize formats (e.g., phone number standardization) → 4) deduplicate within the report → 5) emit typed entity list with source-offset references |
| Models Used | NER model + deterministic pattern extractors (regex/format validators) for high-precision structured fields |
| APIs Used | Internal `/agents/entity-intelligence/extract` |
| Failure Handling | Pattern extractors are deterministic and near-zero-failure; if NER model fails, structured (regex-based) entities still return successfully — degraded gracefully rather than blocking the pipeline |
| Future Improvements | Cross-reference extracted org names against a verified government-contact registry to auto-flag impersonation with near-certainty |

### Agent 5 — Threat Intelligence Agent

| Field | Detail |
|---|---|
| Responsibility | Build/update the fraud intelligence graph; entity linking, fraud ring detection, complaint correlation, risk ranking, emerging scam detection, repeat offender detection |
| Inputs | `ExtractedEntities[]` (Agent 4), full report metadata |
| Outputs | `GraphUpdateResult`: `{ new_nodes, new_edges, correlated_complaints[], ring_membership, updated_risk_scores }` |
| Internal Workflow | 1) Upsert entities as graph nodes (dedup by normalized value) → 2) create/strengthen typed edges (e.g., "co-occurred-in-report," "same-script-pattern") → 3) run correlation query against existing graph for matching entities → 4) run community-detection clustering to check ring membership → 5) recompute risk score for touched nodes based on frequency + recency + cluster size → 6) flag emerging trend if a category's complaint velocity crosses threshold |
| Models Used | Graph algorithms (connected components, Louvain community detection); statistical recency/frequency weighting for risk scoring |
| APIs Used | Internal `/agents/threat-intelligence/update-graph`; Neo4j Cypher queries |
| Failure Handling | Graph writes are transactional; if clustering computation fails, entity/edge insertion still commits and clustering is retried on next scheduled batch job rather than blocking report submission |
| Future Improvements | Graph Neural Network-based risk propagation; temporal graph snapshots for trend visualization over time |

### Agent 6 — Alert & Investigation Agent

| Field | Detail |
|---|---|
| Responsibility | Generate all downstream human-facing outputs: citizen alerts, officer alerts, investigation reports, court-ready intelligence packages, dashboard updates, case summaries, evidence summaries |
| Inputs | Outputs of Agents 2, 4, and 5 (`ThreatAssessment`, `ExtractedEntities`, `GraphUpdateResult`) |
| Outputs | `CitizenAlert`, `OfficerBrief`, `InvestigationReport` (PDF-ready structured doc), `IntelligencePackage` |
| Internal Workflow | 1) Select appropriate template based on severity/context → 2) populate template with structured data from upstream agents → 3) generate LLM-written natural-language summary sections → 4) assemble final structured document (JSON → rendered PDF) → 5) push relevant updates to dashboard cache |
| Models Used | LLM for natural-language summary/brief generation; deterministic templating for structured sections (entities, timeline, scores) |
| APIs Used | Internal `/agents/alert-investigation/generate`; PDF rendering service |
| Failure Handling | Structured/templated sections always render even if the LLM summary generation fails — user still receives a complete, data-accurate report with a shorter auto-generated summary fallback |
| Future Improvements | Digital chain-of-custody signing (cryptographic hash per evidence item); direct e-filing integration with NCRP case system |

---

## 10. System Architecture & Data Flow

```
┌──────────┐      ┌───────────┐      ┌────────────────────────┐
│ CITIZEN  │─────▶│  GATEWAY   │─────▶│  Agent 1: Input          │
│ (upload) │      │ (API/Auth) │      │  Processing               │
└──────────┘      └───────────┘      └────────────┬─────────────┘
                                                    ▼
                                     ┌────────────────────────────┐
                                     │  Agent 2: Threat Detection  │
                                     │  (score, category, reason)  │
                                     └────────────┬─────────────────┘
                                                    ▼
                         ┌──────────────────────────────────────────┐
                         │  Agent 3: Knowledge Intelligence (RAG)     │◀── chat queries
                         │  (grounded answers, citations)             │
                         └────────────────────────┬────────────────────┘
                                                    ▼
                                     ┌────────────────────────────┐
                                     │  Agent 4: Entity            │
                                     │  Intelligence (extraction)  │
                                     └────────────┬─────────────────┘
                                                    ▼
                                     ┌────────────────────────────┐
                                     │  Agent 5: Threat            │
                                     │  Intelligence (graph, rings)│
                                     └────────────┬─────────────────┘
                                                    ▼
                                     ┌────────────────────────────┐
                                     │  Agent 6: Alert &           │
                                     │  Investigation (reports)    │
                                     └────────────┬─────────────────┘
                                                    ▼
                          ┌───────────────────────────────────────────┐
                          │             DATABASE LAYER                  │
                          │  PostgreSQL (relational) + Neo4j (graph)    │
                          │  + Vector Store (knowledge embeddings)      │
                          └───────────────────────┬─────────────────────┘
                                                    ▼
                     ┌───────────────────────────────────────────────────┐
                     │        DASHBOARDS (Citizen / Officer / Analyst)    │
                     │   Module 1        Module 2         Module 3        │
                     │  Fraud Shield   LE Dashboard   Threat Intel Engine │
                     └───────────────────────────────────────────────────┘
```

**Orchestration model:** Agents 1→2→4→5→6 form the synchronous core pipeline for a new report (target: <8s end-to-end for text, <20s including OCR/ASR for media). Agent 3 (Knowledge Intelligence) runs on-demand for chat queries, decoupled from the core pipeline. Dashboard reads are served from cached/materialized views over the database layer, not computed live on every page load, so Module 2/3 dashboards stay responsive as data grows.

**Orchestration technology:** A lightweight internal job orchestrator (queue-based, e.g., a Redis-backed task queue) sequences agent calls, enabling each agent to fail independently and retry without cascading failure — critical for demoing reliability to judges.

---

## 11. Predictive Intelligence Layer

Even within an 18-day MVP, Truvia is architected as a genuine prediction system, not a static rule engine, using transparent heuristics that are explicitly designed to be replaced by learned models post-hackathon.

| Predictive Feature | MVP Implementation | v2 Upgrade Path |
|---|---|---|
| Emerging Scam Trends | Rolling 7-day complaint-velocity per category vs. 30-day baseline; flag categories with >X% velocity increase | Time-series forecasting model (e.g., Prophet) per category |
| Frequently Used Scam Scripts | Cluster reports by text-embedding similarity; surface top recurring script templates | Fine-tuned script-classification model updated on new corpus |
| High-Risk Phone Numbers | Risk score = f(frequency of appearance, recency, number of distinct victims, cluster size) | Graph-propagated risk (GNN) incorporating multi-hop connections |
| High-Risk UPI IDs | Same risk-scoring formula applied to UPI entity nodes | Cross-referenced with anonymized transaction-pattern signals (future bank partnership) |
| High-Risk Websites/Domains | Frequency + category association + presence in known phishing-pattern list | Domain reputation model incorporating registration-age proxies, SSL/hosting signals |
| Most Active Fraud Rings | Ranked by cluster size × complaint velocity within the cluster | Ring lifecycle modeling — predicting when a ring is likely to spin up new "shell" entities |

All risk scores are recomputed incrementally as new reports arrive (via Agent 5), meaning the Threat Intelligence Engine's predictions get sharper the more the platform is used — the core "compounding intelligence" thesis of the product.

---

## 12. Court-Ready Intelligence Packages

Every Intelligence Package generated by the Alert & Investigation Agent (whether triggered from a single complaint in Module 2 or a full ring in Module 3) follows a consistent, structured format designed to mirror what an investigating officer would need to escalate a case:

| Section | Contents |
|---|---|
| Case Header | Case ID, generation timestamp, severity classification, generating officer/system |
| Timeline | Chronological reconstruction of all linked events (report submission times, prior related complaints, entity first-seen/last-seen dates) |
| Evidence | Original uploaded artifacts (screenshot/audio/text) with extraction metadata, OCR/ASR confidence noted |
| Extracted Entities | Full structured entity list with type, normalized value, and first/last seen dates |
| Threat Analysis | Threat score, scam category, and full AI reasoning trace from Agent 2 |
| AI Explanation | Human-readable narrative explaining *why* the system flagged this as fraud, with specific flagged phrases/patterns cited |
| Confidence Score | Explicit model confidence, separated from the threat score, so officers understand certainty vs. severity independently |
| Linked Complaints | All other complaint IDs sharing entities with this case, with the specific shared entity noted |
| Related Fraud Ring | If applicable, the ring ID, cluster size, and other entities in the ring |
| Officer Notes | Free-text field for investigator annotations, versioned/timestamped |

**MVP delivery format:** Structured JSON → rendered to a clean, formatted PDF via the reporting pipeline. **v2 roadmap (documented, not built in MVP):** cryptographic hash-based chain-of-custody per evidence item, digital signature on package generation, and direct e-filing hooks into NCRP's case system — explicitly flagged in the document as the path to true legal admissibility.

---

## 13. Data Architecture & Database Schema

Truvia uses a **polyglot persistence** model: a relational store for transactional/report data, a graph store for entity relationships, and a vector store for the knowledge base — because forcing all three into one relational schema (as a naive single-table design would) is precisely the anti-pattern this system must avoid to demonstrate "enterprise-grade" thinking to judges.

### 13.1 Relational Schema (PostgreSQL)

| Table | Key Columns | Purpose |
|---|---|---|
| `users` | id, role (citizen/officer/analyst), name, contact, created_at | All platform users across all modules |
| `reports` | id, user_id, source_type (screenshot/audio/text), raw_input_ref, cleaned_text, language, status, created_at | Every citizen submission — the intake record |
| `threat_scores` | id, report_id, threat_score, severity_band, scam_category, confidence_score, reasoning_json, model_version, created_at | Output of Threat Detection Agent, versioned for auditability |
| `entities` | id, type (phone/upi/email/domain/device/ip/org), normalized_value, first_seen_at, last_seen_at, risk_score | Master entity table (mirrored into graph store as nodes) |
| `report_entities` | report_id, entity_id, raw_span, confidence | Join table linking reports to extracted entities |
| `relationships` | id, entity_id_a, entity_id_b, relationship_type, strength, created_at | Mirrored into graph store as edges; kept relationally for backup/query simplicity |
| `cases` | id, report_id (nullable if ring-level), assigned_officer_id, status, priority, created_at | Investigation-level tracking, separate from raw reports |
| `evidence` | id, report_id, file_ref, evidence_type, extraction_metadata_json, hash | Raw artifact storage references + integrity hash |
| `knowledge_base` | id, source (RBI/MHA/NCRP/CERT-In/NPCI/custom), title, content, embedding_ref, ingested_at | Source documents for RAG, chunked and embedded separately |
| `alerts` | id, scope (public/officer), title, description, severity, related_case_id, created_at | Generated alerts surfaced in dashboards |
| `intelligence_packages` | id, case_id or ring_id, package_json, generated_at, generated_by | Immutable snapshot of generated court-ready packages |

### 13.2 Graph Schema (Neo4j)

**Nodes:** `Entity` (typed: Phone, UPI, Email, Domain, Device, IP, Org), `Report`, `Ring` (derived cluster node)

**Edges:** `CO_OCCURRED_IN` (Entity–Report), `LINKED_TO` (Entity–Entity, typed by relationship_type), `MEMBER_OF` (Entity–Ring), `SIMILAR_SCRIPT_TO` (Report–Report)

### 13.3 Vector Store

Chunked embeddings of `knowledge_base` content, indexed for similarity search by the Knowledge Intelligence Agent (Agent 3).

### 13.4 Why Not One Table
A single flat `reports` table (the naive approach) cannot represent many-to-many entity relationships, cannot support graph traversal queries ("find all complaints within 2 hops of this UPI ID"), and cannot cleanly version threat scores across model updates. Separating these concerns is what allows Module 3's graph queries to run in milliseconds instead of requiring runtime joins across an unindexed monolith — a decision explicitly called out for judges as evidence of production-minded engineering, not hackathon shortcuts.

---

## 14. Technology Stack & Justification

| Layer | Recommendation | Why Selected | Alternatives Considered | Trade-off |
|---|---|---|---|---|
| Frontend | **Next.js (React) + TypeScript + Tailwind CSS** | Fast to scaffold polished, responsive UIs; strong component ecosystem for dashboards/charts; SSR available if needed for report-sharing links | Plain React + Vite (faster raw setup, less batteries-included); SvelteKit (smaller footprint but smaller ecosystem for chart/graph libraries) | Next.js has slightly more boilerplate than Vite, but the built-in routing/API-route conventions save real time across 3 distinct modules in 18 days |
| Graph Visualization | **react-force-graph or Cytoscape.js** | Purpose-built for interactive force-directed graphs with click-to-expand, exactly matching Module 3's Entity Explorer needs | D3.js raw (maximum control, much higher build time); vis-network (good but less actively maintained) | Slightly less customizable than raw D3, but dramatically faster to ship a polished, judge-impressing graph UI in the time available |
| Charts/Dashboards | **Recharts** | Clean, React-native charting for KPI cards, trend lines, histograms; integrates naturally with Tailwind styling | Chart.js (solid but less idiomatic in React), Nivo (beautiful but heavier bundle) | Recharts trades some visual flexibility for speed and React-idiomatic code |
| Backend / API | **FastAPI (Python)** | Python is the natural choice given the AI-heavy workload (OCR/ASR/LLM orchestration all have first-class Python SDKs); FastAPI gives async support (critical for parallel agent calls) and auto-generated OpenAPI docs, which double as build-time documentation | Node.js/Express (would require bridging to Python AI libraries anyway); Django (too heavyweight/opinionated for an 18-day build) | FastAPI is less "batteries-included" than Django, but the async-first design directly benefits the multi-agent orchestration pattern |
| Relational Database | **PostgreSQL** | Mature, reliable, strong JSON column support (for storing reasoning traces/structured outputs flexibly alongside strict relational integrity for cases/users) | MySQL (comparable, weaker JSON/array support); SQLite (too limited for concurrent dashboard + intake writes) | None significant — Postgres is the safe, correct choice here |
| Graph Database | **Neo4j (Community/Aura Free tier)** | Purpose-built graph store with Cypher query language ideal for "N-hop entity correlation" and native community-detection (via GDS library) for fraud-ring clustering — directly maps to the hackathon's "Graph Intelligence" requirement | Storing relationships in Postgres with recursive CTEs (works at small scale, but multi-hop queries get slow and complex fast); ArangoDB (multi-model but smaller community/less hackathon-ready tooling) | Adds a second database to operate, but the clarity and demo-impressiveness of native graph queries far outweighs the added ops complexity for a judged hackathon |
| Vector Store | **pgvector extension on PostgreSQL** (not a separate vector DB) | Avoids standing up a 4th database system; pgvector is sufficient at the knowledge-base scale needed for RAG in an 18-day MVP | Pinecone/Weaviate/Chroma (better at massive scale, unnecessary operational overhead here) | Slightly less specialized RAG tooling, but consolidating infra is the right call for a 2-person team on a deadline |
| LLM Provider | **Anthropic Claude (via API)** for reasoning/classification/summarization/chat | Strong structured-output reliability (critical for the JSON contracts between agents), strong instruction-following for explainability text, generous context window for RAG-grounded chat | OpenAI GPT models (comparable capability, similar integration effort); open-source LLMs self-hosted (would consume the majority of the 18-day budget on infra alone) | API dependency and per-call cost, acceptable for a hackathon demo; architecture is provider-agnostic (all LLM calls routed through one internal abstraction layer) so switching providers post-hackathon is a config change, not a rewrite |
| OCR | **Cloud Vision OCR API (e.g., Google Cloud Vision or equivalent managed OCR)** | High accuracy out-of-the-box for screenshot text (varied fonts, WhatsApp/SMS UI chrome) without training a custom model | Open-source Tesseract (free but noticeably weaker accuracy on messy real-world screenshots) | Managed OCR has per-call cost, but the accuracy difference materially affects perceived product quality in a live demo |
| Speech-to-Text | **Managed ASR API (e.g., Whisper API or equivalent managed STT)** | Strong accuracy on Indian-accented English and reasonable regional-language support; no infra to manage | Self-hosted Whisper (avoids API cost but adds GPU/infra setup time neither developer can spare) | Slightly less control over the model, acceptable trade for reliability within the timeline |
| Agent Orchestration | **Lightweight custom orchestrator over a Redis-backed task queue** | Full transparency and control over the 6-agent pipeline's sequencing/retry logic — critical since the multi-agent architecture *is* the product's core differentiator and must be demoable, inspectable, and explainable to judges | Full agent frameworks (e.g., LangGraph, CrewAI) | Frameworks would save some boilerplate but add a layer of abstraction that makes it harder to clearly explain "here is exactly how Agent 2 hands off to Agent 4" in a judged demo — a custom, legible orchestrator is more defensible under technical questioning |
| Authentication | **JWT-based auth (simple email/password or magic link)** | Fast to implement, sufficient to demonstrate role separation (citizen vs. officer) | Full OAuth/SSO integration (correct for production, unnecessary complexity for MVP) | No enterprise SSO in MVP — explicitly documented as a v2 government-integration requirement |
| Deployment | **Frontend on Vercel; Backend + DBs on a single managed cloud VM/container group (e.g., Render or Railway) or directly on a cloud VM** | Fastest path to a stable, publicly demoable URL with minimal DevOps overhead for a 2-person team | Full Kubernetes setup (correct at true production scale, wildly disproportionate for 18 days) | Less horizontally scalable out of the box, but scaling story is documented in the roadmap as a config/infra change, not an architecture change |
| PDF Generation | **Server-side HTML-to-PDF rendering (e.g., a headless rendering library)** | Allows report templates to be styled with the same design system as the dashboards, keeping visual consistency between web UI and exported evidence | Client-side PDF libraries (weaker layout control for complex multi-section reports) | Slightly more backend complexity, but ensures the "court-ready" document actually looks professional |

**Guiding principle across all choices:** every technology decision optimizes for *"can two developers demo this convincingly and defend it under technical questioning in 18 days"* while every choice is explicitly documented with its production-scale upgrade path — so the same table doubles as evidence to judges that the team understands the difference between a hackathon shortcut and a real architectural decision.

---

## 15. Design System

Truvia's visual identity must read as **trustworthy government/enterprise security software** — closer to a SOC (Security Operations Center) dashboard or a cybercrime intelligence tool than a consumer app.

### Color Palette
| Role | Color | Usage |
|---|---|---|
| Primary — Trust Navy | `#0B1E39` | Headers, primary navigation, dashboard chrome |
| Secondary — Intelligence Blue | `#1959B8` | Primary actions, links, active states |
| Alert — Critical Red | `#D6303C` | Critical threat scores, urgent alerts |
| Warning — Amber | `#E8A33D` | Moderate/high threat bands |
| Safe — Verified Green | `#1F9D6B` | Low-risk states, verified/confirmed indicators |
| Neutral Base | `#F5F7FA` (light surface) / `#0F1621` (dark surface) | Backgrounds, supports both light and dark dashboard modes |
| Text | `#111827` on light, `#E5E7EB` on dark | Body copy |

### Typography
- **Headings:** Inter (Semibold/Bold) — clean, modern, highly legible at dashboard density
- **Body/UI:** Inter (Regular/Medium)
- **Data/Monospace (entity values, IDs, hashes):** JetBrains Mono — reinforces the "forensic/technical" feel for entity IDs, phone numbers, hashes

### Dashboard Style
- Dense but organized information hierarchy — KPI cards up top, detail below, consistent with SOC/NOC dashboard conventions
- Dark-mode-first for Modules 2 & 3 (Law Enforcement Dashboard, Threat Intelligence Engine) to match the "investigation software" register
- Light-mode-first for Module 1 (Citizen Fraud Shield) to feel approachable and non-intimidating for everyday citizens
- Severity-band color coding used consistently across all three modules (a "Critical" badge looks the same everywhere)

### Government-Grade UI Principles
- No playful illustration/mascot elements — icon-driven (line icons), data-forward
- Every AI-generated claim visibly cites its source or reasoning — never an unexplained black-box score
- Consistent badge/status vocabulary across modules (severity bands, confidence indicators)

### Accessibility
- WCAG AA contrast minimums across both light and dark themes
- All charts paired with data tables/alt-text summaries, not color-only encoding
- Full keyboard navigability on the Citizen Fraud Shield flow (critical given the anxious, time-pressured state of an actual scam victim using it)

### Mobile Responsiveness
- Module 1 (Citizen Fraud Shield) is **mobile-first** — the realistic scenario is a citizen mid-scam-call reaching for their phone, not a desktop
- Modules 2 & 3 are **desktop-first, tablet-responsive** — consistent with how officers actually work, but not required to be fully functional on a phone for MVP

---

## 16. 18-Day Build Roadmap

Two-developer split: **Dev A = Backend/AI Agents & Data**, **Dev B = Frontend/Dashboards & Integration**. Both collaborate on architecture decisions and demo prep.

| Day | Dev A (Backend / AI / Data) | Dev B (Frontend / UX / Integration) | Milestone |
|---|---|---|---|
| 1 | Finalize schema (Postgres + Neo4j), set up repos, provision DBs | Set up Next.js scaffold, design tokens, component library skeleton | Architecture locked |
| 2 | Build Agent 1 (Input Processing: OCR + STT integration) | Build Citizen Fraud Shield upload UI (dropzone, type detection) | Input pipeline online |
| 3 | Build Agent 2 (Threat Detection: scoring + reasoning) | Build Threat Score result screen + explainability panel | First end-to-end score demo |
| 4 | Build Agent 4 (Entity Intelligence: extraction) | Wire Fraud Shield to live backend (Agents 1+2) | **Milestone: Module 1 core loop functional** |
| 5 | Set up Neo4j, build Agent 5 core (entity linking, graph writes) | Build Recommended Actions + Report download (PDF) | Graph writes live |
| 6 | Ingest knowledge base docs, build Agent 3 (RAG chat) | Build AI Chat Assistant UI + citation display | RAG chat functional |
| 7 | Build fraud-ring clustering (community detection) | Build Threat Intelligence Engine graph canvas (force-directed) | Graph visualization online |
| 8 | Build correlation query API + risk scoring | Build Entity Explorer UI + Risk Network subgraph view | **Milestone: Module 3 core loop functional** |
| 9 | Build Agent 6 (report/package generation, PDF templating) | Build Law Enforcement Dashboard shell (KPI cards, nav) | Dashboard shell live |
| 10 | Build Complaint Trends + Emerging Trends aggregation APIs | Build Complaint Table + filters/search | Officer triage view functional |
| 11 | Build Investigation View APIs (case detail, linked complaints) | Build Investigation View UI (AI Summary, entities, evidence tabs) | **Milestone: Module 2 core loop functional** |
| 12 | Seed realistic synthetic dataset (150–300 complaints across categories/cities) | Build City/District Analysis + Threat Score Distribution charts | Populated demo data live |
| 13 | Build Intelligence Package generation (case-level + ring-level) | Build Intelligence Package preview/export UI | Court-ready packages functional |
| 14 | Predictive Intelligence heuristics (trend velocity, risk ranking) | Public Scam Alerts feed + Scam History UI | Predictive layer live |
| 15 | Integration hardening: failure handling across all 6 agents | Cross-module navigation polish (Module 2 ↔ 3 deep links) | Full pipeline stress-tested |
| 16 | Bug fixes, performance pass on graph queries | Full UI polish pass, responsive QA, accessibility pass | **MVP feature-complete** |
| 17 | Deployment to production URLs, environment hardening | Deployment, cross-browser QA, demo script rehearsal | Deployed & stable |
| 18 | Buffer day: fix any deployment issues, final data seeding | Buffer day: final polish, presentation deck, demo video recording | **Submission ready** |

### Risk Mitigation Built Into the Roadmap
- Days 16–18 are explicitly reserved as buffer/hardening, not new-feature days
- Each module reaches a "core loop functional" milestone independently (Days 4, 8, 11) so a slip in one module doesn't block demoing the others
- Synthetic data seeding (Day 12) is scheduled deliberately mid-timeline, not last-minute, since a populated dashboard is what makes Modules 2 & 3 demo well

---

## 17. Risk Register & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OCR/ASR accuracy too low on messy real-world screenshots/audio | Medium | High | Curate demo inputs known to work well; show `low_confidence` graceful degradation as a *feature* ("system knows when it's unsure"), not hide it |
| Neo4j operational complexity eats into timeline | Medium | Medium | Use managed Neo4j Aura Free tier to skip self-hosting; fall back to Postgres recursive queries for a reduced 1-hop-only correlation feature if graph setup stalls past Day 6 |
| LLM API costs/rate limits during demo | Low | Medium | Cache/pre-warm demo-path responses before live judging; keep a recorded backup demo video as fallback |
| Scope creep across 3 modules | High | High | Strict adherence to MVP table (Section 6); any new idea during build goes to a "Future Scope" backlog, not the sprint |
| Two-person team illness/unavailability | Low | High | Daily EOD sync + shared documentation of API contracts (Section 9 tables) so either developer can pick up the other's module if needed |
| Synthetic dataset looks fake/unconvincing to judges | Medium | Medium | Base synthetic complaints on real, publicly reported scam patterns (RBI/CERT-In advisory examples) rather than fully fabricated text |
| Graph visualization performance lags with force-directed rendering | Low | Medium | Cap initial graph render to top-N highest-risk clusters with lazy-load expansion, rather than rendering the entire graph at once |

---

## 18. Success Metrics & Judging Alignment

| Judging Criterion (typical hackathon rubric) | How Truvia Scores |
|---|---|
| Technical Depth | 6-agent orchestrated pipeline with explicit contracts, polyglot database architecture (relational + graph + vector), real graph algorithms (not just an LLM wrapper) |
| Innovation | Reframes the entire category from "classification" to "intelligence generation"; the Threat Intelligence Engine is a genuinely novel centerpiece vs. typical scam-checker submissions |
| Real-World Feasibility | Every technology choice justified against production trade-offs; MVP/stretch split shows deliberate, realistic scoping rather than an unfinished feature list |
| Design & UX | Distinct, purpose-built visual language per audience (approachable for citizens, SOC-grade for officers/analysts) |
| Problem-Statement Alignment | Full requirement-mapping table (Section 7) directly ties every official ask to a shipped feature |
| Presentation-Readiness | Structured demo narrative: Citizen reports → Threat scored & explained → Entity extracted → Graph correlates to existing ring → Officer gets ready-made case package — a complete, compelling story arc for a live demo |

---

## 19. Appendix

### A. Glossary
- **Threat Intelligence Score:** 0–100 composite score representing likelihood + severity of fraud
- **Fraud Ring:** A graph-detected cluster of entities (phone numbers, UPI IDs, domains, etc.) that co-occur across multiple complaints, suggesting coordinated fraudulent activity
- **Entity:** Any structured, extractable identifier (phone, UPI ID, email, domain, device ID, IP, impersonated org name)
- **Intelligence Package:** The structured, exportable document combining threat analysis, entities, timeline, and linked complaints for a case or ring
- **Digital Arrest Scam:** A fraud pattern in which scammers impersonate law enforcement/government officials and falsely claim the victim is under investigation or "digital arrest," coercing payment or information

### B. Sample Demo Narrative (for hackathon presentation)
1. A citizen pastes a suspicious "Digital Arrest" call transcript into the Citizen Fraud Shield.
2. Truvia returns a Critical threat score in seconds, with reasoning citing specific red-flag phrases and an explicit note: "Real law enforcement never demands payment via UPI to avoid arrest — RBI/MHA guidance."
3. Behind the scenes, the phone number and UPI ID from the transcript are extracted and checked against the graph — they match a cluster of 14 other complaints filed in the last 9 days.
4. The officer dashboard shows this as an Emerging Scam Trend with a spiking KPI.
5. The officer opens the Threat Intelligence Engine, sees the full fraud ring visually, and generates a ring-level Intelligence Package in one click — a complete, structured case file that would have taken hours to assemble manually.

### C. Open Questions for Engineering Kickoff
- Final choice of managed OCR/ASR vendor pending cost/rate-limit testing on Day 1–2
- Exact community-detection algorithm parameters (resolution threshold for Louvain clustering) to be tuned once synthetic dataset is seeded
- Confirm PDF rendering library choice compatible with chosen deployment host
