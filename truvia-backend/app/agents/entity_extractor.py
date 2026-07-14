import re
import logging
from sqlalchemy import select, insert, update
from app.data.postgres_client import AsyncSessionLocal
from app.models.report import Report, Entity, ReportEntity, Relationship
from datetime import datetime

logger = logging.getLogger("truvia.agents.entity_extractor")

# Regex compilation for extraction
PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
UPI_REGEX = re.compile(r'\b[a-zA-Z0-9.\-_]{2,50}@[a-zA-Z]{2,20}\b')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
URL_REGEX = re.compile(r'\bhttps?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}\b')

class EntityExtractorAgent:
    async def extract_entities(self, report_id: str) -> dict:
        """
        Main entry point for Agent 4. Analyzes report text, extracts unique entities,
        updates global ledger, and derives pairwise connections in SQL.
        """
        import uuid
        if isinstance(report_id, str):
            report_id = uuid.UUID(report_id)

        async with AsyncSessionLocal() as session:
            try:
                # 1. Fetch Report
                report_result = await session.execute(
                    select(Report).where(Report.id == report_id)
                )
                report = report_result.scalar_one_or_none()
                if not report or not report.cleaned_text:
                    logger.warning(f"Report {report_id} has no text. Skipping entity extraction.")
                    return {"status": "skipped", "message": "No text content"}

                text = report.cleaned_text
                extracted_items = []

                # 2. Extract types
                # A. UPI IDs
                upis = UPI_REGEX.findall(text)
                for upi in upis:
                    extracted_items.append({
                        "type": "upi",
                        "raw_value": upi,
                        "normalized_value": upi.lower().strip()
                    })

                # B. Phone numbers
                phones = PHONE_REGEX.findall(text)
                for phone in phones:
                    # Keep only digits for normalization
                    normalized_phone = "".join(filter(str.isdigit, phone))
                    if len(normalized_phone) >= 10:  # Valid local/intl number length check
                        extracted_items.append({
                            "type": "phone",
                            "raw_value": phone,
                            "normalized_value": normalized_phone[-10:] # Last 10 digits for Indian standard
                        })

                # C. Emails
                emails = EMAIL_REGEX.findall(text)
                for email in emails:
                    extracted_items.append({
                        "type": "email",
                        "raw_value": email,
                        "normalized_value": email.lower().strip()
                    })

                # D. URLs
                urls = URL_REGEX.findall(text)
                for url in urls:
                    domain = url.replace("https://", "").replace("http://", "").split("/")[0]
                    extracted_items.append({
                        "type": "domain",
                        "raw_value": url,
                        "normalized_value": domain.lower().strip()
                    })

                # De-duplicate local list
                seen = set()
                unique_extractions = []
                for item in extracted_items:
                    key = (item["type"], item["normalized_value"])
                    if key not in seen:
                        seen.add(key)
                        unique_extractions.append(item)

                saved_entities = []

                # 3. Save unique entities & links in Postgres
                for item in unique_extractions:
                    # Check if entity exists
                    entity_result = await session.execute(
                        select(Entity)
                        .where(Entity.type == item["type"])
                        .where(Entity.normalized_value == item["normalized_value"])
                    )
                    entity = entity_result.scalar_one_or_none()

                    if entity:
                        # Update existing entity seen counters
                        entity.occurrence_count += 1
                        entity.last_seen_at = datetime.utcnow()
                        # Increment risk slightly on recurring alerts
                        entity.risk_score = min(entity.risk_score + 10.0, 100.0)
                        if entity.risk_score >= 90:
                            entity.risk_tier = "critical"
                        elif entity.risk_score >= 70:
                            entity.risk_tier = "high"
                        elif entity.risk_score >= 40:
                            entity.risk_tier = "moderate"
                    else:
                        # Insert new Entity
                        entity = Entity(
                            type=item["type"],
                            raw_value=item["raw_value"],
                            normalized_value=item["normalized_value"],
                            risk_score=25.0,  # Starting suspicion risk score
                            risk_tier="low",
                            occurrence_count=1
                        )
                        session.add(entity)
                    
                    # Force flush to generate UUIDs
                    await session.flush()

                    # Create report-entity mapping
                    report_entity_link = ReportEntity(
                        report_id=report.id,
                        entity_id=entity.id,
                        raw_span=item["raw_value"],
                        extraction_confidence=0.950
                    )
                    session.add(report_entity_link)
                    saved_entities.append(entity)

                # 4. Create Pairwise Relationships between co-occurring entities
                # For each pair in the report, create a relationship
                for i in range(len(saved_entities)):
                    for j in range(i + 1, len(saved_entities)):
                        ent_a = saved_entities[i]
                        ent_b = saved_entities[j]

                        # Check if relationship already exists
                        rel_result = await session.execute(
                            select(Relationship)
                            .where(
                                ((Relationship.entity_id_a == ent_a.id) & (Relationship.entity_id_b == ent_b.id)) |
                                ((Relationship.entity_id_a == ent_b.id) & (Relationship.entity_id_b == ent_a.id))
                            )
                        )
                        existing_rel = rel_result.scalar_one_or_none()

                        if not existing_rel:
                            # Create a co-occurrence link
                            new_rel = Relationship(
                                entity_id_a=ent_a.id,
                                entity_id_b=ent_b.id,
                                relationship_type="co_occurred_in_report",
                                strength=1.000,
                                evidence_report_id=report.id
                            )
                            session.add(new_rel)

                # Entity extraction is an enrichment step — it must NOT change the
                # report's lifecycle status. Escalation is an explicit user/officer action
                # handled by the /escalate endpoint. Leave the status set by the threat
                # evaluator (e.g. "scored") untouched.
                await session.commit()
                logger.info(f"Report {report_id}: extracted {len(saved_entities)} entities and linked relationship pairs")
                
                return {
                    "report_id": report_id,
                    "extracted_count": len(saved_entities),
                    "entities": [e.raw_value for e in saved_entities]
                }
            except Exception as e:
                logger.error(f"Error in Agent 4 extracting entities for report {report_id}: {str(e)}")
                raise

entity_extractor_agent = EntityExtractorAgent()
