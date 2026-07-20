# Neon PostgreSQL Schema Report for Truvia

This report details the schema configuration, table definitions, indexes, foreign keys, and row counts of the Truvia database, hosted on a **Neon serverless PostgreSQL** cluster.

## Database Overview

| Section | Table Name | Row Count | Primary Key | Foreign Keys | Indexes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| User Management & Authentication | `users` | 8 | id | invited_by->users | users_email_key |
| User Management & Authentication | `sessions` | 47 | id | user_id->users | sessions_refresh_token_hash_key |
| User Management & Authentication | `password_reset_tokens` | 2 | id | issued_by->users, user_id->users | idx_password_reset_tokens_user, uq_password_reset_tokens_token_hash |
| Reports & Incident Capture | `reports` | 202 | id | user_id->users | None |
| Reports & Incident Capture | `evidence` | 12 | id | report_id->reports | None |
| Reports & Incident Capture | `threat_scores` | 196 | id | report_id->reports | None |
| Case Management & Investigations Workspace | `cases` | 23 | id | assigned_officer_id->users | cases_case_number_key |
| Case Management & Investigations Workspace | `case_reports` | 62 | case_id, report_id | case_id->cases, report_id->reports | None |
| Case Management & Investigations Workspace | `officer_assignments` | 1 | id | assigned_by->users, case_id->cases, officer_id->users | None |
| Case Management & Investigations Workspace | `intelligence_packages` | 6 | id | case_id->cases, generated_by->users | intelligence_packages_case_id_version_key |
| Scam Graph & Network Intelligence | `entities` | 62 | id | None | entities_type_normalized_value_key |
| Scam Graph & Network Intelligence | `report_entities` | 62 | id | entity_id->entities, report_id->reports | report_entities_report_id_entity_id_raw_span_key |
| Scam Graph & Network Intelligence | `relationships` | 63 | id | entity_id_a->entities, entity_id_b->entities, evidence_report_id->reports | relationships_entity_id_a_entity_id_b_relationship_type_key |
| Scam Graph & Network Intelligence | `fraud_rings` | 9 | id | None | idx_fraud_rings_risk_tier, uq_fraud_rings_neo4j_ring_id |
| Scam Graph & Network Intelligence | `fraud_ring_members` | 34 | ring_id, entity_id | entity_id->entities, ring_id->fraud_rings | idx_fraud_ring_members_entity |
| Real-time Call/Live Session Auditing | `live_sessions` | 7 | id | linked_case_id->cases, user_id->users | idx_live_sessions_status, idx_live_sessions_user_id |
| Real-time Call/Live Session Auditing | `live_session_turns` | 22 | id | session_id->live_sessions | idx_live_session_turns_session_id, uq_live_session_turns_session_turn |
| Knowledge Base & LLM Context | `knowledge_base` | 21 | id | added_by->users | None |
| Knowledge Base & LLM Context | `knowledge_base_chunks` | 42 | id | knowledge_base_id->knowledge_base | knowledge_base_chunks_knowledge_base_id_chunk_index_embeddi_key |
| Alerts & System Infrastructure | `alerts` | 11 | id | related_case_id->cases, related_report_id->reports | None |
| Alerts & System Infrastructure | `notifications` | 0 | id | user_id->users | None |
| Alerts & System Infrastructure | `audit_logs` | 1 | id | actor_id->users | None |
| Alerts & System Infrastructure | `settings` | 0 | key | updated_by->users | None |
| Alerts & System Infrastructure | `alembic_version` | 1 | version_num | None | None |

## User Management & Authentication

### Table: `users`
- **Current Row Count:** 8

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **role** | `VARCHAR(50)` | NOT NULL | *None* |
| **email** | `VARCHAR(255)` | NOT NULL | *None* |
| **password_hash** | `TEXT` | NOT NULL | *None* |
| **name** | `VARCHAR(255)` | NOT NULL | *None* |
| **phone** | `VARCHAR(50)` | Nullable | *None* |
| **officer_badge_id** | `VARCHAR(100)` | Nullable | *None* |
| **status** | `VARCHAR(50)` | NOT NULL | 'active'::character varying |
| **invited_by** | `UUID` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |
| **updated_at** | `TIMESTAMP` | NOT NULL | now() |
| **deleted_at** | `TIMESTAMP` | Nullable | *None* |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `users_pkey`)
- **Foreign Keys:**
  - `invited_by` references `users`(`id`) `ON DELETE SET NULL` (Constraint Name: `users_invited_by_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `users_email_key` | `email` | Yes | *None* |

---

### Table: `sessions`
- **Current Row Count:** 47

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **user_id** | `UUID` | NOT NULL | *None* |
| **refresh_token_hash** | `TEXT` | NOT NULL | *None* |
| **device_label** | `VARCHAR(255)` | Nullable | *None* |
| **ip_address** | `INET` | Nullable | *None* |
| **issued_at** | `TIMESTAMP` | NOT NULL | now() |
| **expires_at** | `TIMESTAMP` | NOT NULL | *None* |
| **revoked_at** | `TIMESTAMP` | Nullable | *None* |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `sessions_pkey`)
- **Foreign Keys:**
  - `user_id` references `users`(`id`) `ON DELETE CASCADE` (Constraint Name: `sessions_user_id_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `sessions_refresh_token_hash_key` | `refresh_token_hash` | Yes | *None* |

---

### Table: `password_reset_tokens`
- **Current Row Count:** 2

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **user_id** | `UUID` | NOT NULL | *None* |
| **token_hash** | `TEXT` | NOT NULL | *None* |
| **issued_by** | `UUID` | Nullable | *None* |
| **expires_at** | `TIMESTAMP` | NOT NULL | *None* |
| **used_at** | `TIMESTAMP` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `password_reset_tokens_pkey`)
- **Foreign Keys:**
  - `issued_by` references `users`(`id`) `ON DELETE SET NULL` (Constraint Name: `password_reset_tokens_issued_by_fkey`)
  - `user_id` references `users`(`id`) `ON DELETE CASCADE` (Constraint Name: `password_reset_tokens_user_id_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `idx_password_reset_tokens_user` | `user_id` | No | *None* |
| `uq_password_reset_tokens_token_hash` | `token_hash` | Yes | *None* |

---

## Reports & Incident Capture

### Table: `reports`
- **Current Row Count:** 202

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **user_id** | `UUID` | NOT NULL | *None* |
| **source_type** | `VARCHAR(50)` | NOT NULL | *None* |
| **raw_input_ref** | `TEXT` | NOT NULL | *None* |
| **cleaned_text** | `TEXT` | Nullable | *None* |
| **detected_language** | `VARCHAR(10)` | Nullable | *None* |
| **input_confidence** | `NUMERIC(4, 3)` | Nullable | *None* |
| **low_confidence_flag** | `BOOLEAN` | NOT NULL | false |
| **status** | `VARCHAR(50)` | NOT NULL | 'submitted'::character varying |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |
| **updated_at** | `TIMESTAMP` | NOT NULL | now() |
| **deleted_at** | `TIMESTAMP` | Nullable | *None* |
| **city** | `VARCHAR(100)` | Nullable | *None* |
| **pipeline_stage** | `VARCHAR(50)` | Nullable | *None* |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `reports_pkey`)
- **Foreign Keys:**
  - `user_id` references `users`(`id`) `ON DELETE RESTRICT` (Constraint Name: `reports_user_id_fkey`)

---

### Table: `evidence`
- **Current Row Count:** 12

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **report_id** | `UUID` | NOT NULL | *None* |
| **evidence_type** | `VARCHAR(50)` | NOT NULL | *None* |
| **file_ref** | `TEXT` | Nullable | *None* |
| **file_hash** | `VARCHAR(64)` | Nullable | *None* |
| **extraction_metadata_json** | `JSONB` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |
| **deleted_at** | `TIMESTAMP` | Nullable | *None* |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `evidence_pkey`)
- **Foreign Keys:**
  - `report_id` references `reports`(`id`) `ON DELETE RESTRICT` (Constraint Name: `evidence_report_id_fkey`)

---

### Table: `threat_scores`
- **Current Row Count:** 196

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **report_id** | `UUID` | NOT NULL | *None* |
| **threat_score** | `SMALLINT` | NOT NULL | *None* |
| **severity_band** | `VARCHAR(50)` | NOT NULL | *None* |
| **scam_category** | `VARCHAR(100)` | NOT NULL | *None* |
| **confidence_score** | `NUMERIC(4, 3)` | NOT NULL | *None* |
| **reasoning_json** | `JSONB` | NOT NULL | *None* |
| **degraded_mode** | `BOOLEAN` | NOT NULL | false |
| **model_version** | `VARCHAR(50)` | NOT NULL | *None* |
| **is_current** | `BOOLEAN` | NOT NULL | true |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `threat_scores_pkey`)
- **Foreign Keys:**
  - `report_id` references `reports`(`id`) `ON DELETE RESTRICT` (Constraint Name: `threat_scores_report_id_fkey`)

---

## Case Management & Investigations Workspace

### Table: `cases`
- **Current Row Count:** 23

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **case_number** | `VARCHAR(50)` | NOT NULL | *None* |
| **case_type** | `VARCHAR(50)` | NOT NULL | *None* |
| **assigned_officer_id** | `UUID` | Nullable | *None* |
| **status** | `VARCHAR(50)` | NOT NULL | 'open'::character varying |
| **priority** | `VARCHAR(50)` | NOT NULL | 'medium'::character varying |
| **ai_summary** | `TEXT` | Nullable | *None* |
| **neo4j_ring_id** | `VARCHAR(100)` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |
| **updated_at** | `TIMESTAMP` | NOT NULL | now() |
| **closed_at** | `TIMESTAMP` | Nullable | *None* |
| **deleted_at** | `TIMESTAMP` | Nullable | *None* |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `cases_pkey`)
- **Foreign Keys:**
  - `assigned_officer_id` references `users`(`id`) `ON DELETE SET NULL` (Constraint Name: `cases_assigned_officer_id_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `cases_case_number_key` | `case_number` | Yes | *None* |

---

### Table: `case_reports`
- **Current Row Count:** 62

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **case_id** | `UUID` | NOT NULL | *None* |
| **report_id** | `UUID` | NOT NULL | *None* |
| **linked_at** | `TIMESTAMP` | NOT NULL | now() |
| **linked_reason** | `TEXT` | Nullable | *None* |

#### Constraints & Relationships
- **Primary Key:** `case_id`, `report_id` (Constraint Name: `case_reports_pkey`)
- **Foreign Keys:**
  - `case_id` references `cases`(`id`) `ON DELETE CASCADE` (Constraint Name: `case_reports_case_id_fkey`)
  - `report_id` references `reports`(`id`) `ON DELETE RESTRICT` (Constraint Name: `case_reports_report_id_fkey`)

---

### Table: `officer_assignments`
- **Current Row Count:** 1

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **case_id** | `UUID` | NOT NULL | *None* |
| **officer_id** | `UUID` | NOT NULL | *None* |
| **assigned_by** | `UUID` | NOT NULL | *None* |
| **assigned_at** | `TIMESTAMP` | NOT NULL | now() |
| **unassigned_at** | `TIMESTAMP` | Nullable | *None* |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `officer_assignments_pkey`)
- **Foreign Keys:**
  - `assigned_by` references `users`(`id`) `ON DELETE RESTRICT` (Constraint Name: `officer_assignments_assigned_by_fkey`)
  - `case_id` references `cases`(`id`) `ON DELETE RESTRICT` (Constraint Name: `officer_assignments_case_id_fkey`)
  - `officer_id` references `users`(`id`) `ON DELETE RESTRICT` (Constraint Name: `officer_assignments_officer_id_fkey`)

---

### Table: `intelligence_packages`
- **Current Row Count:** 6

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **case_id** | `UUID` | NOT NULL | *None* |
| **package_json** | `JSONB` | NOT NULL | *None* |
| **package_type** | `VARCHAR(50)` | NOT NULL | *None* |
| **content_hash** | `VARCHAR(64)` | NOT NULL | *None* |
| **pdf_ref** | `TEXT` | Nullable | *None* |
| **version** | `INTEGER` | NOT NULL | 1 |
| **generated_by** | `UUID` | NOT NULL | *None* |
| **generated_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `intelligence_packages_pkey`)
- **Foreign Keys:**
  - `case_id` references `cases`(`id`) `ON DELETE RESTRICT` (Constraint Name: `intelligence_packages_case_id_fkey`)
  - `generated_by` references `users`(`id`) `ON DELETE RESTRICT` (Constraint Name: `intelligence_packages_generated_by_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `intelligence_packages_case_id_version_key` | `case_id`, `version` | Yes | *None* |

---

## Scam Graph & Network Intelligence

### Table: `entities`
- **Current Row Count:** 62

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **type** | `VARCHAR(50)` | NOT NULL | *None* |
| **raw_value** | `TEXT` | NOT NULL | *None* |
| **normalized_value** | `TEXT` | NOT NULL | *None* |
| **risk_score** | `NUMERIC(5, 2)` | NOT NULL | 0.00 |
| **risk_tier** | `VARCHAR(50)` | NOT NULL | 'low'::character varying |
| **occurrence_count** | `INTEGER` | NOT NULL | 1 |
| **first_seen_at** | `TIMESTAMP` | NOT NULL | now() |
| **last_seen_at** | `TIMESTAMP` | NOT NULL | now() |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |
| **updated_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `entities_pkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `entities_type_normalized_value_key` | `type`, `normalized_value` | Yes | *None* |

---

### Table: `report_entities`
- **Current Row Count:** 62

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **report_id** | `UUID` | NOT NULL | *None* |
| **entity_id** | `UUID` | NOT NULL | *None* |
| **raw_span** | `TEXT` | Nullable | *None* |
| **extraction_confidence** | `NUMERIC(4, 3)` | NOT NULL | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `report_entities_pkey`)
- **Foreign Keys:**
  - `entity_id` references `entities`(`id`) `ON DELETE RESTRICT` (Constraint Name: `report_entities_entity_id_fkey`)
  - `report_id` references `reports`(`id`) `ON DELETE RESTRICT` (Constraint Name: `report_entities_report_id_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `report_entities_report_id_entity_id_raw_span_key` | `report_id`, `entity_id`, `raw_span` | Yes | *None* |

---

### Table: `relationships`
- **Current Row Count:** 63

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **entity_id_a** | `UUID` | NOT NULL | *None* |
| **entity_id_b** | `UUID` | NOT NULL | *None* |
| **relationship_type** | `VARCHAR(100)` | NOT NULL | *None* |
| **strength** | `NUMERIC(4, 3)` | NOT NULL | 1.000 |
| **evidence_report_id** | `UUID` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `relationships_pkey`)
- **Foreign Keys:**
  - `entity_id_a` references `entities`(`id`) `ON DELETE RESTRICT` (Constraint Name: `relationships_entity_id_a_fkey`)
  - `entity_id_b` references `entities`(`id`) `ON DELETE RESTRICT` (Constraint Name: `relationships_entity_id_b_fkey`)
  - `evidence_report_id` references `reports`(`id`) `ON DELETE SET NULL` (Constraint Name: `relationships_evidence_report_id_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `relationships_entity_id_a_entity_id_b_relationship_type_key` | `entity_id_a`, `entity_id_b`, `relationship_type` | Yes | *None* |

---

### Table: `fraud_rings`
- **Current Row Count:** 9

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **neo4j_ring_id** | `VARCHAR(100)` | NOT NULL | *None* |
| **algorithm** | `VARCHAR(50)` | NOT NULL | 'python_louvain'::character varying |
| **algorithm_version** | `VARCHAR(50)` | NOT NULL | 'v1'::character varying |
| **member_count** | `INTEGER` | NOT NULL | 0 |
| **complaint_count** | `INTEGER` | NOT NULL | 0 |
| **dominant_category** | `VARCHAR(100)` | Nullable | *None* |
| **aggregate_risk_score** | `NUMERIC(5, 2)` | NOT NULL | '0'::numeric |
| **risk_tier** | `VARCHAR(50)` | NOT NULL | 'low'::character varying |
| **first_activity_at** | `TIMESTAMP` | Nullable | *None* |
| **last_activity_at** | `TIMESTAMP` | Nullable | *None* |
| **detected_at** | `TIMESTAMP` | NOT NULL | now() |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |
| **updated_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `fraud_rings_pkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `idx_fraud_rings_risk_tier` | `risk_tier` | No | *None* |
| `uq_fraud_rings_neo4j_ring_id` | `neo4j_ring_id` | Yes | *None* |

---

### Table: `fraud_ring_members`
- **Current Row Count:** 34

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **ring_id** | `UUID` | NOT NULL | *None* |
| **entity_id** | `UUID` | NOT NULL | *None* |
| **membership_confidence** | `NUMERIC(4, 3)` | NOT NULL | 1.0 |
| **assigned_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `ring_id`, `entity_id` (Constraint Name: `fraud_ring_members_pkey`)
- **Foreign Keys:**
  - `entity_id` references `entities`(`id`) `ON DELETE CASCADE` (Constraint Name: `fraud_ring_members_entity_id_fkey`)
  - `ring_id` references `fraud_rings`(`id`) `ON DELETE CASCADE` (Constraint Name: `fraud_ring_members_ring_id_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `idx_fraud_ring_members_entity` | `entity_id` | No | *None* |

---

## Real-time Call/Live Session Auditing

### Table: `live_sessions`
- **Current Row Count:** 7

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **user_id** | `UUID` | NOT NULL | *None* |
| **status** | `TEXT` | NOT NULL | 'active'::text |
| **current_severity_band** | `TEXT` | NOT NULL | 'low'::text |
| **current_score** | `SMALLINT` | NOT NULL | '0'::smallint |
| **scam_category** | `TEXT` | Nullable | *None* |
| **intervention_shown_at** | `TIMESTAMP` | Nullable | *None* |
| **linked_case_id** | `UUID` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |
| **ended_at** | `TIMESTAMP` | Nullable | *None* |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `live_sessions_pkey`)
- **Foreign Keys:**
  - `linked_case_id` references `cases`(`id`) `ON DELETE SET NULL` (Constraint Name: `live_sessions_linked_case_id_fkey`)
  - `user_id` references `users`(`id`) `ON DELETE RESTRICT` (Constraint Name: `live_sessions_user_id_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `idx_live_sessions_status` | `status` | No | `WHERE (status = 'active'::text)` |
| `idx_live_sessions_user_id` | `user_id` | No | *None* |

---

### Table: `live_session_turns`
- **Current Row Count:** 22

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **session_id** | `UUID` | NOT NULL | *None* |
| **turn_index** | `INTEGER` | NOT NULL | *None* |
| **raw_text** | `TEXT` | NOT NULL | *None* |
| **turn_score** | `SMALLINT` | NOT NULL | *None* |
| **cumulative_score** | `SMALLINT` | NOT NULL | *None* |
| **flagged_phrases_json** | `JSONB` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `live_session_turns_pkey`)
- **Foreign Keys:**
  - `session_id` references `live_sessions`(`id`) `ON DELETE CASCADE` (Constraint Name: `live_session_turns_session_id_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `idx_live_session_turns_session_id` | `session_id` | No | *None* |
| `uq_live_session_turns_session_turn` | `session_id`, `turn_index` | Yes | *None* |

---

## Knowledge Base & LLM Context

### Table: `knowledge_base`
- **Current Row Count:** 21

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **source** | `VARCHAR(50)` | NOT NULL | *None* |
| **title** | `VARCHAR(255)` | NOT NULL | *None* |
| **content** | `TEXT` | NOT NULL | *None* |
| **source_url** | `TEXT` | Nullable | *None* |
| **added_by** | `UUID` | NOT NULL | *None* |
| **status** | `VARCHAR(50)` | NOT NULL | 'processing'::character varying |
| **version** | `INTEGER` | NOT NULL | 1 |
| **ingested_at** | `TIMESTAMP` | NOT NULL | now() |
| **updated_at** | `TIMESTAMP` | NOT NULL | now() |
| **deleted_at** | `TIMESTAMP` | Nullable | *None* |
| **times_cited** | `INTEGER` | NOT NULL | 0 |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `knowledge_base_pkey`)
- **Foreign Keys:**
  - `added_by` references `users`(`id`) `ON DELETE RESTRICT` (Constraint Name: `knowledge_base_added_by_fkey`)

---

### Table: `knowledge_base_chunks`
- **Current Row Count:** 42

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **knowledge_base_id** | `UUID` | NOT NULL | *None* |
| **chunk_index** | `INTEGER` | NOT NULL | *None* |
| **chunk_text** | `TEXT` | NOT NULL | *None* |
| **embedding** | `NULL` | NOT NULL | *None* |
| **embedding_model_version** | `VARCHAR(50)` | NOT NULL | *None* |
| **token_count** | `INTEGER` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `knowledge_base_chunks_pkey`)
- **Foreign Keys:**
  - `knowledge_base_id` references `knowledge_base`(`id`) `ON DELETE CASCADE` (Constraint Name: `knowledge_base_chunks_knowledge_base_id_fkey`)

#### Indexes
| Index Name | Columns | Unique | Details / Partial Clause |
| :--- | :--- | :--- | :--- |
| `knowledge_base_chunks_knowledge_base_id_chunk_index_embeddi_key` | `knowledge_base_id`, `chunk_index`, `embedding_model_version` | Yes | *None* |

---

## Alerts & System Infrastructure

### Table: `alerts`
- **Current Row Count:** 11

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **scope** | `VARCHAR(50)` | NOT NULL | *None* |
| **title** | `VARCHAR(255)` | NOT NULL | *None* |
| **description** | `TEXT` | NOT NULL | *None* |
| **severity** | `VARCHAR(50)` | NOT NULL | *None* |
| **related_case_id** | `UUID` | Nullable | *None* |
| **related_report_id** | `UUID` | Nullable | *None* |
| **velocity_metric** | `JSONB` | Nullable | *None* |
| **is_active** | `BOOLEAN` | NOT NULL | true |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |
| **expires_at** | `TIMESTAMP` | Nullable | *None* |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `alerts_pkey`)
- **Foreign Keys:**
  - `related_case_id` references `cases`(`id`) `ON DELETE SET NULL` (Constraint Name: `alerts_related_case_id_fkey`)
  - `related_report_id` references `reports`(`id`) `ON DELETE SET NULL` (Constraint Name: `alerts_related_report_id_fkey`)

---

### Table: `notifications`
- **Current Row Count:** 0

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **user_id** | `UUID` | NOT NULL | *None* |
| **type** | `VARCHAR(50)` | NOT NULL | *None* |
| **title** | `VARCHAR(255)` | NOT NULL | *None* |
| **body** | `TEXT` | Nullable | *None* |
| **related_entity_type** | `VARCHAR(50)` | Nullable | *None* |
| **related_entity_id** | `UUID` | Nullable | *None* |
| **read_at** | `TIMESTAMP` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `notifications_pkey`)
- **Foreign Keys:**
  - `user_id` references `users`(`id`) `ON DELETE CASCADE` (Constraint Name: `notifications_user_id_fkey`)

---

### Table: `audit_logs`
- **Current Row Count:** 1

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **id** | `UUID` | NOT NULL | gen_random_uuid() |
| **actor_id** | `UUID` | Nullable | *None* |
| **actor_type** | `VARCHAR(50)` | NOT NULL | 'user'::character varying |
| **action** | `VARCHAR(100)` | NOT NULL | *None* |
| **entity_type** | `VARCHAR(50)` | NOT NULL | *None* |
| **entity_id** | `UUID` | NOT NULL | *None* |
| **diff_json** | `JSONB` | Nullable | *None* |
| **ip_address** | `INET` | Nullable | *None* |
| **created_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `id` (Constraint Name: `audit_logs_pkey`)
- **Foreign Keys:**
  - `actor_id` references `users`(`id`) `ON DELETE SET NULL` (Constraint Name: `audit_logs_actor_id_fkey`)

---

### Table: `settings`
- **Current Row Count:** 0

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **key** | `VARCHAR(255)` | NOT NULL | *None* |
| **value_json** | `JSONB` | NOT NULL | *None* |
| **description** | `TEXT` | Nullable | *None* |
| **updated_by** | `UUID` | Nullable | *None* |
| **updated_at** | `TIMESTAMP` | NOT NULL | now() |

#### Constraints & Relationships
- **Primary Key:** `key` (Constraint Name: `settings_pkey`)
- **Foreign Keys:**
  - `updated_by` references `users`(`id`) `ON DELETE SET NULL` (Constraint Name: `settings_updated_by_fkey`)

---

### Table: `alembic_version`
- **Current Row Count:** 1

#### Column Specifications
| Column | Data Type | Nullability | Default Value |
| :--- | :--- | :--- | :--- |
| **version_num** | `VARCHAR(32)` | NOT NULL | *None* |

#### Constraints & Relationships
- **Primary Key:** `version_num` (Constraint Name: `alembic_version_pkc`)

---

## Architecture and Optimization Review

### 1. Vector Search for LLM Semantic Retrieval
- The `knowledge_base_chunks` table includes a special column type `vector` (pgvector extension) for semantic embedding representation.
- This allows the AI agent pipelines to perform fast cosine/Euclidean similarity searches directly in Neon PostgreSQL without relying on an external vector database (like Pinecone).

### 2. High-Performance JSONB Columns
- Semi-structured data (such as LLM evaluation reasoning paths, entity extraction metadata, and fraud graph intelligence packages) is stored in native `JSONB` columns in `threat_scores`, `evidence`, `intelligence_packages`, and `live_session_turns`.
- JSONB stores data in a decomposed binary format, allowing fast indexing and key extraction queries.

### 3. Graph Mirroring and Local Fallbacks
- `fraud_rings` and `fraud_ring_members` are designed as local Postgres mirrors of Neo4j nodes and edges.
- This dual-storage design ensures that if Neo4j is offline or temporarily unreachable, the frontend can query fraud ring memberships directly from Postgres, maintaining high system availability.

### 4. Indexing & Query Optimizations
- Custom indexes are implemented on key high-cardinality foreign keys (`idx_fraud_ring_members_entity`, `idx_live_sessions_user_id`, `idx_live_session_turns_session_id`).
- A partial index is defined on `live_sessions` (`idx_live_sessions_status` with clause `WHERE (status = 'active'::text)`) to optimize lookups for currently active assistance calls.