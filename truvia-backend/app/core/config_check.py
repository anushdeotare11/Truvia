"""
Startup configuration check.

Surfaces — loudly and honestly — which external credentials/services are
configured and which are missing. The platform is designed to degrade
gracefully (rule-based threat scoring, lexical RAG, honest low-confidence OCR/ASR)
rather than fabricate data, so a missing key is a *capability* limitation, not a
crash. This report makes that state explicit for operators instead of hiding it.
"""
from __future__ import annotations

import logging
from typing import Dict

from app.config import settings

logger = logging.getLogger("truvia.config_check")


_gemini_disabled = False


def disable_gemini() -> None:
    global _gemini_disabled
    if not _gemini_disabled:
        _gemini_disabled = True
        logger.warning("Google Gemini integrations have been disabled due to invalid credentials.")


def is_gemini_enabled() -> bool:
    global _gemini_disabled
    if _gemini_disabled:
        return False
    return _key_present(settings.GOOGLE_API_KEY, "your-google-key")


async def verify_gemini_key_background() -> None:
    """Verify the Gemini API key in the background on startup."""
    import google.generativeai as genai
    import google.api_core.exceptions as exc
    import asyncio

    if not is_gemini_enabled():
        return

    key = settings.GOOGLE_API_KEY
    try:
        from app.core.genai_helper import configure_genai
        configure_genai(key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Verifying Google Gemini API key credentials in background...")
        await asyncio.wait_for(
            asyncio.to_thread(
                model.generate_content,
                "ping",
                generation_config={"max_output_tokens": 1}
            ),
            timeout=5.0
        )
        logger.info("Google Gemini API key credentials verified successfully.")
    except exc.Unauthenticated as e:
        logger.error(f"Google Gemini key validation failed with 401 Unauthenticated: {e}. Disabling Gemini integrations.")
        disable_gemini()
    except Exception as e:
        logger.warning(f"Google Gemini key validation check returned exception: {e}. Keeping integration active.")


def _key_present(value: str | None, placeholder_fragment: str) -> bool:
    return bool(value and placeholder_fragment not in value and len(value) > 10)


def get_capability_report() -> Dict[str, Dict[str, object]]:
    """Return a structured report of AI/data capabilities and their config state."""
    gemini_ok = is_gemini_enabled()
    openai_ok = _key_present(settings.OPENAI_API_KEY, "your-openai-key")

    # Offline OCR (RapidOCR/ONNX) — bundled models, no cloud key or system binary.
    try:
        import rapidocr_onnxruntime  # noqa: F401
        local_ocr_ok = True
    except Exception:
        local_ocr_ok = False

    # Offline STT (faster-whisper) — model auto-downloads once, then cached.
    try:
        import faster_whisper  # noqa: F401
        local_asr_ok = True
    except Exception:
        local_asr_ok = False

    return {
        "image_ocr": {
            "configured": gemini_ok or local_ocr_ok,
            "provider": "gemini-vision" if gemini_ok else ("local-rapidocr" if local_ocr_ok else None),
            "missing": None if (gemini_ok or local_ocr_ok)
            else "Install rapidocr-onnxruntime (offline) or set GOOGLE_API_KEY (Gemini vision).",
        },
        "audio_asr": {
            "configured": openai_ok or local_asr_ok,
            "provider": "openai-whisper" if openai_ok else ("local-faster-whisper" if local_asr_ok else None),
            "missing": None if (openai_ok or local_asr_ok)
            else "Install faster-whisper (offline) or set OPENAI_API_KEY (Whisper API).",
        },
        "llm_threat_reasoning": {
            "configured": gemini_ok,
            "provider": "gemini-2.0-flash" if gemini_ok else "local-rule-engine",
            "missing": None if gemini_ok
            else "Set GOOGLE_API_KEY to enable LLM-based structured reasoning (rule engine used meanwhile).",
        },
        "rag_chat_llm": {
            "configured": gemini_ok,
            "provider": "gemini-2.0-flash" if gemini_ok else "local-grounded-answers",
            "missing": None if gemini_ok
            else "Set GOOGLE_API_KEY for LLM-composed answers (grounded lexical answers used meanwhile).",
        },
    }


def log_config_check() -> Dict[str, Dict[str, object]]:
    """Log the capability report at startup and return it."""
    report = get_capability_report()
    logger.info("=" * 68)
    logger.info("Truvia capability / configuration check")
    logger.info("-" * 68)
    for capability, info in report.items():
        if info["configured"]:
            logger.info(f"  [OK]       {capability:<22} -> provider: {info['provider']}")
        else:
            logger.warning(f"  [DEGRADED] {capability:<22} -> {info['missing']}")
    if not any(c["configured"] and c["provider"] not in (None, "local-rule-engine", "local-grounded-answers")
               for c in report.values()):
        logger.warning(
            "  No cloud AI credentials detected. The platform is fully operational in "
            "degraded/local mode and will NOT fabricate results — image/audio inputs "
            "without an OCR/ASR provider are honestly flagged as low-confidence."
        )
    logger.info("=" * 68)
    return report
