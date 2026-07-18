"""Admin observability / telemetry for System Health (App Flow §8.5).

Everything here is real and non-invasive:
  * A logging handler on the `truvia.agents.*` loggers records genuine
    per-agent ERROR counts (rolling 1h window).
  * Agent entrypoint methods are wrapped AT STARTUP (monkeypatch) to record
    real execution latency and failures — the agent source files are never
    edited, honouring "do not touch Section 5/6/7 code".
  * `knowledge_agent.answer_query` is wrapped to persist real citation counts
    (knowledge_base.times_cited) — genuine chat-citation logging, not a faked
    number.

No latency/error numbers are fabricated: before an agent has run, its latency
is reported as null ("no runs yet").
"""
import logging
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Deque, Dict, List, Optional, Tuple

logger = logging.getLogger("truvia.core.metrics")

# Six pipeline agents (TRD). key -> display metadata.
AGENTS: List[Dict[str, str]] = [
    {"key": "input_processor", "name": "Agent 1 — Input Processor (OCR/STT)",
     "module": "app.agents.input_processor", "obj": "input_processor_agent",
     "method": "process_report", "capability": "image_ocr"},
    {"key": "threat_evaluator", "name": "Agent 2 — Threat Evaluator",
     "module": "app.agents.threat_evaluator", "obj": "threat_evaluator_agent",
     "method": "evaluate_threat", "capability": "llm_threat_reasoning"},
    {"key": "knowledge_agent", "name": "Agent 3 — Knowledge / RAG Chat",
     "module": "app.agents.knowledge_agent", "obj": "knowledge_agent",
     "method": "answer_query", "capability": "rag_chat_llm"},
    {"key": "entity_extractor", "name": "Agent 4 — Entity Extractor",
     "module": "app.agents.entity_extractor", "obj": "entity_extractor_agent",
     "method": "extract_entities", "capability": None},
    {"key": "threat_intel", "name": "Agent 5 — Threat Intelligence (Graph)",
     "module": "app.agents.threat_intel", "obj": "threat_intel_agent",
     "method": "index_report_in_graph", "capability": None},
    {"key": "investigation", "name": "Agent 6 — Investigation Summarizer",
     "module": "app.agents.investigation", "obj": "investigation_agent",
     "method": "summarize_case", "capability": None},
]

_WINDOW_SECONDS = 3600  # 1 hour rolling window
_MAXLEN = 2000


class _Registry:
    def __init__(self) -> None:
        # agent_key -> deque[(ts_epoch, duration_ms_or_None, is_error)]
        self._events: Dict[str, Deque[Tuple[float, Optional[float], bool]]] = {
            a["key"]: deque(maxlen=_MAXLEN) for a in AGENTS
        }
        self._lock = Lock()

    def record_run(self, key: str, duration_ms: Optional[float], is_error: bool) -> None:
        if key not in self._events:
            return
        with self._lock:
            self._events[key].append((time.time(), duration_ms, is_error))

    def record_error(self, key: str) -> None:
        self.record_run(key, None, True)

    def stats(self, key: str) -> Dict[str, object]:
        now = time.time()
        with self._lock:
            events = [e for e in self._events.get(key, ()) if now - e[0] <= _WINDOW_SECONDS]
        runs = len(events)
        errors = sum(1 for e in events if e[2])
        durations = [e[1] for e in events if e[1] is not None]
        avg_latency = round(sum(durations) / len(durations), 1) if durations else None
        last_run = max((e[0] for e in events), default=None)
        return {
            "runs_last_hour": runs,
            "errors_last_hour": errors,
            "avg_latency_ms": avg_latency,
            "last_run_at": datetime.fromtimestamp(last_run, tz=timezone.utc).isoformat() if last_run else None,
        }


registry = _Registry()


class _AgentLogHandler(logging.Handler):
    """Counts ERROR+ log records emitted by truvia.agents.* loggers."""

    _suffix_to_key = {a["module"].split(".")[-1]: a["key"] for a in AGENTS}

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno < logging.ERROR:
                return
            name = record.name  # e.g. "truvia.agents.threat_intel"
            if ".agents." not in name:
                return
            suffix = name.split(".")[-1]
            key = self._suffix_to_key.get(suffix)
            if key:
                registry.record_error(key)
        except Exception:
            pass


def _wrap_latency(agent_key: str, func):
    async def wrapper(*args, **kwargs):
        start = time.time()
        is_error = False
        try:
            return await func(*args, **kwargs)
        except Exception:
            is_error = True
            raise
        finally:
            registry.record_run(agent_key, (time.time() - start) * 1000.0, is_error)
    return wrapper


def _wrap_knowledge_with_citations(func):
    """Wrap answer_query to record real citation counts, then latency."""
    async def wrapper(*args, **kwargs):
        start = time.time()
        is_error = False
        result = None
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception:
            is_error = True
            raise
        finally:
            registry.record_run("knowledge_agent", (time.time() - start) * 1000.0, is_error)
            if result and isinstance(result, dict):
                await _log_citations(result.get("citations") or [])
    return wrapper


async def _log_citations(citations: list) -> None:
    """Increment knowledge_base.times_cited for each cited source (own session)."""
    if not citations:
        return
    try:
        from sqlalchemy import update
        from app.data.postgres_client import AsyncSessionLocal
        from app.models.knowledge import KnowledgeBase
        seen = set()
        async with AsyncSessionLocal() as session:
            for c in citations:
                src, title = c.get("source"), c.get("title")
                if not src or not title or (src, title) in seen:
                    continue
                seen.add((src, title))
                await session.execute(
                    update(KnowledgeBase)
                    .where(KnowledgeBase.source == src, KnowledgeBase.title == title)
                    .values(times_cited=KnowledgeBase.times_cited + 1)
                )
            await session.commit()
    except Exception as e:
        logger.warning(f"Citation logging skipped: {e}")


_installed = False


def install() -> None:
    """Attach the log handler and wrap agent methods. Idempotent."""
    global _installed
    if _installed:
        return
    _installed = True

    # 1. ERROR log handler on the agents logger tree.
    agents_logger = logging.getLogger("truvia.agents")
    if not any(isinstance(h, _AgentLogHandler) for h in agents_logger.handlers):
        agents_logger.addHandler(_AgentLogHandler(level=logging.ERROR))

    # 2. Wrap agent entrypoints for real latency + citation logging.
    import importlib
    for a in AGENTS:
        try:
            mod = importlib.import_module(a["module"])
            obj = getattr(mod, a["obj"])
            method = getattr(obj, a["method"])
            if getattr(method, "_truvia_wrapped", False):
                continue
            if a["key"] == "knowledge_agent":
                wrapped = _wrap_knowledge_with_citations(method)
            else:
                wrapped = _wrap_latency(a["key"], method)
            wrapped._truvia_wrapped = True  # type: ignore[attr-defined]
            setattr(obj, a["method"], wrapped)
        except Exception as e:
            logger.warning(f"Could not instrument {a['key']}: {e}")
    logger.info("Admin telemetry installed (agent latency + error + citation logging).")


def get_agent_health() -> List[Dict[str, object]]:
    """Per-agent health derived from real config + live run/error stats."""
    from app.core.config_check import get_capability_report
    caps = get_capability_report()
    out = []
    for a in AGENTS:
        s = registry.stats(a["key"])
        cap = a["capability"]
        cap_info = caps.get(cap) if cap else None
        cap_degraded = bool(cap_info and not cap_info.get("configured"))
        provider = cap_info.get("provider") if cap_info else None

        # Status heuristic (real signals): hard-down if a cloud-only capability
        # has no provider at all; degraded if running on a local fallback or if
        # errors occurred in the last hour; otherwise healthy.
        if cap_info and not cap_info.get("configured") and provider is None:
            status = "down"
        elif s["errors_last_hour"] and s["errors_last_hour"] >= max(1, s["runs_last_hour"]):
            status = "down"
        elif cap_degraded or (provider in ("local-rule-engine", "local-grounded-answers",
                                           "local-rapidocr", "local-faster-whisper")) or s["errors_last_hour"]:
            status = "degraded"
        else:
            status = "healthy"

        out.append({
            "key": a["key"],
            "name": a["name"],
            "status": status,
            "provider": provider,
            "avg_latency_ms": s["avg_latency_ms"],
            "runs_last_hour": s["runs_last_hour"],
            "errors_last_hour": s["errors_last_hour"],
            "last_run_at": s["last_run_at"],
        })
    return out
