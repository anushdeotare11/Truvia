# Implementation Plan: Truvia Remaining Features

## Overview

This plan implements 10 requirements in dependency order: schema changes first, then backend agents/endpoints, then the seed script (which needs all agents working), and finally frontend updates. Each task builds incrementally on the previous.

## Tasks

- [x] 1. Database schema updates and model changes
  - [x] 1.1 Add `city` and `pipeline_stage` columns to the Report SQLAlchemy model
    - Open `app/models/report.py`
    - Add `city = Column(String(100), nullable=True)` after the `status` column
    - Add `pipeline_stage = Column(String(50), nullable=True)` after `city`
    - _Requirements: 1.3_
  - [x] 1.2 Update the ReportOut Pydantic schema
    - Open `app/schemas/report.py`
    - Add `city: Optional[str] = None` and `pipeline_stage: Optional[str] = None` to `ReportOut`
    - _Requirements: 1.4_
  - [x] 1.3 Create Alembic migration for new columns
    - Create `alembic/versions/0002_add_city_pipeline_stage.py`
    - Implement `upgrade()` adding both columns and `downgrade()` dropping them
    - _Requirements: 1.1, 1.2_

- [x] 2. Pipeline stage integration
  - [x] 2.1 Create pipeline stage update helper in `app/orchestration/pipeline.py`
    - Add async function `_update_pipeline_stage(report_id, stage)` that opens a session and sets `report.pipeline_stage`
    - _Requirements: 10.1_
  - [x] 2.2 Wire stage updates into `run_pipeline()` and `run_pipeline_continuation()`
    - Insert `_update_pipeline_stage(report_id, "ingesting")` at the start of `run_pipeline()`
    - Insert `_update_pipeline_stage(report_id, "extracting_text")` before Agent 1
    - Insert `_update_pipeline_stage(report_id, "evaluating_threat")` before Agent 2
    - Insert `_update_pipeline_stage(report_id, "extracting_entities")` before Agent 4
    - Insert `_update_pipeline_stage(report_id, "indexing_graph")` before Agent 5
    - Insert `_update_pipeline_stage(report_id, "completed")` at the end
    - _Requirements: 10.2, 10.3, 10.4, 10.5, 10.6_
  - [x] 2.3 Add GET /reports/{id}/status endpoint
    - Open `app/api/v1/reports.py`
    - Add endpoint returning `{"id", "status", "pipeline_stage"}` for a given report ID
    - _Requirements: 10.7_
  - [ ]* 2.4 Write property test for pipeline stage progression
    - **Property 9: Pipeline Stage Progression**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6**

- [x] 3. Complete entity extraction
  - [x] 3.1 Add new regex patterns to `app/agents/entity_extractor.py`
    - Add `IFSC_REGEX = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b')`
    - Add `IP_REGEX = re.compile(r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b')`
    - Add `BANK_ACCOUNT_REGEX = re.compile(r'\b\d{9,18}\b')`
    - Add `ORG_KEYWORDS` list with CBI, RBI, Police, TRAI, Customs, Income Tax, NPCI, SBI, HDFC, ICICI
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 3.2 Add extraction loops for new entity types in `extract_entities()`
    - After existing URL extraction section, add IFSC extraction loop (type="ifsc", normalized=uppercase)
    - Add IP extraction loop (type="ip", normalized=dotted-quad string)
    - Add bank account extraction loop (type="bank_account", normalized=digits only) with length validation (9-18 digits)
    - Add org keyword scan using case-insensitive search (type="org", normalized=lowercase)
    - All new entities go through existing de-duplication and save logic
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [ ]* 3.3 Write property test for entity extraction completeness
    - **Property 1: Entity Extraction Completeness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
  - [ ]* 3.4 Write property test for entity normalization invariant
    - **Property 2: Entity Normalization Invariant**
    - **Validates: Requirements 4.5**

- [x] 4. Alert auto-generation in pipeline
  - [x] 4.1 Add alert generation helper in `app/orchestration/pipeline.py`
    - Create async function `_maybe_generate_alert(report_id)` that:
      - Fetches the latest ThreatScore for the report
      - If threat_score >= 75, creates an Alert record with report_id, severity_band, scam_category, and descriptive title
    - _Requirements: 5.1, 5.2_
  - [x] 4.2 Wire alert generation into pipeline after entity extraction
    - Call `_maybe_generate_alert(report_id)` in `run_pipeline_continuation()` after Agent 4 (entity extraction)
    - _Requirements: 5.4_
  - [ ]* 4.3 Write property test for alert generation threshold
    - **Property 3: Alert Generation Threshold**
    - **Validates: Requirements 5.1, 5.2**

- [x] 5. Report-scoped chat
  - [x] 5.1 Update ChatQuery schema to accept optional report_id
    - Open `app/api/v1/chat.py`
    - Add `report_id: Optional[UUID] = None` to `ChatQuery` model
    - Pass `report_id` to `knowledge_agent.answer_query()`
    - If `report_id` is provided but report not found, return 404
    - _Requirements: 3.1, 3.4_
  - [x] 5.2 Update KnowledgeAgent to accept report context
    - Open `app/agents/knowledge_agent.py`
    - Modify `answer_query()` signature to accept optional `report_id`
    - When report_id is provided: fetch report, latest ThreatScore, and linked entities
    - Prepend report context block (scam_category, severity, entity list) to the RAG prompt
    - _Requirements: 3.2, 3.3_
  - [ ]* 5.3 Write property test for report-scoped chat context inclusion
    - **Property 10: Report-Scoped Chat Context Inclusion**
    - **Validates: Requirements 3.2, 3.3**

- [x] 6. Checkpoint - Ensure all backend agent changes work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Dashboard endpoints
  - [x] 7.1 Create `app/api/v1/dashboard.py` with geo-breakdown endpoint
    - Create new router file
    - Implement `GET /geo-breakdown` that queries reports grouped by city, returns `[{"city": str, "count": int}]`
    - _Requirements: 6.1_
  - [x] 7.2 Add timeline endpoint to dashboard router
    - Implement `GET /timeline` that fetches last 50 reports with threat score info, ordered by created_at DESC
    - Return `[{"id", "source_type", "created_at", "severity", "event_type"}]`
    - _Requirements: 6.2_
  - [x] 7.3 Add score-distribution endpoint to dashboard router
    - Implement `GET /score-distribution` that buckets current threat scores into 5 ranges (0-19, 20-39, 40-59, 60-79, 80-100)
    - Return `[{"range": str, "count": int}]`
    - _Requirements: 6.3_
  - [x] 7.4 Add evidence-timeline endpoint to cases router
    - Open `app/api/v1/cases.py`
    - Add `GET /{case_id}/evidence-timeline` that compiles chronological events (report submissions, case creation, assignments, package generation) from audit_logs and related timestamps
    - _Requirements: 6.4_
  - [x] 7.5 Wire dashboard router into main.py
    - Open `app/main.py`
    - Import and include dashboard router at prefix `/api/v1/dashboard`
    - _Requirements: 10.8_
  - [ ]* 7.6 Write property tests for dashboard endpoints
    - **Property 4: Geo-Breakdown Partition Invariant**
    - **Property 5: Timeline Chronological Ordering**
    - **Property 6: Score Distribution Partition**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 8. Graph endpoints
  - [x] 8.1 Add GET /graph/rings endpoint
    - Open `app/api/v1/graph.py`
    - Implement endpoint that runs `calculate_local_communities()`, groups entities by community, filters communities with 3+ members
    - Return `[{"ring_id", "member_count", "aggregate_risk", "entities": [...]}]`
    - Use Neo4j GDS Louvain when available, BFS connected components for SQL fallback
    - _Requirements: 7.1_
  - [x] 8.2 Add GET /graph/entity/{id}/subgraph endpoint
    - Implement BFS traversal from entity_id up to depth N (query param, max 3)
    - SQL: iterative relationship joins; Neo4j: variable-length path query
    - Return `{"nodes": [...], "edges": [...]}`
    - _Requirements: 7.2_
  - [x] 8.3 Add GET /graph/correlate endpoint
    - Accept `report_id` query param
    - Find entities linked to report, then find other reports sharing those entities
    - Return `[{"id", "source_type", "status", "shared_entities", "created_at"}]`
    - _Requirements: 7.3_
  - [x] 8.4 Add POST /graph/intelligence-package endpoint
    - Accept `ring_id` in request body
    - Gather all entities in that community and their linked reports
    - Generate ring-level PDF using extended PDF generation logic
    - Return StreamingResponse with PDF
    - _Requirements: 7.4_
  - [x] 8.5 Add GET /graph/export endpoint
    - Accept `entity_id` query param
    - Fetch entity's subgraph (depth=2) and all linked report IDs
    - Return JSON document
    - _Requirements: 7.5_
  - [ ]* 8.6 Write property tests for graph endpoints
    - **Property 7: Subgraph Depth Bound**
    - **Property 8: Correlation Shared Entity Invariant**
    - **Validates: Requirements 7.2, 7.3**

- [x] 9. Ring-level investigation agent
  - [x] 9.1 Add `generate_ring_summary()` method to InvestigationAgent
    - Open `app/agents/investigation.py`
    - Add method that accepts a list of entity IDs, fetches all linked reports, compiles ring-level intelligence summary using LLM or local fallback
    - Return structured data with summary, patterns, total_victims, estimated_losses
    - _Requirements: 5.3_

- [x] 10. Court-ready PDF enhancement
  - [x] 10.1 Extend PDF generation for complete court-ready package
    - Open `app/core/pdf.py`
    - Create `generate_case_pdf(case_data: dict) -> io.BytesIO` function
    - Implement all 10 sections: Case Header, Timeline, Evidence, Extracted Entities, Threat Analysis, AI Explanation, Confidence Score, Linked Complaints, Related Fraud Ring, Officer Notes
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10_
  - [x] 10.2 Update `compile_intelligence_package()` in cases.py to use new PDF function
    - Replace inline PDF generation with call to `generate_case_pdf()`
    - Pass complete case data including ring community info
    - _Requirements: 9.9_
  - [ ]* 10.3 Write property test for PDF section completeness
    - **Property 11: Court-Ready PDF Section Completeness**
    - **Validates: Requirements 9.1-9.10**

- [x] 11. Checkpoint - Ensure all backend endpoints work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Seed data script
  - [x] 12.1 Create `scripts/seed_data.py` with user and report generation
    - Create the script file with async main function
    - Define CITIES list (12 Indian cities) and CATEGORIES list (8 scam categories)
    - Define scam text templates for each category with realistic Indian-context content including phone numbers, UPI IDs, IFSC codes, org names
    - Create 3 demo users (admin, officer, citizen) with proper roles and hashed passwords
    - Generate 180 reports distributed across categories (~22 each) and cities (~15 each)
    - Set `city` field on each report, set `cleaned_text` with template text
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 12.2 Add pipeline execution and case creation to seed script
    - Call `run_pipeline_continuation(report_id)` on each generated report
    - After all reports processed, group related reports by shared entities/categories
    - Create 15+ Case records linking related reports via CaseReport
    - Run `investigation_agent.summarize_case()` on each case for AI summaries
    - _Requirements: 2.4, 2.5_
  - [x] 12.3 Add knowledge base seeding to script
    - Insert 20+ knowledge_base documents with advisory content (RBI fraud warnings, CERT-In alerts, MHA digital arrest guidance, NPCI UPI safety)
    - Chunk documents into ~500-token pieces and store in knowledge_base_chunks
    - Use dummy embedder for vector storage (compatible with SQLite mode)
    - _Requirements: 2.6, 2.7_

- [x] 13. Frontend updates - Processing stepper
  - [x] 13.1 Create ProcessingStepper component
    - Create component in `truvia-frontend/src/components/` that accepts a `pipeline_stage` prop
    - Render 6 stages with active/completed/pending states: Submitting → Extracting Text → Evaluating Threats → Extracting Entities → Indexing Graph → Complete
    - Style with existing Tailwind classes matching the app's design system
    - _Requirements: 8.1_
  - [x] 13.2 Integrate stepper into fraud-shield processing page
    - Open the fraud-shield result/processing page
    - Add polling of `GET /api/v1/reports/{id}/status` every 2 seconds
    - Replace existing spinner with ProcessingStepper component
    - Stop polling when pipeline_stage is "completed"
    - _Requirements: 8.1_

- [x] 14. Frontend updates - Dashboard charts
  - [x] 14.1 Add TypeScript interfaces for new dashboard data
    - Open `truvia-frontend/src/lib/types.ts`
    - Add `GeoBreakdown`, `TimelineEvent`, `ScoreDistribution`, `FraudRing`, `PipelineStatus` interfaces
    - _Requirements: 8.2, 8.3, 8.4_
  - [x] 14.2 Create geo bar chart component on dashboard
    - Fetch data from `GET /api/v1/dashboard/geo-breakdown`
    - Render Recharts BarChart with city on X-axis, count on Y-axis
    - _Requirements: 8.2_
  - [x] 14.3 Create score distribution histogram on dashboard
    - Fetch data from `GET /api/v1/dashboard/score-distribution`
    - Render Recharts BarChart with 5 score range buckets, color-coded by severity
    - _Requirements: 8.3_
  - [x] 14.4 Create threat timeline component on dashboard
    - Fetch data from `GET /api/v1/dashboard/timeline`
    - Render vertical timeline with severity-colored badges and timestamps
    - _Requirements: 8.4_

- [x] 15. Frontend updates - Threat intel ring listing
  - [x] 15.1 Create ring listing panel on threat-intel page
    - Fetch data from `GET /api/v1/graph/rings`
    - Render card list showing ring ID, member count, aggregate risk score
    - Add expandable section showing member entities
    - _Requirements: 8.5_

- [x] 16. Final checkpoint - Verify full integration
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Backend tasks (1-12) should be completed before frontend tasks (13-15)
- The seed script (task 12) depends on all agent/pipeline changes being complete
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- The detected programming language is Python (backend) and TypeScript (frontend)
