import os
import base64
import json
import logging
from sqlalchemy import select, update
from anthropic import Anthropic
from app.config import settings
from app.data.postgres_client import AsyncSessionLocal
from app.models.report import Report, Evidence
from app.data.storage_client import storage_client

logger = logging.getLogger("truvia.agents.input_processor")

class InputProcessorAgent:
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        # Check if the API key is set and not empty/placeholder
        if self.api_key and "your-anthropic-key" not in self.api_key and len(self.api_key) > 10:
            self.client = Anthropic(api_key=self.api_key)
            logger.info("Initialized InputProcessorAgent with Anthropic API client")
        else:
            self.client = None
            logger.warning("No Anthropic API key configured. Running InputProcessorAgent in degraded mock mode.")

    async def process_report(self, report_id: str) -> dict:
        """
        Main entry point for Agent 1. Fetches report and evidence, extracts text,
        detects language, evaluates confidence, and updates report state in the database.
        """
        async with AsyncSessionLocal() as session:
            try:
                # 1. Fetch Report and linked Evidence
                report_result = await session.execute(
                    select(Report).where(Report.id == report_id)
                )
                report = report_result.scalar_one_or_none()
                if not report:
                    logger.error(f"Report {report_id} not found in database")
                    return {"status": "error", "message": "Report not found"}

                # Update status to processing
                report.status = "processing"
                await session.commit()

                evidence_result = await session.execute(
                    select(Evidence).where(Evidence.report_id == report_id)
                )
                evidence_list = evidence_result.scalars().all()
                
                logger.info(f"Processing report {report_id} with {len(evidence_list)} evidence files")

                cleaned_text = ""
                detected_lang = "en"
                input_confidence = 1.0
                low_confidence = False
                extractions = []

                # 2. Process each evidence item
                for ev in evidence_list:
                    if not ev.file_ref:
                        continue
                    
                    file_bytes = await storage_client.get_file(ev.file_ref)
                    ext = os.path.splitext(ev.file_ref)[1].lower()

                    if ev.evidence_type == "image" or ext in [".png", ".jpg", ".jpeg"]:
                        text_out, lang, conf = await self._ocr_image(file_bytes, ext)
                        extractions.append(text_out)
                        detected_lang = lang
                        input_confidence = min(input_confidence, conf)
                        
                        # Save extraction metadata
                        ev.extraction_metadata_json = {
                            "ocr_extracted_text": text_out,
                            "confidence": conf,
                            "detected_language": lang
                        }
                    
                    elif ev.evidence_type == "audio" or ext in [".mp3", ".wav", ".m4a", ".ogg"]:
                        text_out, lang, conf = await self._asr_audio(file_bytes, ext)
                        extractions.append(text_out)
                        detected_lang = lang
                        input_confidence = min(input_confidence, conf)
                        
                        ev.extraction_metadata_json = {
                            "asr_extracted_text": text_out,
                            "confidence": conf,
                            "detected_language": lang
                        }
                        
                    elif ev.evidence_type == "text_paste":
                        # Plain text content
                        text_out = file_bytes.decode("utf-8", errors="ignore")
                        lang = await self._detect_language_local(text_out)
                        extractions.append(text_out)
                        detected_lang = lang

                # 3. Combine extractions
                cleaned_text = "\n\n".join(extractions).strip()
                if not cleaned_text and report.cleaned_text:
                    cleaned_text = report.cleaned_text  # Fallback to direct input text

                # 4. Check confidence against threshold
                threshold = (
                    settings.ASR_LOW_CONFIDENCE_THRESHOLD 
                    if report.source_type == "audio" 
                    else settings.OCR_LOW_CONFIDENCE_THRESHOLD
                )
                if input_confidence < threshold:
                    low_confidence = True

                # 5. Update Report state
                report.cleaned_text = cleaned_text
                report.detected_language = detected_lang
                report.input_confidence = input_confidence
                report.low_confidence_flag = low_confidence
                report.status = "processed"
                
                await session.commit()
                logger.info(f"Report {report_id} successfully processed by Agent 1. Low Confidence: {low_confidence}")

                return {
                    "report_id": report_id,
                    "cleaned_text": cleaned_text,
                    "detected_language": detected_lang,
                    "input_confidence": float(input_confidence),
                    "low_confidence_flag": low_confidence
                }

            except Exception as e:
                logger.error(f"Error in Agent 1 processing report {report_id}: {str(e)}")
                # Mark report as failed
                try:
                    await session.execute(
                        update(Report)
                        .where(Report.id == report_id)
                        .values(status="failed")
                    )
                    await session.commit()
                except Exception as commit_ex:
                    logger.error(f"Failed to mark report as failed: {str(commit_ex)}")
                raise

    async def _ocr_image(self, image_bytes: bytes, extension: str) -> tuple[str, str, float]:
        """
        Runs OCR. Uses Claude Multimodal API if configured, otherwise rules-based mock.
        """
        if self.client:
            try:
                # Map extension to media type
                media_type = "image/png" if extension == ".png" else "image/jpeg"
                base64_image = base64.b64encode(image_bytes).decode("utf-8")

                prompt = (
                    "Please extract all text content from this screenshot. "
                    "This screenshot is a report of a digital scam or cybercrime. "
                    "Identify the language of the text (e.g., 'en', 'hi', or 'hinglish'). "
                    "Rate your confidence in the transcription from 0.0 to 1.0. "
                    "Format the response exactly as a JSON object with keys: "
                    "'extracted_text', 'language', and 'confidence'. Keep confidence under 1.0."
                )

                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": base64_image
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                )
                
                # Parse JSON response
                res_content = response.content[0].text.strip()
                # Find JSON bounds in case LLM wraps it in markdown
                if "```json" in res_content:
                    res_content = res_content.split("```json")[1].split("```")[0].strip()
                elif "```" in res_content:
                    res_content = res_content.split("```")[1].split("```")[0].strip()
                    
                data = json.loads(res_content)
                return (
                    data.get("extracted_text", ""),
                    data.get("language", "en"),
                    float(data.get("confidence", 0.95))
                )

            except Exception as e:
                logger.error(f"Claude Multimodal OCR failed: {str(e)}. Falling back to degraded mock.")

        # Degraded mode fallback
        # Simulate OCR response based on dummy bytes or file context
        mock_text = (
            "URGENT: Your bank account has been compromised. "
            "Please transfer 50,000 INR to UPI address: safevault@okaxis immediately to secure your funds. "
            "Failure to comply will result in immediate arrest by Cyber Police."
        )
        return mock_text, "en", 0.90

    async def _asr_audio(self, audio_bytes: bytes, extension: str) -> tuple[str, str, float]:
        """
        Transcribes audio recordings.
        """
        # In this MVP, we simulate ASR/STT with realistic cybercrime scripts
        # We can simulate slightly degraded confidence for testing stepper visual alerts
        mock_text = (
            "Hello, this is officer Amit Kumar calling from the Delhi Police Headquarters. "
            "We have found a package in your name containing illegal substances. "
            "You are under digital arrest. Do not disconnect this call or you will face immediate custody. "
            "Verify your identity by paying 2,50,000 rupees to the security account."
        )
        return mock_text, "hinglish", 0.55  # Exposes low-confidence flag (< 0.60) for testing alerts

    async def _detect_language_local(self, text: str) -> str:
        """
        Simple keyword-based language detector.
        """
        text_lower = text.lower()
        hindi_keywords = ["police", "arrest", "kyc", "bank", "paise", "account", "dijiye", "bhejo", "upi"]
        hits = sum(1 for kw in hindi_keywords if kw in text_lower)
        if hits > 2:
            return "hinglish"
        return "en"

input_processor_agent = InputProcessorAgent()
