"use client";

import { useState, useEffect, useRef, FormEvent } from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Icon } from "@/components/Icon";
import { RiskGauge } from "@/components/RiskGauge";
import { ProcessingStepper } from "@/components/ProcessingStepper";
import { api, ApiError } from "@/lib/api";
import type { Report, ChatResponse, Citation } from "@/lib/types";
import {
  severityBadge,
  severityText,
  statusBadge,
  reportTitle,
  formatDateTime,
} from "@/lib/format";

type SourceType = "text" | "screenshot" | "audio";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

const SOURCE_ICON: Record<SourceType, string> = {
  text: "notes",
  screenshot: "image",
  audio: "mic",
};

export default function FraudShieldPage() {
  const [sourceType, setSourceType] = useState<SourceType>("text");
  const [textContent, setTextContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [escalating, setEscalating] = useState(false);
  const [escalated, setEscalated] = useState<{ caseId: string } | null>(null);
  const [dismissing, setDismissing] = useState(false);
  const [history, setHistory] = useState<Report[]>([]);
  const [pipelineStage, setPipelineStage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text:
        "Hello. I am Vigil, your fraud-analysis assistant. Ask me about any suspicious message, UPI ID, or scam pattern and I'll cross-reference RBI / NCRP guidelines.",
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // ─── Motion (respects reduced-motion) ───────────────────────────────────────
  const reduce = useReducedMotion();
  const container: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.08, delayChildren: 0.02 } },
  };
  const item: Variants = {
    hidden: { opacity: 0, y: reduce ? 0 : 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
  };
  const cardHover = reduce ? undefined : { y: -3, transition: { duration: 0.2 } };

  async function loadHistory() {
    try {
      const reports = await api.get<Report[]>("/reports?limit=6");
      setHistory(reports);
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const currentScore = report?.threat_scores?.[0];

  async function pollReport(id: string): Promise<Report> {
    // Poll until scored/failed/escalated or a threat score is attached.
    // Audio transcription (speech-to-text) can take noticeably longer than OCR/text,
    // so we allow a generous window (~90s) before giving up, to avoid prematurely
    // showing a "no verdict" state while the backend is still transcribing/scoring.
    for (let i = 0; i < 60; i++) {
      // Fetch lightweight status to update the stepper
      try {
        const statusRes = await api.get<{ id: string; status: string; pipeline_stage: string | null }>(`/reports/${id}/status`);
        setPipelineStage(statusRes.pipeline_stage);
      } catch {
        /* status endpoint may not be available, continue with full poll */
      }

      const r = await api.get<Report>(`/reports/${id}`);
      if (["scored", "escalated", "failed", "dismissed"].includes(r.status) || r.threat_scores.length > 0) {
        setPipelineStage("completed");
        return r;
      }
      await new Promise((res) => setTimeout(res, 1500));
    }
    return api.get<Report>(`/reports/${id}`);
  }

  async function runAnalysis() {
    setError(null);
    setEscalated(null);
    if (sourceType === "text" && textContent.trim().length < 10) {
      setError("Please paste at least 10 characters of the suspicious message.");
      return;
    }
    if (sourceType !== "text" && !file) {
      setError(`Please select a ${sourceType} file to analyze.`);
      return;
    }
    setAnalyzing(true);
    setReport(null);
    try {
      const form = new FormData();
      form.append("source_type", sourceType);
      if (sourceType === "text") {
        form.append("text_content", textContent);
      } else if (file) {
        form.append("files", file);
      }
      const created = await api.postForm<Report>("/reports/submit", form);
      setPipelineStage("ingesting");
      const final = created.threat_scores.length > 0 ? created : await pollReport(created.id);
      if (final.status === "failed") {
        setError("Analysis could not extract readable content from this file. Try a clearer image or paste the text directly under the Text tab.");
        setReport(null);
      } else {
        setReport(final);
        loadHistory();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Analysis service timed out. Please try again or paste the text directly.");
    } finally {
      setAnalyzing(false);
      setPipelineStage(null);
    }
  }

  async function handleEscalate() {
    if (!report) return;
    // §10.1 "Report to Police" confirmation before submitting to the police queue.
    // Uses the same native-confirm gate the app already uses for its other
    // destructive/irreversible confirmations (§10.6 suspend, §10.8 remove doc).
    if (
      !confirm(
        "This will submit your report, including all uploaded evidence, to the police complaint queue. Continue?"
      )
    )
      return;
    setEscalating(true);
    setError(null);
    try {
      const res = await api.post<{ status: string; case_id: string }>(`/reports/${report.id}/escalate`);
      setEscalated({ caseId: res.case_id });
      const refreshed = await api.get<Report>(`/reports/${report.id}`);
      setReport(refreshed);
      loadHistory();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Escalation failed.");
    } finally {
      setEscalating(false);
    }
  }

  async function handleDownload() {
    if (!report) return;
    try {
      await api.download(`/reports/${report.id}/pdf`, `truvia-report-${report.id.slice(0, 8)}.pdf`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not download report.");
    }
  }

  async function handleDismiss() {
    if (!report) return;
    setDismissing(true);
    setError(null);
    try {
      await api.post(`/reports/${report.id}/dismiss`);
      const refreshed = await api.get<Report>(`/reports/${report.id}`);
      setReport(refreshed);
      loadHistory();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not mark as reviewed.");
    } finally {
      setDismissing(false);
    }
  }

  async function sendChat(e: FormEvent) {
    e.preventDefault();
    const q = chatInput.trim();
    if (q.length < 3 || chatBusy) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setChatInput("");
    setChatBusy(true);
    try {
      const res = await api.post<ChatResponse>("/chat", { query: q });
      setMessages((m) => [...m, { role: "assistant", text: res.answer, citations: res.citations }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text:
            err instanceof ApiError
              ? `Sorry, I hit an error: ${err.message}`
              : "Sorry, I couldn't reach the knowledge engine right now.",
        },
      ]);
    } finally {
      setChatBusy(false);
    }
  }

  const redFlags = currentScore?.reasoning_json?.key_indicators ?? [];
  const victimInstructions = currentScore?.reasoning_json?.victim_instructions ?? [];

  return (
    <div className="relative min-h-[calc(100vh-64px)] bg-background p-6 lg:p-margin-page">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="mx-auto w-full max-w-container-max space-y-stack-lg"
      >
        {/* ─── Header ─────────────────────────────────────────────────────────── */}
        <motion.header variants={item} className="flex flex-col gap-stack-sm">
          <p className="font-label-sm uppercase tracking-[0.25em] text-primary">Citizen Portal</p>
          <h1 className="font-heading text-headline-lg md:text-display-lg text-on-surface">
            Fraud Shield
          </h1>
          <p className="max-w-2xl text-body-lg text-on-surface-variant">
            Deploy AI-powered analysis to detect phishing, social engineering, and financial fraud in
            screenshots, audio, or text messages.
          </p>
          <div>
            <a
              href="/live-shield"
              className="mt-stack-sm inline-flex items-center gap-stack-sm rounded-xl border border-primary/40 bg-primary/10 px-stack-lg py-stack-md font-label-md uppercase tracking-widest text-primary primary-glow transition-all hover:bg-primary/20 active:scale-[0.98]"
            >
              <Icon name="record_voice_over" className="text-[18px]" />
              Start a Live Session
            </a>
          </div>
        </motion.header>

        {/* ─── Analysis grid: Evidence (5) · Results (7) ──────────────────────── */}
        <div className="grid grid-cols-1 gap-gutter lg:grid-cols-12">
          {/* LEFT — Evidence Capture */}
          <motion.section variants={item} className="lg:col-span-5">
            <div className="glass-panel space-y-stack-md p-6">
              <div className="flex items-center gap-stack-sm">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/20 bg-primary/15">
                  <Icon name="upload_file" className="text-[20px] text-primary" />
                </span>
                <h2 className="font-heading text-headline-sm text-on-surface">Evidence Capture</h2>
              </div>

              {/* Segmented source control */}
              <div className="flex gap-1 rounded-xl bg-surface-container-low p-1">
                {(["text", "screenshot", "audio"] as SourceType[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => {
                      setSourceType(t);
                      setFile(null);
                      setError(null);
                    }}
                    className={`flex flex-1 items-center justify-center gap-stack-sm rounded-lg px-stack-md py-2 font-label-md uppercase tracking-wide transition-all ${
                      sourceType === t
                        ? "bg-surface-container-high text-on-surface shadow-sm"
                        : "text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    <Icon name={SOURCE_ICON[t]} className="text-[18px]" />
                    {t}
                  </button>
                ))}
              </div>

              {/* Input: textarea (text) or dropzone (screenshot/audio) */}
              {sourceType === "text" ? (
                <textarea
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  rows={12}
                  placeholder="Paste the suspicious SMS, WhatsApp message, or email content here..."
                  className="min-h-[340px] w-full resize-none rounded-3xl border border-outline/20 bg-white/[0.02] p-stack-md font-body-md text-on-surface outline-none transition-all placeholder:text-on-surface-variant/50 focus:border-primary/50 focus:ring-1 focus:ring-primary/40"
                />
              ) : (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="group relative flex min-h-[340px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed border-outline/20 bg-white/[0.02] p-stack-lg text-center transition-all hover:border-primary/50"
                >
                  {/* Blurred accent blobs */}
                  <div className="pointer-events-none absolute -left-10 -top-10 h-40 w-40 rounded-full bg-primary/20 blur-3xl" />
                  <div className="pointer-events-none absolute -bottom-12 -right-8 h-44 w-44 rounded-full bg-secondary-container/20 blur-3xl" />

                  {/* Raised icon tile */}
                  <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl border border-white/10 bg-surface-container-high">
                    <Icon
                      name="cloud_upload"
                      className="text-4xl text-primary transition-transform duration-300 group-hover:scale-110"
                    />
                  </div>

                  <h3 className="relative mt-stack-md font-heading text-headline-sm text-on-surface">
                    {file ? file.name : `Upload ${sourceType}`}
                  </h3>
                  <p className="relative mt-1 max-w-sm text-body-md text-on-surface-variant">
                    {sourceType === "screenshot"
                      ? "Drag and drop a screenshot of the suspicious message, or browse your device."
                      : "Upload an audio recording of the suspicious call, or browse your device."}
                  </p>

                  {/* Browse pill */}
                  <span className="relative mt-stack-md inline-flex items-center gap-stack-sm rounded-full border border-white/10 bg-surface-container-high px-stack-md py-2 font-label-md text-on-surface">
                    <Icon name="folder_open" className="text-[18px]" />
                    Browse Local Files
                  </span>

                  {/* File-type hints */}
                  <p className="relative mt-stack-sm text-body-sm text-on-surface-variant/60">
                    {sourceType === "screenshot" ? "PNG · JPG · WEBP" : "MP3 · WAV · M4A"}
                  </p>

                  <input
                    ref={fileInputRef}
                    className="hidden"
                    type="file"
                    accept={sourceType === "screenshot" ? "image/*" : "audio/*"}
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </div>
              )}

              {error && (
                <div className="flex items-start gap-stack-sm rounded-xl border border-error/30 bg-error/10 p-stack-md">
                  <Icon name="error" className="text-[18px] text-error" />
                  <p className="text-body-md text-error">{error}</p>
                </div>
              )}

              {/* Run analysis */}
              <button
                onClick={runAnalysis}
                disabled={analyzing}
                className="btn-bloom flex w-full items-center justify-center gap-stack-md rounded-xl py-stack-md font-heading text-headline-sm text-on-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Icon
                  name={analyzing ? "sync" : "online_prediction"}
                  className={analyzing ? "animate-spin" : ""}
                />
                {analyzing ? "ANALYZING FORENSICS..." : "RUN AI ANALYSIS"}
              </button>

              {/* Processing stepper — visible during analysis */}
              {analyzing && (
                <div className="rounded-xl border border-outline-variant bg-surface-container-low/60 p-stack-md">
                  <ProcessingStepper stage={pipelineStage} />
                </div>
              )}

              {/* Data Privacy Protocol note */}
              <div className="flex items-start gap-stack-sm rounded-xl border border-tertiary/20 bg-tertiary/5 p-stack-md">
                <Icon name="privacy_tip" className="text-[18px] text-tertiary" />
                <div>
                  <p className="font-label-md uppercase tracking-wide text-tertiary">
                    Data Privacy Protocol
                  </p>
                  <p className="mt-1 text-body-sm text-on-surface-variant">
                    Evidence is processed securely for this analysis only and is never shared without
                    your explicit consent.
                  </p>
                </div>
              </div>
            </div>
          </motion.section>

          {/* RIGHT — Results */}
          <motion.section variants={item} className="lg:col-span-7">
            {!report ? (
              <div className="glass-panel relative flex h-full min-h-[340px] flex-col items-center justify-center overflow-hidden p-8 text-center">
                <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-error/10 blur-3xl" />
                <Icon name="shield_with_heart" className="relative mb-stack-md text-6xl text-outline" />
                <h3 className="relative mb-stack-sm font-heading text-headline-sm text-on-surface">
                  Awaiting Evidence
                </h3>
                <p className="relative max-w-xs text-body-md text-on-surface-variant">
                  Submit evidence and run analysis to view the AI threat verdict here.
                </p>
              </div>
            ) : (
              <div className="glass-panel critical-glow relative h-full space-y-stack-md overflow-hidden p-8">
                <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-error/10 blur-3xl" />

                {/* Verdict header */}
                <div className="relative flex items-center justify-between border-b border-outline-variant pb-stack-md">
                  <div className="flex flex-col">
                    <span className="font-label-sm uppercase tracking-widest text-on-surface-variant">
                      Analysis Verdict
                    </span>
                    <span className={`font-heading text-headline-sm ${severityText(currentScore?.severity_band)}`}>
                      {currentScore
                        ? `${currentScore.severity_band.toUpperCase()} THREAT`
                        : report.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="rounded bg-surface-container-high px-stack-sm py-1 font-mono text-[10px] font-bold uppercase text-on-surface-variant">
                    #{report.id.slice(0, 8)}
                  </div>
                </div>

                {report.low_confidence_flag && (
                  <div className="relative flex items-start gap-stack-sm rounded-lg border border-tertiary/30 bg-tertiary/10 p-stack-sm">
                    <Icon name="info" className="text-[18px] text-tertiary" />
                    <p className="font-label-md text-tertiary">
                      Low input confidence — the extracted text may be incomplete. Consider re-submitting as
                      clearer text.
                    </p>
                  </div>
                )}

                {currentScore ? (
                  <>
                    {/* Gauge + severity pill */}
                    <div className="relative flex flex-col items-center gap-stack-md py-stack-sm">
                      <RiskGauge value={currentScore.threat_score} severity={currentScore.severity_band} />
                      <span
                        className={`rounded-full px-stack-md py-1 font-label-md uppercase tracking-widest ${severityBadge(
                          currentScore.severity_band
                        )}`}
                      >
                        {currentScore.severity_band} threat
                      </span>
                    </div>

                    {/* Confidence + category */}
                    <div className="relative grid grid-cols-2 gap-stack-md rounded-xl border border-white/5 bg-white/5 p-stack-md text-center">
                      <div>
                        <p className="font-label-md uppercase text-[10px] text-on-surface-variant">Confidence</p>
                        <p className="font-heading text-headline-sm text-primary">
                          {Math.round((currentScore.confidence_score ?? 0) * 100)}%
                        </p>
                      </div>
                      <div>
                        <p className="font-label-md uppercase text-[10px] text-on-surface-variant">Category</p>
                        <p className="font-heading text-[16px] leading-tight text-on-surface">
                          {currentScore.scam_category}
                        </p>
                      </div>
                    </div>

                    {/* Red flags */}
                    {redFlags.length > 0 && (
                      <div className="relative space-y-stack-sm">
                        <p className="font-label-md uppercase tracking-widest text-[10px] text-on-surface-variant">
                          Detected Red Flags
                        </p>
                        <ul className="space-y-stack-sm">
                          {redFlags.map((flag, i) => (
                            <motion.li
                              key={i}
                              whileHover={cardHover}
                              className="flex items-start gap-stack-md rounded-xl border border-white/5 bg-white/5 p-stack-md text-body-md"
                            >
                              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-error/20 bg-error/15">
                                <Icon name="warning" className="text-[18px] text-error" />
                              </span>
                              <span className="text-on-surface">{flag}</span>
                            </motion.li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Recommended actions */}
                    {victimInstructions.length > 0 && (
                      <div className="relative space-y-stack-sm">
                        <p className="font-label-md uppercase tracking-widest text-[10px] text-on-surface-variant">
                          Recommended Response
                        </p>
                        <ul className="space-y-stack-sm">
                          {victimInstructions.map((inst, i) => (
                            <motion.li
                              key={i}
                              whileHover={cardHover}
                              className="flex items-start gap-stack-md rounded-xl border border-white/5 bg-white/5 p-stack-md text-body-md"
                            >
                              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/15">
                                <Icon name="check_circle" className="text-[18px] text-primary" />
                              </span>
                              <span className="text-on-surface">{inst}</span>
                            </motion.li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="relative py-stack-lg text-center">
                    <Icon name="hourglass_empty" className="mb-stack-sm text-4xl text-outline" />
                    <p className="text-body-md text-on-surface-variant">
                      Status: {report.status}. The AI scoring pipeline did not return a verdict. You can still
                      escalate this report.
                    </p>
                  </div>
                )}

                {escalated && (
                  <div className="relative flex items-start gap-stack-sm rounded-lg border border-primary/30 bg-primary/10 p-stack-sm">
                    <Icon name="local_police" className="text-[18px] text-primary" />
                    <p className="font-label-md text-primary">
                      Reported to Cyber Cell. Case reference: {escalated.caseId.slice(0, 8).toUpperCase()}
                    </p>
                  </div>
                )}

                {/* Actions */}
                <div className="relative flex flex-col gap-stack-sm border-t border-outline-variant pt-stack-md">
                  <button
                    onClick={handleEscalate}
                    disabled={escalating || report.status === "escalated"}
                    className="btn-bloom flex w-full items-center justify-center gap-stack-sm rounded-xl py-stack-md font-label-md uppercase tracking-widest text-on-primary disabled:opacity-60"
                  >
                    <Icon name="local_police" className="text-[18px]" />
                    {report.status === "escalated" ? "Reported to Cyber Cell" : "Report to Cyber Cell"}
                  </button>
                  <button
                    onClick={handleDownload}
                    className="flex w-full items-center justify-center gap-stack-sm rounded-xl border border-white/10 bg-white/[0.02] py-stack-md font-label-md uppercase tracking-widest text-on-surface transition-all hover:bg-white/5"
                  >
                    <Icon name="file_download" className="text-[18px]" />
                    Export Report
                  </button>
                  <button
                    onClick={handleDismiss}
                    disabled={dismissing || report.status === "dismissed" || report.status === "escalated"}
                    className="flex w-full items-center justify-center gap-stack-sm rounded-xl border border-white/10 bg-white/[0.02] py-stack-md font-label-md uppercase tracking-widest text-on-surface transition-all hover:bg-white/5 disabled:opacity-60"
                  >
                    <Icon name="check_circle" className="text-[18px]" />
                    {report.status === "dismissed" ? "Marked as Reviewed" : "Mark as Reviewed"}
                  </button>
                </div>
              </div>
            )}
          </motion.section>
        </div>

        {/* ─── Vigil chat (7) · Recent Scans (5) ──────────────────────────────── */}
        <div className="grid grid-cols-1 gap-gutter lg:grid-cols-12">
          {/* Vigil AI assistant */}
          <motion.section variants={item} className="lg:col-span-7">
            <div className="glass-panel flex h-full min-h-[440px] flex-col p-6">
              <div className="flex items-center gap-stack-sm">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/20 bg-primary/15">
                  <Icon name="smart_toy" className="text-[20px] text-primary" />
                </span>
                <div>
                  <h3 className="font-heading text-headline-sm leading-tight text-on-surface">
                    Vigil AI Assistant
                  </h3>
                  <p className="text-body-sm text-on-surface-variant/70">RBI / NCRP knowledge engine</p>
                </div>
              </div>

              <div className="custom-scrollbar my-stack-md min-h-[240px] flex-1 space-y-stack-md overflow-y-auto pr-1">
                {messages.map((m, i) => (
                  <div
                    key={i}
                    className={
                      m.role === "assistant"
                        ? "rounded-xl border border-white/5 bg-white/5 p-stack-md text-body-md text-on-surface"
                        : "ml-stack-md rounded-xl border border-primary/20 bg-primary/10 p-stack-md text-body-md text-on-surface"
                    }
                  >
                    <p className="whitespace-pre-wrap">{m.text}</p>
                    {m.citations && m.citations.length > 0 && (
                      <div className="mt-stack-sm space-y-1 border-t border-outline-variant/40 pt-stack-sm">
                        {m.citations.map((c, ci) => (
                          <div key={ci} className="font-label-md text-[10px] text-on-surface-variant">
                            <span className="text-primary">{c.source}</span> — {c.title}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {chatBusy && (
                  <div className="flex items-center gap-stack-sm rounded-xl border border-white/5 bg-white/5 p-stack-md text-on-surface-variant">
                    <Icon name="progress_activity" className="animate-spin text-[18px] text-primary" />
                    Analyzing knowledge base...
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <form onSubmit={sendChat} className="relative mt-auto">
                <textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendChat(e as unknown as FormEvent);
                    }
                  }}
                  rows={2}
                  placeholder="Ask Vigil about a scam..."
                  className="w-full resize-none rounded-xl border border-outline/20 bg-white/[0.03] p-stack-md pr-12 font-body-md text-on-surface outline-none transition-all placeholder:text-on-surface-variant/50 focus:border-primary/50 focus:ring-1 focus:ring-primary/40"
                />
                <button
                  type="submit"
                  disabled={chatBusy}
                  className="btn-bloom absolute bottom-3 right-2 rounded-lg p-2 text-on-primary disabled:opacity-50"
                >
                  <Icon name="send" className="text-[20px]" />
                </button>
              </form>
            </div>
          </motion.section>

          {/* Recent Scans */}
          <motion.section variants={item} className="lg:col-span-5">
            <div className="glass-panel h-full p-6">
              <div className="mb-stack-md flex items-center gap-stack-sm">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/20 bg-primary/15">
                  <Icon name="history" className="text-[20px] text-primary" />
                </span>
                <h3 className="font-heading text-headline-sm text-on-surface">Recent Scans</h3>
              </div>

              {history.length === 0 ? (
                <p className="text-body-sm text-on-surface-variant/60">No previous reports yet.</p>
              ) : (
                <div className="custom-scrollbar -mx-1 overflow-x-auto px-1">
                  <table className="w-full border-collapse text-left">
                    <thead>
                      <tr className="border-b border-outline-variant">
                        <th className="py-stack-sm pr-stack-md font-label-sm uppercase tracking-widest text-on-surface-variant">
                          Date
                        </th>
                        <th className="py-stack-sm pr-stack-md font-label-sm uppercase tracking-widest text-on-surface-variant">
                          Type
                        </th>
                        <th className="py-stack-sm pr-stack-md font-label-sm uppercase tracking-widest text-on-surface-variant">
                          Score
                        </th>
                        <th className="py-stack-sm font-label-sm uppercase tracking-widest text-on-surface-variant">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((r) => {
                        const sev = r.threat_scores?.[0]?.severity_band;
                        const score = r.threat_scores?.[0]?.threat_score;
                        return (
                          <tr
                            key={r.id}
                            onClick={() => {
                              setReport(r);
                              setEscalated(null);
                            }}
                            title={reportTitle(r)}
                            className="cursor-pointer border-b border-outline-variant/40 transition-colors last:border-0 hover:bg-white/5"
                          >
                            <td className="whitespace-nowrap py-stack-md pr-stack-md text-body-sm text-on-surface-variant">
                              {formatDateTime(r.created_at)}
                            </td>
                            <td className="py-stack-md pr-stack-md">
                              <span className="inline-flex items-center gap-stack-sm text-body-sm text-on-surface">
                                <Icon
                                  name={SOURCE_ICON[r.source_type as SourceType] ?? "policy"}
                                  className="text-[16px] text-on-surface-variant"
                                />
                                <span className="capitalize">{r.source_type}</span>
                              </span>
                            </td>
                            <td className="py-stack-md pr-stack-md">
                              {typeof score === "number" ? (
                                <span
                                  className={`rounded-full px-stack-sm py-0.5 text-[11px] font-bold ${severityBadge(sev)}`}
                                >
                                  {Math.round(score)}%
                                </span>
                              ) : (
                                <span className="text-body-sm text-on-surface-variant/50">—</span>
                              )}
                            </td>
                            <td className="py-stack-md">
                              <span
                                className={`rounded-full px-stack-sm py-0.5 text-[11px] font-medium uppercase tracking-wide ${statusBadge(
                                  r.status
                                )}`}
                              >
                                {r.status}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </motion.section>
        </div>
      </motion.div>
    </div>
  );
}
