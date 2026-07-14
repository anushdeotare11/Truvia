import logging
import json
import asyncio
from sqlalchemy import select
from app.data.postgres_client import AsyncSessionLocal
from app.models.case import Case, CaseReport
from app.models.report import Report, Entity, ReportEntity
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger("truvia.agents.investigation")

class InvestigationAgent:
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        if self.api_key and "your-google-key" not in self.api_key and len(self.api_key) > 10:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel("gemini-1.5-flash")
            logger.info("Initialized InvestigationAgent with Google Gemini API")
        else:
            self.client = None
            logger.warning("No Google API Key configured. Running InvestigationAgent in degraded local mode.")

    async def summarize_case(self, case_id: str) -> dict:
        """
        Main entry point for Agent 6. Summarizes a multi-complaint case,
        extracting primary targets, operating patterns, and loss estimates.
        """
        import uuid
        if isinstance(case_id, str):
            case_id = uuid.UUID(case_id)

        async with AsyncSessionLocal() as session:
            try:
                # 1. Fetch Case
                case_result = await session.execute(
                    select(Case).where(Case.id == case_id)
                )
                case = case_result.scalar_one_or_none()
                if not case:
                    return {"status": "error", "message": "Case not found"}

                # 2. Fetch linked Reports
                reports_result = await session.execute(
                    select(Report)
                    .join(CaseReport, CaseReport.report_id == Report.id)
                    .where(CaseReport.case_id == case.id)
                )
                reports = reports_result.scalars().all()

                if not reports:
                    return {
                        "summary": "No reports linked to this case yet.",
                        "primary_patterns": [],
                        "estimated_losses": 0.0
                    }

                # 3. Fetch linked Entities
                report_ids = [r.id for r in reports]
                entities_result = await session.execute(
                    select(Entity)
                    .join(ReportEntity, ReportEntity.entity_id == Entity.id)
                    .where(ReportEntity.report_id.in_(report_ids))
                )
                entities = entities_result.scalars().all()

                # Group values for prompt/rules
                phone_list = [e.raw_value for e in entities if e.type == "phone"]
                upi_list = [e.raw_value for e in entities if e.type == "upi"]
                cleaned_texts = [r.cleaned_text for r in reports if r.cleaned_text]

                # 4. Generate Summary
                if self.client and cleaned_texts:
                    summary_data = await self._generate_llm_summary(cleaned_texts, phone_list, upi_list)
                else:
                    summary_data = await self._generate_local_summary(cleaned_texts, phone_list, upi_list)

                # 5. Save summary back to Case
                case.ai_summary = summary_data["summary"]
                await session.commit()

                return summary_data

            except Exception as e:
                logger.error(f"InvestigationAgent failed for case {case_id}: {str(e)}")
                return {"status": "error", "message": str(e)}

    async def _generate_llm_summary(self, texts: list, phones: list, upis: list) -> dict:
        """
        Calls Claude to compile the investigation dossier.
        """
        try:
            prompt = (
                "You are Truvia's Senior Cybercrime Investigator. Analyze the following group of complaints "
                "representing an active fraud ring. Compile a structured intelligence briefing.\n\n"
                f"Complaint Transcripts:\n{chr(10).join(texts)}\n\n"
                f"Linked Phones: {', '.join(set(phones))}\n"
                f"Linked UPI Addresses: {', '.join(set(upis))}\n\n"
                "Return a JSON block containing:\n"
                "1. \"summary\": A paragraph detailing the scam modus operandi, operating hours, and victim pressure tactics.\n"
                "2. \"primary_patterns\": A list of key operating patterns identified.\n"
                "3. \"estimated_losses\": An estimated float value of total ring losses (extracting values from texts or making a computed estimate).\n\n"
                "Format output STRICTLY as valid JSON."
            )

            response = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            raw_content = response.text.strip()
            # Parse json safely
            start_idx = raw_content.find("{")
            end_idx = raw_content.rfind("}")
            if start_idx != -1 and end_idx != -1:
                return json.loads(raw_content[start_idx:end_idx+1])
            return {"summary": raw_content, "primary_patterns": [], "estimated_losses": 0.0}
        except Exception as e:
            logger.error(f"Failed to generate LLM summary: {str(e)}")
            return await self._generate_local_summary(texts, phones, upis)

    async def _generate_local_summary(self, texts: list, phones: list, upis: list) -> dict:
        """
        Deterministic, degraded-mode summary composed from the ACTUAL case facts
        (number of complaints, scam patterns detected in the real text, distinct
        linked identifiers, and monetary amounts actually mentioned). No canned prose
        and no fabricated loss figure — everything here is derived from the inputs.
        """
        import re

        num = len(texts)
        blob = "\n".join(texts).lower()

        # Detect operating patterns from the real content.
        patterns = []
        if any(w in blob for w in ["arrest", "police", "customs", "cbi", "custody", "narcotic"]):
            patterns.append("Digital-arrest intimidation (impersonation of law enforcement)")
        if any(w in blob for w in ["upi", "qr", "collect", "refund", "pin"]):
            patterns.append("UPI collect-request / refund redirection")
        if any(w in blob for w in ["kyc", "account", "suspend", "block", "netbanking", "otp"]):
            patterns.append("KYC / credential-harvesting phishing")
        if any(w in blob for w in ["electricity", "bill", "disconnect", "power"]):
            patterns.append("Utility-disconnection payment pressure")
        if not patterns:
            patterns.append("Social-engineering credential harvest")

        # Extract monetary amounts actually mentioned (INR / Rs / rupees).
        amounts = []
        for m in re.findall(r"(?:rs\.?|inr|rupees?)\s*([0-9][0-9,]{2,})", blob):
            try:
                amounts.append(int(m.replace(",", "")))
            except ValueError:
                continue
        estimated_losses = float(sum(amounts)) if amounts else 0.0

        distinct_phones = sorted(set(p for p in phones if p))
        distinct_upis = sorted(set(u for u in upis if u))

        parts = [
            f"This case aggregates {num} linked complaint(s).",
            f"Detected operating pattern(s): {', '.join(patterns)}.",
        ]
        if distinct_phones or distinct_upis:
            frag = []
            if distinct_phones:
                frag.append(f"{len(distinct_phones)} distinct phone number(s) (e.g. {', '.join(distinct_phones[:3])})")
            if distinct_upis:
                frag.append(f"{len(distinct_upis)} UPI handle(s) (e.g. {', '.join(distinct_upis[:3])})")
            parts.append("Recurring identifiers across the evidence: " + "; ".join(frag) + ".")
        if amounts:
            parts.append(
                f"Amounts explicitly demanded in the evidence total approximately INR {estimated_losses:,.0f}."
            )
        summary = " ".join(parts)

        return {
            "summary": summary,
            "primary_patterns": patterns,
            "estimated_losses": estimated_losses,
        }

investigation_agent = InvestigationAgent()
