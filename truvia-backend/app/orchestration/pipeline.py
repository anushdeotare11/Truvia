import logging
from sqlalchemy import select
from app.agents.input_processor import input_processor_agent
from app.agents.threat_evaluator import threat_evaluator_agent
from app.agents.entity_extractor import entity_extractor_agent
from app.agents.threat_intel import threat_intel_agent
from app.data.postgres_client import AsyncSessionLocal
from app.models.alert import Alert
from app.models.report import Report, ThreatScore

logger = logging.getLogger("truvia.orchestration.pipeline")


async def _update_pipeline_stage(report_id: str, stage: str) -> None:
    """
    Update the pipeline_stage column for a report using a separate DB session.
    This is fault-tolerant: a failed stage update will not crash the pipeline.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Report).where(Report.id == report_id)
            )
            report = result.scalar_one_or_none()
            if report:
                report.pipeline_stage = stage
                await session.commit()
                logger.debug(f"Report {report_id} pipeline_stage set to '{stage}'")
            else:
                logger.warning(f"Report {report_id} not found when updating pipeline_stage to '{stage}'")
    except Exception as e:
        logger.error(f"Failed to update pipeline_stage for report {report_id}: {e}")

async def _maybe_generate_alert(report_id: str) -> None:
    """
    Check the report's latest threat score and auto-generate an Alert if score >= 75.
    Uses a separate DB session for fault tolerance (same pattern as _update_pipeline_stage).
    """
    try:
        async with AsyncSessionLocal() as session:
            # Fetch the latest (current) ThreatScore for this report
            result = await session.execute(
                select(ThreatScore).where(
                    ThreatScore.report_id == report_id,
                    ThreatScore.is_current == True,
                )
            )
            threat_score_record = result.scalar_one_or_none()

            if threat_score_record is None:
                logger.debug(f"Report {report_id}: no current ThreatScore found, skipping alert generation")
                return

            if threat_score_record.threat_score < 75:
                logger.debug(
                    f"Report {report_id}: threat_score={threat_score_record.threat_score} "
                    f"(below 75), no alert generated"
                )
                return

            # Score >= 75 — create an alert
            scam_category = threat_score_record.scam_category
            score_value = threat_score_record.threat_score
            severity = threat_score_record.severity_band

            alert = Alert(
                scope="officer",
                severity=severity,
                title=f"High-Severity {scam_category} Report Detected",
                description=(
                    f"Report scored {score_value}/100 in the {scam_category} category. "
                    f"Immediate review recommended."
                ),
                related_report_id=report_id,
                is_active=True,
            )
            session.add(alert)
            await session.commit()
            logger.info(
                f"Report {report_id}: Alert generated (severity={severity}, "
                f"score={score_value}, category={scam_category})"
            )
    except Exception as e:
        logger.error(f"Failed to generate alert for report {report_id}: {e}")


async def run_pipeline(report_id: str) -> dict:
    """
    Orchestrates the entire intake analysis workflow:
    Agent 1 (OCR/Speech) -> Agent 2 (Threat Evaluator) -> Agent 4 (Entity Extractor)

    Low OCR/ASR confidence is a *caveat flag*, not a stop condition: the citizen
    must always receive a verdict. We therefore always continue to scoring, and the
    low_confidence_flag is surfaced to the UI so the result is shown with a caveat.
    If extraction produced no readable text at all, Agent 2 still returns an explicit
    "insufficient content" verdict rather than silently producing nothing.
    """
    logger.info(f"Starting analysis pipeline for report {report_id}")

    # Mark pipeline as started
    await _update_pipeline_stage(report_id, "ingesting")

    # Step 1: Ingest & Extract Text (Agent 1)
    await _update_pipeline_stage(report_id, "extracting_text")
    agent1_result = await input_processor_agent.process_report(report_id)

    if agent1_result.get("low_confidence_flag"):
        logger.warning(
            f"Report {report_id} flagged low-confidence "
            f"(input_confidence={agent1_result.get('input_confidence')}). "
            "Continuing to scoring with a caveat rather than halting."
        )

    # Step 2+: Always evaluate threat, extract entities, index graph.
    continuation_result = await run_pipeline_continuation(report_id)
    return {
        "status": "completed",
        "report_id": report_id,
        "low_confidence_flag": agent1_result.get("low_confidence_flag", False),
        "agent1": agent1_result,
        "threat_evaluation": continuation_result,
    }

async def run_pipeline_continuation(report_id: str) -> dict:
    """
    Runs the remaining steps of the pipeline (Agent 2 -> Agent 4 -> Agent 5).
    Can be called directly after a citizen manually verifies/edits a low-confidence transcript.
    """
    logger.info(f"Running pipeline continuation steps for report {report_id}")
    
    # 1. Threat scoring (Agent 2)
    await _update_pipeline_stage(report_id, "evaluating_threat")
    agent2_result = await threat_evaluator_agent.evaluate_threat(report_id)
    
    # 2. Entity extraction and relationship linkage (Agent 4)
    await _update_pipeline_stage(report_id, "extracting_entities")
    agent4_result = await entity_extractor_agent.extract_entities(report_id)
    
    # 3. Alert auto-generation (if threat_score >= 75)
    await _maybe_generate_alert(report_id)
    
    # 4. Graph database indexing (Agent 5)
    await _update_pipeline_stage(report_id, "indexing_graph")
    agent5_result = await threat_intel_agent.index_report_in_graph(report_id)
    
    # Mark pipeline as completed
    await _update_pipeline_stage(report_id, "completed")
    
    return {
        "agent2": agent2_result,
        "agent4": agent4_result,
        "agent5": agent5_result
    }
