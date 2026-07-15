"use client";

import { useState, useEffect, useRef, FormEvent } from "react";
import { Icon } from "@/components/Icon";
import { RiskGauge } from "@/components/RiskGauge";
import { ProcessingStepper } from "@/components/ProcessingStepper";
import { api, ApiError } from "@/lib/api";
import type { Report, ChatResponse, Citation } from "@/lib/types";
import { severityBadge, severityText, reportTitle, formatDateTime } from "@/lib/format";

type SourceType = "text" | "screenshot" | "audio";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

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
      setReport(final);
      setPipelineStage(null);
      loadHistory();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Analysis failed. Please try again.");
    } finally {
      setAnalyzing(false);
      setPipelineStage(null);
    }
  }

  async function handleEscalate() {
    if (!report) return;
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
    <div className="flex flex-col lg:flex-row min-h-[calc(100vh-64px)]">
      {/* Left: upload + result */}
      <div className="flex-1 overflow-y-auto p-stack-lg lg:p-margin-page space-y-stack-lg custom-scrollbar">
        <header>
          <h1 className="text-headline-lg text-primary">Citizen Fraud Shield</h1>
          <p className="text-on-surface-variant max-w-2xl text-body-lg mt-1">
            Deploy AI-powered analysis to detect phishing, social engineering, and financial fraud in
            screenshots, audio, or text messages.
          </p>
        </header>

        <div className="grid grid-cols-12 gap-gutter">
          {/* Input */}
          <section className="col-span-12 xl:col-span-7 space-y-stack-md">
            {/* Source tabs */}
            <div className="flex gap-stack-sm">
              {(["text", "screenshot", "audio"] as SourceType[]).map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setSourceType(t);
                    setFile(null);
                    setError(null);
                  }}
                  className={`flex items-center gap-stack-sm px-stack-md py-2 rounded-lg font-label-md uppercase transition-colors ${
                    sourceType === t
                      ? "bg-primary-container text-white"
                      : "bg-surface-container-high text-on-surface hover:bg-surface-variant"
                  }`}
                >
                  <Icon
                    name={t === "text" ? "notes" : t === "screenshot" ? "image" : "mic"}
                    className="text-[18px]"
                  />
                  {t}
                </button>
              ))}
            </div>

            {sourceType === "text" ? (
              <textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                rows={10}
                placeholder="Paste the suspicious SMS, WhatsApp message, or email content here..."
                className="w-full bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md font-body-md text-on-surface resize-none focus:ring-1 focus:ring-primary outline-none min-h-[280px]"
              />
            ) : (
              <div
                className="relative border-2 border-transparent bg-surface-container-lowest rounded-xl p-stack-lg flex flex-col items-center justify-center min-h-[280px] upload-dashed cursor-pointer hover:bg-surface-container-high/40 transition-all"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="w-16 h-16 bg-surface-container-high rounded-full flex items-center justify-center mb-stack-md">
                  <Icon name="cloud_upload" className="text-primary text-3xl" />
                </div>
                <h3 className="font-headline-sm text-on-surface mb-1">
                  {file ? file.name : `Upload ${sourceType}`}
                </h3>
                <p className="text-on-surface-variant font-body-md text-center max-w-sm">
                  {sourceType === "screenshot"
                    ? "Drag and drop a screenshot (PNG/JPG) of the suspicious message."
                    : "Upload an audio recording (MP3/WAV/M4A) of the suspicious call."}
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
              <div className="flex items-start gap-stack-sm p-stack-md bg-error/10 rounded-lg border border-error/30">
                <Icon name="error" className="text-error text-[18px]" />
                <p className="font-body-md text-error">{error}</p>
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={runAnalysis}
                disabled={analyzing}
                className="px-stack-lg py-stack-md bg-primary-container text-white font-headline-sm rounded-xl hover:shadow-[0_0_20px_rgba(93,95,239,0.3)] active:scale-[0.98] transition-all flex items-center gap-stack-md disabled:opacity-60"
              >
                <Icon name={analyzing ? "sync" : "online_prediction"} className={analyzing ? "animate-spin" : ""} />
                {analyzing ? "ANALYZING FORENSICS..." : "RUN AI ANALYSIS"}
              </button>
            </div>
          </section>

          {/* Processing stepper — visible during analysis */}
          {analyzing && (
            <div className="col-span-12 p-stack-md bg-surface-container-lowest border border-outline-variant rounded-xl">
              <ProcessingStepper stage={pipelineStage} />
            </div>
          )}

          {/* Result */}
          <section className="col-span-12 xl:col-span-5">
            {!report ? (
              <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-card-padding h-full flex flex-col items-center justify-center text-center min-h-[280px] opacity-70">
                <Icon name="shield_with_heart" className="text-outline text-5xl mb-stack-md" />
                <p className="font-body-md text-on-surface-variant max-w-xs">
                  Submit evidence and run analysis to view the AI threat verdict here.
                </p>
              </div>
            ) : (
              <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-card-padding space-y-stack-md h-full glow-effect">
                <div className="flex items-center justify-between border-b border-outline-variant pb-stack-md">
                  <div className="flex flex-col">
                    <span className="font-label-md text-on-surface-variant uppercase text-[10px] tracking-widest">
                      Analysis Verdict
                    </span>
                    <span className={`font-headline-sm ${severityText(currentScore?.severity_band)}`}>
                      {currentScore
                        ? `${currentScore.severity_band.toUpperCase()} THREAT`
                        : report.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="px-stack-sm py-1 bg-surface-container-high text-on-surface-variant text-[10px] font-bold rounded uppercase font-mono">
                    #{report.id.slice(0, 8)}
                  </div>
                </div>

                {report.low_confidence_flag && (
                  <div className="flex items-start gap-stack-sm p-stack-sm bg-tertiary/10 rounded-lg border border-tertiary/30">
                    <Icon name="info" className="text-tertiary text-[18px]" />
                    <p className="font-label-md text-tertiary">
                      Low input confidence — the extracted text may be incomplete. Consider re-submitting as
                      clearer text.
                    </p>
                  </div>
                )}

                {currentScore ? (
                  <>
                    <div className="flex flex-col items-center py-stack-md">
                      <RiskGauge value={currentScore.threat_score} severity={currentScore.severity_band} />
                    </div>

                    <div className="grid grid-cols-2 gap-stack-md text-center bg-surface-container-low p-stack-md rounded-xl">
                      <div>
                        <p className="font-label-md text-on-surface-variant uppercase text-[10px]">Confidence</p>
                        <p className="font-headline-sm text-primary">
                          {Math.round((currentScore.confidence_score ?? 0) * 100)}%
                        </p>
                      </div>
                      <div>
                        <p className="font-label-md text-on-surface-variant uppercase text-[10px]">Category</p>
                        <p className="font-headline-sm text-on-surface text-[16px] leading-tight">
                          {currentScore.scam_category}
                        </p>
                      </div>
                    </div>

                    {redFlags.length > 0 && (
                      <div className="space-y-stack-sm">
                        <p className="font-label-md text-on-surface-variant uppercase text-[10px] tracking-widest">
                          Detected Red Flags
                        </p>
                        <ul className="space-y-stack-sm">
                          {redFlags.map((flag, i) => (
                            <li
                              key={i}
                              className="flex items-start gap-stack-sm text-body-md bg-error/5 p-stack-sm rounded-lg border border-error/20"
                            >
                              <Icon name="warning" className="text-error text-[18px]" />
                              <span className="text-on-surface">{flag}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {victimInstructions.length > 0 && (
                      <div className="space-y-stack-sm">
                        <p className="font-label-md text-on-surface-variant uppercase text-[10px] tracking-widest">
                          Recommended Actions
                        </p>
                        <ul className="space-y-stack-sm">
                          {victimInstructions.map((inst, i) => (
                            <li
                              key={i}
                              className="flex items-start gap-stack-sm text-body-md bg-primary/5 p-stack-sm rounded-lg border border-primary/20"
                            >
                              <Icon name="check_circle" className="text-primary text-[18px]" />
                              <span className="text-on-surface">{inst}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="py-stack-lg text-center">
                    <Icon name="hourglass_empty" className="text-outline text-4xl mb-stack-sm" />
                    <p className="font-body-md text-on-surface-variant">
                      Status: {report.status}. The AI scoring pipeline did not return a verdict. You can still
                      escalate this report.
                    </p>
                  </div>
                )}

                {escalated && (
                  <div className="flex items-start gap-stack-sm p-stack-sm bg-primary/10 rounded-lg border border-primary/30">
                    <Icon name="local_police" className="text-primary text-[18px]" />
                    <p className="font-label-md text-primary">
                      Reported to Cyber Cell. Case reference: {escalated.caseId.slice(0, 8).toUpperCase()}
                    </p>
                  </div>
                )}

                <div className="pt-stack-md border-t border-outline-variant flex flex-col gap-stack-sm">
                  <button
                    onClick={handleEscalate}
                    disabled={escalating || report.status === "escalated"}
                    className="w-full py-stack-md bg-primary text-on-primary rounded-xl font-label-md uppercase tracking-widest hover:brightness-110 transition-all flex items-center justify-center gap-stack-sm disabled:opacity-60"
                  >
                    <Icon name="local_police" className="text-[18px]" />
                    {report.status === "escalated" ? "Reported to Cyber Cell" : "Report to Cyber Cell"}
                  </button>
                  <button
                    onClick={handleDownload}
                    className="w-full py-stack-md bg-surface-container-high text-on-surface rounded-xl font-label-md uppercase tracking-widest hover:bg-surface-variant transition-all flex items-center justify-center gap-stack-sm"
                  >
                    <Icon name="file_download" className="text-[18px]" />
                    Download Report
                  </button>
                  <button
                    onClick={handleDismiss}
                    disabled={dismissing || report.status === "dismissed" || report.status === "escalated"}
                    className="w-full py-stack-md bg-surface-container-high text-on-surface rounded-xl font-label-md uppercase tracking-widest hover:bg-surface-variant transition-all flex items-center justify-center gap-stack-sm disabled:opacity-60"
                  >
                    <Icon name="check_circle" className="text-[18px]" />
                    {report.status === "dismissed" ? "Marked as Reviewed" : "Mark as Reviewed"}
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Right: AI assistant + history */}
      <aside className="w-full lg:w-[360px] border-t lg:border-t-0 lg:border-l border-outline-variant bg-surface-container-lowest flex flex-col lg:h-[calc(100vh-64px)]">
        <div className="p-stack-lg flex-1 flex flex-col min-h-0">
          <div className="flex items-center gap-stack-sm mb-stack-md">
            <Icon name="smart_toy" className="text-primary" />
            <h3 className="font-headline-sm text-on-surface">Vigil AI Assistant</h3>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar space-y-stack-md mb-stack-md min-h-[240px]">
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "assistant"
                    ? "bg-surface-container-low p-stack-md rounded-xl border border-outline-variant text-body-md text-on-surface"
                    : "bg-secondary-container p-stack-md rounded-xl text-on-secondary-container text-body-md ml-stack-md border border-primary/20"
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
              <div className="bg-surface-container-low p-stack-md rounded-xl border border-outline-variant text-on-surface-variant flex items-center gap-stack-sm">
                <Icon name="progress_activity" className="animate-spin text-primary text-[18px]" />
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
              className="w-full bg-surface-container-high border border-outline-variant rounded-xl p-stack-md pr-12 font-body-md text-on-surface resize-none focus:ring-1 focus:ring-primary outline-none"
            />
            <button
              type="submit"
              disabled={chatBusy}
              className="absolute right-2 bottom-3 p-2 bg-primary text-on-primary rounded-lg hover:scale-105 transition-transform disabled:opacity-50"
            >
              <Icon name="send" className="text-[20px]" />
            </button>
          </form>
        </div>

        <div className="bg-surface-container-low p-stack-lg border-t border-outline-variant">
          <h4 className="font-label-md text-on-surface-variant uppercase text-[10px] tracking-widest mb-stack-md">
            Recent Analyses
          </h4>
          {history.length === 0 ? (
            <p className="font-body-md text-on-surface-variant/60 text-[12px]">No previous reports yet.</p>
          ) : (
            <div className="space-y-stack-sm max-h-52 overflow-y-auto custom-scrollbar">
              {history.map((r) => {
                const sev = r.threat_scores?.[0]?.severity_band;
                return (
                  <button
                    key={r.id}
                    onClick={() => {
                      setReport(r);
                      setEscalated(null);
                    }}
                    className="w-full flex items-center gap-stack-sm group text-left hover:bg-surface-container p-stack-sm rounded-lg transition-colors"
                  >
                    <div className={`p-2 rounded-lg ${severityBadge(sev)}`}>
                      <Icon name="policy" className="text-[18px]" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="font-label-md text-on-surface text-[11px] truncate">
                        {reportTitle(r)}
                      </span>
                      <span className="font-body-md text-on-surface-variant text-[11px]">
                        {formatDateTime(r.created_at)}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
