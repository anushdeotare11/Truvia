import json
import logging
import asyncio
from sqlalchemy import select, update
import google.generativeai as genai
from app.config import settings
from app.data.postgres_client import AsyncSessionLocal
from app.models.report import Report, ThreatScore

logger = logging.getLogger("truvia.agents.threat_evaluator")

class ThreatEvaluatorAgent:
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        if self.api_key and "your-google-key" not in self.api_key and len(self.api_key) > 10:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel("gemini-2.5-flash")
            logger.info("Initialized ThreatEvaluatorAgent with Google Gemini API client")
        else:
            self.client = None
            logger.warning("No Google API key configured. Running ThreatEvaluatorAgent in degraded mock mode.")

    async def evaluate_threat(self, report_id: str) -> dict:
        """
        Main entry point for Agent 2. Fetches the processed report text,
        evaluates scam indicators, calculates risk score, and records it in the database.
        """
        import uuid
        if isinstance(report_id, str):
            report_id = uuid.UUID(report_id)

        async with AsyncSessionLocal() as session:
            try:
                # 1. Fetch Report
                report_result = await session.execute(
                    select(Report).where(Report.id == report_id)
                )
                report = report_result.scalar_one_or_none()
                if not report:
                    logger.error(f"Report {report_id} not found for threat evaluation")
                    return {"status": "error", "message": "Report not found"}

                text_content = report.cleaned_text or ""
                if not text_content:
                    logger.warning(f"Report {report_id} has empty cleaned text. Skipping threat evaluation.")
                    # Give it a safe zero score
                    score_val, band, cat = 0, "low", "unclassified"
                    reasoning = {"reason": "Empty report content submitted"}
                    degraded = True
                else:
                    # 2. Run analysis
                    score_val, band, cat, confidence, reasoning, degraded = await self._analyze_text(text_content)

                # 3. Mark old scores as not current
                await session.execute(
                    update(ThreatScore)
                    .where(ThreatScore.report_id == report.id)
                    .values(is_current=False)
                )

                # 4. Insert new ThreatScore
                new_score = ThreatScore(
                    report_id=report.id,
                    threat_score=score_val,
                    severity_band=band,
                    scam_category=cat,
                    confidence_score=confidence,
                    reasoning_json=reasoning,
                    degraded_mode=degraded,
                    model_version="claude-3-5-sonnet" if not degraded else "local-rule-engine",
                    is_current=True
                )
                session.add(new_score)
                
                # Update report status to scored
                report.status = "scored"
                await session.commit()
                
                logger.info(f"Report {report_id} evaluated with threat score {score_val} ({band})")
                return {
                    "report_id": report_id,
                    "threat_score": score_val,
                    "severity_band": band,
                    "scam_category": cat,
                    "reasoning": reasoning
                }

            except Exception as e:
                logger.error(f"Error in Agent 2 evaluating report {report_id}: {str(e)}")
                raise

    async def _analyze_text(self, text: str) -> tuple[int, str, str, float, dict, bool]:
        """
        Performs threat score calculations.
        """
        if self.client:
            try:
                prompt = (
                    "You are a cybercrime investigator analyzing a report of a digital scam.\n"
                    f"Report Text: \"\"\"\n{text}\n\"\"\"\n\n"
                    "Analyze the text and extract:\n"
                    "1. Threat Score: integer from 0 (completely safe) to 100 (confirmed malicious scam).\n"
                    "2. Severity Band: 'low' (0-39), 'moderate' (40-69), 'high' (70-89), or 'critical' (90-100).\n"
                    "3. Scam Category: classification (e.g., 'Digital Arrest', 'UPI Refund Scam', 'KYC Verification Scam', 'Lottery/Job Scam', 'Imposter Scam').\n"
                    "4. Confidence Score: float between 0.0 and 1.0.\n"
                    "5. Reasoning: a detailed explanation containing:\n"
                    "   - 'key_indicators': list of specific red flags found (e.g. urgent threats, UPI requests).\n"
                    "   - 'victim_instructions': safety tips or instructions for the citizen.\n"
                    "   - 'risk_explanation': brief explanation of why this was scored as such.\n\n"
                    "Format the response EXACTLY as a JSON object with keys:\n"
                    "'threat_score', 'severity_band', 'scam_category', 'confidence_score', 'reasoning'."
                )

                response = await asyncio.to_thread(
                    self.client.generate_content,
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )

                res_content = response.text.strip()
                if "```json" in res_content:
                    res_content = res_content.split("```json")[1].split("```")[0].strip()
                elif "```" in res_content:
                    res_content = res_content.split("```")[1].split("```")[0].strip()

                data = json.loads(res_content)
                return (
                    int(data.get("threat_score", 50)),
                    data.get("severity_band", "moderate"),
                    data.get("scam_category", "unclassified"),
                    float(data.get("confidence_score", 0.90)),
                    data.get("reasoning", {}),
                    False
                )
            except Exception as e:
                logger.error(f"Gemini threat evaluation failed: {str(e)}. Falling back to local rule-engine.")

        # Local rule engine fallback
        text_lower = text.lower()
        score_val = 15  # Default baseline
        cat = "Suspected Scam"
        indicators = []

        if "arrest" in text_lower or "police" in text_lower or "custody" in text_lower:
            score_val += 50
            cat = "Digital Arrest Scam"
            indicators.append("Impersonation of law enforcement officials")
            indicators.append("Threats of immediate arrest or custody")
        
        if "upi" in text_lower or "transfer" in text_lower or "pay" in text_lower or "rupees" in text_lower or "inr" in text_lower:
            score_val += 30
            indicators.append("Demand for immediate financial transactions")
            if cat == "Suspected Scam":
                cat = "UPI / Financial Fraud"

        if "compromised" in text_lower or "otp" in text_lower or "kyc" in text_lower:
            score_val += 20
            indicators.append("Request for security OTPs or account details")

        # Clamp score at 100
        score_val = min(score_val, 100)

        # Map to bands
        if score_val >= 90:
            band = "critical"
        elif score_val >= 70:
            band = "high"
        elif score_val >= 40:
            band = "moderate"
        else:
            band = "low"

        reasoning = {
            "key_indicators": indicators or ["Suspicious communications requesting attention"],
            "victim_instructions": [
                "Do not make any transfers or share OTP keys.",
                "Verify calling numbers with the official website of the organization.",
                "Report this immediately to the national cybercrime portal."
            ],
            "risk_explanation": f"Evaluated based on suspicious keywords representing {cat} patterns."
        }

        return score_val, band, cat, 0.80, reasoning, True

threat_evaluator_agent = ThreatEvaluatorAgent()
