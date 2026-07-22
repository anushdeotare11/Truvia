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
            from app.core.genai_helper import configure_genai
            configure_genai(self.api_key)
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
                from app.core.config_check import is_gemini_enabled
                if self.client and is_gemini_enabled() and cleaned_texts:
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
            import google.api_core.exceptions as exc
            if isinstance(e, exc.Unauthenticated):
                logger.error(f"Failed to generate LLM summary with 401 Unauthenticated: {str(e)}. Disabling Gemini integration.")
                from app.core.config_check import disable_gemini
                disable_gemini()
            else:
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

    async def generate_ring_summary(self, entity_ids: list) -> dict:
        """
        Generate a ring-level intelligence summary for a set of entities
        identified as a fraud ring cluster. Fetches all linked reports and
        compiles a comprehensive ring-level intelligence briefing.
        """
        import uuid
        import re

        # Normalize entity IDs to UUID objects
        parsed_ids = []
        for eid in entity_ids:
            if isinstance(eid, str):
                parsed_ids.append(uuid.UUID(eid))
            else:
                parsed_ids.append(eid)

        async with AsyncSessionLocal() as session:
            try:
                # Fetch all entities matching the provided IDs
                entities_result = await session.execute(
                    select(Entity).where(Entity.id.in_(parsed_ids))
                )
                entities = entities_result.scalars().all()

                # Get distinct phones and UPIs from the entities
                phone_list = [e.raw_value for e in entities if e.type == "phone"]
                upi_list = [e.raw_value for e in entities if e.type == "upi"]

                # Fetch all reports linked to these entities via ReportEntity join
                report_entity_result = await session.execute(
                    select(Report)
                    .join(ReportEntity, ReportEntity.report_id == Report.id)
                    .where(ReportEntity.entity_id.in_(parsed_ids))
                    .distinct()
                )
                reports = report_entity_result.scalars().all()

                total_reports = len(reports)
                if total_reports == 0:
                    return {
                        "summary": "No reports linked to the specified entities.",
                        "primary_patterns": [],
                        "total_victims": 0,
                        "total_reports": 0,
                        "estimated_losses": 0.0,
                        "key_entities": [],
                    }

                # Get cleaned_text from all linked reports
                cleaned_texts = [r.cleaned_text for r in reports if r.cleaned_text]

                # Count total unique victims (distinct user_ids across reports)
                total_victims = len(set(r.user_id for r in reports))

                # Top entity values (by occurrence count or just raw values)
                key_entities = sorted(
                    [e.raw_value for e in entities if e.raw_value],
                    key=lambda v: v
                )[:10]

                # Generate summary using LLM or local fallback
                from app.core.config_check import is_gemini_enabled
                if self.client and is_gemini_enabled() and cleaned_texts:
                    summary_data = await self._generate_ring_llm_summary(
                        cleaned_texts, phone_list, upi_list, total_victims, total_reports
                    )
                else:
                    summary_data = await self._generate_ring_local_summary(
                        cleaned_texts, phone_list, upi_list, total_victims, total_reports
                    )

                # Ensure all required fields are present
                summary_data.setdefault("total_victims", total_victims)
                summary_data.setdefault("total_reports", total_reports)
                summary_data.setdefault("key_entities", key_entities)

                return summary_data

            except Exception as e:
                logger.error(f"generate_ring_summary failed: {str(e)}")
                return {
                    "summary": f"Error generating ring summary: {str(e)}",
                    "primary_patterns": [],
                    "total_victims": 0,
                    "total_reports": 0,
                    "estimated_losses": 0.0,
                    "key_entities": [],
                }

    async def _generate_ring_llm_summary(
        self, texts: list, phones: list, upis: list, total_victims: int, total_reports: int
    ) -> dict:
        """
        Uses LLM to generate a ring-level intelligence briefing.
        """
        try:
            prompt = (
                "You are Truvia's Senior Cybercrime Investigator. Analyze the following group of complaints "
                "linked to an identified fraud ring cluster. Compile a comprehensive ring-level intelligence briefing.\n\n"
                f"Total Reports in Ring: {total_reports}\n"
                f"Total Unique Victims: {total_victims}\n"
                f"Complaint Transcripts:\n{chr(10).join(texts[:20])}\n\n"
                f"Linked Phones: {', '.join(set(phones))}\n"
                f"Linked UPI Addresses: {', '.join(set(upis))}\n\n"
                "Return a JSON block containing:\n"
                "1. \"summary\": A comprehensive ring intelligence briefing paragraph detailing the ring's modus operandi, "
                "scale of operations, victim targeting patterns, and key identifiers.\n"
                "2. \"primary_patterns\": A list of key operating patterns identified across the ring.\n"
                "3. \"estimated_losses\": A float estimate of total ring losses based on evidence.\n\n"
                "Format output STRICTLY as valid JSON."
            )

            response = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            raw_content = response.text.strip()
            start_idx = raw_content.find("{")
            end_idx = raw_content.rfind("}")
            if start_idx != -1 and end_idx != -1:
                result = json.loads(raw_content[start_idx:end_idx + 1])
                result.setdefault("summary", "")
                result.setdefault("primary_patterns", [])
                result.setdefault("estimated_losses", 0.0)
                return result
            return {
                "summary": raw_content,
                "primary_patterns": [],
                "estimated_losses": 0.0,
            }
        except Exception as e:
            import google.api_core.exceptions as exc
            if isinstance(e, exc.Unauthenticated):
                logger.error(f"Ring LLM summary failed with 401 Unauthenticated: {str(e)}. Disabling Gemini integration.")
                from app.core.config_check import disable_gemini
                disable_gemini()
            else:
                logger.error(f"Ring LLM summary failed: {str(e)}")
            return await self._generate_ring_local_summary(texts, phones, upis, total_victims, total_reports)

    async def _generate_ring_local_summary(
        self, texts: list, phones: list, upis: list, total_victims: int, total_reports: int
    ) -> dict:
        """
        Deterministic ring-level summary built from actual evidence when LLM is unavailable.
        Counts reports, detects patterns from text content, sums mentioned monetary amounts.
        """
        import re

        blob = "\n".join(texts).lower()

        # Detect operating patterns from the real content
        patterns = []
        if any(w in blob for w in ["arrest", "police", "customs", "cbi", "custody", "narcotic"]):
            patterns.append("Digital-arrest intimidation (impersonation of law enforcement)")
        if any(w in blob for w in ["upi", "qr", "collect", "refund", "pin"]):
            patterns.append("UPI collect-request / refund redirection")
        if any(w in blob for w in ["kyc", "account", "suspend", "block", "netbanking", "otp"]):
            patterns.append("KYC / credential-harvesting phishing")
        if any(w in blob for w in ["electricity", "bill", "disconnect", "power"]):
            patterns.append("Utility-disconnection payment pressure")
        if any(w in blob for w in ["job", "hiring", "salary", "placement", "interview"]):
            patterns.append("Fake job / recruitment scam")
        if any(w in blob for w in ["loan", "emi", "processing fee", "pre-approved"]):
            patterns.append("Loan fraud / advance-fee scheme")
        if any(w in blob for w in ["invest", "trading", "crypto", "stock", "return", "profit"]):
            patterns.append("Investment / Ponzi scheme")
        if any(w in blob for w in ["video", "nude", "compromising", "blackmail", "sextort"]):
            patterns.append("Sextortion / blackmail")
        if not patterns:
            patterns.append("Social-engineering credential harvest")

        # Extract monetary amounts mentioned (INR / Rs / rupees)
        amounts = []
        for m in re.findall(r"(?:rs\.?|inr|rupees?)\s*([0-9][0-9,]{2,})", blob):
            try:
                amounts.append(int(m.replace(",", "")))
            except ValueError:
                continue
        estimated_losses = float(sum(amounts)) if amounts else 0.0

        distinct_phones = sorted(set(p for p in phones if p))
        distinct_upis = sorted(set(u for u in upis if u))

        # Build summary narrative
        parts = [
            f"Fraud ring intelligence briefing: This cluster comprises {total_reports} linked complaint(s) "
            f"affecting {total_victims} unique victim(s).",
            f"Detected operating pattern(s): {', '.join(patterns)}.",
        ]
        if distinct_phones or distinct_upis:
            frag = []
            if distinct_phones:
                frag.append(f"{len(distinct_phones)} distinct phone number(s) (e.g. {', '.join(distinct_phones[:3])})")
            if distinct_upis:
                frag.append(f"{len(distinct_upis)} UPI handle(s) (e.g. {', '.join(distinct_upis[:3])})")
            parts.append("Key ring identifiers: " + "; ".join(frag) + ".")
        if amounts:
            parts.append(
                f"Total monetary losses extracted from evidence: approximately INR {estimated_losses:,.0f}."
            )
        summary = " ".join(parts)

        return {
            "summary": summary,
            "primary_patterns": patterns,
            "total_victims": total_victims,
            "total_reports": total_reports,
            "estimated_losses": estimated_losses,
            "key_entities": [],
        }


investigation_agent = InvestigationAgent()
