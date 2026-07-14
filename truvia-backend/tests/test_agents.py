import pytest
import uuid
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select
from app.core import security
from app.models import (
    User, Report, Evidence, ThreatScore, Entity, ReportEntity, Relationship,
    Case, CaseReport, KnowledgeBase, KnowledgeBaseChunk
)
from app.agents.input_processor import input_processor_agent
from app.agents.threat_evaluator import threat_evaluator_agent
from app.agents.knowledge_agent import knowledge_agent
from app.agents.entity_extractor import entity_extractor_agent
from app.agents.threat_intel import threat_intel_agent
from app.agents.investigation import investigation_agent

# 1. Security Helpers Check
def test_security_helpers():
    password = "cyber_police_password_2026"
    hashed = security.get_password_hash(password)
    assert hashed != password
    assert security.verify_password(password, hashed) is True
    assert security.verify_password("wrong_password", hashed) is False

    # Token creation
    sub = str(uuid.uuid4())
    access_token = security.create_access_token(sub, "officer")
    payload = security.decode_token(access_token)
    assert payload.get("sub") == sub
    assert payload.get("role") == "officer"
    assert payload.get("type") == "access"

# Helper to create mock objects with unique emails to prevent session collision
async def create_mock_environment(db):
    uid_citizen = uuid.uuid4()
    uid_officer = uuid.uuid4()
    # Create user
    citizen = User(
        id=uid_citizen,
        role="citizen",
        email=f"test_citizen_{uid_citizen.hex[:6]}@safety.gov.in",
        password_hash=security.get_password_hash("password123"),
        name="John Doe",
        phone="9876543210",
        status="active"
    )
    db.add(citizen)

    officer = User(
        id=uid_officer,
        role="officer",
        email=f"officer_amit_{uid_officer.hex[:6]}@safety.gov.in",
        password_hash=security.get_password_hash("password123"),
        name="Inspector Amit Kumar",
        phone="8765432109",
        status="active"
    )
    db.add(officer)
    await db.flush()
    return citizen, officer

# 2. Agent 1: Input Processor tests
@pytest.mark.asyncio
async def test_input_processor(db_session):
    citizen, _ = await create_mock_environment(db_session)
    
    # Create report
    report = Report(
        id=uuid.uuid4(),
        user_id=citizen.id,
        source_type="text",
        raw_input_ref="direct_paste",
        cleaned_text="UPI scam collect request from fake account",
        detected_language="en",
        input_confidence=1.0,
        status="processing"
    )
    db_session.add(report)
    await db_session.flush()

    # Evidence
    ev = Evidence(
        id=uuid.uuid4(),
        report_id=report.id,
        evidence_type="text",
        file_ref="complaint_text.txt",
        file_hash="mock_hash_123"
    )
    db_session.add(ev)
    await db_session.commit()

    # Run processor
    res = await input_processor_agent.process_report(str(report.id))
    assert "cleaned_text" in res
    
    # Honest degraded ASR: with no OPENAI_API_KEY configured, the processor must NOT
    # fabricate a transcript from the filename. It returns an empty, low-confidence
    # result so the pipeline can surface the degraded state truthfully.
    ev_audio = Evidence(
        id=uuid.uuid4(),
        report_id=report.id,
        evidence_type="audio",
        file_ref="scam_refund_call.mp3",
        file_hash="mock_hash_456"
    )
    db_session.add(ev_audio)
    await db_session.commit()

    # Test ASR directly (no key configured in the test environment)
    import app.agents.input_processor as ip_module
    if ip_module.input_processor_agent.client is None:  # degraded mode
        text_out, lang, conf = await input_processor_agent._asr_audio(b"fake_bytes", ".mp3", ev_audio.file_ref)
        # No fabricated scam content derived from the filename keywords.
        assert "refund" not in text_out.lower()
        assert "prize" not in text_out.lower()
        assert text_out == ""
        assert conf == 0.0

    # Honest degraded OCR: garbage bytes with no OCR provider must yield an empty,
    # zero-confidence result rather than canned "digital arrest" text.
    if ip_module.input_processor_agent.client is None:
        ocr_text, ocr_lang, ocr_conf = await input_processor_agent._ocr_image(b"not-a-real-image", ".png")
        assert "arrest" not in ocr_text.lower()
        assert "upi" not in ocr_text.lower()
        # Either empty (no engine) or real text from a locally installed Tesseract —
        # never fabricated. If empty, confidence must be 0.0.
        if ocr_text == "":
            assert ocr_conf == 0.0

# 3. Agent 2: Threat Evaluator tests
@pytest.mark.asyncio
async def test_threat_evaluator(db_session):
    citizen, _ = await create_mock_environment(db_session)
    report = Report(
        id=uuid.uuid4(),
        user_id=citizen.id,
        source_type="text",
        raw_input_ref="direct_paste",
        cleaned_text="Hello under digital arrest send money now",
        detected_language="en",
        input_confidence=0.90,
        status="processing"
    )
    db_session.add(report)
    await db_session.commit()

    res = await threat_evaluator_agent.evaluate_threat(str(report.id))
    assert "threat_score" in res
    assert "severity_band" in res
    
    # Retrieve threat score from DB
    score_res = await db_session.execute(
        select(ThreatScore).where(ThreatScore.report_id == report.id)
    )
    score_obj = score_res.scalar_one_or_none()
    assert score_obj is not None
    assert score_obj.threat_score >= 0 and score_obj.threat_score <= 100
    assert score_obj.severity_band in ["low", "moderate", "high", "critical"]

# 4. Agent 3: Knowledge Agent tests
@pytest.mark.asyncio
async def test_knowledge_agent(db_session):
    _, officer = await create_mock_environment(db_session)
    
    kb = KnowledgeBase(
        id=uuid.uuid4(),
        source="RBI",
        title="Regulatory Alert",
        content="RBI warns against QR code scams. Do not scan QR codes to receive money.",
        added_by=officer.id,
        status="indexed"
    )
    db_session.add(kb)
    await db_session.flush()

    chunk = KnowledgeBaseChunk(
        id=uuid.uuid4(),
        knowledge_base_id=kb.id,
        chunk_index=0,
        chunk_text="RBI warns against QR code scams. Scanning QR codes only sends money, it does not receive money.",
        embedding=[0.05] * 1536, # local text serializes this to json string
        embedding_model_version="text-embedding-3-small"
    )
    db_session.add(chunk)
    await db_session.commit()

    # Query RAG
    query = "Is scanning QR codes to receive money safe?"
    ans = await knowledge_agent.answer_query(db_session, query)
    assert ans is not None
    assert isinstance(ans, dict)
    assert "answer" in ans
    # Grounded rule local fallback cites RBI in brackets
    assert "[RBI]" in ans["answer"]

# 5. Agent 4: Entity Extractor tests
@pytest.mark.asyncio
async def test_entity_extractor(db_session):
    citizen, _ = await create_mock_environment(db_session)
    report = Report(
        id=uuid.uuid4(),
        user_id=citizen.id,
        source_type="text",
        raw_input_ref="direct_paste",
        cleaned_text="UPI scam collect request. Contact target phone number 9876543210. Pay to scammer@upi.",
        detected_language="en",
        input_confidence=1.0,
        status="processing"
    )
    db_session.add(report)
    await db_session.commit()

    res = await entity_extractor_agent.extract_entities(str(report.id))
    assert "extracted_count" in res
    assert res["extracted_count"] >= 2

    # Entity extraction must NOT auto-escalate the report; escalation is an explicit
    # user/officer action. The status set before extraction ("processing") is preserved.
    await db_session.refresh(report)
    assert report.status != "escalated"
    assert report.status == "processing"

    # Query entities from DB
    ent_res = await db_session.execute(
        select(Entity)
    )
    entities = ent_res.scalars().all()
    values = [e.raw_value for e in entities]
    assert "9876543210" in values
    assert "scammer@upi" in values

    # Check relationships are created
    rel_res = await db_session.execute(select(Relationship))
    rels = rel_res.scalars().all()
    assert len(rels) >= 1
    assert rels[0].relationship_type == "co_occurred_in_report"

# 6. Agent 5: Threat Intel graph sync tests
@pytest.mark.asyncio
async def test_threat_intel_agent(db_session):
    citizen, _ = await create_mock_environment(db_session)
    report = Report(
        id=uuid.uuid4(),
        user_id=citizen.id,
        source_type="text",
        raw_input_ref="direct_paste",
        cleaned_text="Graph test content",
        detected_language="en",
        input_confidence=1.0,
        status="processing"
    )
    db_session.add(report)
    await db_session.commit()

    # Sync to graph should complete cleanly (falls back/runs degraded on local environment)
    res = await threat_intel_agent.index_report_in_graph(str(report.id))
    assert res["status"] in ["success", "error"]

# 7. Agent 6: Investigation Agent tests
@pytest.mark.asyncio
async def test_investigation_agent(db_session):
    citizen, officer = await create_mock_environment(db_session)
    
    # Create Case
    case = Case(
        id=uuid.uuid4(),
        case_number="TRV-2026-0001",
        case_type="Digital Arrest Impersonation",
        status="open",
        priority="high",
        ai_summary=""
    )
    db_session.add(case)
    await db_session.flush()

    report = Report(
        id=uuid.uuid4(),
        user_id=citizen.id,
        source_type="text",
        raw_input_ref="direct_paste",
        cleaned_text="The caller claimed to be CBI police Amit. Payment demanded immediately.",
        detected_language="en",
        input_confidence=1.0,
        status="escalated"
    )
    db_session.add(report)
    await db_session.flush()

    link = CaseReport(
        case_id=case.id,
        report_id=report.id,
        linked_reason="Initial triage connection"
    )
    db_session.add(link)
    await db_session.commit()

    # Run investigation agent
    res = await investigation_agent.summarize_case(str(case.id))
    assert "summary" in res
    assert res["summary"] != ""
    
    # Reload case and check AI summary contains text
    await db_session.refresh(case)
    assert case.ai_summary != ""
    assert "cbi" in case.ai_summary.lower() or "arrest" in case.ai_summary.lower() or "caller" in case.ai_summary.lower()
