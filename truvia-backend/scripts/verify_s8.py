"""One-shot Section 8 (Admin) verification against real Neon data.
Direct-call of route handlers with a real admin user; exercises user mgmt,
KB ingest + citation chain, and system health. Cleans up test rows.
Run: .venv\\Scripts\\python.exe -m scripts.verify_s8
"""
import asyncio
import sys
import uuid

from sqlalchemy import select, delete

from app.core import metrics
from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User
from app.models.knowledge import KnowledgeBase
from app.models.auth_token import PasswordResetToken
from app.api.v1 import admin as A
from app.agents.knowledge_agent import knowledge_agent


async def main() -> int:
    metrics.install()  # activate citation-logging wrapper on answer_query
    async with AsyncSessionLocal() as db:
        admin_user = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        if not admin_user:
            print("NO admin user"); return 1
        print(f"admin: {admin_user.email}")

        # ---- Users ----
        lst = await A.list_users(role=None, status_filter=None, search=None, page=1, page_size=5,
                                 db=db, current_user=admin_user)
        print(f"[users list] total={lst['total']} page_items={len(lst['items'])}")

        test_email = f"s8test_{uuid.uuid4().hex[:8]}@truvia.ai"
        inv = await A.invite_user(A.InviteBody(name="S8 Test Officer", email=test_email, role="officer"),
                                  db=db, current_user=admin_user)
        tid = inv["id"]
        print(f"[invite] id={tid} status={inv['status']} setup_token_len={len(inv['setup_token'])}")

        det = await A.get_user(user_id=tid, db=db, current_user=admin_user)
        print(f"[user detail] role={det['role']} assigned_cases={det['assigned_case_count']} activity={len(det['activity'])}")

        pat = await A.patch_user(user_id=tid, payload=A.UserPatch(role="admin", phone="+910000000000"),
                                 db=db, current_user=admin_user)
        print(f"[patch] role={pat['role']} phone={pat['phone']}")

        sus = await A.suspend_user(user_id=tid, payload=A.SuspendBody(suspend=True), db=db, current_user=admin_user)
        rea = await A.suspend_user(user_id=tid, payload=A.SuspendBody(suspend=False), db=db, current_user=admin_user)
        print(f"[suspend->reactivate] {sus['status']} -> {rea['status']}")

        fpr = await A.force_password_reset(user_id=tid, db=db, current_user=admin_user)
        print(f"[force-reset] token_len={len(fpr['reset_token'])} url={fpr['reset_url'][:20]}...")

        # ---- Knowledge Base: add -> indexed -> citable ----
        marker = f"ZephyrionQuantumScam{uuid.uuid4().hex[:6]}"
        content = (f"The {marker} advisory: fraudsters impersonate the fictional {marker} tax bureau "
                   f"and demand crypto payments via a {marker} wallet. Never pay the {marker} bureau; "
                   f"report {marker} scams to the national helpline 1930 immediately.")
        addbody = A.AddDocBody(source="CERT-In", title=f"{marker} Advisory", content=content, source_url=None)
        kb = await A.add_knowledge_base(payload=addbody, db=db, current_user=admin_user)
        kb_id = kb["id"]
        print(f"[kb add] id={kb_id} status={kb['status']} chunks={kb['chunk_count']} times_cited={kb['times_cited']}")

        kb_list = await A.list_knowledge_base(source="CERT-In", status_filter=None, db=db, current_user=admin_user)
        print(f"[kb list CERT-In] count={len(kb_list)}")

        # Citability: query with the exact first chunk so the dummy-embedding
        # search deterministically retrieves this new doc -> it gets cited.
        first_chunk = content[:250]
        resp = await knowledge_agent.answer_query(db, first_chunk)
        cited_titles = [c["title"] for c in resp["citations"]]
        cited = any(marker in t for t in cited_titles)
        print(f"[chat citation] new doc cited={cited} citations={len(resp['citations'])}")

        # times_cited counter incremented by the citation-logging wrapper
        await asyncio.sleep(0.2)
        kb_after = await A.get_knowledge_base(kb_id=kb_id, db=db, current_user=admin_user)
        print(f"[times_cited] after_chat={kb_after['times_cited']}")

        rex = await A.reindex_knowledge_base(kb_id=kb_id, db=db, current_user=admin_user)
        print(f"[reindex] status={rex['status']} chunks={rex['chunk_count']}")

        # ---- System Health ----
        sh = await A.system_health(db=db, current_user=admin_user)
        print(f"[health] agents={len(sh['agents'])} statuses={[a['status'] for a in sh['agents']]} "
              f"queue_available={sh['queue']['available']} failed={len(sh['failed_tasks'])}")

        # ---- Cleanup test rows ----
        deldoc = await A.delete_knowledge_base(kb_id=kb_id, db=db, current_user=admin_user)
        await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == uuid.UUID(tid)))
        await db.execute(delete(User).where(User.id == uuid.UUID(tid)))
        await db.commit()
        print(f"[cleanup] kb_removed={deldoc['removed']} test_user_deleted=True")

        ok = (lst['total'] > 0 and inv['status'] == 'pending_invite' and pat['role'] == 'admin'
              and rea['status'] == 'active' and kb['chunk_count'] > 0 and kb['status'] == 'indexed'
              and cited and kb_after['times_cited'] >= 1 and len(sh['agents']) == 6)
    print("ALL_S8_OK" if ok else "S8_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(asyncio.wait_for(main(), timeout=120)))
    except asyncio.TimeoutError:
        print("TIMEOUT", file=sys.stderr); sys.exit(2)
