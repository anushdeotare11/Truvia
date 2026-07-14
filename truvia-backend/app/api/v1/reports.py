from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.data.postgres_client import get_db
from app.models.user import User
from app.models.report import Report, Evidence, ThreatScore
from datetime import datetime
import csv
import io
from app.schemas.report import ReportOut
from app.api import deps
from app.data.storage_client import storage_client
from app.core.queue import enqueue_job
from app.orchestration.pipeline import run_pipeline, run_pipeline_continuation
from typing import List, Optional, Union
import hashlib
import logging

logger = logging.getLogger("truvia.api.reports")
router = APIRouter()

# Core worker tasks that will be processed in background
def run_intake_pipeline(report_id: str):
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return asyncio.ensure_future(run_pipeline(report_id))
    else:
        return loop.run_until_complete(run_pipeline(report_id))

def run_continuation_pipeline(report_id: str):
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return asyncio.ensure_future(run_pipeline_continuation(report_id))
    else:
        return loop.run_until_complete(run_pipeline_continuation(report_id))

@router.post("/submit", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def submit_report(
    background_tasks: BackgroundTasks,
    source_type: str = Form(...),  # screenshot, audio, text
    text_content: Optional[str] = Form(None),
    files: Optional[Union[List[UploadFile], UploadFile]] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if source_type not in ["screenshot", "audio", "text"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source type. Must be 'screenshot', 'audio', or 'text'."
        )

    # 1. Create Report in submitted state
    raw_input_ref = "direct_paste" if source_type == "text" else "file_uploads"
    
    new_report = Report(
        user_id=current_user.id,
        source_type=source_type,
        raw_input_ref=raw_input_ref,
        cleaned_text=text_content if source_type == "text" else None,
        status="submitted",
        low_confidence_flag=False
    )
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    # 2. Process and save uploaded files
    if files and source_type != "text":
        uploaded_files = files if isinstance(files, list) else [files]
        for upload_file in uploaded_files:
            content = await upload_file.read()
            # Calculate SHA-256 hash
            sha256 = hashlib.sha256(content).hexdigest()
            
            # Save file via storage client
            file_ref = await storage_client.save_file(
                file_content=content,
                filename=upload_file.filename,
                content_type=upload_file.content_type
            )
            
            # Create Evidence linked record
            evidence_type = "image" if source_type == "screenshot" else "audio"
            evidence_item = Evidence(
                report_id=new_report.id,
                evidence_type=evidence_type,
                file_ref=file_ref,
                file_hash=sha256
            )
            db.add(evidence_item)
            
        await db.commit()
        await db.refresh(new_report)

    # 3. Schedule Agent pipeline to run in-process after the response is returned.
    #    (Redis/RQ worker is not required — the pipeline runs as a FastAPI background task.)
    background_tasks.add_task(run_pipeline, str(new_report.id))

    # Return report structure
    # Fetch complete object with evidence items preloaded
    result = await db.execute(
        select(Report).options(
            selectinload(Report.evidence_items),
            selectinload(Report.threat_scores)
        ).where(Report.id == new_report.id)
    )
    return result.scalar_one()

def _report_filter_conditions(
    current_user, search, status_f, source_type, category,
    score_min, score_max, date_from, date_to,
):
    """Shared WHERE conditions for the complaint table + CSV export (real narrowing)."""
    conds = []
    # Citizens are always restricted to their own reports.
    if current_user.role not in ["officer", "admin"]:
        conds.append(Report.user_id == current_user.id)
    if search:
        conds.append(Report.cleaned_text.ilike(f"%{search}%"))
    if status_f:
        conds.append(Report.status == status_f)
    if source_type:
        conds.append(Report.source_type == source_type)

    # category + score range resolve against the report's CURRENT threat score.
    ts_conds = [ThreatScore.is_current == True]
    if category:
        ts_conds.append(ThreatScore.scam_category == category)
    if score_min is not None:
        ts_conds.append(ThreatScore.threat_score >= score_min)
    if score_max is not None:
        ts_conds.append(ThreatScore.threat_score <= score_max)
    if len(ts_conds) > 1:
        conds.append(Report.id.in_(select(ThreatScore.report_id).where(and_(*ts_conds))))

    if date_from:
        try:
            conds.append(Report.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            conds.append(Report.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass
    return conds


@router.get("", response_model=List[ReportOut])
async def list_reports(
    search: Optional[str] = None,
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    conds = _report_filter_conditions(
        current_user, search, status, source_type, category,
        score_min, score_max, date_from, date_to,
    )
    query = (
        select(Report)
        .options(selectinload(Report.evidence_items), selectinload(Report.threat_scores))
        .where(and_(*conds)) if conds else
        select(Report).options(selectinload(Report.evidence_items), selectinload(Report.threat_scores))
    )
    query = query.order_by(Report.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/export")
async def export_reports_csv(
    search: Optional[str] = None,
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Export the CURRENTLY-FILTERED complaint set as a real CSV (not a static file)."""
    conds = _report_filter_conditions(
        current_user, search, status, source_type, category,
        score_min, score_max, date_from, date_to,
    )
    query = select(Report).options(selectinload(Report.threat_scores))
    if conds:
        query = query.where(and_(*conds))
    query = query.order_by(Report.created_at.desc()).limit(5000)
    result = await db.execute(query)
    reports = result.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Report ID", "Source Type", "Status", "Scam Category", "Threat Score",
        "Severity", "Confidence", "Detected Language", "Created At", "Content",
    ])
    for r in reports:
        ts = None
        for t in (r.threat_scores or []):
            if t.is_current:
                ts = t
                break
        if ts is None and r.threat_scores:
            ts = r.threat_scores[0]
        writer.writerow([
            str(r.id), r.source_type, r.status,
            ts.scam_category if ts else "",
            ts.threat_score if ts else "",
            ts.severity_band if ts else "",
            float(ts.confidence_score) if ts else "",
            r.detected_language or "",
            r.created_at.isoformat() if r.created_at else "",
            (r.cleaned_text or "").replace("\n", " ").replace("\r", " "),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=truvia-complaints-export.csv"},
    )

@router.get("/{report_id}/status", status_code=status.HTTP_200_OK)
async def get_report_status(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    import uuid
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
        
    result = await db.execute(
        select(Report).where(Report.id == report_uuid)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report.user_id != current_user.id and current_user.role not in ["officer", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": str(report.id),
        "status": report.status,
        "low_confidence_flag": report.low_confidence_flag,
        "input_confidence": float(report.input_confidence) if report.input_confidence else None
    }

@router.get("/{report_id}", response_model=ReportOut)
async def get_report_details(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    import uuid
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
        
    result = await db.execute(
        select(Report).options(
            selectinload(Report.evidence_items),
            selectinload(Report.threat_scores)
        ).where(Report.id == report_uuid)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    # Ensure privacy: citizens can only view their own reports
    if report.user_id != current_user.id and current_user.role not in ["officer", "admin"]:
      raise HTTPException(status_code=403, detail="Access denied")

    return report

from fastapi import Body

@router.patch("/{report_id}/text", response_model=ReportOut)
async def update_report_text(
    report_id: str,
    background_tasks: BackgroundTasks,
    cleaned_text: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    import uuid
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
        
    result = await db.execute(
        select(Report).options(
            selectinload(Report.evidence_items),
            selectinload(Report.threat_scores)
        ).where(Report.id == report_uuid)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report.user_id != current_user.id and current_user.role not in ["officer", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    report.cleaned_text = cleaned_text
    report.low_confidence_flag = False
    report.input_confidence = 1.000
    
    await db.commit()
    await db.refresh(report)

    try:
        background_tasks.add_task(run_pipeline_continuation, str(report.id))
    except Exception as e:
        logger.error(f"Failed to schedule continuation job: {str(e)}. Running synchronously instead.")
        await run_pipeline_continuation(str(report.id))
        await db.refresh(report)
        
    return report

from fastapi.responses import StreamingResponse
from app.core.pdf import generate_report_pdf
from app.models import ThreatScore, Entity, ReportEntity, Case, CaseReport

@router.get("/{report_id}/pdf")
async def get_report_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    import uuid
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
        
    result = await db.execute(
        select(Report).where(Report.id == report_uuid)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report.user_id != current_user.id and current_user.role not in ["officer", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    threat_result = await db.execute(
        select(ThreatScore)
        .where(ThreatScore.report_id == report_uuid)
        .where(ThreatScore.is_current == True)
    )
    threat = threat_result.scalar_one_or_none()
    
    entities_result = await db.execute(
        select(Entity)
        .join(ReportEntity)
        .where(ReportEntity.report_id == report_uuid)
    )
    entities = entities_result.scalars().all()
    
    report_data = {
        "id": report.id,
        "source_type": report.source_type,
        "cleaned_text": report.cleaned_text,
        "detected_language": report.detected_language,
        "status": report.status,
        "created_at": report.created_at.strftime("%Y-%m-%d %H:%M:%S") if report.created_at else "N/A",
        "threat_score": threat.threat_score if threat else None,
        "severity_band": threat.severity_band if threat else None,
        "scam_category": threat.scam_category if threat else None,
        "entities": [{"type": e.type, "raw_value": e.raw_value} for e in entities]
    }
    
    pdf_buffer = generate_report_pdf(report_data)
    filename = f"truvia-report-{report.id.hex[:8]}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/{report_id}/dismiss", status_code=status.HTTP_200_OK)
async def dismiss_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Citizen (or officer) marks a report as reviewed/dismissed — e.g. a low-risk
    result the citizen has read and is closing out. Persists status='dismissed'
    so it survives refresh. An already-escalated report cannot be dismissed
    (it is now an active case).
    """
    import uuid
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    result = await db.execute(select(Report).where(Report.id == report_uuid))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.user_id != current_user.id and current_user.role not in ["officer", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if report.status == "escalated":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This report has been escalated to a case and cannot be dismissed.",
        )

    report.status = "dismissed"
    await db.commit()
    return {"status": "dismissed", "report_id": str(report.id)}

@router.post("/{report_id}/escalate", status_code=status.HTTP_200_OK)
async def escalate_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    import uuid
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
        
    result = await db.execute(
        select(Report).where(Report.id == report_uuid)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report.user_id != current_user.id and current_user.role not in ["officer", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    if report.status == "escalated":
        case_link_result = await db.execute(
            select(CaseReport).where(CaseReport.report_id == report_uuid)
        )
        existing_link = case_link_result.scalar_one_or_none()
        if existing_link:
            return {"status": "already_escalated", "case_id": str(existing_link.case_id)}
            
    report.status = "escalated"
    await db.commit()

    entities_result = await db.execute(
        select(Entity.id)
        .join(ReportEntity)
        .where(ReportEntity.report_id == report_uuid)
    )
    entity_ids = [row for row in entities_result.scalars().all()]
    
    linked_case_id = None
    if entity_ids:
        case_search_result = await db.execute(
            select(CaseReport.case_id)
            .join(ReportEntity, ReportEntity.report_id == CaseReport.report_id)
            .where(ReportEntity.entity_id.in_(entity_ids))
            .limit(1)
        )
        linked_case_id = case_search_result.scalar_one_or_none()

    if linked_case_id:
        new_link = CaseReport(
            case_id=linked_case_id,
            report_id=report.id,
            linked_reason="Automated matching of shared threat entities (UPI/phone/domain)"
        )
        db.add(new_link)
        logger.info(f"Report {report.id} auto-linked to existing Case {linked_case_id}")
    else:
        import random
        case_num = f"CASE-2026-{random.randint(1000, 9999)}"
        new_case = Case(
            case_number=case_num,
            case_type="single_report" if len(entity_ids) == 0 else "ring_level",
            status="open",
            priority="medium",
            ai_summary="Intake report automatically escalated by citizen."
        )
        db.add(new_case)
        await db.flush()
        
        new_link = CaseReport(
            case_id=new_case.id,
            report_id=report.id,
            linked_reason="Initial ingestion of incident report"
        )
        db.add(new_link)
        linked_case_id = new_case.id
        logger.info(f"Report {report.id} escalated to newly created Case {case_num}")

    await db.commit()
    
    # Trigger Agent 6 to summarize the case background dynamically after escalation
    try:
        from app.agents.investigation import investigation_agent
        await investigation_agent.summarize_case(str(linked_case_id))
    except Exception as ie:
        logger.error(f"Agent 6 case summarization failed on escalation: {str(ie)}")

    return {
        "status": "escalated",
        "report_id": str(report.id),
        "case_id": str(linked_case_id)
    }
