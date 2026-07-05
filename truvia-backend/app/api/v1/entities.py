from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.data.postgres_client import get_db
from app.api import deps
from app.models.report import Entity, Relationship, ReportEntity, Report
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import uuid

router = APIRouter()



@router.get("/{entity_id}", status_code=status.HTTP_200_OK)
async def get_entity_details(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_user)
):
    try:
        entity_uuid = uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Entity UUID format")
        
    # 1. Fetch Entity
    entity_result = await db.execute(
        select(Entity).where(Entity.id == entity_uuid)
    )
    entity = entity_result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
        
    # 2. Fetch all reports linked to this entity
    reports_result = await db.execute(
        select(Report)
        .join(ReportEntity, ReportEntity.report_id == Report.id)
        .where(ReportEntity.entity_id == entity_uuid)
    )
    reports = reports_result.scalars().all()
    
    # 3. Fetch all relationships (direct connections) for this entity
    relationships_result = await db.execute(
        select(Relationship)
        .where((Relationship.entity_id_a == entity_uuid) | (Relationship.entity_id_b == entity_uuid))
    )
    relationships = relationships_result.scalars().all()
    
    # Get all unique connected entity IDs
    connected_ids = set()
    for rel in relationships:
        if rel.entity_id_a != entity_uuid:
            connected_ids.add(rel.entity_id_a)
        if rel.entity_id_b != entity_uuid:
            connected_ids.add(rel.entity_id_b)
            
    # Fetch connected entities
    connected_entities = []
    if connected_ids:
        conn_result = await db.execute(
            select(Entity).where(Entity.id.in_(list(connected_ids)))
        )
        connected_entities = conn_result.scalars().all()

    # 4. Construct local subgraph
    # Nodes: the center entity and all neighbors
    nodes = [{
        "id": str(entity.id),
        "label": entity.raw_value,
        "type": entity.type,
        "risk_score": float(entity.risk_score),
        "occurrence_count": entity.occurrence_count
    }]
    for ce in connected_entities:
        nodes.append({
            "id": str(ce.id),
            "label": ce.raw_value,
            "type": ce.type,
            "risk_score": float(ce.risk_score),
            "occurrence_count": ce.occurrence_count
        })
        
    # Edges: relationship mappings
    edges = []
    for rel in relationships:
        edges.append({
            "id": str(rel.id),
            "source": str(rel.entity_id_a),
            "target": str(rel.entity_id_b),
            "type": rel.relationship_type,
            "weight": float(rel.strength)
        })

    # Return structured details
    return {
        "id": str(entity.id),
        "raw_value": entity.raw_value,
        "normalized_value": entity.normalized_value,
        "type": entity.type,
        "risk_score": float(entity.risk_score),
        "risk_tier": entity.risk_tier,
        "occurrence_count": entity.occurrence_count,
        "first_seen_at": entity.first_seen_at.isoformat() if entity.first_seen_at else None,
        "last_seen_at": entity.last_seen_at.isoformat() if entity.last_seen_at else None,
        "linked_reports": [{
            "id": str(r.id),
            "source_type": r.source_type,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in reports],
        "subgraph": {
            "nodes": nodes,
            "edges": edges
        }
    }
