import logging
from app.agents.input_processor import input_processor_agent
from app.agents.threat_evaluator import threat_evaluator_agent
from app.agents.entity_extractor import entity_extractor_agent
from app.agents.threat_intel import threat_intel_agent
from app.data.postgres_client import AsyncSessionLocal
from app.models.report import Report

logger = logging.getLogger("truvia.orchestration.pipeline")

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

    # Step 1: Ingest & Extract Text (Agent 1)
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
    agent2_result = await threat_evaluator_agent.evaluate_threat(report_id)
    
    # 2. Entity extraction and relationship linkage (Agent 4)
    agent4_result = await entity_extractor_agent.extract_entities(report_id)
    
    # 3. Graph database indexing (Agent 5)
    agent5_result = await threat_intel_agent.index_report_in_graph(report_id)
    
    return {
        "agent2": agent2_result,
        "agent4": agent4_result,
        "agent5": agent5_result
    }
