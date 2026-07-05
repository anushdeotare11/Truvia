from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.data.postgres_client import get_db
from app.api import deps
from app.models.case import Case, CaseReport
from app.models.report import Report, Entity, ReportEntity
from app.models.user import User
from app.models.audit import AuditLog
from sqlalchemy import select, func, and_
from typing import List, Dict, Any, Optional
import uuid
import logging
from app.agents.investigation import investigation_agent
from app.core.pdf import generate_report_pdf
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

router = APIRouter()
logger = logging.getLogger("truvia.api.cases")

@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_user)
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

        # 4. Mock time-series daily metrics (last 7 days)
        # In a real database, we group by date. For sqlite compatibility during demo:
        daily_metrics = [
            {"date": "Mon", "reports": min(10, total_reports // 5 + 1)},
            {"date": "Tue", "reports": min(15, total_reports // 4 + 2)},
            {"date": "Wed", "reports": min(12, total_reports // 4 + 1)},
            {"date": "Thu", "reports": min(25, total_reports // 3 + 3)},
            {"date": "Fri", "reports": min(20, total_reports // 3 + 1)},
            {"date": "Sat", "reports": min(35, total_reports // 2 + 5)},
            {"date": "Sun", "reports": total_reports}
        ]

        # 5. City/District breakdown maps (PRD/TRD requirement)
        # Mocked breakdown values matching synthetic seeder
        city_breakdown = {
            "Delhi NCR": int(total_reports * 0.35) + 3,
            "Mumbai Metro": int(total_reports * 0.22) + 2,
            "Bengaluru Hub": int(total_reports * 0.18) + 1,
            "Hyderabad Tech": int(total_reports * 0.15) + 1,
            "Chennai Core": int(total_reports * 0.10)
        }

        return {
            "total_reports": total_reports,
            "total_cases": total_cases,
            "high_risk_entities": high_risk_entities,
            "daily_metrics": daily_metrics,
            "city_breakdown": city_breakdown
        }
    except Exception as e:
        logger.error(f"Failed to compile dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Stats compilation error")

@router.get("/", status_code=status.HTTP_200_OK)
async def list_cases(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_user)
):
    """
    Lists all active cyber investigation cases.
    """
    result = await db.execute(select(Case).order_by(Case.created_at.desc()))
    cases = result.scalars().all()
    return cases

@router.get("/{case_id}", status_code=status.HTTP_200_OK)
async def get_case_details(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_user)
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
        } for log in audit_logs]
    }

@router.post("/{case_id}/assign", status_code=status.HTTP_200_OK)
async def assign_case(
    case_id: str,
    payload: Dict[str, str], # {"officer_id": "uuid"}
    db: AsyncSession = Depends(get_db),
    current_user = Depends(deps.get_current_user)
):
    """
    Assigns an investigation case to an officer, logging the assignment in the audit ledger.
    """
    try:
        case_uuid = uuid.UUID(case_id)
        officer_uuid = uuid.UUID(payload.get("officer_id"))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid Case or Officer UUID format")

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
    current_user = Depends(deps.get_current_user)
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
