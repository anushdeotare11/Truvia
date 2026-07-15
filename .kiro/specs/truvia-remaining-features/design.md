# Design Document: Truvia Remaining Features

## Overview

This design covers 10 requirements spanning database schema changes, a seed data script, report-scoped chat, expanded entity extraction, alert automation, new dashboard/graph API endpoints, frontend updates, court-ready PDF enhancement, and pipeline stage tracking. The implementation language is Python (FastAPI backend) and TypeScript (Next.js frontend).

## Architecture

The existing architecture is preserved:
- **Backend**: FastAPI with async SQLAlchemy (PostgreSQL/SQLite), Neo4j graph DB (with SQL fallback), Redis
- **Frontend**: Next.js with TypeScript, Recharts for charts, react-force-graph for graph visualization
- **Agents**: Modular async agent classes (InputProcessor, ThreatEvaluator, EntityExtractor, ThreatIntel, Investigation, Knowledge)
- **Pipeline**: Orchestration layer calling agents sequentially

---

## Phase 1: Database Schema Updates

### Files Modified
- `app/models/report.py` — Add `city` and `pipeline_stage` columns
- `app/schemas/report.py` — Add optional fields to `ReportOut`
- `alembic/versions/0002_add_city_pipeline_stage.py` — New migration

### Implementation

```python
# In app/models/report.py - Add to Report class:
city = Column(String(100), nullable=True)
pipeline_stage = Column(String(50), nullable=True)  # ingesting, extracting_text, evaluating_threat, extracting_entities, indexing_graph, completed
```

```python
# In app/schemas/report.py - Add to ReportOut:
city: Optional[str] = None
pipeline_stage: Optional[str] = None
```

### Migration

```python
# alembic/versions/0002_add_city_pipeline_stage.py
def upgrade():
    op.add_column('reports', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('reports', sa.Column('pipeline_stage', sa.String(50), nullable=True))

def downgrade():
    op.drop_column('reports', 'pipeline_stage')
    op.drop_column('reports', 'city')
```

---

## Phase 2: Seed Data Script

### Files Created
- `scripts/seed_data.py` — Main seed script

### Approach

The script will:
1. Create demo users (admin, officer, citizen) via SQLAlchemy
2. Define 8 scam category templates with realistic Indian-context text
3. Generate 180 reports distributed across categories and 12 cities
4. Run `run_pipeline()` (or `run_pipeline_continuation()`) on each report to produce real threat scores, entities, and graph relationships
5. Group related reports (shared entities/categories) into 15+ Cases
6. Insert 20+ knowledge_base documents with chunked advisory content

### Data Distribution

```python
CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
          "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Chandigarh", "Kochi"]

CATEGORIES = ["Digital Arrest", "UPI Fraud", "KYC Scam", "Job Scam",
              "Sextortion", "Loan Scam", "Electricity Scam", "Investment Fraud"]

# ~22-23 reports per category, 15 reports per city
```

### Pipeline Execution

Each report is created with `cleaned_text` pre-populated (simulating Agent 1 output), then `run_pipeline_continuation(report_id)` is called which executes Agent 2 (threat scoring), Agent 4 (entity extraction), and Agent 5 (graph indexing). This uses local rule-engine fallbacks when no LLM API key is configured.

---

## Phase 3: Report-Scoped Chat

### Files Modified
- `app/api/v1/chat.py` — Add optional `report_id` to `ChatQuery`
- `app/agents/knowledge_agent.py` — Accept report context in `answer_query()`

### Interface Changes

```python
# chat.py - Updated schema
class ChatQuery(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    report_id: Optional[UUID] = None
```

### Knowledge Agent Changes

When `report_id` is provided:
1. Fetch the report from DB
2. Fetch latest ThreatScore for the report (scam_category, severity_band)
3. Fetch linked entities via ReportEntity join
4. Prepend a context block to the RAG prompt:
   ```
   [Report Context]
   Scam Category: {scam_category}
   Severity: {severity_band}
   Extracted Entities: {entity_list}
   ```
5. Proceed with normal RAG retrieval and answer generation

---

## Phase 4: Complete Entity Extraction

### Files Modified
- `app/agents/entity_extractor.py` — Add new regex patterns and extraction logic

### New Patterns

```python
IFSC_REGEX = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b')
IP_REGEX = re.compile(r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b')
BANK_ACCOUNT_REGEX = re.compile(r'\b\d{9,18}\b')

ORG_KEYWORDS = ["cbi", "rbi", "police", "trai", "customs", "income tax", "npci",
                "sbi", "hdfc", "icici", "reserve bank", "enforcement directorate"]
```

### Normalization Rules
- **IFSC**: Store uppercase as-is (already uppercase from regex)
- **IP**: Store as dotted-quad string
- **Bank Account**: Store digits only
- **Org**: Store lowercase, trimmed

### Integration

Add extraction loops after existing UPI/Phone/Email/URL extraction in `extract_entities()`. De-duplication via the existing `seen` set with `(type, normalized_value)` keys.

---

## Phase 5: Alert and Investigation Agent

### Files Modified
- `app/orchestration/pipeline.py` — Add alert generation step
- `app/agents/investigation.py` — Add `generate_ring_summary()` method
- `app/models/alert.py` — Verify Alert model supports required fields

### Alert Auto-Generation

After entity extraction in the pipeline, check the report's latest threat score:
```python
async def _maybe_generate_alert(report_id: str):
    # Fetch latest ThreatScore for report
    # If threat_score >= 75, create Alert record
    alert = Alert(
        report_id=report_id,
        severity=severity_band,
        title=f"High-Severity {scam_category} Report Detected",
        description=f"Report scored {threat_score}/100 in {scam_category} category",
        ...
    )
```

### Ring Intelligence

Add method to InvestigationAgent:
```python
async def generate_ring_summary(self, ring_entity_ids: List[str]) -> dict:
    # Fetch all reports linked to these entities
    # Compile summary using LLM or local fallback
    # Return structured intelligence package data
```

---

## Phase 6: Dashboard Endpoints

### Files Created
- `app/api/v1/dashboard.py` — New router with 3 endpoints

### Endpoint Designs

**GET /dashboard/geo-breakdown**
```python
# Query: SELECT city, COUNT(*) FROM reports WHERE city IS NOT NULL GROUP BY city
# Returns: [{"city": "Mumbai", "count": 25}, ...]
```

**GET /dashboard/timeline**
```python
# Query: SELECT id, source_type, created_at, severity_band FROM reports
#         JOIN threat_scores ... ORDER BY created_at DESC LIMIT 50
# Returns: [{"id": "...", "source_type": "text", "created_at": "...", "severity": "high"}, ...]
```

**GET /dashboard/score-distribution**
```python
# Bucket threat scores into ranges using CASE WHEN
# Returns: [{"range": "0-19", "count": 12}, {"range": "20-39", "count": 28}, ...]
```

### Evidence Timeline (Cases Router Addition)

**GET /cases/{id}/evidence-timeline**
```python
# Combine: report.created_at, entity extraction timestamps, case.created_at,
#          officer assignment dates, package generation dates
# Sort chronologically and return as timeline events
```

---

## Phase 7: Graph Endpoints

### Files Modified
- `app/api/v1/graph.py` — Add 5 new endpoint methods

### Endpoint Designs

**GET /graph/rings**
- Run `calculate_local_communities()` on all entities/relationships
- Group by community ID
- Filter communities with 3+ members
- Return: `[{"ring_id": 0, "member_count": 5, "aggregate_risk": 72.5, "entities": [...]}]`

**GET /graph/entity/{id}/subgraph?depth=N**
- BFS traversal from entity_id up to N hops (max 3)
- SQL: iterative joins on Relationship table
- Neo4j: `MATCH path = (e:Entity {uid: $uid})-[*1..N]-(connected) RETURN path`
- Return: `{"nodes": [...], "edges": [...]}`

**GET /graph/correlate?report_id=X**
- Find all entities linked to the given report
- Find all other reports linked to those entities
- Return with shared_entity_count

**POST /graph/intelligence-package**
- Accept `ring_id` in body
- Gather all entities in that community
- Gather all linked reports
- Generate ring-level PDF using extended `generate_report_pdf()`
- Return StreamingResponse with PDF

**GET /graph/export?entity_id=X**
- Fetch entity's subgraph (depth=2)
- Fetch all linked report IDs
- Return JSON: `{"entity": {...}, "subgraph": {"nodes": [...], "edges": [...]}, "linked_reports": [...]}`

---

## Phase 8: Frontend Updates

### Files Modified
- `truvia-frontend/src/app/(app)/fraud-shield/` — Processing stepper component
- `truvia-frontend/src/app/(app)/dashboard/` — Geo chart, histogram, timeline
- `truvia-frontend/src/app/(app)/threat-intel/` — Ring listing panel
- `truvia-frontend/src/lib/types.ts` — New TypeScript interfaces

### Processing Stepper

Poll `GET /api/v1/reports/{id}/status` every 2 seconds. Map `pipeline_stage` to stepper steps:
```typescript
const STAGES = [
  { key: "ingesting", label: "Submitting" },
  { key: "extracting_text", label: "Extracting Text" },
  { key: "evaluating_threat", label: "Evaluating Threats" },
  { key: "extracting_entities", label: "Extracting Entities" },
  { key: "indexing_graph", label: "Indexing Graph" },
  { key: "completed", label: "Complete" },
];
```

### Dashboard Components
- **Geo Bar Chart**: Recharts `BarChart` with city on X-axis, count on Y-axis
- **Score Histogram**: Recharts `BarChart` with score ranges on X-axis
- **Threat Timeline**: Vertical timeline component with severity-colored badges

### Ring Listing Panel
- Fetch from `GET /api/v1/graph/rings`
- Display card list with ring ID, member count, risk score, expandable entity list

---

## Phase 9: Court-Ready Package Enhancement

### Files Modified
- `app/core/pdf.py` — Extend `generate_report_pdf()` or create `generate_case_pdf()`
- `app/api/v1/cases.py` — Update `compile_intelligence_package()` to use enhanced PDF

### PDF Sections (in order)

1. **Case Header**: case_number, priority, type, creation_date, status
2. **Timeline**: Chronological events from report submission through investigation
3. **Evidence**: All report transcripts with source_type and submission dates
4. **Extracted Entities**: Table of all entities with type, value, risk_score, risk_tier
5. **Threat Analysis**: Per-report threat_score and severity_band
6. **AI Explanation**: reasoning_json key_indicators, risk_explanation, victim_instructions
7. **Confidence Score**: confidence_score value and degraded_mode flag per score
8. **Linked Complaints**: List of all report IDs with brief metadata
9. **Related Fraud Ring**: Entities in the same community cluster (via calculate_local_communities)
10. **Officer Notes**: Empty section with placeholder text for handwritten/typed notes

---

## Phase 10: Pipeline Stage Integration

### Files Modified
- `app/orchestration/pipeline.py` — Add stage update calls
- `app/api/v1/reports.py` — Add `/reports/{id}/status` endpoint
- `app/main.py` — Wire dashboard router

### Pipeline Stage Updates

```python
async def _update_pipeline_stage(report_id: str, stage: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if report:
            report.pipeline_stage = stage
            await session.commit()
```

Insert calls at each step in `run_pipeline()` and `run_pipeline_continuation()`.

### Status Endpoint

```python
@router.get("/{report_id}/status")
async def get_report_status(report_id: str, db: AsyncSession = Depends(get_db)):
    report = await db.get(Report, uuid.UUID(report_id))
    if not report:
        raise HTTPException(status_code=404)
    return {"id": str(report.id), "status": report.status, "pipeline_stage": report.pipeline_stage}
```

### Router Wiring

```python
# In app/main.py
from app.api.v1 import dashboard
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Analytics Dashboard"])
```

---

## Error Handling

- All new endpoints follow existing pattern: try/except with logging and appropriate HTTP status codes
- Seed script uses transaction rollback on failure
- Pipeline stage updates use separate sessions to avoid interfering with agent transactions
- Frontend polling uses exponential backoff if status endpoint fails

## Data Models

### New TypeScript Interfaces

```typescript
interface GeoBreakdown {
  city: string;
  count: number;
}

interface TimelineEvent {
  id: string;
  source_type: string;
  created_at: string;
  severity: string;
  event_type: string;
}

interface ScoreDistribution {
  range: string;
  count: number;
}

interface FraudRing {
  ring_id: number;
  member_count: number;
  aggregate_risk: number;
  entities: { id: string; type: string; value: string; risk_score: number }[];
}

interface PipelineStatus {
  id: string;
  status: string;
  pipeline_stage: string | null;
}
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Entity Extraction Completeness

*For any* report text containing one or more IFSC codes, IP addresses, bank account numbers, or organization references, the entity extractor SHALL extract all matching patterns and store them with the correct entity type.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 2: Entity Normalization Invariant

*For any* extracted entity, the stored normalized_value SHALL conform to its type's normalization rule: IFSC values are uppercase alphanumeric, IP values are dotted-quad format, bank_account values contain only digits, and org values are lowercase.

**Validates: Requirements 4.5**

### Property 3: Alert Generation Threshold

*For any* report that completes pipeline processing with a threat_score of 75 or above, an Alert record SHALL exist in the database linked to that report with non-null severity, scam_category, and title fields.

**Validates: Requirements 5.1, 5.2**

### Property 4: Geo-Breakdown Partition Invariant

*For any* set of reports in the database with non-null city values, the geo-breakdown endpoint SHALL return city groups whose counts sum to the total number of reports with non-null city.

**Validates: Requirements 6.1**

### Property 5: Timeline Chronological Ordering

*For any* response from the dashboard timeline endpoint, the returned events SHALL be ordered by timestamp in descending order (newest first).

**Validates: Requirements 6.2**

### Property 6: Score Distribution Partition

*For any* set of scored reports, the score-distribution endpoint SHALL return exactly 5 buckets whose counts sum to the total number of current threat scores, and each score SHALL fall into exactly one bucket.

**Validates: Requirements 6.3**

### Property 7: Subgraph Depth Bound

*For any* entity and depth parameter N (1-3), all nodes returned by the subgraph endpoint SHALL be reachable from the source entity within N relationship hops.

**Validates: Requirements 7.2**

### Property 8: Correlation Shared Entity Invariant

*For any* report returned by the correlate endpoint, that report SHALL share at least one entity with the source report.

**Validates: Requirements 7.3**

### Property 9: Pipeline Stage Progression

*For any* report that completes full pipeline processing, the pipeline_stage SHALL have been set to each of the 6 defined stages in order (ingesting → extracting_text → evaluating_threat → extracting_entities → indexing_graph → completed) and the final value SHALL be "completed".

**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6**

### Property 10: Report-Scoped Chat Context Inclusion

*For any* valid report_id provided to the chat endpoint, the RAG prompt context SHALL include the report's scam category and at least one extracted entity value (when entities exist for that report).

**Validates: Requirements 3.2, 3.3**

### Property 11: Court-Ready PDF Section Completeness

*For any* case with linked reports, entities, and threat scores, the generated PDF SHALL contain all 10 required sections: Case Header, Timeline, Evidence, Extracted Entities, Threat Analysis, AI Explanation, Confidence Score, Linked Complaints, Related Fraud Ring, and Officer Notes.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10**
