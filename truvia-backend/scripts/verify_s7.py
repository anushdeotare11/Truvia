"""One-shot Section 7 endpoint verification against real Neon data.
Calls the route handlers directly with a real officer/admin user and a live DB
session (no blocking server). Run:
    .venv\\Scripts\\python.exe -m scripts.verify_s7
"""
import asyncio
import sys

from sqlalchemy import select

from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User
from app.models.ring import FraudRing, FraudRingMember
from app.api.v1 import graph as G


async def main() -> int:
    async with AsyncSessionLocal() as db:
        user = (await db.execute(
            select(User).where(User.role.in_(["officer", "admin"]))
        )).scalars().first()
        if not user:
            print("NO officer/admin user found — cannot verify package generation FK.")
            return 1
        print(f"actor: {user.email} ({user.role})")

        ring = (await db.execute(select(FraudRing).order_by(FraudRing.member_count.desc()))).scalars().first()
        if not ring:
            print("NO rings — run scripts.cluster_rings first.")
            return 1
        member = (await db.execute(
            select(FraudRingMember).where(FraudRingMember.ring_id == ring.id)
        )).scalars().first()
        ring_id = ring.neo4j_ring_id
        entity_id = str(member.entity_id)
        print(f"ring_id={ring_id} entity_id={entity_id}")

        ov = await G.get_graph_overview(top_n_clusters=8, db=db, current_user=user)
        print(f"[overview] clusters={ov['cluster_count']} nodes={len(ov['nodes'])} edges={len(ov['edges'])} top_entities={len(ov['top_entities'])} engine={ov['engine']} algo={ov['algorithm']}")

        rings = await G.list_rings(limit=50, sort="risk", db=db, current_user=user)
        print(f"[rings] count={len(rings)} first={rings[0]['id']} members={rings[0]['member_count']} complaints={rings[0]['complaint_count']} tier={rings[0]['risk_tier']} cat={rings[0]['dominant_category']}")

        rd = await G.get_ring_detail(ring_id=ring_id, db=db, current_user=user)
        print(f"[ring detail] members={len(rd['members'])} subgraph_nodes={len(rd['subgraph']['nodes'])} subgraph_edges={len(rd['subgraph']['edges'])} complaints={len(rd['complaints'])}")

        ent = await G.get_entity(entity_id=entity_id, db=db, current_user=user)
        print(f"[entity] type={ent['type']} value={ent['value']} risk={ent['risk_score']} tier={ent['risk_tier']} conns={ent['connection_count']} complaints={ent['complaint_count']} in_ring={ent['in_ring']}")

        for d in (1, 2, 3):
            sg = await G.get_entity_subgraph(entity_id=entity_id, depth=d, db=db, current_user=user)
            print(f"[subgraph depth={d}] nodes={len(sg['nodes'])} edges={len(sg['edges'])}")

        rs = await G.get_entity_risk_score(entity_id=entity_id, db=db, current_user=user)
        print(f"[risk-score] current={rs['current_score']} tier={rs['risk_tier']} factors={len(rs['factors'])} history_points={len(rs['history'])}")

        se = await G.search_entities(q=ent["value"][:3], limit=10, db=db, current_user=user)
        print(f"[search q='{ent['value'][:3]}'] results={len(se)}")

        from app.api.v1.graph import PackageRequest
        pkg = await G.generate_intelligence_package(PackageRequest(ring_id=ring_id), db=db, current_user=user)
        print(f"[package ring] id={pkg['id']} case={pkg['case_number']} v={pkg['version']} hash={pkg['content_hash'][:12]} entities={pkg['entity_count']} complaints={pkg['complaint_count']}")

        pkg2 = await G.generate_intelligence_package(PackageRequest(entity_id=entity_id), db=db, current_user=user)
        print(f"[package entity] id={pkg2['id']} case={pkg2['case_number']} v={pkg2['version']}")

        dl = await G.download_intelligence_package(package_id=pkg["id"], db=db, current_user=user)
        print(f"[package download] media={dl.media_type}")
        ex = await G.export_ring_evidence(ring_id=ring_id, db=db, current_user=user)
        print(f"[export evidence] media={ex.media_type}")

    print("ALL_S7_ENDPOINTS_OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(asyncio.wait_for(main(), timeout=90)))
    except asyncio.TimeoutError:
        print("TIMEOUT", file=sys.stderr)
        sys.exit(2)
