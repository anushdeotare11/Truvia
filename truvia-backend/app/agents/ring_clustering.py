"""Fraud-ring clustering (Backend_Schema §9.4).

Detects fraud rings via Louvain community detection over the entity graph, then
persists them so the Threat Intelligence Engine can serve real ring data.

Dual-path, per the prompt's "Neo4j GDS (or equivalent)":
  * PRIMARY  — Neo4j GDS `gds.louvain.stream` when Neo4j + GDS are reachable.
  * EQUIVALENT — `python-louvain` (community.best_partition) over a NetworkX
                 graph built from the authoritative Postgres `relationships`
                 table, so ring detection works with Neo4j offline.

Results are written to Postgres (`fraud_rings` / `fraud_ring_members`) — always —
and mirrored into Neo4j (`:Ring` nodes + `[:MEMBER_OF]` edges) when reachable.

Run as a command:
    .venv\\Scripts\\python.exe -m scripts.cluster_rings            (Windows)
    .venv/bin/python -m scripts.cluster_rings                      (macOS/Linux)
"""
import hashlib
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from sqlalchemy import select, delete

from app.data.postgres_client import AsyncSessionLocal
from app.data.neo4j_client import neo4j_client
from app.models.report import Entity, Relationship, ReportEntity, ThreatScore, Report
from app.models.ring import FraudRing, FraudRingMember

logger = logging.getLogger("truvia.agents.ring_clustering")

MIN_RING_SIZE = 3          # a "ring" needs at least 3 correlated entities
ALGORITHM_VERSION = "v1"


def _risk_tier(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "moderate"
    return "low"


def _ring_key(member_ids: List[str]) -> str:
    """Stable identifier for a community from its member set (order-independent).

    Keeps `neo4j_ring_id` consistent across re-runs when the same community
    reforms, so `cases.neo4j_ring_id` references remain valid.
    """
    digest = hashlib.sha1(",".join(sorted(member_ids)).encode()).hexdigest()[:12]
    return f"ring-{digest}"


def _louvain_local(node_ids: List[str], edges: List[Tuple[str, str, float]]) -> Dict[str, int]:
    """Equivalent Louvain via python-louvain over NetworkX (Postgres-backed)."""
    import networkx as nx
    import community as community_louvain  # python-louvain

    g = nx.Graph()
    g.add_nodes_from(node_ids)
    for a, b, w in edges:
        if a in g and b in g:
            # accumulate weight for repeated pairs
            if g.has_edge(a, b):
                g[a][b]["weight"] += w
            else:
                g.add_edge(a, b, weight=w)

    if g.number_of_edges() == 0:
        return {n: i for i, n in enumerate(node_ids)}
    return community_louvain.best_partition(g, weight="weight", random_state=42)


def _louvain_gds_sync() -> Dict[str, int]:
    """Synchronous GDS Louvain using a short-lived sync driver."""
    from neo4j import GraphDatabase
    from app.config import settings

    graph_name = "truvia-entity-graph"
    partition: Dict[str, int] = {}
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        connection_timeout=5,
    )
    try:
        with driver.session() as s:
            # GDS must be installed; this raises if not, triggering the fallback.
            s.run("RETURN gds.version()").consume()
            s.run(
                "CALL gds.graph.exists($g) YIELD exists "
                "WITH exists WHERE exists CALL gds.graph.drop($g) YIELD graphName "
                "RETURN graphName", {"g": graph_name},
            ).consume()
            s.run(
                "CALL gds.graph.project($g, 'Entity', "
                "{LINKED_TO: {orientation: 'UNDIRECTED', properties: 'strength'}})",
                {"g": graph_name},
            ).consume()
            result = s.run(
                "CALL gds.louvain.stream($g, {relationshipWeightProperty: 'strength'}) "
                "YIELD nodeId, communityId "
                "RETURN gds.util.asNode(nodeId).id AS id, communityId", {"g": graph_name},
            )
            for rec in result:
                if rec["id"] is not None:
                    partition[str(rec["id"])] = int(rec["communityId"])
            s.run(
                "CALL gds.graph.exists($g) YIELD exists "
                "WITH exists WHERE exists CALL gds.graph.drop($g) YIELD graphName "
                "RETURN graphName", {"g": graph_name},
            ).consume()
    finally:
        driver.close()
    return partition


async def detect_and_persist_rings(min_ring_size: int = MIN_RING_SIZE) -> dict:
    """Compute Louvain communities and persist rings to Postgres (+ Neo4j)."""
    async with AsyncSessionLocal() as session:
        entities = (await session.execute(select(Entity))).scalars().all()
        relationships = (await session.execute(select(Relationship))).scalars().all()

        entity_by_id = {str(e.id): e for e in entities}
        node_ids = list(entity_by_id.keys())
        edges = [
            (str(r.entity_id_a), str(r.entity_id_b), float(r.strength or 1.0))
            for r in relationships
        ]

        if not node_ids:
            return {"algorithm": None, "rings": 0, "message": "No entities to cluster."}

        # --- choose engine ---
        algorithm = "python_louvain"
        partition: Dict[str, int] = {}
        try:
            import asyncio
            partition = await asyncio.to_thread(_louvain_gds_sync)
            if partition:
                algorithm = "gds_louvain"
            else:
                raise RuntimeError("GDS returned empty partition")
        except Exception as e:
            logger.info(f"GDS Louvain unavailable ({type(e).__name__}); using python-louvain equivalent. {str(e)[:80]}")
            import asyncio
            partition = await asyncio.to_thread(_louvain_local, node_ids, edges)
            algorithm = "python_louvain"

        # Ensure every node has a community (GDS only returns projected nodes).
        next_comm = (max(partition.values()) + 1) if partition else 0
        for nid in node_ids:
            if nid not in partition:
                partition[nid] = next_comm
                next_comm += 1

        # --- group into candidate rings ---
        groups: Dict[int, List[str]] = {}
        for nid, comm in partition.items():
            groups.setdefault(comm, []).append(nid)
        candidate_rings = [m for m in groups.values() if len(m) >= min_ring_size]

        # --- enrich each ring with report-derived stats ---
        # Preload report_entities + threat scores for all ring members at once.
        all_member_ids = [mid for ring in candidate_rings for mid in ring]
        member_uuids = [entity_by_id[m].id for m in all_member_ids]
        report_links = []
        if member_uuids:
            report_links = (await session.execute(
                select(ReportEntity).where(ReportEntity.entity_id.in_(member_uuids))
            )).scalars().all()
        entity_to_reports: Dict[str, set] = {}
        for rl in report_links:
            entity_to_reports.setdefault(str(rl.entity_id), set()).add(rl.report_id)

        # report -> (created_at, category)
        involved_report_ids = {rid for s in entity_to_reports.values() for rid in s}
        report_meta: Dict[str, Tuple] = {}
        if involved_report_ids:
            reports = (await session.execute(
                select(Report).where(Report.id.in_(list(involved_report_ids)))
            )).scalars().all()
            scores = (await session.execute(
                select(ThreatScore).where(
                    ThreatScore.report_id.in_(list(involved_report_ids)),
                    ThreatScore.is_current == True,  # noqa: E712
                )
            )).scalars().all()
            cat_by_report = {str(sc.report_id): sc.scam_category for sc in scores}
            for r in reports:
                report_meta[str(r.id)] = (r.created_at, cat_by_report.get(str(r.id)))

        # --- wipe & rewrite rings (full recompute; idempotent) ---
        await session.execute(delete(FraudRingMember))
        await session.execute(delete(FraudRing))
        await session.flush()

        persisted = []
        for members in candidate_rings:
            member_entities = [entity_by_id[m] for m in members]
            agg_risk = sum(float(e.risk_score) for e in member_entities) / len(member_entities)

            ring_report_ids = set()
            for m in members:
                ring_report_ids |= entity_to_reports.get(m, set())
            complaint_count = len(ring_report_ids)

            cats = [report_meta[str(rid)][1] for rid in ring_report_ids
                    if str(rid) in report_meta and report_meta[str(rid)][1]]
            dominant_category = Counter(cats).most_common(1)[0][0] if cats else None

            dates = [report_meta[str(rid)][0] for rid in ring_report_ids
                     if str(rid) in report_meta and report_meta[str(rid)][0]]
            first_activity = min(dates) if dates else None
            last_activity = max(dates) if dates else None

            ring_key = _ring_key(members)
            ring = FraudRing(
                neo4j_ring_id=ring_key,
                algorithm=algorithm,
                algorithm_version=ALGORITHM_VERSION,
                member_count=len(members),
                complaint_count=complaint_count,
                dominant_category=dominant_category,
                aggregate_risk_score=round(agg_risk, 2),
                risk_tier=_risk_tier(agg_risk),
                first_activity_at=first_activity,
                last_activity_at=last_activity,
                detected_at=datetime.now(timezone.utc),
            )
            session.add(ring)
            await session.flush()  # get ring.id
            for e in member_entities:
                session.add(FraudRingMember(
                    ring_id=ring.id,
                    entity_id=e.id,
                    membership_confidence=1.000,
                ))
            persisted.append((ring_key, [str(e.id) for e in member_entities]))

        await session.commit()

    # --- mirror into Neo4j when reachable (best-effort) ---
    neo4j_written = 0
    try:
        if not neo4j_client.driver:
            neo4j_client.connect()
        if neo4j_client.driver:
            # clear stale ring structure, then rewrite
            await neo4j_client.run_query("MATCH (g:Ring) DETACH DELETE g")
            for ring_key, member_ids in persisted:
                await neo4j_client.run_query(
                    "MERGE (g:Ring {id: $id}) "
                    "SET g.detected_at = $ts, g.algorithm_version = $ver, g.member_count = $mc",
                    {"id": ring_key, "ts": datetime.now(timezone.utc).isoformat(),
                     "ver": ALGORITHM_VERSION, "mc": len(member_ids)},
                )
                for eid in member_ids:
                    await neo4j_client.run_query(
                        "MATCH (e:Entity {id: $eid}) MATCH (g:Ring {id: $gid}) "
                        "MERGE (e)-[m:MEMBER_OF]->(g) SET m.membership_confidence = 1.0, m.assigned_at = $ts",
                        {"eid": eid, "gid": ring_key, "ts": datetime.now(timezone.utc).isoformat()},
                    )
                neo4j_written += 1
    except Exception as e:
        logger.info(f"Neo4j ring mirror skipped (offline or error): {str(e)[:100]}")

    result = {
        "algorithm": algorithm,
        "rings": len(persisted),
        "neo4j_rings_written": neo4j_written,
    }
    logger.info(f"Ring clustering complete: {result}")
    return result
