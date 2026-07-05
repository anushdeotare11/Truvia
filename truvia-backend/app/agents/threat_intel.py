import logging
from sqlalchemy import select
from app.data.postgres_client import AsyncSessionLocal
from app.models.report import Report, Entity, ReportEntity, Relationship
from app.data.neo4j_client import neo4j_client

logger = logging.getLogger("truvia.agents.threat_intel")

class ThreatIntelAgent:
    async def index_report_in_graph(self, report_id: str) -> dict:
        """
        Main entry point for Agent 5. Links Postgres entities and report details
        into Neo4j Graph database for cluster analysis.
        """
        async with AsyncSessionLocal() as session:
            try:
                # 1. Fetch Report
                report_result = await session.execute(
                    select(Report).where(Report.id == report_id)
                )
                report = report_result.scalar_one_or_none()
                if not report:
                    logger.error(f"Report {report_id} not found for graph indexing")
                    return {"status": "error", "message": "Report not found"}

                # 2. Fetch Entities associated with this report
                entities_result = await session.execute(
                    select(Entity)
                    .join(ReportEntity)
                    .where(ReportEntity.report_id == report.id)
                )
                entities = entities_result.scalars().all()

                logger.info(f"Indexing report {report_id} and {len(entities)} entities in graph database")

                # 3. Check if Neo4j is connected
                if not neo4j_client.driver:
                    try:
                        neo4j_client.connect()
                    except Exception:
                        pass
                
                if not neo4j_client.driver:
                    logger.warning("Neo4j client is not connected. Running in degraded graph mode.")
                    return {
                        "status": "degraded_mode",
                        "message": "Graph indexed locally in SQL only (Neo4j offline)"
                    }

                # 4. Run Cypher transactional queries to load Neo4j nodes and edges
                # A. Upsert Report Node
                report_cypher = (
                    "MERGE (r:Report {id: $report_id}) "
                    "SET r.source_type = $source_type, "
                    "    r.status = $status, "
                    "    r.created_at = $created_at "
                    "RETURN r"
                )
                await neo4j_client.run_query(report_cypher, {
                    "report_id": str(report.id),
                    "source_type": report.source_type,
                    "status": report.status,
                    "created_at": report.created_at.isoformat()
                })

                # B. Upsert Entity Nodes and HAS_ENTITY edges
                for entity in entities:
                    uid = f"{entity.type}:{entity.normalized_value}"
                    entity_cypher = (
                        "MERGE (e:Entity {uid: $uid}) "
                        "SET e.id = $id, "
                        "    e.type = $type, "
                        "    e.value = $value, "
                        "    e.risk_score = $risk_score, "
                        "    e.risk_tier = $risk_tier, "
                        "    e.occurrence_count = $occurrence_count "
                        "WITH e "
                        "MATCH (r:Report {id: $report_id}) "
                        "MERGE (r)-[:HAS_ENTITY]->(e)"
                    )
                    await neo4j_client.run_query(entity_cypher, {
                        "uid": uid,
                        "id": str(entity.id),
                        "type": entity.type,
                        "value": entity.raw_value,
                        "risk_score": float(entity.risk_score),
                        "risk_tier": entity.risk_tier,
                        "occurrence_count": int(entity.occurrence_count),
                        "report_id": str(report.id)
                    })

                # C. Link co-occurring entities with CO_OCCURRED_IN relationships
                for i in range(len(entities)):
                    for j in range(i + 1, len(entities)):
                        uid_a = f"{entities[i].type}:{entities[i].normalized_value}"
                        uid_b = f"{entities[j].type}:{entities[j].normalized_value}"
                        
                        co_occur_cypher = (
                            "MATCH (e1:Entity {uid: $uid_a}) "
                            "MATCH (e2:Entity {uid: $uid_b}) "
                            "MERGE (e1)-[r:CO_OCCURRED_WITH]-(e2) "
                            "ON CREATE SET r.weight = 1.0, r.report_ids = [$report_id] "
                            "ON MATCH SET r.weight = r.weight + 1.0, "
                            "             r.report_ids = CASE WHEN NOT $report_id IN r.report_ids THEN r.report_ids + $report_id ELSE r.report_ids END"
                        )
                        await neo4j_client.run_query(co_occur_cypher, {
                            "uid_a": uid_a,
                            "uid_b": uid_b,
                            "report_id": str(report.id)
                        })

                logger.info(f"Report {report_id} successfully indexed in Neo4j")
                return {"status": "success", "report_id": report_id}

            except Exception as e:
                logger.error(f"Failed to index report in Neo4j: {str(e)}")
                # We do not crash the pipeline since Graph writes are decoulpled/background
                return {"status": "error", "message": str(e)}

threat_intel_agent = ThreatIntelAgent()
