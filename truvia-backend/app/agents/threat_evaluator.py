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
            self.client = genai.GenerativeModel("gemini-2.0-flash")
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
                if not text_content.strip():
                    logger.warning(f"Report {report_id} has empty cleaned text. Emitting explicit insufficient-content verdict.")
                    # Explicit, honest "could not extract enough content" verdict — NOT a
                    # silent no-op. The UI renders this as a real (zero) result with a clear
                    # explanation instead of "the pipeline did not return a verdict".
                    score_val, band, cat, confidence = 0, "low", "Insufficient Content", 0.0
                    reasoning = {
                        "key_indicators": [],
                        "victim_instructions": [
                            "We could not extract readable text from your upload.",
                            "Try a clearer screenshot/recording, or paste the message text directly for analysis.",
                        ],
                        "risk_explanation": (
                            "No readable content could be extracted from the submitted evidence, "
                            "so a threat score could not be computed. This is not a safety verdict — "
                            "please resubmit clearer content or paste the text."
                        ),
                    }
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
                    model_version="gemini-2.0-flash" if not degraded else "local-rule-engine",
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
        Performs threat score calculations. Attempts the full LLM structured-
        reasoning pass first, falling back to the rule-based engine on any failure.
        """
        if self.client:
            try:
                return await self._llm_analyze(text)
            except Exception as e:
                logger.error(f"Gemini threat evaluation failed: {str(e)}. Falling back to local rule-engine.")

        return self.rule_based_analyze(text)

    async def _llm_analyze(self, text: str) -> tuple[int, str, str, float, dict, bool]:
        """Full LLM structured-reasoning pass (Agent 2).

        Reused as-is by the Live Scam Interceptor, which invokes it per-turn
        only once the rule-based cumulative score reaches 'moderate' or above
        (cost/latency-aware conditional call, Spec §7.3). Raises on failure so
        callers can decide whether to fall back to rule-based scoring.
        """
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

    def rule_based_analyze(self, text: str) -> tuple[int, str, str, float, dict, bool]:
        """Rule-based red-flag extractor (Agent 2).

        Returns (score, severity_band, scam_category, confidence, reasoning, degraded=True).
        Reused per-turn by the Live Scam Interceptor's turn scorer — do NOT
        duplicate this logic; call this method instead (Spec §7.1).
        """
        # Local rule engine
        text_lower = text.lower()
        score_val = 15  # Default baseline
        cat = "Suspected Scam"
        indicators = []
        victim_instructions = [
            "Do not make any transfers or share OTP keys.",
            "Verify calling numbers with the official website of the organization.",
            "Report this immediately to the national cybercrime portal."
        ]

        # 1. Digital Arrest / Law Enforcement Impersonation
        if any(kw in text_lower for kw in ["arrest", "police", "custody", "cbi", "court", "warrant"]):
            score_val += 60
            cat = "Digital Arrest Scam"
            indicators.append("Impersonation of law enforcement officials")
            indicators.append("Threats of immediate arrest or custody")
            victim_instructions.extend([
                "Government or police officials will never place you under 'digital arrest' or demand money via video calls.",
                "Immediately disconnect any video calls claiming to be from law enforcement demanding payment."
            ])
        
        # 2. UPI / Financial Fraud
        if any(kw in text_lower for kw in ["upi", "transfer", "pay", "rupees", "inr", "refund", "cashback", "prize", "won", "lottery"]):
            score_val += 30
            indicators.append("Demand for immediate financial transactions or prize claims")
            if cat == "Suspected Scam":
                cat = "UPI Refund Scam"
            victim_instructions.append("Never approve unknown UPI collect requests or enter your UPI PIN to receive money.")

        # 3. Phishing / Brand Impersonation / KYC / Pancard Scams
        # Check bank/reputable brand names
        bank_brands = ["hdfc", "sbi", "icici", "axis", "pnb", "citi", "hsbc", "kotak", "bank", "netbanking"]
        has_bank = any(brand in text_lower for brand in bank_brands)
        
        # Check KYC/Pancard/Aadhaar/Identity keywords
        has_identity = any(kw in text_lower for kw in ["pancard", "pan card", "aadhaar", "kyc", "verify", "verification", "update", "compromised", "otp"])
        
        # Check urgency/account threat keywords
        has_urgency = any(kw in text_lower for kw in ["block", "suspend", "deactivat", "freez", "disabl", "today", "immediately", "expired", "action required", "notice"])
        
        # Check link/url or contact markers
        has_link = any(kw in text_lower for kw in ["http://", "https://", ".gy", "bit.ly", "tinyurl", "t.co", ".link", ".cc", ".top", ".xyz", "visit", "click"])

        if has_bank or has_identity or has_urgency or has_link:
            phishing_signals = 0
            if has_bank:
                phishing_signals += 1
            if has_identity:
                phishing_signals += 1
            if has_urgency:
                phishing_signals += 1
            if has_link:
                phishing_signals += 1

            if phishing_signals >= 3:
                score_val += 75
                cat = "KYC Verification Scam"
                indicators.append("Urgent security/KYC/PAN update demand linked to account suspension")
                indicators.append("Presence of external suspicious links/URLs requesting credentials")
                victim_instructions.extend([
                    "Do not click on links in unsolicited messages claiming your bank account is blocked.",
                    "Verify the status of your account directly via the bank's official app or official hotline."
                ])
            elif phishing_signals == 2:
                score_val += 45
                if cat == "Suspected Scam":
                    cat = "KYC Verification Scam"
                indicators.append("Suspicious account action or verification request detected")
                if has_link:
                    indicators.append("Presence of external link or call-to-action")
            else:
                score_val += 15

        # 4. Job / Part-time Tasks Scam
        if any(kw in text_lower for kw in ["job", "part-time", "part time", "salary", "earn", "commission", "youtube likes", "telegram tasks"]):
            score_val += 35
            indicators.append("Unsolicited offers promising easy money or task-based commission")
            if cat == "Suspected Scam":
                cat = "Lottery/Job Scam"
            victim_instructions.extend([
                "Be wary of jobs requiring upfront deposits or paying for video likes and Telegram tasks.",
                "Legitimate organizations do not charge fees to secure employment."
            ])

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

        # Unique list of indicators and instructions to keep it clean
        unique_indicators = list(dict.fromkeys(indicators))
        unique_instructions = list(dict.fromkeys(victim_instructions))

        # Dynamic confidence score based on the strength of signals matched
        confidence_val = 0.80
        if len(unique_indicators) >= 2:
            confidence_val = 0.90
        elif len(unique_indicators) == 0:
            confidence_val = 0.50

        reasoning = {
            "key_indicators": unique_indicators or ["Suspicious communications requesting attention"],
            "victim_instructions": unique_instructions,
            "risk_explanation": f"Evaluated based on suspicious keywords representing {cat} patterns."
        }

        return score_val, band, cat, confidence_val, reasoning, True

threat_evaluator_agent = ThreatEvaluatorAgent()
