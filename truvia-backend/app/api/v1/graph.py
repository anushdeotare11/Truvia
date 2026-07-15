from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.data.postgres_client import get_db
from app.api import deps
from app.models.report import Entity, Relationship, ReportEntity, Report
from sqlalchemy import select
from app.data.neo4j_client import neo4j_client
from app.core.pdf import generate_report_pdf
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import asyncio
import uuid

router = APIRouter()
logger = logging.getLogger("truvia.api.graph")

def calculate_local_communities(nodes_list: List[Dict[str, Any]], edges_list: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Computes connected components to partition nodes into color-coded scam rings.
    """
    node_ids = [n["id"] for n in nodes_list]
    adj = {nid: set() for nid in node_ids}
    
    for edge in edges_list:
        s = edge["source"]
        t = edge["target"]
        if s in adj and t in adj:
            adj[s].add(t)
            adj[t].add(s)
            
    visited = set()
    communities = {}
    current_community = 0
    
    for nid in node_ids:
        if nid not in visited:
            queue = [nid]
            visited.add(nid)
            component = []
            
            while queue:
                curr = queue.pop(0)
                component.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
                        
            for member in component:
                communities[member] = current_community
            current_community += 1
            
    return communities

@router.get("/overview", status_code=status.HTTP_200_OK)
async def get_graph_overview(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_user) # Restrict to authenticated officers/admins
):
    """
    Returns nodes and edges for the SOC Threat Graph Engine.
    Leverages Neo4j queries if online, otherwise falls back to SQL relations with local clustering.
    """
    # 1. Check if Neo4j is connected and query it
    if neo4j_client.driver:
        try:
            # Retrieve Entities and HAS_ENTITY links
            cypher_query = (
                "MATCH (e:Entity) "
                "OPTIONAL MATCH (e)-[r:CO_OCCURRED_WITH]-(e2:Entity) "
                "RETURN e, r, e2 LIMIT 200"
            )
            records = await neo4j_client.run_query(cypher_query)
            
            nodes_map = {}
            edges = []
            
            # Simple conversion to D3-friendly structure
            for record in records:
                e_node = record.get("e")
                if e_node:
                    uid = e_node.get("uid")
                    if uid not in nodes_map:
                        nodes_map[uid] = {
                            "id": uid,
                            "label": e_node.get("value"),
                            "type": e_node.get("type"),
                            "risk_score": e_node.get("risk_score", 50.0),
                            "group": 0 # Louvain component fallback
                        }
                
                e2_node = record.get("e2")
                r_rel = record.get("r")
                if e_node and e2_node and r_rel:
                    uid1 = e_node.get("uid")
                    uid2 = e2_node.get("uid")
                    edges.append({
                        "source": uid1,
                        "target": uid2,
                        "type": "CO_OCCURRED_WITH",
                        "weight": float(r_rel.get("weight", 1.0))
                    })
            
            # Run local clustering over Neo4j nodes to determine community groups
            nodes_list = list(nodes_map.values())
            communities = await asyncio.to_thread(calculate_local_communities, nodes_list, edges)
            for node in nodes_list:
                node["group"] = communities.get(node["id"], 0)
                
            return {
                "engine": "neo4j",
                "nodes": nodes_list,
                "edges": edges
            }
        except Exception as e:
            logger.warning(f"Neo4j query failed (falling back to SQL): {str(e)}")

    # 2. SQL Fallback Mode (100% Free / Resilient)
    try:
        # Fetch entities
        entities_result = await db.execute(select(Entity))
        entities = entities_result.scalars().all()
        
        # Fetch relationships
        relationships_result = await db.execute(select(Relationship))
        relationships = relationships_result.scalars().all()
        
        nodes_list = []
        for ent in entities:
            nodes_list.append({
                "id": str(ent.id),
                "label": ent.raw_value,
                "type": ent.type,
                "risk_score": float(ent.risk_score),
                "group": 0
            })
            
        edges_list = []
        for rel in relationships:
            edges_list.append({
                "source": str(rel.entity_id_a),
                "target": str(rel.entity_id_b),
                "type": rel.relationship_type,
                "weight": float(rel.strength)
            })
            
        # Run Connected Components search to partition nodes into community rings
        communities = await asyncio.to_thread(calculate_local_communities, nodes_list, edges_list)
        for node in nodes_list:
            node["group"] = communities.get(node["id"], 0)
            
        return {
            "engine": "sqlite_fallback",
            "nodes": nodes_list,
            "edges": edges_list
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch graph data: {str(e)}"
        )


# --- 8.1: GET /rings - Fraud Ring Detection ---

@router.get("/rings", status_code=status.HTTP_200_OK)
async def get_fraud_rings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Detect fraud rings by computing connected communities and returning
    those with 3+ members.
    """
    try:
        # Fetch all entities
        entities_result = await db.execute(select(Entity))
        entities = entities_result.scalars().all()

        # Fetch all relationships
        relationships_result = await db.execute(select(Relationship))
        relationships = relationships_result.scalars().all()

        nodes_list = []
        for ent in entities:
            nodes_list.append({
                "id": str(ent.id),
                "type": ent.type,
                "value": ent.raw_value,
                "risk_score": float(ent.risk_score)
            })

        edges_list = []
        for rel in relationships:
            edges_list.append({
                "source": str(rel.entity_id_a),
                "target": str(rel.entity_id_b),
                "type": rel.relationship_type,
                "weight": float(rel.strength)
            })

        # Run community detection
        communities = await asyncio.to_thread(calculate_local_communities, nodes_list, edges_list)

        # Group nodes by community ID
        community_groups: Dict[int, List[Dict[str, Any]]] = {}
        for node in nodes_list:
            community_id = communities.get(node["id"], 0)
            if community_id not in community_groups:
                community_groups[community_id] = []
            community_groups[community_id].append(node)

        # Filter communities with 3+ members
        rings = []
        for ring_id, members in community_groups.items():
            if len(members) >= 3:
                aggregate_risk = sum(m["risk_score"] for m in members) / len(members)
                rings.append({
                    "ring_id": ring_id,
                    "member_count": len(members),
                    "aggregate_risk": round(aggregate_risk, 2),
                    "entities": [
                        {
                            "id": m["id"],
                            "type": m["type"],
                            "value": m["value"],
                            "risk_score": m["risk_score"]
                        }
                        for m in members
                    ]
                })

        return rings

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute fraud rings: {str(e)}"
        )


# --- 8.2: GET /entity/{entity_id}/subgraph - Entity Subgraph ---

async def _get_entity_subgraph(entity_id: str, depth: int, db: AsyncSession) -> Dict[str, Any]:
    """
    BFS traversal from entity_id through Relationship table up to N hops.
    Returns {"nodes": [...], "edges": [...]}.
    """
    visited_nodes = set()
    visited_edges = set()
    nodes = []
    edges = []

    # Start BFS from entity_id
    current_layer = {entity_id}
    visited_nodes.add(entity_id)

    for _ in range(depth):
        if not current_layer:
            break

        next_layer = set()
        for node_id in current_layer:
            try:
                node_uuid = uuid.UUID(node_id)
            except ValueError:
                continue

            # Get relationships where this entity is on either side
            result_a = await db.execute(
                select(Relationship).where(Relationship.entity_id_a == node_uuid)
            )
            rels_a = result_a.scalars().all()

            result_b = await db.execute(
                select(Relationship).where(Relationship.entity_id_b == node_uuid)
            )
            rels_b = result_b.scalars().all()

            for rel in rels_a:
                neighbor_id = str(rel.entity_id_b)
                edge_key = (str(rel.entity_id_a), neighbor_id, rel.relationship_type)
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    edges.append({
                        "source": str(rel.entity_id_a),
                        "target": neighbor_id,
                        "type": rel.relationship_type,
                        "weight": float(rel.strength)
                    })
                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    next_layer.add(neighbor_id)

            for rel in rels_b:
                neighbor_id = str(rel.entity_id_a)
                edge_key = (neighbor_id, str(rel.entity_id_b), rel.relationship_type)
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    edges.append({
                        "source": neighbor_id,
                        "target": str(rel.entity_id_b),
                        "type": rel.relationship_type,
                        "weight": float(rel.strength)
                    })
                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    next_layer.add(neighbor_id)

        current_layer = next_layer

    # Fetch entity details for all visited nodes
    for node_id in visited_nodes:
        try:
            node_uuid = uuid.UUID(node_id)
        except ValueError:
            continue
        result = await db.execute(select(Entity).where(Entity.id == node_uuid))
        entity = result.scalar_one_or_none()
        if entity:
            nodes.append({
                "id": str(entity.id),
                "type": entity.type,
                "value": entity.raw_value,
                "risk_score": float(entity.risk_score)
            })

    return {"nodes": nodes, "edges": edges}


@router.get("/entity/{entity_id}/subgraph", status_code=status.HTTP_200_OK)
async def get_entity_subgraph(
    entity_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Returns the subgraph around an entity up to N hops (1-3).
    Uses iterative BFS through the Relationship table.
    """
    # Validate entity exists
    try:
        entity_uuid = uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity_id format"
        )

    result = await db.execute(select(Entity).where(Entity.id == entity_uuid))
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )

    try:
        subgraph = await _get_entity_subgraph(entity_id, depth, db)
        return subgraph
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch entity subgraph: {str(e)}"
        )


# --- 8.3: GET /correlate - Report Correlation ---

@router.get("/correlate", status_code=status.HTTP_200_OK)
async def correlate_report(
    report_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Find all reports that share entities with the given report.
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report_id format"
        )

    # Verify the report exists
    report_result = await db.execute(select(Report).where(Report.id == report_uuid))
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    try:
        # Find all entities linked to this report
        re_result = await db.execute(
            select(ReportEntity).where(ReportEntity.report_id == report_uuid)
        )
        report_entities = re_result.scalars().all()
        entity_ids = [re.entity_id for re in report_entities]

        if not entity_ids:
            return []

        # Find all other reports that share those entities
        correlated_reports: Dict[str, int] = {}  # report_id -> shared_entity_count
        for entity_id in entity_ids:
            other_re_result = await db.execute(
                select(ReportEntity).where(
                    ReportEntity.entity_id == entity_id,
                    ReportEntity.report_id != report_uuid
                )
            )
            other_report_entities = other_re_result.scalars().all()
            for ore in other_report_entities:
                rid = str(ore.report_id)
                correlated_reports[rid] = correlated_reports.get(rid, 0) + 1

        # Fetch report details for correlated reports
        results = []
        for rid_str, shared_count in correlated_reports.items():
            rid_uuid = uuid.UUID(rid_str)
            r_result = await db.execute(select(Report).where(Report.id == rid_uuid))
            corr_report = r_result.scalar_one_or_none()
            if corr_report:
                results.append({
                    "id": str(corr_report.id),
                    "source_type": corr_report.source_type,
                    "status": corr_report.status,
                    "shared_entities": shared_count,
                    "created_at": corr_report.created_at.isoformat() if corr_report.created_at else None
                })

        # Sort by shared entities descending
        results.sort(key=lambda x: x["shared_entities"], reverse=True)
        return results

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to correlate reports: {str(e)}"
        )


# --- 8.4: POST /intelligence-package - Ring Intelligence Package ---

class RingPackageRequest(BaseModel):
    ring_id: int


@router.post("/intelligence-package", status_code=status.HTTP_200_OK)
async def generate_ring_intelligence_package(
    payload: RingPackageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Generate a PDF intelligence package for a given fraud ring.
    """
    try:
        # Fetch all entities and relationships to compute communities
        entities_result = await db.execute(select(Entity))
        entities = entities_result.scalars().all()

        relationships_result = await db.execute(select(Relationship))
        relationships = relationships_result.scalars().all()

        nodes_list = []
        entity_map = {}
        for ent in entities:
            node = {
                "id": str(ent.id),
                "type": ent.type,
                "value": ent.raw_value,
                "risk_score": float(ent.risk_score)
            }
            nodes_list.append(node)
            entity_map[str(ent.id)] = ent

        edges_list = []
        for rel in relationships:
            edges_list.append({
                "source": str(rel.entity_id_a),
                "target": str(rel.entity_id_b),
                "type": rel.relationship_type,
                "weight": float(rel.strength)
            })

        # Compute communities
        communities = await asyncio.to_thread(calculate_local_communities, nodes_list, edges_list)

        # Find entities in the requested ring
        ring_entity_ids = [
            node_id for node_id, community_id in communities.items()
            if community_id == payload.ring_id
        ]

        if not ring_entity_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ring with id {payload.ring_id} not found or has no members"
            )

        # Get all reports linked to those entities
        linked_report_ids = set()
        for eid_str in ring_entity_ids:
            try:
                eid_uuid = uuid.UUID(eid_str)
            except ValueError:
                continue
            re_result = await db.execute(
                select(ReportEntity).where(ReportEntity.entity_id == eid_uuid)
            )
            report_entities = re_result.scalars().all()
            for re_item in report_entities:
                linked_report_ids.add(re_item.report_id)

        # Build ring summary data for PDF
        ring_entities = []
        for eid_str in ring_entity_ids:
            ent = entity_map.get(eid_str)
            if ent:
                ring_entities.append({
                    "type": ent.type,
                    "raw_value": ent.raw_value,
                    "risk_score": float(ent.risk_score)
                })

        aggregate_risk = (
            sum(e["risk_score"] for e in ring_entities) / len(ring_entities)
            if ring_entities else 0.0
        )

        # Build report data for PDF generation
        report_data = {
            "id": f"RING-{payload.ring_id:04d}",
            "source_type": "intelligence_package",
            "detected_language": "en",
            "created_at": "Generated on demand",
            "status": "ring_analysis",
            "threat_score": round(aggregate_risk),
            "severity_band": (
                "critical" if aggregate_risk >= 75 else
                "high" if aggregate_risk >= 50 else
                "moderate" if aggregate_risk >= 25 else "low"
            ),
            "scam_category": "Fraud Ring Detection",
            "cleaned_text": (
                f"Intelligence Package for Fraud Ring #{payload.ring_id}\n"
                f"Members: {len(ring_entity_ids)} entities\n"
                f"Linked Reports: {len(linked_report_ids)}\n"
                f"Aggregate Risk Score: {aggregate_risk:.2f}"
            ),
            "entities": ring_entities
        }

        # Generate PDF
        pdf_buffer = generate_report_pdf(report_data)

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ring_{payload.ring_id}_intelligence.pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate intelligence package: {str(e)}"
        )


# --- 8.5: GET /export - Entity Subgraph Export ---

@router.get("/export", status_code=status.HTTP_200_OK)
async def export_entity_subgraph(
    entity_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Export an entity's details, its subgraph (depth=2), and all linked report IDs as JSON.
    """
    # Validate entity
    try:
        entity_uuid = uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity_id format"
        )

    result = await db.execute(select(Entity).where(Entity.id == entity_uuid))
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )

    try:
        # Get subgraph at depth=2
        subgraph = await _get_entity_subgraph(entity_id, depth=2, db=db)

        # Get all linked report IDs
        re_result = await db.execute(
            select(ReportEntity).where(ReportEntity.entity_id == entity_uuid)
        )
        report_entities = re_result.scalars().all()
        linked_reports = [str(re.report_id) for re in report_entities]

        return {
            "entity": {
                "id": str(entity.id),
                "type": entity.type,
                "raw_value": entity.raw_value,
                "normalized_value": entity.normalized_value,
                "risk_score": float(entity.risk_score),
                "risk_tier": entity.risk_tier,
                "occurrence_count": entity.occurrence_count,
                "first_seen_at": entity.first_seen_at.isoformat() if entity.first_seen_at else None,
                "last_seen_at": entity.last_seen_at.isoformat() if entity.last_seen_at else None
            },
            "subgraph": subgraph,
            "linked_reports": linked_reports
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export entity subgraph: {str(e)}"
        )
