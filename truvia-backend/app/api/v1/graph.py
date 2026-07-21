"""Threat Intelligence Engine API (App Flow §7, Backend_Schema §9).

All data is computed from the authoritative Postgres store (entities,
relationships, report_entities, threat_scores, fraud_rings). Neo4j, when
online, is a derived correlation index; these endpoints do not hard-depend on
it, so the engine works from a fresh clone with or without Neo4j running.

Every route is restricted to officer/admin via deps.require_officer.
"""
import hashlib
import json
import logging
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pdf import generate_report_pdf
from app.data.postgres_client import get_db
from app.models.case import Case, CaseReport, IntelligencePackage
from app.models.report import Entity, Relationship, Report, ReportEntity, ThreatScore
from app.models.ring import FraudRing, FraudRingMember

router = APIRouter()
logger = logging.getLogger("truvia.api.graph")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _risk_tier(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "moderate"
    return "low"


def _entity_node(e: Entity, group: int = 0) -> Dict[str, Any]:
    return {
        "id": str(e.id),
        "label": e.raw_value,
        "value": e.raw_value,
        "normalized_value": e.normalized_value,
        "type": e.type,
        "risk_score": float(e.risk_score),
        "risk_tier": e.risk_tier,
        "occurrence_count": e.occurrence_count,
        "group": group,
    }


async def _get_entity_or_404(entity_id: str, db: AsyncSession) -> Entity:
    try:
        entity_uuid = uuid.UUID(entity_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid entity id format")
    entity = (await db.execute(select(Entity).where(Entity.id == entity_uuid))).scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


async def _bfs_subgraph(entity_id: str, depth: int, db: AsyncSession) -> Dict[str, Any]:
    """Breadth-first traversal over the Postgres relationships table up to N hops."""
    visited_nodes = {entity_id}
    visited_edges: set = set()
    edges: List[Dict[str, Any]] = []
    current_layer = {entity_id}

    for _ in range(depth):
        if not current_layer:
            break
        layer_uuids = []
        for nid in current_layer:
            try:
                layer_uuids.append(uuid.UUID(nid))
            except (ValueError, TypeError):
                continue
        if not layer_uuids:
            break
        rels = (await db.execute(
            select(Relationship).where(
                or_(Relationship.entity_id_a.in_(layer_uuids),
                    Relationship.entity_id_b.in_(layer_uuids))
            )
        )).scalars().all()
        next_layer = set()
        for rel in rels:
            a, b = str(rel.entity_id_a), str(rel.entity_id_b)
            ekey = (a, b, rel.relationship_type)
            if ekey not in visited_edges:
                visited_edges.add(ekey)
                edges.append({
                    "source": a, "target": b,
                    "type": rel.relationship_type, "weight": float(rel.strength),
                })
            for neighbor in (a, b):
                if neighbor not in visited_nodes:
                    visited_nodes.add(neighbor)
                    next_layer.add(neighbor)
        current_layer = next_layer

    node_uuids = []
    for nid in visited_nodes:
        try:
            node_uuids.append(uuid.UUID(nid))
        except (ValueError, TypeError):
            continue
    entities = (await db.execute(select(Entity).where(Entity.id.in_(node_uuids)))).scalars().all()
    nodes = [_entity_node(e) for e in entities]
    return {"nodes": nodes, "edges": edges}


async def _entity_ring(entity_id: uuid.UUID, db: AsyncSession) -> Optional[FraudRing]:
    """Return the FraudRing this entity belongs to, if any."""
    member = (await db.execute(
        select(FraudRingMember).where(FraudRingMember.entity_id == entity_id)
    )).scalars().first()
    if not member:
        return None
    return (await db.execute(
        select(FraudRing).where(FraudRing.id == member.ring_id)
    )).scalar_one_or_none()


# --------------------------------------------------------------------------- #
# §7.1 Graph Home — capped top-N cluster overview
# --------------------------------------------------------------------------- #
@router.get("/overview", status_code=status.HTTP_200_OK)
async def get_graph_overview(
    top_n_clusters: int = Query(default=8, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """Zoomed-out, cluster-level snapshot capped to the top-N highest-risk rings.

    Caps the node/edge payload (PRD performance-risk mitigation) by only
    returning members of the top-N detected clusters plus their internal edges.
    Returns empty nodes/edges when the graph is still building (fresh system).
    """
    rings = (await db.execute(
        select(FraudRing).order_by(
            FraudRing.aggregate_risk_score.desc(), FraudRing.member_count.desc()
        ).limit(top_n_clusters)
    )).scalars().all()

    nodes: List[Dict[str, Any]] = []
    node_ids: set = set()
    clusters_meta: List[Dict[str, Any]] = []

    # Batch-load members for ALL top-N rings in a single query (was an N+1:
    # one query per ring). Group in Python, preserving the original semantics
    # where a shared entity is assigned to the first (highest-risk) ring's group.
    from collections import defaultdict as _defaultdict
    members_by_ring: Dict[Any, List[Entity]] = _defaultdict(list)
    if rings:
        ring_ids = [ring.id for ring in rings]
        member_rows = (await db.execute(
            select(Entity, FraudRingMember.ring_id)
            .join(FraudRingMember, FraudRingMember.entity_id == Entity.id)
            .where(FraudRingMember.ring_id.in_(ring_ids))
        )).all()
        for entity, ring_id in member_rows:
            members_by_ring[ring_id].append(entity)

    for group_idx, ring in enumerate(rings):
        clusters_meta.append({
            "ring_id": ring.neo4j_ring_id,
            "group": group_idx,
            "member_count": ring.member_count,
            "risk_tier": ring.risk_tier,
            "aggregate_risk_score": float(ring.aggregate_risk_score),
            "dominant_category": ring.dominant_category,
        })
        for e in members_by_ring.get(ring.id, []):
            if str(e.id) not in node_ids:
                node_ids.add(str(e.id))
                nodes.append(_entity_node(e, group=group_idx))

    edges: List[Dict[str, Any]] = []
    if node_ids:
        node_uuids = [uuid.UUID(nid) for nid in node_ids]
        rels = (await db.execute(
            select(Relationship).where(
                Relationship.entity_id_a.in_(node_uuids),
                Relationship.entity_id_b.in_(node_uuids),
            )
        )).scalars().all()
        for rel in rels:
            edges.append({
                "source": str(rel.entity_id_a), "target": str(rel.entity_id_b),
                "type": rel.relationship_type, "weight": float(rel.strength),
            })

    # Top-N high-risk entity sidebar list (independent of ring membership).
    top_entities_rows = (await db.execute(
        select(Entity).order_by(Entity.risk_score.desc(), Entity.occurrence_count.desc()).limit(10)
    )).scalars().all()
    top_entities = [_entity_node(e) for e in top_entities_rows]

    algorithm = rings[0].algorithm if rings else None
    return {
        "engine": "postgres",              # authoritative source served
        "algorithm": algorithm,            # gds_louvain | python_louvain | None
        "clusters": clusters_meta,
        "cluster_count": len(clusters_meta),
        "nodes": nodes,
        "edges": edges,
        "top_entities": top_entities,
    }


# --------------------------------------------------------------------------- #
# §7.1 Entity search autocomplete
# --------------------------------------------------------------------------- #
@router.get("/search", status_code=status.HTTP_200_OK)
async def search_entities(
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(default=10, ge=1, le=25),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """Entity-lookup autocomplete for the Graph Home search bar."""
    pattern = f"%{q.strip()}%"
    rows = (await db.execute(
        select(Entity).where(
            or_(Entity.normalized_value.ilike(pattern), Entity.raw_value.ilike(pattern))
        ).order_by(Entity.risk_score.desc()).limit(limit)
    )).scalars().all()
    return [{
        "id": str(e.id), "value": e.raw_value, "normalized_value": e.normalized_value,
        "type": e.type, "risk_score": float(e.risk_score), "risk_tier": e.risk_tier,
    } for e in rows]


# --------------------------------------------------------------------------- #
# §7.3 Fraud Ring list
# --------------------------------------------------------------------------- #
@router.get("/rings", status_code=status.HTTP_200_OK)
async def list_rings(
    limit: int = Query(default=50, ge=1, le=200),
    sort: str = Query(default="risk", pattern="^(size|recency|risk)$"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """Ranked list of detected fraud rings with real size/complaint/activity/risk."""
    order = {
        "size": (FraudRing.member_count.desc(),),
        "recency": (FraudRing.last_activity_at.desc().nullslast(),),
        "risk": (FraudRing.aggregate_risk_score.desc(), FraudRing.member_count.desc()),
    }[sort]
    rings = (await db.execute(select(FraudRing).order_by(*order).limit(limit))).scalars().all()
    return [_ring_summary(r) for r in rings]


def _ring_summary(r: FraudRing) -> Dict[str, Any]:
    return {
        "id": r.neo4j_ring_id,
        "member_count": r.member_count,
        "complaint_count": r.complaint_count,
        "dominant_category": r.dominant_category,
        "aggregate_risk_score": float(r.aggregate_risk_score),
        "risk_tier": r.risk_tier,
        "algorithm": r.algorithm,
        "first_activity_at": r.first_activity_at.isoformat() if r.first_activity_at else None,
        "last_activity_at": r.last_activity_at.isoformat() if r.last_activity_at else None,
        "detected_at": r.detected_at.isoformat() if r.detected_at else None,
    }


async def _get_ring_or_404(ring_id: str, db: AsyncSession) -> FraudRing:
    ring = (await db.execute(
        select(FraudRing).where(FraudRing.neo4j_ring_id == ring_id)
    )).scalar_one_or_none()
    if not ring:
        raise HTTPException(status_code=404, detail="Fraud ring not found")
    return ring


async def _ring_member_entities(ring: FraudRing, db: AsyncSession) -> List[Entity]:
    return (await db.execute(
        select(Entity).join(FraudRingMember, FraudRingMember.entity_id == Entity.id)
        .where(FraudRingMember.ring_id == ring.id)
    )).scalars().all()


async def _ring_correlated_reports(member_ids: List[uuid.UUID], db: AsyncSession) -> List[Dict[str, Any]]:
    if not member_ids:
        return []
    links = (await db.execute(
        select(ReportEntity).where(ReportEntity.entity_id.in_(member_ids))
    )).scalars().all()
    report_ids = list({lr.report_id for lr in links})
    if not report_ids:
        return []
    reports = (await db.execute(select(Report).where(Report.id.in_(report_ids)))).scalars().all()
    scores = (await db.execute(
        select(ThreatScore).where(
            ThreatScore.report_id.in_(report_ids), ThreatScore.is_current == True,  # noqa: E712
        )
    )).scalars().all()
    score_by_report = {str(s.report_id): s for s in scores}
    out = []
    for r in reports:
        s = score_by_report.get(str(r.id))
        out.append({
            "id": str(r.id),
            "source_type": r.source_type,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "threat_score": int(s.threat_score) if s else None,
            "severity_band": s.severity_band if s else None,
            "scam_category": s.scam_category if s else None,
        })
    out.sort(key=lambda x: (x["threat_score"] or 0), reverse=True)
    return out


@router.get("/rings/{ring_id}", status_code=status.HTTP_200_OK)
async def get_ring_detail(
    ring_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """Full ring-scoped subgraph, member list, and correlated complaints."""
    ring = await _get_ring_or_404(ring_id, db)
    members = await _ring_member_entities(ring, db)
    member_uuids = [e.id for e in members]

    # Ring-scoped subgraph: nodes = members, edges = relationships among members.
    nodes = [_entity_node(e) for e in members]
    edges = []
    if member_uuids:
        rels = (await db.execute(
            select(Relationship).where(
                Relationship.entity_id_a.in_(member_uuids),
                Relationship.entity_id_b.in_(member_uuids),
            )
        )).scalars().all()
        edges = [{
            "source": str(rel.entity_id_a), "target": str(rel.entity_id_b),
            "type": rel.relationship_type, "weight": float(rel.strength),
        } for rel in rels]

    complaints = await _ring_correlated_reports(member_uuids, db)
    return {
        **_ring_summary(ring),
        "members": nodes,
        "subgraph": {"nodes": nodes, "edges": edges},
        "complaints": complaints,
    }


# --------------------------------------------------------------------------- #
# §7.2 Entity Explorer
# --------------------------------------------------------------------------- #
@router.get("/entity/{entity_id}", status_code=status.HTTP_200_OK)
async def get_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """Entity header + overview: identity, risk, connection/complaint counts, ring membership."""
    entity = await _get_entity_or_404(entity_id, db)

    rels = (await db.execute(
        select(Relationship).where(
            or_(Relationship.entity_id_a == entity.id, Relationship.entity_id_b == entity.id)
        )
    )).scalars().all()
    connected_ids = set()
    for rel in rels:
        connected_ids.add(rel.entity_id_a if rel.entity_id_a != entity.id else rel.entity_id_b)
    connected_ids.discard(entity.id)

    complaint_count = (await db.execute(
        select(func.count(func.distinct(ReportEntity.report_id)))
        .where(ReportEntity.entity_id == entity.id)
    )).scalar() or 0

    ring = await _entity_ring(entity.id, db)

    complaints = await _ring_correlated_reports([entity.id], db)

    return {
        "id": str(entity.id),
        "type": entity.type,
        "raw_value": entity.raw_value,
        "value": entity.raw_value,
        "normalized_value": entity.normalized_value,
        "risk_score": float(entity.risk_score),
        "risk_tier": entity.risk_tier,
        "occurrence_count": entity.occurrence_count,
        "connection_count": len(connected_ids),
        "complaint_count": complaint_count,
        "complaints": complaints,
        "first_seen_at": entity.first_seen_at.isoformat() if entity.first_seen_at else None,
        "last_seen_at": entity.last_seen_at.isoformat() if entity.last_seen_at else None,
        "ring": _ring_summary(ring) if ring else None,
        "in_ring": ring is not None,
    }


@router.get("/entity/{entity_id}/subgraph", status_code=status.HTTP_200_OK)
async def get_entity_subgraph(
    entity_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """N-hop (1-3) neighbourhood subgraph around the entity."""
    await _get_entity_or_404(entity_id, db)
    return await _bfs_subgraph(entity_id, depth, db)


@router.get("/entity/{entity_id}/risk-score", status_code=status.HTTP_200_OK)
async def get_entity_risk_score(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """Computed risk score, contributing factors, and risk history (sparkline)."""
    entity = await _get_entity_or_404(entity_id, db)

    # Reports touching this entity, with current threat scores, chronological.
    links = (await db.execute(
        select(ReportEntity).where(ReportEntity.entity_id == entity.id)
    )).scalars().all()
    report_ids = list({lr.report_id for lr in links})
    history: List[Dict[str, Any]] = []
    high_sev = 0
    categories: List[str] = []
    if report_ids:
        reports = (await db.execute(select(Report).where(Report.id.in_(report_ids)))).scalars().all()
        scores = (await db.execute(
            select(ThreatScore).where(
                ThreatScore.report_id.in_(report_ids), ThreatScore.is_current == True,  # noqa: E712
            )
        )).scalars().all()
        score_by_report = {str(s.report_id): s for s in scores}
        for r in sorted(reports, key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc)):
            s = score_by_report.get(str(r.id))
            if not s:
                continue
            if s.severity_band in ("high", "critical"):
                high_sev += 1
            if s.scam_category:
                categories.append(s.scam_category)
            history.append({
                "date": r.created_at.isoformat() if r.created_at else None,
                "score": int(s.threat_score),
                "category": s.scam_category,
            })

    rels_count = (await db.execute(
        select(func.count(Relationship.id)).where(
            or_(Relationship.entity_id_a == entity.id, Relationship.entity_id_b == entity.id)
        )
    )).scalar() or 0
    ring = await _entity_ring(entity.id, db)

    factors: List[Dict[str, Any]] = []
    factors.append({"factor": "Report appearances", "detail": f"Seen in {entity.occurrence_count} report(s)", "weight": entity.occurrence_count})
    factors.append({"factor": "Network connections", "detail": f"Directly linked to {rels_count} relationship edge(s)", "weight": rels_count})
    if high_sev:
        factors.append({"factor": "High-severity complaints", "detail": f"{high_sev} linked complaint(s) scored high/critical", "weight": high_sev})
    if categories:
        top_cat, cnt = Counter(categories).most_common(1)[0]
        factors.append({"factor": "Dominant scam category", "detail": f"{top_cat} ({cnt} complaint(s))", "weight": cnt})
    if ring:
        factors.append({"factor": "Fraud ring membership", "detail": f"Member of {ring.neo4j_ring_id} ({ring.risk_tier} tier, {ring.member_count} entities)", "weight": ring.member_count})

    return {
        "id": str(entity.id),
        "current_score": float(entity.risk_score),
        "risk_tier": entity.risk_tier,
        "factors": factors,
        "history": history,
    }


# --------------------------------------------------------------------------- #
# §7.2 / §7.4 Intelligence Package (persisted to intelligence_packages)
# --------------------------------------------------------------------------- #
class PackageRequest(BaseModel):
    ring_id: Optional[str] = None
    entity_id: Optional[str] = None


async def _find_or_create_ring_case(ring: FraudRing, report_ids: List[uuid.UUID],
                                    db: AsyncSession) -> Case:
    case = (await db.execute(
        select(Case).where(Case.neo4j_ring_id == ring.neo4j_ring_id)
    )).scalar_one_or_none()
    if case:
        return case
    priority = {"critical": "urgent", "high": "high", "moderate": "medium", "low": "low"}.get(ring.risk_tier, "medium")
    suffix = ring.neo4j_ring_id.replace("ring-", "").upper()
    case = Case(
        case_number=f"RING-{datetime.now(timezone.utc).year}-{suffix}",
        case_type="ring_level",
        status="open",
        priority=priority,
        neo4j_ring_id=ring.neo4j_ring_id,
        ai_summary=(
            f"Auto-created ring investigation for {ring.neo4j_ring_id}: "
            f"{ring.member_count} correlated entities, {ring.complaint_count} complaints, "
            f"dominant category {ring.dominant_category or 'n/a'}."
        ),
    )
    db.add(case)
    await db.flush()
    # Link correlated reports (best-effort; ignore duplicates).
    existing = set()
    for rid in report_ids:
        if rid in existing:
            continue
        existing.add(rid)
        db.add(CaseReport(case_id=case.id, report_id=rid, linked_reason=f"ring correlation: {ring.neo4j_ring_id}"))
    return case


async def _assemble_ring_package_json(ring: FraudRing, focus_entity_id: Optional[str],
                                      db: AsyncSession) -> Dict[str, Any]:
    members = await _ring_member_entities(ring, db)
    member_uuids = [e.id for e in members]
    complaints = await _ring_correlated_reports(member_uuids, db)
    return {
        "package_kind": "entity" if focus_entity_id else "ring",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ring": _ring_summary(ring),
        "focus_entity_id": focus_entity_id,
        "entities": [{
            "id": str(e.id), "type": e.type, "value": e.raw_value,
            "normalized_value": e.normalized_value,
            "risk_score": float(e.risk_score), "risk_tier": e.risk_tier,
            "occurrence_count": e.occurrence_count,
        } for e in members],
        "correlated_complaints": complaints,
        "complaint_count": len(complaints),
        "aggregate_risk_score": float(ring.aggregate_risk_score),
        "dominant_category": ring.dominant_category,
    }


@router.post("/intelligence-package", status_code=status.HTTP_201_CREATED)
async def generate_intelligence_package(
    payload: PackageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """Assemble and persist a court-ready intelligence package (ring or entity focus).

    Entity-focused packages are only permitted when the entity is part of a
    detected ring (App Flow §7.2). Both are stored as ring_level packages tied
    to the ring's case, immutably (versioned).
    """
    if not payload.ring_id and not payload.entity_id:
        raise HTTPException(status_code=400, detail="Provide ring_id or entity_id")

    focus_entity_id = None
    if payload.entity_id:
        entity = await _get_entity_or_404(payload.entity_id, db)
        ring = await _entity_ring(entity.id, db)
        if not ring:
            raise HTTPException(
                status_code=409,
                detail="Entity is not part of a detected fraud ring; package generation is unavailable.",
            )
        focus_entity_id = str(entity.id)
    else:
        ring = await _get_ring_or_404(payload.ring_id, db)

    package_json = await _assemble_ring_package_json(ring, focus_entity_id, db)
    report_ids = [uuid.UUID(c["id"]) for c in package_json["correlated_complaints"]]

    case = await _find_or_create_ring_case(ring, report_ids, db)

    # Immutable + versioned: next version for this case.
    prev = (await db.execute(
        select(func.max(IntelligencePackage.version)).where(IntelligencePackage.case_id == case.id)
    )).scalar()
    version = (prev or 0) + 1

    content_hash = hashlib.sha256(
        json.dumps(package_json, sort_keys=True, default=str).encode()
    ).hexdigest()

    pkg = IntelligencePackage(
        case_id=case.id,
        package_json=package_json,
        package_type="ring_level",
        content_hash=content_hash,
        version=version,
        generated_by=current_user.id,
    )
    db.add(pkg)
    await db.commit()
    await db.refresh(pkg)

    return {
        "id": str(pkg.id),
        "case_id": str(case.id),
        "case_number": case.case_number,
        "ring_id": ring.neo4j_ring_id,
        "package_type": pkg.package_type,
        "version": pkg.version,
        "content_hash": pkg.content_hash,
        "generated_at": pkg.generated_at.isoformat() if pkg.generated_at else None,
        "entity_count": len(package_json["entities"]),
        "complaint_count": package_json["complaint_count"],
        "download_url": f"/graph/intelligence-package/{pkg.id}/download",
    }


@router.get("/intelligence-package/{package_id}/download", status_code=status.HTTP_200_OK)
async def download_intelligence_package(
    package_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """Render the persisted package snapshot as a downloadable PDF."""
    try:
        pkg_uuid = uuid.UUID(package_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid package id")
    pkg = (await db.execute(
        select(IntelligencePackage).where(IntelligencePackage.id == pkg_uuid)
    )).scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    pj = pkg.package_json
    ring = pj.get("ring", {})
    lines = [
        f"Intelligence Package (v{pkg.version})",
        f"Ring: {ring.get('id')}  |  Members: {ring.get('member_count')}  |  Complaints: {pj.get('complaint_count')}",
        f"Dominant category: {pj.get('dominant_category') or 'n/a'}",
        f"Aggregate risk: {pj.get('aggregate_risk_score')}  ({ring.get('risk_tier')})",
        f"Content hash (SHA-256): {pkg.content_hash}",
        "",
        "Member entities:",
    ]
    for e in pj.get("entities", []):
        lines.append(f"  - [{e['type']}] {e['value']}  (risk {e['risk_score']}, {e['risk_tier']})")
    lines.append("")
    lines.append("Correlated complaints:")
    for c in pj.get("correlated_complaints", []):
        lines.append(f"  - {c['id']}  {c.get('scam_category') or ''}  score={c.get('threat_score')}  {c.get('created_at') or ''}")

    report_data = {
        "id": f"PKG-{str(pkg.id)[:8]}",
        "source_type": "intelligence_package",
        "detected_language": "en",
        "created_at": pkg.generated_at.isoformat() if pkg.generated_at else "",
        "status": "ring_analysis",
        "threat_score": round(float(pj.get("aggregate_risk_score") or 0)),
        "severity_band": ring.get("risk_tier", "low"),
        "scam_category": pj.get("dominant_category") or "Fraud Ring",
        "cleaned_text": "\n".join(lines),
        "entities": [{
            "type": e["type"], "raw_value": e["value"], "risk_score": e["risk_score"],
        } for e in pj.get("entities", [])],
    }
    pdf_buffer = generate_report_pdf(report_data)
    return StreamingResponse(
        pdf_buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=intelligence_package_{pkg.id}.pdf"},
    )


# --------------------------------------------------------------------------- #
# §7.4 Export Evidence — ring subgraph + complaint IDs bundle
# --------------------------------------------------------------------------- #
@router.get("/rings/{ring_id}/export", status_code=status.HTTP_200_OK)
async def export_ring_evidence(
    ring_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """Downloadable JSON bundle: ring subgraph + correlated complaint IDs."""
    ring = await _get_ring_or_404(ring_id, db)
    members = await _ring_member_entities(ring, db)
    member_uuids = [e.id for e in members]
    edges = []
    if member_uuids:
        rels = (await db.execute(
            select(Relationship).where(
                Relationship.entity_id_a.in_(member_uuids),
                Relationship.entity_id_b.in_(member_uuids),
            )
        )).scalars().all()
        edges = [{
            "source": str(rel.entity_id_a), "target": str(rel.entity_id_b),
            "type": rel.relationship_type, "weight": float(rel.strength),
        } for rel in rels]
    complaints = await _ring_correlated_reports(member_uuids, db)

    bundle = {
        "ring": _ring_summary(ring),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by": str(current_user.id),
        "subgraph": {"nodes": [_entity_node(e) for e in members], "edges": edges},
        "complaint_ids": [c["id"] for c in complaints],
        "complaints": complaints,
    }
    payload = json.dumps(bundle, indent=2, default=str).encode()
    import io
    return StreamingResponse(
        io.BytesIO(payload), media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=ring_evidence_{ring.neo4j_ring_id}.json"},
    )
