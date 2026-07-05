from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.data.postgres_client import get_db
from app.api import deps
from app.models.report import Entity, Relationship
from sqlalchemy import select
from app.data.neo4j_client import neo4j_client
from typing import List, Dict, Any
import logging

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
            communities = calculate_local_communities(nodes_list, edges)
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
        communities = calculate_local_communities(nodes_list, edges_list)
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
