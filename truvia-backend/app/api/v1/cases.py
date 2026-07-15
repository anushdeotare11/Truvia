from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.data.postgres_client import get_db
from app.api import deps
from app.models.case import Case, CaseReport, OfficerAssignment, IntelligencePackage
from app.models.report import Report, Entity, ReportEntity, ThreatScore
from app.models.user import User
from app.models.audit import AuditLog
from sqlalchemy import select, func, and_
from typing import List, Dict, Any, Optional
import uuid
import hashlib
import json
import logging
from app.agents.investigation import investigation_agent
from app.core.pdf import generate_report_pdf
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from pydantic import BaseModel
from uuid import UUID

class CaseAssignmentPayload(BaseModel):
    officer_id: UUID

router = APIRouter()
logger = logging.getLogger("truvia.api.cases")

@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.require_officer)
):
    """
    Returns KPI summaries, daily time-series report volumes, and city/district breakdowns.
    """
    try:
        # 1. Total reports
        rep_count_result = await db.execute(select(func.count(Report.id)))
        total_reports = rep_count_result.scalar() or 0
        
        # 2. Total active cases
        case_count_result = await db.execute(select(func.count(Case.id)))
        total_cases = case_count_result.scalar() or 0
        
        # 3. High-risk entities
        ent_count_result = await db.execute(
            select(func.count(Entity.id)).where(Entity.risk_score >= 65)
        )
        high_risk_entities = ent_count_result.scalar() or 0

        # 4. REAL daily complaint volume for the last 7 days (grouped by calendar date).
        #    func.date() works on both SQLite and Postgres. Missing days are zero-filled
        #    so the trend chart always shows a continuous 7-day window.
        from datetime import datetime, timedelta
        today = datetime.now().date()
        window_start = today - timedelta(days=6)
        day_rows = await db.execute(
            select(func.date(Report.created_at), func.count(Report.id))
            .where(Report.created_at >= datetime(window_start.year, window_start.month, window_start.day))
            .group_by(func.date(Report.created_at))
        )
        counts_by_day = {str(d): int(c) for d, c in day_rows.all()}
        daily_metrics = []
        for i in range(7):
            d = window_start + timedelta(days=i)
            daily_metrics.append({
                "date": d.strftime("%a"),
                "reports": counts_by_day.get(d.isoformat(), 0),
            })

        # 5. Average threat score across all current scores (real KPI, per TRD dashboard spec).
        avg_score_result = await db.execute(
            select(func.avg(ThreatScore.threat_score)).where(ThreatScore.is_current == True)
        )
        avg_threat_score = round(float(avg_score_result.scalar() or 0), 1)

        return {
            "total_reports": total_reports,
            "total_cases": total_cases,
            "high_risk_entities": high_risk_entities,
            "avg_threat_score": avg_threat_score,
            "daily_metrics": daily_metrics,
        }
    except Exception as e:
        logger.error(f"Failed to compile dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Stats compilation error")

@router.get("", status_code=status.HTTP_200_OK)
async def list_cases(
    mine: bool = False,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.require_officer)
):
    """
    Lists investigation cases. `mine=true` scopes to the logged-in officer's assigned
    cases (§6.4 My Assigned Cases); `status` narrows by case status.
    """
    query = select(Case)
    if mine:
        query = query.where(Case.assigned_officer_id == current_user.id)
    if status:
        query = query.where(Case.status == status)
    query = query.order_by(Case.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{case_id}", status_code=status.HTTP_200_OK)
async def get_case_details(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.require_officer)
):
    """
    Returns full details for a case, including its linked reports, entities, and audit trails.
    """
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID format")

    case_result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 1. Fetch linked reports
    reports_result = await db.execute(
        select(Report)
        .join(CaseReport, CaseReport.report_id == Report.id)
        .where(CaseReport.case_id == case_uuid)
    )
    reports = reports_result.scalars().all()

    # 2. Fetch associated entities
    entities = []
    if reports:
        report_ids = [r.id for r in reports]
        entities_result = await db.execute(
            select(Entity)
            .join(ReportEntity, ReportEntity.entity_id == Entity.id)
            .where(ReportEntity.report_id.in_(report_ids))
        )
        entities = entities_result.scalars().all()

    # 3. Fetch audit logs
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.entity_id == case_uuid)
        .order_by(AuditLog.created_at.desc())
    )
    audit_logs = audit_result.scalars().all()

    # 3b. Correlated complaints: OTHER reports (not already linked to this case) that
    #     share at least one extracted entity with this case's reports. Real Postgres
    #     correlation via report_entities — the graph module will deepen this later.
    correlated = []
    linked_report_ids = {r.id for r in reports}
    if entities:
        entity_ids = [e.id for e in entities]
        corr_result = await db.execute(
            select(Report, func.count(func.distinct(ReportEntity.entity_id)).label("shared"))
            .join(ReportEntity, ReportEntity.report_id == Report.id)
            .where(and_(ReportEntity.entity_id.in_(entity_ids), Report.id.notin_(list(linked_report_ids) or [uuid.uuid4()])))
            .group_by(Report.id)
            .order_by(func.count(func.distinct(ReportEntity.entity_id)).desc())
            .limit(20)
        )
        for rep, shared in corr_result.all():
            correlated.append({
                "id": str(rep.id),
                "source_type": rep.source_type,
                "status": rep.status,
                "cleaned_text": (rep.cleaned_text or "")[:200],
                "shared_entities": int(shared),
                "created_at": rep.created_at.isoformat() if rep.created_at else None,
            })

    # Get assigned officer details
    officer_name = "Unassigned"
    if case.assigned_officer_id:
        officer_result = await db.execute(
            select(User).where(User.id == case.assigned_officer_id)
        )
        officer = officer_result.scalar_one_or_none()
        if officer:
            officer_name = officer.name

    return {
        "id": str(case.id),
        "case_number": case.case_number,
        "case_type": case.case_type,
        "status": case.status,
        "priority": case.priority,
        "ai_summary": case.ai_summary or "Evaluating case reports...",
        "assigned_officer_id": str(case.assigned_officer_id) if case.assigned_officer_id else None,
        "assigned_officer_name": officer_name,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "linked_reports": [{
            "id": str(r.id),
            "source_type": r.source_type,
            "status": r.status,
            "cleaned_text": r.cleaned_text,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in reports],
        "entities": [{
            "id": str(e.id),
            "raw_value": e.raw_value,
            "type": e.type,
            "risk_score": float(e.risk_score),
            "risk_tier": e.risk_tier,
            "occurrence_count": e.occurrence_count
        } for e in entities],
        "audit_logs": [{
            "id": str(log.id),
            "actor_type": log.actor_type,
            "action": log.action,
            "diff_json": log.diff_json,
            "created_at": log.created_at.isoformat()
        } for log in audit_logs],
        "correlated_reports": correlated,
    }

@router.get("/{case_id}/evidence-timeline", status_code=status.HTTP_200_OK)
async def get_evidence_timeline(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_officer),
):
    """
    Compiles a chronological timeline of events for a case: report submissions,
    case creation, officer assignments, package generation, and audit logs.
    """
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID format")

    # Verify case exists
    case_result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    events: List[Dict[str, Any]] = []

    # 1. Case creation event
    if case.created_at:
        events.append({
            "event_type": "case_created",
            "description": f"Case {case.case_number} created ({case.case_type})",
            "timestamp": case.created_at.isoformat(),
        })

    # 2. Report submission events (via case_reports join)
    reports_result = await db.execute(
        select(Report)
        .join(CaseReport, CaseReport.report_id == Report.id)
        .where(CaseReport.case_id == case_uuid)
    )
    for report in reports_result.scalars().all():
        if report.created_at:
            events.append({
                "event_type": "report_submitted",
                "description": f"Report submitted ({report.source_type}) - ID: {str(report.id)[:8]}",
                "timestamp": report.created_at.isoformat(),
            })

    # 3. Officer assignment events
    assignments_result = await db.execute(
        select(OfficerAssignment).where(OfficerAssignment.case_id == case_uuid)
    )
    for assignment in assignments_result.scalars().all():
        if assignment.assigned_at:
            events.append({
                "event_type": "officer_assigned",
                "description": f"Officer assigned to case",
                "timestamp": assignment.assigned_at.isoformat(),
            })

    # 4. Intelligence package generation events
    packages_result = await db.execute(
        select(IntelligencePackage).where(IntelligencePackage.case_id == case_uuid)
    )
    for pkg in packages_result.scalars().all():
        if pkg.generated_at:
            events.append({
                "event_type": "package_generated",
                "description": f"Intelligence package generated ({pkg.package_type}, v{pkg.version})",
                "timestamp": pkg.generated_at.isoformat(),
            })

    # 5. Audit log events for this case
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.entity_id == case_uuid)
        .where(AuditLog.entity_type == "cases")
    )
    for log in audit_result.scalars().all():
        if log.created_at:
            events.append({
                "event_type": "audit_log",
                "description": f"{log.action} ({log.actor_type})",
                "timestamp": log.created_at.isoformat(),
            })

    # Sort chronologically ascending
    events.sort(key=lambda e: e["timestamp"])

    return events


@router.post("/{case_id}/assign", status_code=status.HTTP_200_OK)
async def assign_case(
    case_id: str,
    payload: CaseAssignmentPayload,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.require_officer)
):
    """
    Assigns an investigation case to an officer, logging the assignment in the audit ledger.
    """
    try:
        case_uuid = uuid.UUID(case_id)
        officer_uuid = payload.officer_id
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid Case UUID format")

    # Fetch Case
    case_result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Verify Officer
    officer_result = await db.execute(select(User).where(User.id == officer_uuid))
    officer = officer_result.scalar_one_or_none()
    if not officer or officer.role not in ["officer", "admin"]:
        raise HTTPException(status_code=404, detail="Officer not found or invalid role")

    # Update Case
    case.assigned_officer_id = officer.id
    case.status = "under_investigation"

    # Persist real assignment HISTORY in officer_assignments (schema §): close any
    # currently-open assignment for this case, then open a new one. This is the
    # durable record of who was assigned when and by whom — not just a status flag.
    from datetime import datetime
    open_rows = await db.execute(
        select(OfficerAssignment).where(
            and_(OfficerAssignment.case_id == case.id, OfficerAssignment.unassigned_at.is_(None))
        )
    )
    for prev in open_rows.scalars().all():
        prev.unassigned_at = datetime.utcnow()

    db.add(OfficerAssignment(
        case_id=case.id,
        officer_id=officer.id,
        assigned_by=current_user.id,
    ))

    # Log Audit Trail
    audit = AuditLog(
        actor_id=current_user.id,
        actor_type="user",
        action="case.assign",
        entity_type="cases",
        entity_id=case.id,
        diff_json={"assigned_to": officer.name, "officer_id": str(officer.id)}
    )
    db.add(audit)
    
    await db.commit()

    # Trigger Agent 6 to summarize the case background
    await investigation_agent.summarize_case(str(case.id))

    return {"status": "success", "message": f"Case assigned to {officer.name}"}

@router.get("/{case_id}/package", status_code=status.HTTP_200_OK)
async def compile_intelligence_package(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.require_officer)
):
    """
    Compiles a comprehensive court-ready multi-page PDF package containing all case-linked evidence.
    """
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID format")

    case_result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Fetch reports
    reports_result = await db.execute(
        select(Report)
        .join(CaseReport, CaseReport.report_id == Report.id)
        .where(CaseReport.case_id == case_uuid)
    )
    reports = reports_result.scalars().all()

    # Fetch entities
    entities = []
    if reports:
        report_ids = [r.id for r in reports]
        entities_result = await db.execute(
            select(Entity)
            .join(ReportEntity, ReportEntity.entity_id == Entity.id)
            .where(ReportEntity.report_id.in_(report_ids))
        )
        entities = entities_result.scalars().all()

    # Persist a real IntelligencePackage record (schema: intelligence_packages) capturing
    # the case's actual assembled data, before rendering the downloadable PDF.
    package_json = {
        "case_number": case.case_number,
        "case_type": case.case_type,
        "priority": case.priority,
        "status": case.status,
        "ai_summary": case.ai_summary,
        "entities": [
            {"type": e.type, "value": e.raw_value, "risk_score": float(e.risk_score), "risk_tier": e.risk_tier}
            for e in entities
        ],
        "reports": [
            {"id": str(r.id), "source_type": r.source_type, "status": r.status, "cleaned_text": r.cleaned_text}
            for r in reports
        ],
    }
    content_hash = hashlib.sha256(
        json.dumps(package_json, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    package = IntelligencePackage(
        case_id=case.id,
        package_json=package_json,
        package_type="ring_level" if case.case_type == "ring_level" else "case_level",
        content_hash=content_hash,
        generated_by=current_user.id,
    )
    db.add(package)
    await db.commit()

    # Generate Case PDF Document
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'PackageTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor('#0B1E39'),
        spaceAfter=15
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=colors.HexColor('#1959B8'),
        spaceBefore=15,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14
    )

    story = []

    # Title & Summary
    story.append(Paragraph(f"COURT EVIDENCE DOSSIER: {case.case_number}", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Case Priority:</b> " + case.priority.upper(), body_style))
    story.append(Paragraph("<b>Investigation Status:</b> " + case.status.upper(), body_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph("Executive AI Investigation Briefing", section_heading))
    story.append(Paragraph(case.ai_summary or "No summary prepared.", body_style))
    story.append(Spacer(1, 15))

    # Entities
    if entities:
        story.append(Paragraph("Target Threat Entities Linked", section_heading))
        entity_rows = [[Paragraph("<b>Type</b>", body_style), Paragraph("<b>Raw Value</b>", body_style), Paragraph("<b>Risk Score</b>", body_style)]]
        for ent in entities:
            entity_rows.append([
                Paragraph(ent.type.upper(), body_style),
                Paragraph(ent.raw_value, body_style),
                Paragraph(f"{ent.risk_score} ({ent.risk_tier})", body_style)
            ])
        t = Table(entity_rows, colWidths=[120, 260, 120])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F4F4F5')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 6)
        ]))
        story.append(t)
        story.append(Spacer(1, 15))

    # Evidence transcripts
    if reports:
        story.append(Paragraph("Complaints & Evidence logs", section_heading))
        for r in reports:
            story.append(Paragraph(f"<b>Complaint ID:</b> #{str(r.id)[:8]} ({r.source_type.upper()})", body_style))
            story.append(Paragraph(f"<i>Cleaned Text:</i> {r.cleaned_text or 'No transcript'}", body_style))
            story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    
    filename = f"dossier-{case.case_number}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
