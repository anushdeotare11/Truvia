"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { CaseDetails } from "@/lib/types";
import { severityBadge, statusBadge, formatDateTime, shortId } from "@/lib/format";

export default function InvestigationDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { user } = useAuth();

  const [detail, setDetail] = useState<CaseDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  async function load() {
    try {
      const data = await api.get<CaseDetails>(`/cases/${id}`);
      setDetail(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load case.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function assignToMe() {
    if (!user) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/cases/${id}/assign`, { officer_id: user.id });
      setToast("Case assigned to you.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Assignment failed.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadPackage() {
    setBusy(true);
    try {
      await api.download(`/cases/${id}/package`, `dossier-${detail?.case_number ?? id}.pdf`);
      setToast("Intelligence package compiled.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not compile package.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <PageLoader />;
  if (error && !detail) return <div className="p-margin-page text-error font-body-md">{error}</div>;
  if (!detail) return null;

  // Build a timeline from linked reports + audit logs.
  const timeline = [
    ...detail.linked_reports.map((r) => ({
      kind: "report" as const,
      title: `Evidence linked: ${r.source_type}`,
      body: r.cleaned_text?.slice(0, 140) ?? "No transcript",
      time: r.created_at,
      icon: "radar",
    })),
    ...detail.audit_logs.map((l) => ({
      kind: "audit" as const,
      title: l.action.replace(/[._]/g, " "),
      body: l.diff_json ? JSON.stringify(l.diff_json) : "",
      time: l.created_at,
      icon: "sync_alt",
    })),
  ].sort((a, b) => new Date(b.time ?? 0).getTime() - new Date(a.time ?? 0).getTime());

  // Highest-risk extracted entity — the node the graph should auto-center on when
  // the officer opens "View in Threat Intelligence Engine" (App Flow §9).
  const topEntity = detail.entities.length
    ? [...detail.entities].sort((a, b) => b.risk_score - a.risk_score)[0]
    : null;

  return (
    <div className="p-gutter">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-stack-md mb-stack-lg">
        <div>
          <nav className="flex items-center gap-2 text-on-surface-variant mb-1">
            <Link href="/investigations" className="text-[11px] uppercase font-bold tracking-wider hover:text-primary">
              Investigations
            </Link>
            <Icon name="chevron_right" className="text-[14px]" />
            <span className="text-[11px] uppercase font-bold tracking-wider text-primary">
              {detail.case_number}
            </span>
          </nav>
          <h2 className="text-headline-md font-bold text-on-surface tracking-tight">
            {detail.case_type?.replace(/_/g, " ") || "Investigation"} — {detail.case_number}
          </h2>
        </div>
        <button
          onClick={downloadPackage}
          disabled={busy}
          className="bg-primary text-on-primary px-6 py-2.5 rounded-xl text-[11px] font-bold uppercase tracking-wider hover:brightness-110 transition-all flex items-center gap-2 shadow-lg shadow-primary/20 disabled:opacity-60"
        >
          <Icon name="auto_awesome" className="text-[18px]" />
          Intelligence Package
        </button>
      </div>

      {toast && (
        <div className="mb-stack-md flex items-center gap-stack-sm p-stack-sm bg-primary/10 border border-primary/30 rounded-lg text-primary font-body-md">
          <Icon name="check_circle" className="text-[18px]" />
          {toast}
        </div>
      )}
      {error && (
        <div className="mb-stack-md flex items-center gap-stack-sm p-stack-sm bg-error/10 border border-error/30 rounded-lg text-error font-body-md">
          <Icon name="error" className="text-[18px]" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-12 gap-gutter">
        {/* LEFT */}
        <div className="col-span-12 lg:col-span-3 space-y-gutter">
          <div className="bg-surface-container border border-outline-variant p-card-padding rounded-xl">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-stack-md flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              Case Assignment
            </h3>
            <div className="space-y-stack-sm">
              <Row label="Priority">
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${severityBadge(detail.priority)}`}>
                  {detail.priority}
                </span>
              </Row>
              <Row label="Status">
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${statusBadge(detail.status)}`}>
                  {detail.status?.replace(/_/g, " ")}
                </span>
              </Row>
              <Row label="Assignee">
                <span className="text-body-md font-medium text-on-surface">{detail.assigned_officer_name}</span>
              </Row>
            </div>
            <button
              onClick={assignToMe}
              disabled={busy || detail.assigned_officer_id === user?.id}
              className="w-full mt-stack-md py-stack-sm bg-surface-container-high hover:bg-surface-variant rounded-lg font-label-md uppercase text-[11px] text-on-surface transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Icon name="assignment_ind" className="text-[16px]" />
              {detail.assigned_officer_id === user?.id ? "Assigned to You" : "Assign to Me"}
            </button>
          </div>

          <div className="bg-surface-container border border-outline-variant p-card-padding rounded-xl">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-stack-md">
              Case Metadata
            </h3>
            <div className="space-y-stack-md">
              <Meta label="Linked Reports" value={String(detail.linked_reports.length)} />
              <Meta label="Extracted Entities" value={String(detail.entities.length)} />
              <Meta label="Audit Events" value={String(detail.audit_logs.length)} />
              <div className="pt-stack-sm border-t border-outline-variant">
                <p className="text-[9px] font-bold text-on-surface-variant/50 uppercase tracking-widest mb-1">
                  AI Summary
                </p>
                <p className="bg-surface-container-high p-stack-sm rounded-lg border border-outline-variant italic text-body-sm leading-relaxed text-on-surface-variant">
                  {detail.ai_summary || "No summary prepared."}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* CENTER */}
        <div className="col-span-12 lg:col-span-6 space-y-gutter">
          <div className="bg-surface-container border border-outline-variant p-card-padding rounded-xl">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-stack-lg">
              Evidence & Activity Timeline
            </h3>
            {timeline.length === 0 ? (
              <p className="font-body-md text-on-surface-variant">No timeline events.</p>
            ) : (
              <div className="relative pl-8 border-l border-outline-variant ml-2 space-y-stack-lg pb-4">
                {timeline.map((t, i) => (
                  <div key={i} className="relative">
                    <div
                      className={`absolute -left-[41px] top-1 w-5 h-5 rounded-full flex items-center justify-center ring-[6px] ring-surface-container ${
                        t.kind === "report" ? "bg-primary" : "bg-surface-container-high border border-outline-variant"
                      }`}
                    >
                      <Icon
                        name={t.icon}
                        className={`text-[10px] ${t.kind === "report" ? "text-on-primary" : "text-on-surface-variant"}`}
                      />
                    </div>
                    <div className="flex justify-between items-start gap-2">
                      <p className="text-body-md font-bold text-on-surface capitalize">{t.title}</p>
                      <span className="text-[10px] font-mono text-on-surface-variant/60 whitespace-nowrap">
                        {formatDateTime(t.time)}
                      </span>
                    </div>
                    {t.body && (
                      <p className="text-body-sm text-on-surface-variant mt-1 leading-relaxed break-words">
                        {t.body}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Linked reports evidence */}
          <div className="bg-surface-container border border-outline-variant rounded-xl overflow-hidden">
            <div className="p-4 border-b border-outline-variant flex items-center gap-3">
              <Icon name="data_object" className="text-primary" />
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface">Linked Evidence</h3>
            </div>
            <div className="divide-y divide-outline-variant/30 max-h-80 overflow-y-auto custom-scrollbar">
              {detail.linked_reports.map((r) => (
                <div key={r.id} className="p-4 hover:bg-surface-container-high/40 transition-colors">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-[11px] text-primary">#{shortId(r.id)}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${statusBadge(r.status)}`}>
                      {r.status}
                    </span>
                  </div>
                  <p className="text-body-sm text-on-surface-variant line-clamp-2">
                    {r.cleaned_text || "No transcript available."}
                  </p>
                </div>
              ))}
              {detail.linked_reports.length === 0 && (
                <p className="p-4 text-on-surface-variant font-body-md">No evidence linked.</p>
              )}
            </div>
          </div>

          {/* Correlated complaints (share extracted entities with this case) */}
          <div className="bg-surface-container border border-outline-variant rounded-xl overflow-hidden">
            <div className="p-4 border-b border-outline-variant flex items-center gap-3">
              <Icon name="account_tree" className="text-primary" />
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface">Correlated Complaints</h3>
            </div>
            <div className="divide-y divide-outline-variant/30 max-h-80 overflow-y-auto custom-scrollbar">
              {(detail.correlated_reports ?? []).map((r) => (
                <div key={r.id} className="p-4 hover:bg-surface-container-high/40 transition-colors">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-[11px] text-primary">#{shortId(r.id)}</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-primary/10 text-primary">
                      {r.shared_entities} shared {r.shared_entities === 1 ? "entity" : "entities"}
                    </span>
                  </div>
                  <p className="text-body-sm text-on-surface-variant line-clamp-2">
                    {r.cleaned_text || "No transcript available."}
                  </p>
                </div>
              ))}
              {(!detail.correlated_reports || detail.correlated_reports.length === 0) && (
                <p className="p-4 text-on-surface-variant font-body-md">
                  No correlated complaints found — this appears to be an isolated report.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="col-span-12 lg:col-span-3 space-y-gutter">
          <div className="bg-surface-container border border-outline-variant rounded-xl overflow-hidden flex flex-col">
            <div className="p-4 border-b border-outline-variant flex items-center justify-between">
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                Extracted Entities
              </h3>
              <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-[10px] font-bold">
                {detail.entities.length}
              </span>
            </div>
            {topEntity && (
              <Link
                href={`/intelligence/graph?focus=${topEntity.id}`}
                className="flex items-center justify-center gap-2 px-4 py-2.5 border-b border-outline-variant bg-primary/5 hover:bg-primary/10 text-primary font-bold text-[11px] uppercase tracking-wider transition-colors"
              >
                <Icon name="hub" className="text-[16px]" />
                View in Threat Intelligence Engine
              </Link>
            )}
            <div className="max-h-96 overflow-y-auto custom-scrollbar">
              {detail.entities.map((e) => (
                <div
                  key={e.id}
                  className="p-3 border-b border-outline-variant/30 hover:bg-primary/5 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-primary font-bold opacity-70 font-mono text-[10px] uppercase">
                      {e.type}
                    </span>
                    <span className={`px-1.5 rounded text-[10px] font-bold ${severityBadge(e.risk_tier)}`}>
                      {Math.round(e.risk_score)}
                    </span>
                  </div>
                  <Link
                    href={`/intelligence/entity/${e.id}?from=${encodeURIComponent(`/investigations/${id}`)}`}
                    className="text-on-surface font-mono text-[12px] break-all hover:text-primary transition-colors"
                  >
                    {e.raw_value}
                  </Link>
                </div>
              ))}
              {detail.entities.length === 0 && (
                <p className="p-4 text-on-surface-variant font-body-md">No entities extracted.</p>
              )}
            </div>
          </div>

          <div className="bg-surface-container border border-outline-variant p-card-padding rounded-xl">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-stack-md">
              Officer Activity Log
            </h3>
            <div className="space-y-stack-sm max-h-64 overflow-y-auto custom-scrollbar">
              {detail.audit_logs.map((l) => (
                <div
                  key={l.id}
                  className="p-3 bg-surface-container-high rounded-xl border border-outline-variant/50 text-body-sm leading-snug"
                >
                  <span className="font-bold text-primary mr-1 capitalize">{l.action.replace(/[._]/g, " ")}:</span>
                  <span className="text-on-surface-variant">
                    {l.diff_json ? Object.values(l.diff_json).join(", ") : "—"}
                  </span>
                  <p className="text-[10px] text-on-surface-variant/50 mt-1 font-mono">
                    {formatDateTime(l.created_at)}
                  </p>
                </div>
              ))}
              {detail.audit_logs.length === 0 && (
                <p className="text-on-surface-variant font-body-md text-[12px]">No activity recorded yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center bg-background/40 p-3 rounded-lg border border-outline-variant/30">
      <span className="text-body-sm text-on-surface-variant">{label}</span>
      {children}
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-[9px] font-bold text-on-surface-variant/50 uppercase tracking-widest">{label}</span>
      <span className="text-body-md font-bold text-on-surface">{value}</span>
    </div>
  );
}
