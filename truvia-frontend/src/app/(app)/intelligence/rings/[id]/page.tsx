"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { GraphView } from "@/components/GraphView";
import { api, ApiError } from "@/lib/api";
import type { RingDetail, IntelligencePackageResult } from "@/lib/types";
import { severityBadge, formatDate, formatDateTime } from "@/lib/format";

export default function RingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const ringId = String(params.id);

  const [ring, setRing] = useState<RingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"package" | "export" | null>(null);
  const [toast, setToast] = useState<{ msg: string; kind: "ok" | "err" } | null>(null);
  const [pkg, setPkg] = useState<IntelligencePackageResult | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const r = await api.get<RingDetail>(`/graph/rings/${ringId}`);
      setRing(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load ring.");
    } finally { setLoading(false); }
  }, [ringId]);

  useEffect(() => { load(); }, [load]);

  const notify = (msg: string, kind: "ok" | "err") => {
    setToast({ msg, kind });
    setTimeout(() => setToast(null), 4000);
  };

  const generatePackage = async () => {
    setBusy("package");
    try {
      const res = await api.post<IntelligencePackageResult>("/graph/intelligence-package", { ring_id: ringId });
      setPkg(res);
      notify(`Ring-level Intelligence Package generated (v${res.version})`, "ok");
    } catch (e) {
      notify(e instanceof ApiError ? e.message : "Package generation failed", "err");
    } finally { setBusy(null); }
  };

  const exportEvidence = async () => {
    setBusy("export");
    try {
      await api.download(`/graph/rings/${ringId}/export`, `ring_evidence_${ringId}.json`);
      notify("Evidence bundle downloaded", "ok");
    } catch (e) {
      notify(e instanceof ApiError ? e.message : "Export failed", "err");
    } finally { setBusy(null); }
  };

  if (loading) return <PageLoader />;
  if (error || !ring) {
    return (
      <div className="p-stack-lg">
        <div className="card-obsidian p-stack-lg border-l-4 border-l-error flex items-center justify-between">
          <p className="text-body-md text-on-surface-variant">{error || "Ring not found."}</p>
          <button onClick={load} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-stack-lg flex flex-col gap-stack-lg">
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium ${toast.kind === "ok" ? "bg-primary/10 text-primary border-primary/30" : "bg-error/10 text-error border-error/30"}`}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-stack-md">
        <div className="flex items-center gap-stack-md">
          <button onClick={() => router.push("/intelligence/rings")} className="text-outline hover:text-on-surface"><Icon name="arrow_back" /></button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-headline-md text-on-surface">{ring.dominant_category || "Fraud Ring"}</h1>
              <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase ${severityBadge(ring.risk_tier)}`}>{ring.risk_tier}</span>
            </div>
            <p className="font-mono text-[12px] text-on-surface-variant">{ring.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-stack-sm">
          <button onClick={generatePackage} disabled={busy !== null}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-on-primary font-bold text-sm hover:opacity-90 disabled:opacity-50">
            {busy === "package" ? <Icon name="progress_activity" className="animate-spin text-[18px]" /> : <Icon name="description" className="text-[18px]" />}
            Generate Intelligence Package
          </button>
          <button onClick={exportEvidence} disabled={busy !== null}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-container border border-outline-variant/40 font-bold text-sm text-on-surface hover:bg-surface-container-high disabled:opacity-50">
            {busy === "export" ? <Icon name="progress_activity" className="animate-spin text-[18px]" /> : <Icon name="download" className="text-[18px]" />}
            Export Evidence
          </button>
        </div>
      </div>

      {pkg && (
        <div className="card-obsidian p-stack-md flex items-center justify-between border-l-4 border-l-primary">
          <p className="text-body-md text-on-surface">
            Package <span className="font-mono">{pkg.case_number}</span> v{pkg.version} — {pkg.entity_count} entities, {pkg.complaint_count} complaints.
          </p>
          <button onClick={() => api.download(pkg.download_url, `intelligence_package_${pkg.id}.pdf`)}
            className="px-3 py-1.5 rounded-lg bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20">View Package (PDF)</button>
        </div>
      )}

      <div className="grid grid-cols-4 gap-stack-md">
        <Cell label="Entities" value={String(ring.member_count)} />
        <Cell label="Complaints" value={String(ring.complaint_count)} />
        <Cell label="Aggregate Risk" value={String(Math.round(ring.aggregate_risk_score))} />
        <Cell label="Last Activity" value={formatDate(ring.last_activity_at || undefined)} />
      </div>

      <div className="flex flex-col xl:flex-row gap-stack-lg">
        {/* Scoped subgraph */}
        <div className="flex-1 graph-bg border border-outline-variant/30 rounded-2xl relative overflow-hidden shadow-2xl min-h-[420px]">
          <div className="absolute top-3 left-3 z-10 text-[10px] font-bold text-outline uppercase tracking-widest">Ring Subgraph</div>
          <GraphView nodes={ring.subgraph.nodes} edges={ring.subgraph.edges} onSelect={(id) => router.push(`/intelligence/entity/${id}`)} />
        </div>

        <div className="w-full xl:w-[380px] flex flex-col gap-stack-lg">
          {/* Members */}
          <section className="card-obsidian p-stack-lg">
            <h3 className="text-[11px] font-bold text-outline uppercase tracking-[0.2em] mb-stack-md">Member Entities ({ring.members.length})</h3>
            <div className="space-y-1.5 max-h-64 overflow-y-auto custom-scrollbar">
              {ring.members.map((m) => (
                <button key={m.id} onClick={() => router.push(`/intelligence/entity/${m.id}`)}
                  className="w-full flex items-center justify-between p-2.5 bg-surface-container/30 hover:bg-surface-container rounded-xl border border-transparent hover:border-outline-variant/30 transition-colors">
                  <span className="font-mono text-[12px] text-on-surface truncate">{m.label}</span>
                  <span className="text-[10px] text-outline uppercase">{m.type}</span>
                </button>
              ))}
            </div>
          </section>

          {/* Complaints */}
          <section className="card-obsidian p-stack-lg">
            <h3 className="text-[11px] font-bold text-outline uppercase tracking-[0.2em] mb-stack-md">Correlated Complaints ({ring.complaints.length})</h3>
            <div className="space-y-1.5 max-h-64 overflow-y-auto custom-scrollbar">
              {ring.complaints.length === 0 && <p className="text-body-md text-on-surface-variant/60 text-[12px]">No correlated complaints.</p>}
              {ring.complaints.map((c) => (
                <button key={c.id} onClick={() => router.push(`/investigations/${c.id}`)}
                  className="w-full flex items-center justify-between p-2.5 bg-surface-container-lowest/50 hover:bg-surface-container rounded-lg border border-outline-variant/30 transition-colors text-left">
                  <span className="min-w-0">
                    <span className="block text-[12px] text-on-surface truncate">{c.scam_category || c.source_type}</span>
                    <span className="block text-[10px] text-on-surface-variant">{formatDateTime(c.created_at || undefined)}</span>
                  </span>
                  {c.threat_score != null && (
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${severityBadge(c.severity_band || undefined)}`}>{c.threat_score}</span>
                  )}
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="card-obsidian p-stack-md text-center">
      <p className="text-[9px] font-bold text-outline uppercase">{label}</p>
      <p className="text-xl font-bold text-on-surface mt-1">{value}</p>
    </div>
  );
}
