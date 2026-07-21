"""Submission runner: seed the DB by POSTing generated scam text through the REAL
Fraud Shield endpoint (POST /api/v1/reports/submit), then backfill demo metadata.

Flow per sample:
  1. POST source_type=text, text_content=<generated> with a citizen Bearer token.
  2. Poll GET /reports/{id}/status until pipeline_stage == 'completed' (Agent 1->2->4->5
     all ran: real threat_scores + entities + graph produced) or timeout/failed.
  3. After all submissions, backfill reports.city + backdated reports.created_at (and
     matching threat_scores.created_at) on the rows WE created. This is a metadata fill
     on pipeline-produced rows — the endpoint has no city input and stamps created_at
     with now(); it is NOT a bypass of the pipeline (scores/entities are 100% pipeline).

Batching: limited concurrency (asyncio.Semaphore) to respect Neon cloud latency and
avoid overwhelming the server's in-process background-task pool. Progress is logged
to scripts/seed_run.log and stdout.

Usage:
    .venv\\Scripts\\python.exe -m scripts.seed_submit [VARIED_COUNT] [CONCURRENCY] [POLL_TIMEOUT]
    (defaults: 130, 4, 45)
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import timedelta

import httpx
from sqlalchemy import select, text as sql_text

from app.core.security import create_access_token
from app.data.postgres_client import AsyncSessionLocal
from app.models.user import User
from scripts.seed_corpus import build_corpus, Sample

BASE = "http://127.0.0.1:8000/api/v1"
LOG_PATH = "scripts/seed_run.log"

_log_fh = None


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if _log_fh:
        _log_fh.write(line + "\n")
        _log_fh.flush()


async def _get_citizen_tokens() -> list[tuple[str, str]]:
    """Return [(user_id, bearer_token)] for existing citizen accounts (reused, not new)."""
    async with AsyncSessionLocal() as db:
        citizens = (await db.execute(
            select(User).where(User.role == "citizen", User.status == "active")
        )).scalars().all()
    if not citizens:
        raise RuntimeError("No active citizen accounts found to own reports.")
    out = []
    for u in citizens:
        tok = create_access_token(subject=str(u.id), role="citizen",
                                  expires_delta=timedelta(hours=3))
        out.append((str(u.id), tok))
    return out


async def _request_with_retry(coro_factory, attempts: int = 3):
    """Retry a request on transient connection drops (uvicorn keep-alive races)."""
    last = None
    for _ in range(attempts):
        try:
            return await coro_factory()
        except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError) as e:
            last = e
            await asyncio.sleep(0.5)
    raise last


async def _submit_one(client: httpx.AsyncClient, token: str, sample: Sample,
                      poll_timeout: float) -> dict:
    """POST one report and poll until the pipeline completes. Returns a result dict."""
    headers = {"Authorization": f"Bearer {token}", "Connection": "close"}
    # 1. Submit through the real multipart-form endpoint.
    try:
        r = await _request_with_retry(lambda: client.post(
            f"{BASE}/reports/submit",
            headers=headers,
            data={"source_type": "text", "text_content": sample.text},
        ))
    except Exception as e:
        return {"ok": False, "stage": "submit", "error": f"{type(e).__name__}: {e}"}
    if r.status_code != 201:
        return {"ok": False, "stage": "submit", "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    report_id = r.json()["id"]

    # 2. Poll to completion.
    deadline = time.monotonic() + poll_timeout
    last_stage = None
    while time.monotonic() < deadline:
        await asyncio.sleep(1.0)
        try:
            s = await _request_with_retry(
                lambda: client.get(f"{BASE}/reports/{report_id}/status", headers=headers))
        except Exception:
            continue
        if s.status_code != 200:
            continue
        body = s.json()
        last_stage = body.get("pipeline_stage")
        st = body.get("status")
        if last_stage == "completed":
            return {"ok": True, "report_id": report_id, "status": st,
                    "stage": last_stage, "sample": sample}
        if st == "failed":
            return {"ok": False, "report_id": report_id, "stage": "pipeline",
                    "error": "report status=failed", "sample": sample}
    # Timed out — but the report + (likely) score exist; treat as partial.
    return {"ok": False, "report_id": report_id, "stage": "poll_timeout",
            "error": f"did not reach 'completed' within {poll_timeout}s (last={last_stage})",
            "sample": sample}


async def _backfill(results: list[dict]) -> int:
    """Backfill city + backdated created_at on the reports we created (metadata fill)."""
    rows = [(res["report_id"], res["sample"].city, res["sample"].created_at)
            for res in results if res.get("report_id") and res.get("sample")]
    if not rows:
        return 0
    async with AsyncSessionLocal() as db:
        for report_id, city, created_at in rows:
            await db.execute(
                sql_text(
                    "UPDATE reports SET city = :city, created_at = :ts, updated_at = :ts "
                    "WHERE id = :id"
                ),
                {"city": city, "ts": created_at, "id": report_id},
            )
            await db.execute(
                sql_text(
                    "UPDATE threat_scores SET created_at = :ts WHERE report_id = :id"
                ),
                {"ts": created_at, "id": report_id},
            )
        await db.commit()
    return len(rows)


async def _main() -> int:
    global _log_fh
    varied_count = int(sys.argv[1]) if len(sys.argv) > 1 else 130
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    poll_timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 45.0

    _log_fh = open(LOG_PATH, "a", encoding="utf-8")
    corpus = build_corpus(varied_count=varied_count)
    tokens = await _get_citizen_tokens()
    log("=" * 70)
    log(f"SEED RUN START: {len(corpus)} samples | citizens={len(tokens)} | "
        f"concurrency={concurrency} | poll_timeout={poll_timeout}s")
    log(f"  correlated={sum(1 for s in corpus if s.correlation_group)} "
        f"varied={sum(1 for s in corpus if not s.correlation_group)}")

    sem = asyncio.Semaphore(concurrency)
    results: list[dict] = []
    done = 0
    start = time.monotonic()

    async with httpx.AsyncClient(
        timeout=60.0,
        limits=httpx.Limits(max_keepalive_connections=0, max_connections=concurrency + 4),
        transport=httpx.AsyncHTTPTransport(retries=3),
    ) as client:
        async def worker(idx: int, sample: Sample):
            nonlocal done
            async with sem:
                token = tokens[idx % len(tokens)][1]
                res = await _submit_one(client, token, sample, poll_timeout)
                results.append(res)
                done += 1
                tag = "OK " if res["ok"] else "ERR"
                cg = sample.correlation_group or "-"
                if done % 10 == 0 or not res["ok"]:
                    log(f"  [{done}/{len(corpus)}] {tag} {sample.category:16s} ring={cg:16s} "
                        f"{res.get('error','')}")

        await asyncio.gather(*(worker(i, s) for i, s in enumerate(corpus)))

    elapsed = time.monotonic() - start
    ok = [r for r in results if r["ok"]]
    err = [r for r in results if not r["ok"]]
    log(f"SUBMISSION DONE: ok={len(ok)} failed={len(err)} in {elapsed:.1f}s "
        f"({elapsed/max(len(corpus),1):.2f}s/report)")

    # Backfill metadata (include poll_timeout rows that still have a report_id — the
    # pipeline likely finished just after our poll window; the row is real either way).
    backfillable = [r for r in results if r.get("report_id") and r.get("sample")]
    n = await _backfill(backfillable)
    log(f"BACKFILL: set city + backdated created_at on {n} reports")

    if err:
        log("FAILURE DETAIL (first 15):")
        for r in err[:15]:
            log(f"    stage={r.get('stage')} id={r.get('report_id','-')} {r.get('error','')}")

    log(f"SEED RUN END. submitted_ok={len(ok)} backfilled={n}")
    _log_fh.close()
    # Non-zero only if nothing succeeded.
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
