"use client";

/**
 * Module 5: Live Scam Interceptor — functional frontend wiring only (Spec §8).
 *
 * Deliberately unpolished: reuses existing Icon / RiskGauge / severity-badge
 * helpers and Recharts (already in the stack). Three phases in one route —
 * idle (start), active (turn-by-turn), and summary (trajectory + actions).
 * Layout/spacing/motion polish is explicitly deferred to the final cross-app
 * pass; the bar here is "functional and testable".
 */
import { useEffect, useRef, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import { Icon } from "@/components/Icon";
import { RiskGauge } from "@/components/RiskGauge";
import { api, ApiError } from "@/lib/api";
import { severityBadge, severityText } from "@/lib/format";
import type {
  LiveIntervention,
  LiveSessionDetail,
  LiveTurn,
  LiveTurnResult,
  SeverityBand,
} from "@/lib/types";

type Phase = "idle" | "active" | "summary";

export default function LiveShieldPage() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<LiveTurn[]>([]);
  const [input, setInput] = useState("");
  const [scoring, setScoring] = useState(false);
  const [starting, setStarting] = useState(false);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intervention, setIntervention] = useState<LiveIntervention | null>(null);
  const [summary, setSummary] = useState<LiveSessionDetail | null>(null);
  const [escalating, setEscalating] = useState(false);
  const [caseId, setCaseId] = useState<string | null>(null);
  const listEndRef = useRef<HTMLDivElement>(null);

  const currentScore = turns.length ? (turns[turns.length - 1].cumulative_score ?? 0) : 0;
  const currentBand: SeverityBand =
    (turns.length ? turns[turns.length - 1].severity_band : "low") || "low";

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, intervention]);

  async function startSession() {
    setError(null);
    setStarting(true);
    try {
      const res = await api.post<{ session_id: string; status: string }>("/live-sessions");
      setSessionId(res.session_id);
      setTurns([]);
      setIntervention(null);
      setSummary(null);
      setCaseId(null);
      setPhase("active");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start a live session.");
    } finally {
      setStarting(false);
    }
  }

  async function addTurn() {
    if (!sessionId || input.trim().length < 1 || scoring) return;
    setError(null);
    setScoring(true);
    const text = input.trim();
    try {
      const res = await api.post<LiveTurnResult>(`/live-sessions/${sessionId}/turns`, {
        raw_text: text,
      });
      setTurns((prev) => [
        ...prev,
        {
          turn_index: res.turn_index,
          raw_text: text,
          turn_score: res.turn_score,
          cumulative_score: res.cumulative_score,
          severity_band: res.severity_band,
        },
      ]);
      setInput("");
      if (res.intervention?.shown) {
        setIntervention(res.intervention);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not score this turn. Try again.");
    } finally {
      setScoring(false);
    }
  }

  async function endSession() {
    if (!sessionId) return;
    setEnding(true);
    setError(null);
    try {
      await api.post(`/live-sessions/${sessionId}/end`);
      const detail = await api.get<LiveSessionDetail>(`/live-sessions/${sessionId}`);
      setSummary(detail);
      setPhase("summary");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not end the session.");
    } finally {
      setEnding(false);
    }
  }

  async function escalate() {
    if (!sessionId) return;
    if (
      !confirm(
        "This will submit this live session to the police complaint queue as a case. Continue?"
      )
    )
      return;
    setEscalating(true);
    setError(null);
    try {
      const res = await api.post<{ status: string; case_id: string }>(
        `/live-sessions/${sessionId}/escalate`
      );
      setCaseId(res.case_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Escalation failed.");
    } finally {
      setEscalating(false);
    }
  }

  async function download() {
    if (!sessionId) return;
    try {
      await api.download(`/live-sessions/${sessionId}/report`, `truvia-live-session-${sessionId.slice(0, 8)}.pdf`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not download report.");
    }
  }

  // Small per-turn risk indicator (reuses the severity-badge styling).
  function RiskDot({ band }: { band?: SeverityBand }) {
    return (
      <span className={`px-stack-sm py-1 rounded-full text-[10px] font-bold uppercase ${severityBadge(band)}`}>
        {severityText(band)}
      </span>
    );
  }

  const errorBanner = error && (
    <div className="flex items-start gap-stack-sm p-stack-md bg-error/10 rounded-lg border border-error/30">
      <Icon name="error" className="text-error text-[18px]" />
      <p className="font-body-md text-error">{error}</p>
    </div>
  );

  return (
    <div className="flex-1 overflow-y-auto p-stack-lg lg:p-margin-page space-y-stack-lg custom-scrollbar">
      <header>
        <h1 className="text-headline-lg text-primary">Live Scam Interceptor</h1>
        <p className="text-on-surface-variant max-w-2xl text-body-lg mt-1">
          Mid-call or mid-chat with a suspected scammer? Type in what they say, turn by turn, and get a
          live risk read-out plus specific guidance before any money moves.
        </p>
      </header>

      {/* ---------------- IDLE ---------------- */}
      {phase === "idle" && (
        <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-card-padding max-w-xl space-y-stack-md">
          <div className="flex items-center gap-stack-sm">
            <Icon name="record_voice_over" className="text-primary text-3xl" />
            <h2 className="font-headline-sm text-on-surface">Start a Live Session</h2>
          </div>
          <p className="font-body-md text-on-surface-variant">
            Each time the other person says something, add it as a turn. Truvia re-scores the whole
            conversation as it unfolds and warns you the moment it crosses into high risk.
          </p>
          {errorBanner}
          <button
            onClick={startSession}
            disabled={starting}
            className="px-stack-lg py-stack-md bg-primary-container text-white font-headline-sm rounded-xl hover:brightness-110 active:scale-[0.98] transition-all flex items-center gap-stack-sm disabled:opacity-60"
          >
            <Icon name={starting ? "sync" : "play_circle"} className={starting ? "animate-spin" : ""} />
            {starting ? "STARTING..." : "START LIVE SESSION"}
          </button>
        </section>
      )}

      {/* ---------------- ACTIVE ---------------- */}
      {phase === "active" && (
        <div className="grid grid-cols-12 gap-gutter">
          <section className="col-span-12 xl:col-span-7 space-y-stack-md">
            {/* Intervention banner (reuses the warning-banner styling) */}
            {intervention && (
              <div className="flex flex-col gap-stack-sm p-stack-md bg-error/10 rounded-xl border border-error/40">
                <div className="flex items-start gap-stack-sm">
                  <Icon name="crisis_alert" className="text-error text-2xl" />
                  <div>
                    <p className="font-headline-sm text-error uppercase text-[13px] tracking-widest">
                      High Scam Risk — {intervention.category}
                    </p>
                    <p className="font-body-md text-on-surface mt-1">{intervention.message}</p>
                  </div>
                </div>
                <button
                  onClick={endSession}
                  disabled={ending}
                  className="self-start px-stack-md py-2 bg-error text-white rounded-lg font-label-md uppercase tracking-widest hover:brightness-110 transition-all flex items-center gap-stack-sm disabled:opacity-60"
                >
                  <Icon name="local_police" className="text-[18px]" />
                  End Session &amp; Report
                </button>
              </div>
            )}

            {/* Turn input */}
            <div className="space-y-stack-sm">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    addTurn();
                  }
                }}
                rows={3}
                placeholder="Type what they just said..."
                className="w-full bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md font-body-md text-on-surface resize-none focus:ring-1 focus:ring-primary outline-none"
              />
              {errorBanner}
              <div className="flex justify-between items-center">
                <button
                  onClick={endSession}
                  disabled={ending}
                  className="px-stack-md py-2 bg-surface-container-high text-on-surface rounded-lg font-label-md uppercase tracking-widest hover:bg-surface-variant transition-all disabled:opacity-60"
                >
                  {ending ? "Ending..." : "End Session"}
                </button>
                <button
                  onClick={addTurn}
                  disabled={scoring || input.trim().length < 1}
                  className="px-stack-lg py-2 bg-primary text-on-primary rounded-lg font-label-md uppercase tracking-widest hover:brightness-110 transition-all flex items-center gap-stack-sm disabled:opacity-60"
                >
                  <Icon name={scoring ? "sync" : "add"} className={scoring ? "animate-spin" : ""} />
                  {scoring ? "Scoring..." : "Add what they just said"}
                </button>
              </div>
            </div>

            {/* Turn list */}
            <div className="space-y-stack-sm">
              {turns.length === 0 ? (
                <p className="font-body-md text-on-surface-variant/70">
                  No turns yet. Add the first thing the other person said to begin scoring.
                </p>
              ) : (
                turns.map((t, idx) => (
                  <div
                    key={t.turn_index ?? idx}
                    className="flex items-start gap-stack-sm p-stack-md bg-surface-container-lowest border border-outline-variant rounded-lg"
                  >
                    <span className="font-mono text-[11px] text-on-surface-variant mt-1">#{(t.turn_index ?? idx) + 1}</span>
                    <p className="flex-1 font-body-md text-on-surface">{t.raw_text || (t as any).text}</p>
                    <div className="flex flex-col items-end gap-1">
                      <RiskDot band={t.severity_band} />
                      <span className="font-mono text-[11px] text-on-surface-variant">risk {t.cumulative_score ?? 0}</span>
                    </div>
                  </div>
                ))
              )}
              <div ref={listEndRef} />
            </div>
          </section>

          {/* Live risk gauge */}
          <section className="col-span-12 xl:col-span-5">
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-card-padding flex flex-col items-center gap-stack-md">
              <span className="font-label-md text-on-surface-variant uppercase text-[10px] tracking-widest">
                Live Risk Trajectory
              </span>
              <RiskGauge value={currentScore} severity={currentBand} />
              <span className={`font-headline-sm ${severityBadge(currentBand)} px-stack-md py-1 rounded-full`}>
                {severityText(currentBand)}
              </span>
              <p className="font-body-md text-on-surface-variant text-center text-[12px]">
                {turns.length} turn{turns.length === 1 ? "" : "s"} scored
              </p>
            </div>
          </section>
        </div>
      )}

      {/* ---------------- SUMMARY ---------------- */}
      {phase === "summary" && summary && (
        <div className="grid grid-cols-12 gap-gutter">
          {/* Trajectory chart */}
          <section className="col-span-12 xl:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-xl p-card-padding space-y-stack-md">
            <h2 className="font-headline-sm text-on-surface">Risk Trajectory</h2>
            {summary.turns.length === 0 ? (
              <p className="font-body-md text-on-surface-variant">
                This session ended with no turns recorded.
              </p>
            ) : (
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <LineChart
                    data={summary.turns.map((t, idx) => ({
                      turn: (t.turn_index ?? idx) + 1,
                      score: t.cumulative_score ?? 0,
                    }))}

                    margin={{ top: 10, right: 20, bottom: 10, left: -10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff20" />
                    <XAxis dataKey="turn" stroke="#ffffff80" fontSize={12} />
                    <YAxis domain={[0, 100]} stroke="#ffffff80" fontSize={12} />
                    <Tooltip />
                    <ReferenceLine y={70} stroke="#ffb4ab" strokeDasharray="4 4" label={{ value: "High", fill: "#ffb4ab", fontSize: 10 }} />
                    <Line type="monotone" dataKey="score" stroke="#4da2ff" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Turn timeline */}
            <div className="space-y-stack-sm">
              {summary.turns.map((t, idx) => (
                <div
                  key={t.turn_index ?? idx}
                  className="flex items-start gap-stack-sm p-stack-sm bg-surface-container-low rounded-lg"
                >
                  <span className="font-mono text-[11px] text-on-surface-variant mt-1">#{(t.turn_index ?? idx) + 1}</span>
                  <p className="flex-1 font-body-md text-on-surface text-[13px]">{t.raw_text || t.text}</p>
                  <span className="font-mono text-[11px] text-on-surface-variant">{t.cumulative_score ?? 0}</span>
                </div>
              ))}

            </div>
          </section>

          {/* Verdict + actions (mirrors the Fraud Shield Result screen) */}
          <section className="col-span-12 xl:col-span-5">
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-card-padding space-y-stack-md">
              <div className="flex items-center justify-between border-b border-outline-variant pb-stack-md">
                <div className="flex flex-col">
                  <span className="font-label-md text-on-surface-variant uppercase text-[10px] tracking-widest">
                    Final Assessment
                  </span>
                  <span className={`font-headline-sm ${severityBadge(summary.session.current_severity_band)} px-stack-sm rounded mt-1`}>
                    {severityText(summary.session.current_severity_band)} THREAT
                  </span>
                </div>
                <div className="px-stack-sm py-1 bg-surface-container-high text-on-surface-variant text-[10px] font-bold rounded uppercase font-mono">
                  #{summary.session.id.slice(0, 8)}
                </div>
              </div>

              <div className="flex flex-col items-center py-stack-md">
                <RiskGauge
                  value={summary.session.current_score ?? 0}
                  severity={summary.session.current_severity_band}
                />
              </div>

              <div className="grid grid-cols-2 gap-stack-md text-center bg-surface-container-low p-stack-md rounded-xl">
                <div>
                  <p className="font-label-md text-on-surface-variant uppercase text-[10px]">Turns</p>
                  <p className="font-headline-sm text-primary">{summary.turns.length}</p>
                </div>
                <div>
                  <p className="font-label-md text-on-surface-variant uppercase text-[10px]">Category</p>
                  <p className="font-headline-sm text-on-surface text-[16px] leading-tight">
                    {String(summary.session.scam_category || "Unclassified")}
                  </p>
                </div>
              </div>

              {caseId && (
                <div className="flex items-start gap-stack-sm p-stack-sm bg-primary/10 rounded-lg border border-primary/30">
                  <Icon name="local_police" className="text-primary text-[18px]" />
                  <p className="font-label-md text-primary">
                    Reported to Cyber Cell. Case reference: {caseId.slice(0, 8).toUpperCase()}
                  </p>
                </div>
              )}

              {errorBanner}

              <div className="pt-stack-md border-t border-outline-variant flex flex-col gap-stack-sm">
                <button
                  onClick={escalate}
                  disabled={escalating || summary.session.status === "escalated" || !!caseId}
                  className="w-full py-stack-md bg-primary text-on-primary rounded-xl font-label-md uppercase tracking-widest hover:brightness-110 transition-all flex items-center justify-center gap-stack-sm disabled:opacity-60"
                >
                  <Icon name="local_police" className="text-[18px]" />
                  {summary.session.status === "escalated" || caseId ? "Reported to Cyber Cell" : "Report to Cyber Cell"}
                </button>
                <button
                  onClick={download}
                  className="w-full py-stack-md bg-surface-container-high text-on-surface rounded-xl font-label-md uppercase tracking-widest hover:bg-surface-variant transition-all flex items-center justify-center gap-stack-sm"
                >
                  <Icon name="file_download" className="text-[18px]" />
                  Download Report
                </button>
                <button
                  onClick={startSession}
                  className="w-full py-stack-md bg-surface-container-high text-on-surface rounded-xl font-label-md uppercase tracking-widest hover:bg-surface-variant transition-all flex items-center justify-center gap-stack-sm"
                >
                  <Icon name="restart_alt" className="text-[18px]" />
                  Start Another Session
                </button>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
