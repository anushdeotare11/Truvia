import os
import base64
import json
import logging
import asyncio
from sqlalchemy import select, update
import google.generativeai as genai
from app.config import settings
from app.data.postgres_client import AsyncSessionLocal
from app.models.report import Report, Evidence
from app.data.storage_client import storage_client

logger = logging.getLogger("truvia.agents.input_processor")

# ---------------------------------------------------------------------------
# Lazy, process-wide singletons for the local (offline, no cloud key required)
# OCR and STT engines. They are relatively expensive to initialise/load, so we
# build them once on first use and reuse them across requests. All heavy calls
# are dispatched via asyncio.to_thread so they never block the event loop.
# ---------------------------------------------------------------------------
_rapidocr_engine = None
_whisper_model = None


def _get_ocr_engine():
    """Return a cached RapidOCR engine (bundled ONNX models, fully offline)."""
    global _rapidocr_engine
    if _rapidocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _rapidocr_engine = RapidOCR()
            logger.info("Local RapidOCR engine initialised (offline OCR).")
        except Exception as e:
            logger.warning(f"Local RapidOCR engine unavailable, using Cloud Gemini Vision: {e}")
            return None
    return _rapidocr_engine


def _get_whisper_model():
    """Return a cached faster-whisper model (CPU int8). Downloads once, then cached."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("Local faster-whisper model initialised (offline ASR).")
        except Exception as e:
            logger.warning(f"Local faster-whisper model unavailable, using Cloud Gemini Audio: {e}")
            return None
    return _whisper_model

class InputProcessorAgent:
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        # Check if the API key is set and not empty/placeholder
        if self.api_key and "your-google-key" not in self.api_key and len(self.api_key) > 10:
            from app.core.genai_helper import configure_genai
            configure_genai(self.api_key)
            self.client = genai.GenerativeModel("gemini-1.5-flash")
            logger.info("Initialized InputProcessorAgent with Google Gemini API client")
        else:
            self.client = None
            logger.warning("No Google API key configured. Running InputProcessorAgent in degraded mock mode.")

    async def warm_engines(self) -> None:
        """
        Preload the local OCR and STT engines so the FIRST citizen upload does not
        pay the one-time model-load/download latency (which can otherwise exceed the
        frontend's result-polling window and surface as a spurious "no verdict").
        Runs off the event loop; failures are non-fatal (engines lazy-load on demand).
        """
        def _load():
            try:
                _get_ocr_engine()
            except Exception as e:
                logger.warning(f"OCR engine warmup skipped: {e}")
            try:
                _get_whisper_model()
            except Exception as e:
                logger.warning(f"ASR engine warmup skipped: {e}")
        try:
            await asyncio.to_thread(_load)
            logger.info("Local OCR/STT engines warmed up.")
        except Exception as e:
            logger.warning(f"Engine warmup failed (will lazy-load on demand): {e}")

    async def process_report(self, report_id: str) -> dict:
        """
        Main entry point for Agent 1. Fetches report and evidence, extracts text,
        detects language, evaluates confidence, and updates report state in the database.
        """
        import uuid
        if isinstance(report_id, str):
            report_id = uuid.UUID(report_id)
            
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
                        text_out, lang, conf = await self._asr_audio(file_bytes, ext, ev.file_ref)
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
                cleaned_text = "\n\n".join(t for t in extractions if t).strip()
                if not cleaned_text and report.cleaned_text:
                    cleaned_text = report.cleaned_text  # Fallback to direct input text

                # For pasted text (or when we fell back to the directly submitted text),
                # there is no OCR/ASR confidence to worry about — run real language
                # detection so downstream analysis and the UI reflect the true language.
                if report.source_type == "text" or not evidence_list:
                    if cleaned_text:
                        detected_lang = await self._detect_language_local(cleaned_text)
                        input_confidence = 1.0

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
        Runs OCR. Uses Gemini Multimodal API if configured, otherwise rules-based mock.
        """
        from app.core.config_check import is_gemini_enabled
        if self.client and is_gemini_enabled():
            try:
                import io
                import PIL.Image
                try:
                    image_input = PIL.Image.open(io.BytesIO(image_bytes))
                except Exception:
                    mime_map = {".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
                    mime = mime_map.get(extension.lower(), "image/jpeg")
                    image_input = {"mime_type": mime, "data": image_bytes}

                prompt = (
                    "Please extract all text content from this screenshot. "
                    "This screenshot is a report of a digital scam or cybercrime. "
                    "Identify the language of the text (e.g., 'en', 'hi', or 'hinglish'). "
                    "Rate your confidence in the transcription from 0.0 to 1.0. "
                    "Format the response exactly as a JSON object with keys: "
                    "'extracted_text', 'language', and 'confidence'. Keep confidence under 1.0."
                )

                response = await asyncio.to_thread(
                    self.client.generate_content,
                    [image_input, prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # Parse JSON response
                res_content = response.text.strip()
                # Find JSON bounds in case LLM wraps it in markdown
                if "```json" in res_content:
                    res_content = res_content.split("```json")[1].split("```")[0].strip()
                elif "```" in res_content:
                    res_content = res_content.split("```")[1].split("```")[0].strip()
                    
                data = json.loads(res_content)
                text = data.get("extracted_text", "").strip()
                if text:
                    return (
                        text,
                        data.get("language", "en"),
                        float(data.get("confidence", 0.95))
                    )
                logger.info("Gemini OCR returned empty text. Trying local RapidOCR engine...")
            except Exception as e:
                import google.api_core.exceptions as exc
                if isinstance(e, exc.Unauthenticated):
                    logger.error(f"Gemini Multimodal OCR failed with 401 Unauthenticated: {str(e)}. Disabling Gemini integration and falling back to local OCR engine.")
                    from app.core.config_check import disable_gemini
                    disable_gemini()
                else:
                    logger.error(f"Gemini Multimodal OCR failed: {str(e)}. Falling back to local OCR engine.")

        # Real on-device OCR (no cloud key required) via RapidOCR (bundled ONNX models).
        local_text, local_conf = await self._local_ocr(image_bytes)
        if local_text and local_text.strip():
            lang = await self._detect_language_local(local_text)
            return local_text.strip(), lang, float(local_conf)

        # Genuinely no readable text could be extracted. Do NOT fabricate content —
        # return an empty, zero-confidence result. The pipeline still proceeds to
        # scoring, which yields an explicit "insufficient content" verdict.
        logger.warning(
            "OCR produced no readable text for this image (empty extraction). "
            "Returning empty, zero-confidence result."
        )
        return "", "und", 0.0

    async def _local_ocr(self, image_bytes: bytes) -> tuple[str, float]:
        """
        Real on-device OCR using RapidOCR (ONNX). Returns (text, mean_confidence).
        Never fabricates content — returns ("", 0.0) if nothing is detected or the
        engine is unavailable.
        """
        def _run() -> tuple[str, float]:
            try:
                import io
                import numpy as np
                import PIL.Image

                engine = _get_ocr_engine()
                image = PIL.Image.open(io.BytesIO(image_bytes)).convert("RGB")
                arr = np.array(image)
                result, _elapse = engine(arr)
                if not result:
                    return "", 0.0
                texts = [row[1] for row in result]
                confs = [float(row[2]) for row in result]
                joined = " ".join(t for t in texts if t).strip()
                mean_conf = (sum(confs) / len(confs)) if confs else 0.0
                return joined, mean_conf
            except Exception as e:
                logger.error(f"Local RapidOCR failed: {str(e)}")
                return "", 0.0

        return await asyncio.to_thread(_run)

    async def _asr_audio(self, audio_bytes: bytes, extension: str, file_ref: str = "") -> tuple[str, str, float]:
        """
        Transcribes audio recordings using OpenAI Whisper API if configured,
        otherwise falls back to a content-aware dynamic mock.
        """
        openai_key = getattr(settings, "OPENAI_API_KEY", None)
        if openai_key and "your-openai-key" not in openai_key and len(openai_key) > 10:
            import httpx
            try:
                headers = {"Authorization": f"Bearer {openai_key}"}
                # Whisper requires multipart file upload
                files = {
                    "file": (f"audio{extension}", audio_bytes, f"audio/{extension.strip('.')}")
                }
                data = {
                    "model": "whisper-1",
                    "response_format": "json"
                }
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers=headers,
                        files=files,
                        data=data,
                        timeout=30.0
                    )
                    if resp.status_code == 200:
                        res_json = resp.json()
                        text = res_json.get("text", "")
                        return text, "en", 0.95
                    else:
                        logger.error(f"OpenAI Whisper API returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"OpenAI Whisper API call failed: {str(e)}")

        # Real on-device speech-to-text (no cloud key required) via faster-whisper.
        local_text, local_lang, local_conf = await self._local_asr(audio_bytes, extension)
        if local_text and local_text.strip():
            return local_text.strip(), local_lang, float(local_conf)

        # Genuinely no speech could be transcribed. Do NOT fabricate a transcript.
        # The pipeline still proceeds to scoring -> explicit "insufficient content" verdict.
        logger.warning(
            "ASR produced no transcript for this audio (empty result). "
            "Returning empty, zero-confidence result."
        )
        return "", "und", 0.0

    async def _local_asr(self, audio_bytes: bytes, extension: str) -> tuple[str, str, float]:
        """
        Real on-device transcription using faster-whisper. faster-whisper bundles
        audio decoding (PyAV), so mp3/m4a/ogg/wav all work without system ffmpeg.
        Returns (transcript, language, confidence). Never fabricates content.
        """
        def _run() -> tuple[str, str, float]:
            import os
            import math
            import tempfile

            tmp_path = None
            try:
                model = _get_whisper_model()
                suffix = extension if extension else ".wav"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name

                segments, info = model.transcribe(tmp_path, beam_size=1)
                texts = []
                logprobs = []
                for seg in segments:
                    texts.append(seg.text)
                    logprobs.append(seg.avg_logprob)
                transcript = " ".join(t.strip() for t in texts).strip()
                # Convert mean token log-probability into a rough 0..1 confidence.
                conf = math.exp(sum(logprobs) / len(logprobs)) if logprobs else 0.0
                lang = info.language or "en"
                return transcript, lang, float(min(max(conf, 0.0), 0.99))
            except Exception as e:
                logger.error(f"Local faster-whisper ASR failed: {str(e)}")
                return "", "und", 0.0
            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

        return await asyncio.to_thread(_run)

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
