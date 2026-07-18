"""Agent 5 — Threat Intelligence graph sync.

Mirrors the authoritative Postgres records into the Neo4j correlation index,
exactly per Backend_Schema §9.1/§9.2:

    (:Entity {id, type, normalized_value, risk_score, risk_tier, occurrence_count})
        with a typed sub-label (:Entity:Phone / :UPI / :Email / :Domain / :Device / :IP / :Org)
    (:Report {id, created_at, scam_category, severity_band})
    (:Entity)-[:CO_OCCURRED_IN {extraction_confidence, raw_span}]->(:Report)
    (:Entity)-[:LINKED_TO {relationship_type, strength, evidence_report_id}]-(:Entity)

Neo4j is a *derived* index (§9.5): every write here has a Postgres source and the
whole graph is rebuildable from Postgres. This agent is therefore best-effort and
MUST NOT crash the ingestion pipeline — if Neo4j is offline it returns a
`degraded_mode` result and the platform continues in Postgres-only mode.
"""
import logging
import uuid

from sqlalchemy import select

from app.data.postgres_client import AsyncSessionLocal
from app.data.neo4j_client import neo4j_client
from app.models.report import Report, Entity, ReportEntity, Relationship, ThreatScore

logger = logging.getLogger("truvia.agents.threat_intel")

# Whitelisted entity-type -> Neo4j typed sub-label (§9.1 dual-labeling).
TYPE_LABEL = {
    "phone": "Phone",
    "upi": "UPI",
    "email": "Email",
    "domain": "Domain",
    "device": "Device",
    "ip": "IP",
    "org": "Org",
}


def _entity_label(entity_type: str) -> str:
    """Return a safe, whitelisted sub-label for an entity type (never user input)."""
    return TYPE_LABEL.get((entity_type or "").lower(), "Unknown")


class ThreatIntelAgent:
    def _ensure_driver(self) -> bool:
        if not neo4j_client.driver:
            try:
                neo4j_client.connect()
            except Exception:
                return False
        return bool(neo4j_client.driver)

    async def _upsert_entity(self, entity: Entity) -> None:
        label = _entity_label(entity.type)
        cypher = (
            "MERGE (e:Entity {id: $id}) "
            f"SET e:{label}, "
            "    e.type = $type, "
            "    e.normalized_value = $normalized_value, "
            "    e.raw_value = $raw_value, "
            "    e.risk_score = $risk_score, "
            "    e.risk_tier = $risk_tier, "
            "    e.occurrence_count = $occurrence_count"
        )
        await neo4j_client.run_query(cypher, {
            "id": str(entity.id),
            "type": entity.type,
            "normalized_value": entity.normalized_value,
            "raw_value": entity.raw_value,
            "risk_score": float(entity.risk_score),
            "risk_tier": entity.risk_tier,
            "occurrence_count": int(entity.occurrence_count),
        })

    async def index_report_in_graph(self, report_id: str) -> dict:
        """Sync a single report and its entities/relationships into Neo4j.

        Called by the ingestion pipeline (Agent 5). Best-effort and non-fatal.
        """
        if isinstance(report_id, str):
            report_id = uuid.UUID(report_id)

        async with AsyncSessionLocal() as session:
            try:
                report = (await session.execute(
                    select(Report).where(Report.id == report_id)
                )).scalar_one_or_none()
                if not report:
                    logger.error(f"Report {report_id} not found for graph indexing")
                    return {"status": "error", "message": "Report not found"}

                # Current threat score powers the denormalized Report node props.
                ts = (await session.execute(
                    select(ThreatScore).where(
                        ThreatScore.report_id == report_id,
                        ThreatScore.is_current == True,  # noqa: E712
                    )
                )).scalar_one_or_none()

                # Entities linked to this report, with the join rows (for edge props).
                link_rows = (await session.execute(
                    select(ReportEntity).where(ReportEntity.report_id == report_id)
                )).scalars().all()
                entity_ids = [lr.entity_id for lr in link_rows]
                entities = []
                if entity_ids:
                    entities = (await session.execute(
                        select(Entity).where(Entity.id.in_(entity_ids))
                    )).scalars().all()

                if not self._ensure_driver():
                    logger.warning("Neo4j offline — report indexed in Postgres only (degraded graph mode).")
                    return {
                        "status": "degraded_mode",
                        "message": "Graph indexed in Postgres only (Neo4j offline)",
                        "entities": len(entities),
                    }

                # A. Report node (thin; denormalized category/severity per §9.1).
                await neo4j_client.run_query(
                    "MERGE (r:Report {id: $id}) "
                    "SET r.created_at = $created_at, "
                    "    r.scam_category = $scam_category, "
                    "    r.severity_band = $severity_band, "
                    "    r.source_type = $source_type, "
                    "    r.status = $status",
                    {
                        "id": str(report.id),
                        "created_at": report.created_at.isoformat() if report.created_at else None,
                        "scam_category": ts.scam_category if ts else None,
                        "severity_band": ts.severity_band if ts else None,
                        "source_type": report.source_type,
                        "status": report.status,
                    },
                )

                # B. Entity nodes + CO_OCCURRED_IN edges (Entity -> Report).
                link_by_entity = {lr.entity_id: lr for lr in link_rows}
                for entity in entities:
                    await self._upsert_entity(entity)
                    lr = link_by_entity.get(entity.id)
                    await neo4j_client.run_query(
                        "MATCH (e:Entity {id: $eid}) "
                        "MATCH (r:Report {id: $rid}) "
                        "MERGE (e)-[c:CO_OCCURRED_IN]->(r) "
                        "SET c.extraction_confidence = $conf, c.raw_span = $span",
                        {
                            "eid": str(entity.id),
                            "rid": str(report.id),
                            "conf": float(lr.extraction_confidence) if lr and lr.extraction_confidence is not None else None,
                            "span": lr.raw_span if lr else None,
                        },
                    )

                # C. LINKED_TO edges from the Postgres relationships table for this
                #    report's entity neighbourhood (mirrors §9.2 exactly).
                if entity_ids:
                    rels = (await session.execute(
                        select(Relationship).where(
                            (Relationship.entity_id_a.in_(entity_ids)) |
                            (Relationship.entity_id_b.in_(entity_ids))
                        )
                    )).scalars().all()
                    for rel in rels:
                        await neo4j_client.run_query(
                            "MATCH (a:Entity {id: $a}) "
                            "MATCH (b:Entity {id: $b}) "
                            "MERGE (a)-[l:LINKED_TO {relationship_type: $rtype}]-(b) "
                            "SET l.strength = $strength, l.evidence_report_id = $evid, l.symmetric = true",
                            {
                                "a": str(rel.entity_id_a),
                                "b": str(rel.entity_id_b),
                                "rtype": rel.relationship_type,
                                "strength": float(rel.strength),
                                "evid": str(rel.evidence_report_id) if rel.evidence_report_id else None,
                            },
                        )

                logger.info(f"Report {report_id} synced to Neo4j ({len(entities)} entities).")
                return {"status": "success", "report_id": str(report_id), "entities": len(entities)}

            except Exception as e:
                # Never propagate — graph sync is decoupled/background.
                logger.error(f"Neo4j sync failed for report {report_id}: {e}")
                return {"status": "error", "message": str(e)}


threat_intel_agent = ThreatIntelAgent()
