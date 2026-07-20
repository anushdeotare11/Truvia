"""Module 5: Live Scam Interceptor — API (Spec §6).

Six endpoints under /api/v1/live-sessions, citizen-role auth, citizens own
their own sessions. Escalation reuses the existing Fraud Shield escalation
pattern (create a real `cases` row + Agent 6 summary) pointed at a session
instead of a report, linked via `live_sessions.linked_case_id`. The PDF report
reuses the existing `generate_report_pdf` renderer — no second PDF path.
"""
import logging
import random
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.core.pdf import generate_report_pdf
from app.data.postgres_client import get_db
from app.models.case import Case
from app.models.live_session import LiveSession, LiveSessionTurn
from app.models.user import User
from app.services import live_session_scorer as scorer

logger = logging.getLogger("truvia.api.live_sessions")
router = APIRouter()


class TurnCreate(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=5000)


def _parse_uuid(session_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id format")


async def _load_owned_session(
    session_id: str, db: AsyncSession, current_user: User, with_turns: bool = False
) -> LiveSession:
    """Fetch a session and enforce citizen ownership."""
    sid = _parse_uuid(session_id)
    query = select(LiveSession).where(LiveSession.id == sid)
    if with_turns:
        query = query.options(selectinload(LiveSession.turns))
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Live session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return session


def _serialize_turn(turn: LiveSessionTurn) -> dict:
    return {
        "id": str(turn.id),
        "turn_index": turn.turn_index,
        "raw_text": turn.raw_text,
        "turn_score": turn.turn_score,
        "cumulative_score": turn.cumulative_score,
        "flagged_phrases": turn.flagged_phrases_json or {},
        "created_at": turn.created_at.isoformat() if turn.created_at else None,
    }


def _serialize_session(session: LiveSession) -> dict:
    return {
        "id": str(session.id),
        "user_id": str(session.user_id),
        "status": session.status,
        "current_severity_band": session.current_severity_band,
        "current_score": session.current_score,
        "scam_category": session.scam_category,
        "intervention_shown_at": session.intervention_shown_at.isoformat()
        if session.intervention_shown_at
        else None,
        "linked_case_id": str(session.linked_case_id) if session.linked_case_id else None,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_live_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_citizen),
):
    """Start a new live session (Spec §6)."""
    session = LiveSession(user_id=current_user.id, status="active")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"session_id": str(session.id), "status": session.status}


@router.post("/{session_id}/turns")
async def add_turn(
    session_id: str,
    payload: TurnCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_citizen),
):
    """Add a turn and return the updated turn-by-turn assessment (Spec §6/§7)."""
    session = await _load_owned_session(session_id, db, current_user, with_turns=True)
    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session is '{session.status}' and no longer accepts turns.",
        )

    existing_turns = list(session.turns)
    prior_turn_scores = [t.turn_score for t in existing_turns]
    previous_cumulative = existing_turns[-1].cumulative_score if existing_turns else 0
    next_index = len(existing_turns)

    full_conversation_text = "\n".join([t.raw_text for t in existing_turns] + [payload.raw_text])

    result = await scorer.score_turn(
        turn_text=payload.raw_text,
        previous_cumulative=previous_cumulative,
        prior_turn_scores=prior_turn_scores,
        full_conversation_text=full_conversation_text,
        intervention_already_shown=session.intervention_shown_at is not None,
    )

    turn = LiveSessionTurn(
        session_id=session.id,
        turn_index=next_index,
        raw_text=payload.raw_text,
        turn_score=result["turn_score"],
        cumulative_score=result["cumulative_score"],
        flagged_phrases_json=result["reasoning"],
    )
    db.add(turn)

    # Update denormalized session state.
    session.current_score = result["cumulative_score"]
    session.current_severity_band = result["severity_band"]
    if result["scam_category"]:
        session.scam_category = result["scam_category"]
    # Record the first "high" crossing so the banner only fires once per session.
    if result["fire_intervention"] and session.intervention_shown_at is None:
        session.intervention_shown_at = datetime.now(timezone.utc)

    await db.commit()

    reasoning = result["reasoning"] or {}
    return {
        "turn_index": next_index,
        "turn_score": result["turn_score"],
        "cumulative_score": result["cumulative_score"],
        "severity_band": result["severity_band"],
        "scam_category": result["scam_category"],
        "is_escalating": result["is_escalating"],
        "intervention": result["intervention"],  # {shown, message, category} | null
        "flagged_phrases": reasoning.get("key_indicators", []),
        "reasoning": reasoning,
    }


@router.get("/{session_id}")
async def get_live_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_citizen),
):
    """Get the full session + turn history — used to render the summary screen."""
    session = await _load_owned_session(session_id, db, current_user, with_turns=True)
    return {
        "session": _serialize_session(session),
        "turns": [_serialize_turn(t) for t in session.turns],
    }


@router.post("/{session_id}/end")
async def end_live_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_citizen),
):
    """End a session (Spec §6)."""
    session = await _load_owned_session(session_id, db, current_user)
    if session.status == "active":
        session.status = "ended"
        session.ended_at = datetime.now(timezone.utc)
        await db.commit()
    return {"status": session.status}


@router.post("/{session_id}/escalate")
async def escalate_live_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_citizen),
):
    """Escalate a live session to a real case.

    Reuses the existing Fraud Shield escalation pattern (create a `cases` row
    identical in shape to a normal escalation, then run Agent 6's case summary)
    pointed at a session instead of a report. Because a live session has no
    report/entities, the link is recorded via `live_sessions.linked_case_id`
    (Spec §6/§10).
    """
    session = await _load_owned_session(session_id, db, current_user)

    # Idempotent: if already escalated, return the existing case.
    if session.status == "escalated" and session.linked_case_id:
        return {"status": "already_escalated", "case_id": str(session.linked_case_id)}

    case_num = f"CASE-2026-{random.randint(1000, 9999)}"
    new_case = Case(
        case_number=case_num,
        case_type="single_report",
        status="open",
        priority="medium",
        ai_summary="Live scam-interception session escalated by citizen.",
    )
    db.add(new_case)
    await db.flush()  # populate new_case.id

    session.linked_case_id = new_case.id
    session.status = "escalated"
    if session.ended_at is None:
        session.ended_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Live session {session.id} escalated to newly created Case {case_num}")

    # Reuse Agent 6 to summarize the case background (same as report escalation).
    try:
        from app.agents.investigation import investigation_agent

        await investigation_agent.summarize_case(str(new_case.id))
    except Exception as ie:  # pragma: no cover - agent/network dependent
        logger.error(f"Agent 6 case summarization failed on live-session escalation: {ie}")

    return {"status": "escalated", "session_id": str(session.id), "case_id": str(new_case.id)}


@router.get("/{session_id}/report")
async def get_live_session_report(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_citizen),
):
    """Download the session summary as a PDF — reuses the existing report PDF
    renderer (`generate_report_pdf`); no second PDF path (Spec §6)."""
    session = await _load_owned_session(session_id, db, current_user, with_turns=True)

    # Build the conversation transcript from the real turns (empty-safe).
    if session.turns:
        transcript = "\n".join(
            f"Turn {t.turn_index + 1} (risk {t.cumulative_score}): {t.raw_text}"
            for t in session.turns
        )
    else:
        transcript = "No turns were recorded in this live session."

    report_data = {
        "id": session.id,
        "source_type": "live_session",
        "cleaned_text": transcript,
        "detected_language": None,
        "status": session.status,
        "created_at": session.created_at.strftime("%Y-%m-%d %H:%M:%S") if session.created_at else "N/A",
        "threat_score": session.current_score,
        "severity_band": session.current_severity_band,
        "scam_category": session.scam_category or "Unclassified",
        "entities": [],
    }

    pdf_buffer = generate_report_pdf(report_data)
    filename = f"truvia-live-session-{session.id.hex[:8]}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
