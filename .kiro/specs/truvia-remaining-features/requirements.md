# Requirements Document

## Introduction

This document specifies the remaining features for the Truvia Digital Public Safety Platform required for a complete MVP demo. The scope covers database schema additions, a comprehensive seed data script, report-scoped chat, expanded entity extraction, alert/investigation automation, new dashboard and graph API endpoints, frontend UI additions, and a court-ready PDF package enhancement.

## Glossary

- **Pipeline**: The sequential processing workflow that analyzes a scam report through multiple agent stages (input processing, threat evaluation, entity extraction, graph indexing)
- **Report**: A citizen-submitted scam complaint (text, screenshot, or audio) stored in the `reports` table
- **Entity**: An identifiable artifact extracted from a report (phone number, UPI ID, email, domain, IFSC code, IP address, bank account, organization name)
- **Case**: A grouped investigation linking multiple related reports under one officer assignment
- **Fraud Ring**: A cluster of interconnected entities detected via community detection (Louvain or BFS connected components)
- **Intelligence Package**: A court-ready PDF document compiling case or ring-level evidence
- **Pipeline Stage**: A granular tracking field representing which agent step a report is currently in (ingesting, extracting_text, evaluating_threat, extracting_entities, indexing_graph, completed)
- **Knowledge Base**: A collection of official regulatory documents (RBI, CERT-In, MHA advisories) used for RAG-grounded chat responses
- **Seed Script**: A Python script that programmatically generates synthetic demo data and runs the full pipeline on each generated report

## Requirements

### Requirement 1: Database Schema Updates

**User Story:** As a developer, I want the reports table to include `city` and `pipeline_stage` columns, so that geo-analysis and granular progress tracking are supported.

#### Acceptance Criteria

1. WHEN an Alembic migration is executed, THE Database SHALL add a `city` column of type String(100), nullable, to the `reports` table
2. WHEN an Alembic migration is executed, THE Database SHALL add a `pipeline_stage` column of type String(50), nullable, to the `reports` table
3. THE Report SQLAlchemy model SHALL include both `city` and `pipeline_stage` column definitions matching the migration
4. THE ReportOut Pydantic schema SHALL expose `city` and `pipeline_stage` as optional string fields

### Requirement 2: Seed Data Script

**User Story:** As a demo presenter, I want the database pre-populated with realistic synthetic data, so that dashboards, graphs, and AI features demonstrate meaningful output during demonstrations.

#### Acceptance Criteria

1. WHEN the seed script executes, THE Seed Script SHALL create 3 demo users: one admin, one officer, and one citizen
2. WHEN the seed script executes, THE Seed Script SHALL generate 180 synthetic scam reports distributed across 8 scam categories (Digital Arrest, UPI Fraud, KYC Scam, Job Scam, Sextortion, Loan Scam, Electricity Scam, Investment Fraud)
3. WHEN the seed script executes, THE Seed Script SHALL distribute reports across 12 Indian cities using the new `city` column
4. WHEN the seed script executes, THE Seed Script SHALL run the full analysis pipeline on each report, producing threat scores, extracted entities, and graph relationships
5. WHEN the seed script executes, THE Seed Script SHALL create 15 or more Cases linking related reports that share entities or scam categories
6. WHEN the seed script executes, THE Seed Script SHALL insert 20 or more knowledge_base documents containing advisory content from RBI, CERT-In, MHA, and NPCI sources
7. IF the LLM API key is unavailable during seeding, THEN THE Seed Script SHALL use local rule-engine fallbacks for threat evaluation and entity extraction without errors

### Requirement 3: Report-Scoped Chat

**User Story:** As a citizen, I want to ask follow-up questions about my specific scam report, so that I receive contextual guidance relevant to my situation.

#### Acceptance Criteria

1. WHEN a POST /api/v1/chat request includes an optional `report_id` field, THE Chat Endpoint SHALL accept the field without breaking existing non-scoped chat behavior
2. WHEN `report_id` is provided and valid, THE Knowledge Agent SHALL include the report's scam category and extracted entity values as additional context in the RAG prompt
3. WHEN `report_id` is provided and valid, THE Chat Endpoint SHALL return answers contextualized to the specific report's threat category and entities
4. IF `report_id` is provided but does not correspond to an existing report, THEN THE Chat Endpoint SHALL return a 404 error with a descriptive message

### Requirement 4: Complete Entity Extraction

**User Story:** As an investigator, I want the system to extract IFSC codes, IP addresses, bank account numbers, and impersonated organization names from reports, so that the threat entity ledger is comprehensive.

#### Acceptance Criteria

1. WHEN a report's cleaned_text contains an IFSC code pattern (4 uppercase letters followed by 0 followed by 6 alphanumeric characters), THE Entity Extractor SHALL extract and store it as an entity of type "ifsc"
2. WHEN a report's cleaned_text contains an IPv4 address pattern, THE Entity Extractor SHALL extract and store it as an entity of type "ip"
3. WHEN a report's cleaned_text contains a bank account number pattern (9-18 consecutive digits), THE Entity Extractor SHALL extract and store it as an entity of type "bank_account"
4. WHEN a report's cleaned_text contains references to government or organizational impersonation names (CBI, RBI, Police, TRAI, Customs, Income Tax, NPCI, SBI, HDFC, ICICI), THE Entity Extractor SHALL extract and store them as entities of type "org"
5. THE Entity Extractor SHALL normalize all new entity types before storage (lowercase for org, digits-only for bank_account, uppercase for ifsc, dotted-quad for ip)

### Requirement 5: Complete Alert and Investigation Agent

**User Story:** As an officer, I want the system to auto-generate alerts for high-severity reports and produce ring-level intelligence packages, so that urgent threats are surfaced proactively.

#### Acceptance Criteria

1. WHEN a report receives a threat_score of 75 or above, THE Pipeline SHALL auto-generate an Alert record linked to that report
2. WHEN an alert is generated, THE Alert Record SHALL contain the report_id, severity band, scam category, and a generated title describing the threat
3. WHEN a fraud ring cluster is identified containing 3 or more entities, THE Investigation Agent SHALL be capable of generating a ring-level intelligence summary
4. THE Alert generation step SHALL be wired into the pipeline as a post-scoring stage that runs after entity extraction

### Requirement 6: Dashboard Endpoints

**User Story:** As an officer, I want dashboard API endpoints for geo-breakdown, timeline, and score distribution, so that the frontend can render analytical visualizations.

#### Acceptance Criteria

1. WHEN GET /api/v1/dashboard/geo-breakdown is called, THE Dashboard Router SHALL return reports grouped by city with count per city
2. WHEN GET /api/v1/dashboard/timeline is called, THE Dashboard Router SHALL return a chronological event stream of the last 50 reports with timestamps, source types, and severity bands
3. WHEN GET /api/v1/dashboard/score-distribution is called, THE Dashboard Router SHALL return threat score counts bucketed into 5 ranges (0-19, 20-39, 40-59, 60-79, 80-100)
4. WHEN GET /api/v1/cases/{id}/evidence-timeline is called, THE Cases Router SHALL return a chronological timeline of case events (report submissions, entity extractions, case creation, assignments, package generation)

### Requirement 7: Graph Endpoints

**User Story:** As an officer, I want graph API endpoints for ring detection, multi-hop traversal, correlation, intelligence packages, and export, so that fraud network analysis is accessible from the frontend.

#### Acceptance Criteria

1. WHEN GET /api/v1/graph/rings is called, THE Graph Router SHALL return a list of detected fraud ring clusters including ring ID, member count, aggregate risk score, and member entity summaries
2. WHEN GET /api/v1/graph/entity/{id}/subgraph is called with a depth parameter (1-3), THE Graph Router SHALL return all entities reachable within N hops and their connecting relationships
3. WHEN GET /api/v1/graph/correlate is called with a report_id query parameter, THE Graph Router SHALL return other reports that share entities with the specified report
4. WHEN POST /api/v1/graph/intelligence-package is called with a ring_id, THE Graph Router SHALL generate a ring-level PDF containing all member entities, linked complaints, aggregate timeline, and total victim count
5. WHEN GET /api/v1/graph/export is called with an entity_id query parameter, THE Graph Router SHALL return the entity's subgraph and linked report IDs as a JSON document

### Requirement 8: Frontend Updates

**User Story:** As a user, I want the frontend to display a processing stepper, geo charts, score histograms, threat timelines, and ring listing panels, so that the platform demonstrates intelligence-grade analytics visually.

#### Acceptance Criteria

1. WHEN a report is being processed, THE Fraud Shield Page SHALL display a 6-stage processing stepper (Submitting, Extracting Text, Evaluating Threats, Extracting Entities, Indexing Graph, Complete)
2. WHEN the dashboard loads, THE Dashboard Page SHALL render a geo bar chart showing reports per city
3. WHEN the dashboard loads, THE Dashboard Page SHALL render a score distribution histogram with 5 severity buckets
4. WHEN the dashboard loads, THE Dashboard Page SHALL render a threat timeline showing the last 20 events chronologically
5. WHEN the threat-intel page loads, THE Threat Intel Page SHALL display a ring listing panel showing detected fraud rings with member counts and risk scores

### Requirement 9: Court-Ready Package Enhancement

**User Story:** As an investigator, I want the PDF intelligence package to include all court-required sections, so that generated documents meet evidentiary standards.

#### Acceptance Criteria

1. THE PDF Generator SHALL produce a document containing a Case Header section with case number, priority, type, and creation date
2. THE PDF Generator SHALL include a Timeline section showing chronological events from report submission through investigation
3. THE PDF Generator SHALL include an Evidence section listing all report transcripts with source types and submission dates
4. THE PDF Generator SHALL include an Extracted Entities section tabulating all threat entities with types, values, and risk scores
5. THE PDF Generator SHALL include a Threat Analysis section with per-report threat scores and severity bands
6. THE PDF Generator SHALL include an AI Explanation section with the reasoning_json key indicators and risk explanation from the threat evaluator
7. THE PDF Generator SHALL include a Confidence Score section showing model confidence and degraded-mode status
8. THE PDF Generator SHALL include a Linked Complaints section listing all report IDs associated with the case
9. THE PDF Generator SHALL include a Related Fraud Ring section showing connected entities in the same community cluster
10. THE PDF Generator SHALL include an Officer Notes section (placeholder for free-text input)

### Requirement 10: Pipeline Stage Integration

**User Story:** As a developer, I want the pipeline to set `report.pipeline_stage` at each agent step and expose new routes properly, so that frontend progress tracking and all new endpoints are accessible.

#### Acceptance Criteria

1. WHEN the pipeline begins processing a report, THE Pipeline SHALL set report.pipeline_stage to "ingesting"
2. WHEN Agent 1 (input processor) starts, THE Pipeline SHALL update report.pipeline_stage to "extracting_text"
3. WHEN Agent 2 (threat evaluator) starts, THE Pipeline SHALL update report.pipeline_stage to "evaluating_threat"
4. WHEN Agent 4 (entity extractor) starts, THE Pipeline SHALL update report.pipeline_stage to "extracting_entities"
5. WHEN Agent 5 (graph indexer) starts, THE Pipeline SHALL update report.pipeline_stage to "indexing_graph"
6. WHEN the pipeline completes all stages, THE Pipeline SHALL update report.pipeline_stage to "completed"
7. WHEN GET /api/v1/reports/{id}/status is called, THE Reports Router SHALL return the current pipeline_stage value
8. THE Main Application SHALL wire the new dashboard router into the FastAPI app at prefix /api/v1/dashboard
