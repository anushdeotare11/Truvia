"""Admin Journey API (App Flow §8). Every route is admin-only.

Real DB reads/writes throughout — no mocked users, documents, stats, or health.
"""
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import metrics
from app.core.security import get_password_hash
from app.data.postgres_client import get_db
from app.models.auth_token import PasswordResetToken
from app.models.case import Case
from app.models.knowledge import KnowledgeBase, KnowledgeBaseChunk
from app.models.user import User, Session as UserSession
from app.services import kb_ingest

router = APIRouter()
logger = logging.getLogger("truvia.api.admin")

RESET_TOKEN_TTL_HOURS = 24
VALID_ROLES = {"citizen", "officer", "admin"}
VALID_KB_SOURCES = {"RBI", "MHA", "NCRP", "CERT-In", "NPCI", "custom"}


def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _user_out(u: User) -> dict:
    return {
        "id": str(u.id),
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "status": u.status,
        "phone": u.phone,
        "officer_badge_id": u.officer_badge_id,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


async def _new_reset_token(db: AsyncSession, user_id: uuid.UUID, issued_by: uuid.UUID) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        issued_by=issued_by,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS),
    ))
    return raw


# =========================================================================== #
# §8.1 / §8.2  User Management
# =========================================================================== #
@router.get("/users", status_code=status.HTTP_200_OK)
async def list_users(
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    conds = [User.deleted_at.is_(None)]
    if role:
        conds.append(User.role == role)
    if status_filter:
        conds.append(User.status == status_filter)
    if search:
        pat = f"%{search.strip()}%"
        conds.append(or_(User.name.ilike(pat), User.email.ilike(pat)))

    total = (await db.execute(select(func.count(User.id)).where(*conds))).scalar() or 0
    rows = (await db.execute(
        select(User).where(*conds).order_by(User.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {
        "items": [_user_out(u) for u in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def _get_user_or_404(user_id: str, db: AsyncSession) -> User:
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user id")
    u = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not u or u.deleted_at is not None:
        raise HTTPException(status_code=404, detail="User not found")
    return u


@router.get("/users/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    u = await _get_user_or_404(user_id, db)
    sessions = (await db.execute(
        select(UserSession).where(UserSession.user_id == u.id).order_by(UserSession.issued_at.desc()).limit(10)
    )).scalars().all()
    assigned_cases = 0
    if u.role in ("officer", "admin"):
        assigned_cases = (await db.execute(
            select(func.count(Case.id)).where(Case.assigned_officer_id == u.id)
        )).scalar() or 0
    return {
        **_user_out(u),
        "invited_by": str(u.invited_by) if u.invited_by else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
        "assigned_case_count": assigned_cases,
        "activity": [{
            "issued_at": s.issued_at.isoformat() if s.issued_at else None,
            "ip_address": str(s.ip_address) if s.ip_address else None,
            "device_label": s.device_label,
            "revoked": s.revoked_at is not None,
        } for s in sessions],
    }


class UserPatch(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None


@router.patch("/users/{user_id}", status_code=status.HTTP_200_OK)
async def patch_user(
    user_id: str,
    payload: UserPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    u = await _get_user_or_404(user_id, db)
    if payload.role is not None:
        if payload.role not in VALID_ROLES:
            raise HTTPException(status_code=422, detail="Invalid role")
        u.role = payload.role
    if payload.name is not None:
        u.name = payload.name
    if payload.phone is not None:
        u.phone = payload.phone
    await db.commit()
    await db.refresh(u)
    return _user_out(u)


class SuspendBody(BaseModel):
    suspend: bool = True


@router.post("/users/{user_id}/suspend", status_code=status.HTTP_200_OK)
async def suspend_user(
    user_id: str,
    payload: SuspendBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    u = await _get_user_or_404(user_id, db)
    if payload.suspend and str(u.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="You cannot suspend your own account")
    u.status = "suspended" if payload.suspend else "active"
    if payload.suspend:
        # Real effect: revoke active sessions so access is lost immediately.
        await db.execute(
            update(UserSession).where(UserSession.user_id == u.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
    await db.commit()
    return {"id": str(u.id), "status": u.status}


class InviteBody(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    role: str = Field(...)


@router.post("/users/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    payload: InviteBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    if payload.role not in ("officer", "admin"):
        raise HTTPException(status_code=422, detail="Invite role must be officer or admin")
    existing = (await db.execute(select(User).where(User.email == str(payload.email)))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    new_user = User(
        role=payload.role,
        email=str(payload.email),
        # Unguessable random password; the invitee sets their own via the reset link.
        password_hash=get_password_hash(secrets.token_urlsafe(24)),
        name=payload.name,
        status="pending_invite",
        invited_by=current_user.id,
    )
    db.add(new_user)
    await db.flush()
    raw = await _new_reset_token(db, new_user.id, current_user.id)
    await db.commit()
    await db.refresh(new_user)
    return {
        **_user_out(new_user),
        # No email service configured: return the real setup link for out-of-band delivery.
        "setup_token": raw,
        "setup_url": f"/reset-password/{raw}",
        "expires_in_hours": RESET_TOKEN_TTL_HOURS,
    }


@router.post("/users/{user_id}/force-password-reset", status_code=status.HTTP_200_OK)
async def force_password_reset(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    u = await _get_user_or_404(user_id, db)
    raw = await _new_reset_token(db, u.id, current_user.id)
    # Revoke sessions so the current password can no longer be used mid-session.
    await db.execute(
        update(UserSession).where(UserSession.user_id == u.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {
        "user_id": str(u.id),
        "reset_token": raw,
        "reset_url": f"/reset-password/{raw}",
        "expires_in_hours": RESET_TOKEN_TTL_HOURS,
        "delivery": "no_email_service_configured_return_link",
    }


# =========================================================================== #
# §8.3 / §8.4  Knowledge Base
# =========================================================================== #
async def _kb_out(kb: KnowledgeBase, db: AsyncSession, with_content: bool = False) -> dict:
    chunk_count = (await db.execute(
        select(func.count(KnowledgeBaseChunk.id)).where(KnowledgeBaseChunk.knowledge_base_id == kb.id)
    )).scalar() or 0
    out = {
        "id": str(kb.id),
        "source": kb.source,
        "title": kb.title,
        "status": kb.status,
        "version": kb.version,
        "source_url": kb.source_url,
        "times_cited": kb.times_cited,
        "chunk_count": chunk_count,
        "ingested_at": kb.ingested_at.isoformat() if kb.ingested_at else None,
        "updated_at": kb.updated_at.isoformat() if kb.updated_at else None,
    }
    if with_content:
        out["content"] = kb.content
    return out


@router.get("/knowledge-base", status_code=status.HTTP_200_OK)
async def list_knowledge_base(
    source: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    conds = [KnowledgeBase.deleted_at.is_(None)]
    if source:
        conds.append(KnowledgeBase.source == source)
    if status_filter:
        conds.append(KnowledgeBase.status == status_filter)
    rows = (await db.execute(
        select(KnowledgeBase).where(*conds).order_by(KnowledgeBase.ingested_at.desc())
    )).scalars().all()
    return [await _kb_out(kb, db) for kb in rows]


async def _get_kb_or_404(kb_id: str, db: AsyncSession) -> KnowledgeBase:
    try:
        kid = uuid.UUID(kb_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document id")
    kb = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kid))).scalar_one_or_none()
    if not kb or kb.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Document not found")
    return kb


@router.get("/knowledge-base/{kb_id}", status_code=status.HTTP_200_OK)
async def get_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    kb = await _get_kb_or_404(kb_id, db)
    return await _kb_out(kb, db, with_content=True)


class AddDocBody(BaseModel):
    source: str = Field(...)
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    source_url: Optional[str] = None


@router.post("/knowledge-base", status_code=status.HTTP_201_CREATED)
async def add_knowledge_base(
    payload: AddDocBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    if payload.source not in VALID_KB_SOURCES:
        raise HTTPException(status_code=422, detail=f"source must be one of {sorted(VALID_KB_SOURCES)}")
    try:
        kb = await kb_ingest.create_and_index(
            db, source=payload.source, title=payload.title, content=payload.content,
            source_url=payload.source_url, added_by=current_user.id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    return await _kb_out(kb, db)


@router.post("/knowledge-base/{kb_id}/reindex", status_code=status.HTTP_200_OK)
async def reindex_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    kb = await _get_kb_or_404(kb_id, db)
    kb.status = "processing"
    await db.commit()
    try:
        await kb_ingest.index_document(db, kb)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-index failed: {e}")
    await db.refresh(kb)
    return await _kb_out(kb, db)


@router.delete("/knowledge-base/{kb_id}", status_code=status.HTTP_200_OK)
async def delete_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    kb = await _get_kb_or_404(kb_id, db)
    # Hard delete so the assistant can no longer cite it (chunks cascade).
    await db.delete(kb)
    await db.commit()
    return {"id": kb_id, "removed": True}


# =========================================================================== #
# §8.5  System Health
# =========================================================================== #
def _queue_and_failed():
    """Return (queue_info, failed_tasks) from RQ, or an honest unavailable state."""
    try:
        from rq.registry import FailedJobRegistry, StartedJobRegistry
        from app.core.queue import task_queue, redis_conn
        redis_conn.ping()
        failed_registry = FailedJobRegistry(queue=task_queue)
        started_registry = StartedJobRegistry(queue=task_queue)
        failed_ids = failed_registry.get_job_ids()
        failed_tasks = []
        for jid in failed_ids[:25]:
            try:
                from rq.job import Job
                job = Job.fetch(jid, connection=redis_conn)
                failed_tasks.append({
                    "job_id": jid,
                    "func": job.func_name,
                    "failed_at": job.ended_at.isoformat() if job.ended_at else None,
                    "error": (job.exc_info or "").strip().splitlines()[-1] if job.exc_info else None,
                })
            except Exception:
                failed_tasks.append({"job_id": jid, "func": None, "failed_at": None, "error": None})
        queue_info = {
            "available": True,
            "pipeline_queue_depth": task_queue.count,
            "in_progress": started_registry.count,
            "failed_count": failed_registry.count,
        }
        return queue_info, failed_tasks
    except Exception as e:
        return ({"available": False, "reason": f"Task queue/Redis unavailable: {str(e)[:80]}",
                 "pipeline_queue_depth": 0, "in_progress": 0, "failed_count": 0}, [])


@router.get("/system-health", status_code=status.HTTP_200_OK)
async def system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.require_admin),
):
    queue_info, failed_tasks = _queue_and_failed()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agents": metrics.get_agent_health(),
        "queue": queue_info,
        "failed_tasks": failed_tasks,
    }


@router.post("/system-health/retry/{job_id}", status_code=status.HTTP_200_OK)
async def retry_failed_task(
    job_id: str,
    current_user: User = Depends(deps.require_admin),
):
    try:
        from rq.registry import FailedJobRegistry
        from app.core.queue import task_queue, redis_conn
        redis_conn.ping()
        registry = FailedJobRegistry(queue=task_queue)
        if job_id not in registry.get_job_ids():
            raise HTTPException(status_code=404, detail="Failed job not found")
        registry.requeue(job_id)
        return {"job_id": job_id, "requeued": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot requeue — task queue unavailable: {str(e)[:80]}")
