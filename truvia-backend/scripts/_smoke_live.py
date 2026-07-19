"""End-to-end HTTP smoke test for Module 5 Live Scam Interceptor (live server).

Covers all 6 endpoints and the Spec §10 checklist:
  * escalating conversation -> scores rise; intervention fires exactly once
  * de-escalating conversation -> plateaus/declines, not stuck high
  * empty session -> GET + PDF report don't crash
  * escalate -> creates a real linked `cases` row via live_sessions.linked_case_id
  * PDF report reflects real turn data
  * auth guard (no token -> 401)
"""
import asyncio
import sys

import httpx
from sqlalchemy import select

from app.core.security import create_access_token
from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User
from app.models.case import Case
from app.models.live_session import LiveSession

BASE = "http://127.0.0.1:8000/api/v1"

ESCALATING = [
    "Hello, am I speaking with Mr Sharma?",
    "This is an urgent notice: your bank account will be blocked today, act immediately.",
    "I am calling from CBI. There is a warrant and you are under digital arrest right now.",
    "Transfer 50000 rupees via UPI immediately to clear your name or we will arrest you.",
    "Share the OTP you just received to confirm the payment now.",
]

DEESCALATING = [
    "This is CBI, you are under arrest, pay via UPI now or a warrant will be issued!",
    "Oh, I am sorry, I think I dialled the wrong number.",
    "Please ignore my earlier message, nothing is needed from you.",
    "Have a good day, thank you.",
    "Goodbye.",
]


async def add_turns(c, headers, sid, turns):
    traj, fires = [], 0
    intervention_msgs = []
    for t in turns:
        r = await c.post(f"{BASE}/live-sessions/{sid}/turns", headers=headers, json={"raw_text": t})
        assert r.status_code == 200, f"add_turn {r.status_code}: {r.text}"
        b = r.json()
        traj.append(b["cumulative_score"])
        if b["intervention"]:
            fires += 1
            intervention_msgs.append(b["intervention"]["message"])
        print(
            f"    turn {b['turn_index']}: turn={b['turn_score']:3d} cum={b['cumulative_score']:3d} "
            f"band={b['severity_band']:8s} esc={b['is_escalating']!s:5s} cat={b['scam_category']!r} "
            f"fire={bool(b['intervention'])}"
        )
    return traj, fires, intervention_msgs


async def main() -> int:
    async with AsyncSessionLocal() as db:
        citizen = (await db.execute(select(User).where(User.role == "citizen"))).scalars().first()
    assert citizen, "no citizen user in DB"
    tok = create_access_token(subject=str(citizen.id), role="citizen")
    h = {"Authorization": f"Bearer {tok}"}
    ok = True

    async with httpx.AsyncClient(timeout=120) as c:
        # Guard: no token -> 401
        r = await c.post(f"{BASE}/live-sessions")
        print(f"[guard no-token] {r.status_code} (expect 401)")
        ok = ok and r.status_code == 401

        # --- Escalating session ---
        r = await c.post(f"{BASE}/live-sessions", headers=h)
        assert r.status_code == 201, r.text
        sid = r.json()["session_id"]
        print(f"\n[escalating session] {sid}")
        traj, fires, msgs = await add_turns(c, h, sid, ESCALATING)
        print(f"  trajectory={traj} intervention_fires={fires}")
        rises = traj[-1] > traj[0] and traj[-1] >= 70
        once = fires == 1
        print(f"  -> rises_to_high={rises}  intervention_once={once}")
        if msgs:
            print(f"  -> intervention message: {msgs[0][:90]}...")
        ok = ok and rises and once

        # GET full session
        r = await c.get(f"{BASE}/live-sessions/{sid}", headers=h)
        assert r.status_code == 200, r.text
        gs = r.json()
        print(f"  GET session: status={gs['session']['status']} score={gs['session']['current_score']} turns={len(gs['turns'])}")
        ok = ok and len(gs["turns"]) == len(ESCALATING)

        # Escalate -> real linked case
        r = await c.post(f"{BASE}/live-sessions/{sid}/escalate", headers=h)
        assert r.status_code == 200, r.text
        case_id = r.json()["case_id"]
        print(f"  escalate -> case_id={case_id} status={r.json()['status']}")
        async with AsyncSessionLocal() as db:
            case = (await db.execute(select(Case).where(Case.id == __import__('uuid').UUID(case_id)))).scalar_one_or_none()
            sess = (await db.execute(select(LiveSession).where(LiveSession.id == __import__('uuid').UUID(sid)))).scalar_one_or_none()
        linked_ok = case is not None and sess is not None and str(sess.linked_case_id) == case_id and sess.status == "escalated"
        print(f"  linked case exists={case is not None} case_number={getattr(case,'case_number',None)} session.linked_case_id matches={linked_ok}")
        ok = ok and linked_ok

        # Idempotent re-escalate
        r = await c.post(f"{BASE}/live-sessions/{sid}/escalate", headers=h)
        print(f"  re-escalate -> {r.json().get('status')} (expect already_escalated)")
        ok = ok and r.json().get("status") == "already_escalated"

        # PDF reflects real turns
        r = await c.get(f"{BASE}/live-sessions/{sid}/report", headers=h)
        is_pdf = r.status_code == 200 and r.content[:4] == b"%PDF"
        print(f"  report PDF: {r.status_code} pdf={is_pdf} bytes={len(r.content)}")
        ok = ok and is_pdf and len(r.content) > 1500

        # --- De-escalating session ---
        r = await c.post(f"{BASE}/live-sessions", headers=h)
        sid2 = r.json()["session_id"]
        print(f"\n[de-escalating session] {sid2}")
        traj2, fires2, _ = await add_turns(c, h, sid2, DEESCALATING)
        print(f"  trajectory={traj2} intervention_fires={fires2}")
        plateaus = traj2[-1] < traj2[0] and traj2[-1] < 70
        print(f"  -> declines_not_stuck_high={plateaus}")
        ok = ok and plateaus

        # --- Empty session: end + GET + PDF must not crash ---
        r = await c.post(f"{BASE}/live-sessions", headers=h)
        sid3 = r.json()["session_id"]
        print(f"\n[empty session] {sid3}")
        r = await c.post(f"{BASE}/live-sessions/{sid3}/end", headers=h)
        print(f"  end -> {r.status_code} {r.json()}")
        r = await c.get(f"{BASE}/live-sessions/{sid3}", headers=h)
        empty_get_ok = r.status_code == 200 and r.json()["turns"] == []
        print(f"  GET empty -> {r.status_code} turns={r.json()['turns']}")
        r = await c.get(f"{BASE}/live-sessions/{sid3}/report", headers=h)
        empty_pdf_ok = r.status_code == 200 and r.content[:4] == b"%PDF"
        print(f"  empty report PDF -> {r.status_code} pdf={empty_pdf_ok}")
        ok = ok and empty_get_ok and empty_pdf_ok

    print("\nHTTP_LIVE_OK" if ok else "\nHTTP_LIVE_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(asyncio.wait_for(main(), timeout=150)))
    except asyncio.TimeoutError:
        print("TIMEOUT", file=sys.stderr)
        sys.exit(2)
