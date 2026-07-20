"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence, useReducedMotion, type Variants } from "framer-motion";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { GraphView } from "@/components/GraphView";
import { api, ApiError } from "@/lib/api";
import type { RingDetail, IntelligencePackageResult, GraphNode } from "@/lib/types";
import { severityBadge, statusBadge, formatDate, formatDateTime, shortId } from "@/lib/format";

// GraphView type palette — keep member chips colored consistently with the graph.
const TYPE_COLOR: Record<string, string> = {
  phone: "#b5c4ff",
  upi: "#ffb787",
  domain: "#658aff",
  email: "#8d90a0",
  ip: "#00f4fe",
  device: "#00dce5",
};

function entityColor(node: GraphNode): string {
  if (node.risk_score >= 80) return "#ffb4ab";
  return TYPE_COLOR[node.type] ?? "#b5c4ff";
}

export default function RingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const ringId = String(params.id);
  const reduce = useReducedMotion();

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

  // ─── Motion variants (respect reduced-motion) ───
  const container: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.06, delayChildren: reduce ? 0 : 0.04 } },
  };
  const item: Variants = {
    hidden: { opacity: 0, y: reduce ? 0 : 18 },
    show: { opacity: 1, y: 0, transition: { duration: reduce ? 0 : 0.45, ease: [0.16, 1, 0.3, 1] } },
  };
  const hoverLift = reduce ? undefined : { y: -4 };

  if (loading) return <PageLoader />;
  if (error || !ring) {
    return (
      <div className="relative min-h-screen bg-background p-margin-page">
        <div className="glass-panel p-stack-lg border-l-4 border-l-error flex items-center justify-between gap-stack-md">
          <p className="font-sans text-body-md text-on-surface-variant">{error || "Ring not found."}</p>
          <div className="flex items-center gap-stack-sm">
            <button onClick={() => router.push("/intelligence/rings")}
              className="px-4 py-2 rounded-xl bg-white/5 text-on-surface-variant font-semibold text-sm hover:bg-white/10 transition-colors">Back</button>
            <button onClick={load}
              className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20 transition-colors">Retry</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-background p-margin-page">
      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: reduce ? 0 : 20, scale: reduce ? 1 : 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: reduce ? 0 : 20, scale: reduce ? 1 : 0.96 }}
            className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium ${toast.kind === "ok" ? "bg-primary/10 text-primary border-primary/30" : "bg-error/10 text-error border-error/30"}`}
          >
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div variants={container} initial="hidden" animate="show" className="flex flex-col gap-stack-lg">
        {/* Header */}
        <motion.header variants={item} className="flex items-start justify-between flex-wrap gap-stack-md">
          <div className="flex items-start gap-stack-md">
            <button
              onClick={() => router.push("/intelligence/rings")}
              aria-label="Back to fraud rings"
              className="mt-1 flex items-center justify-center w-11 h-11 rounded-xl bg-white/5 border border-white/10 text-on-surface-variant hover:text-on-surface hover:border-secondary-container/40 hover:bg-white/10 transition-colors"
            >
              <Icon name="arrow_back" />
            </button>
            <div className="min-w-0">
              {/* Breadcrumb */}
              <nav className="flex items-center gap-1.5 font-sans text-[11px] uppercase tracking-[0.18em] text-outline mb-1.5">
                <button onClick={() => router.push("/intelligence")} className="hover:text-on-surface-variant transition-colors">Intelligence</button>
                <span className="text-outline-variant">/</span>
                <button onClick={() => router.push("/intelligence/rings")} className="hover:text-on-surface-variant transition-colors">Fraud Rings</button>
                <span className="text-outline-variant">/</span>
                <span className="font-mono text-secondary-container normal-case tracking-normal truncate">{ring.id}</span>
              </nav>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="font-heading text-headline-lg text-on-surface">{ring.dominant_category || "Fraud Ring"}</h1>
                <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider ${severityBadge(ring.risk_tier)}`}>{ring.risk_tier}</span>
              </div>
              <p className="font-mono text-[12px] text-on-surface-variant/70 mt-1">{ring.id}</p>
            </div>
          </div>
        </motion.header>

        {/* Metrics tiles */}
        <motion.section variants={item} className="grid grid-cols-2 lg:grid-cols-4 gap-stack-md">
          <MetricTile label="Member Entities" value={String(ring.member_count)} icon="hub" />
          <MetricTile label="Complaints" value={String(ring.complaint_count)} icon="report" />
          <MetricTile label="Aggregate Risk" value={String(Math.round(ring.aggregate_risk_score))} icon="risk" />
          <MetricTile label="Last Activity" value={formatDate(ring.last_activity_at || undefined)} icon="schedule" />
        </motion.section>

        {/* Package result banner */}
        <AnimatePresence>
          {pkg && (
            <motion.div
              variants={item}
              initial="hidden"
              animate="show"
              exit={{ opacity: 0, y: reduce ? 0 : -8 }}
              className="obsidian-panel electric-edge p-stack-md flex items-center justify-between flex-wrap gap-stack-sm"
            >
              <p className="font-sans text-body-md text-on-surface">
                Package <span className="font-mono text-secondary-container">{pkg.case_number}</span> v{pkg.version}
                {pkg.entity_count != null && pkg.complaint_count != null && (
                  <> — {pkg.entity_count} entities, {pkg.complaint_count} complaints.</>
                )}
              </p>
              <button
                onClick={() => api.download(pkg.download_url, `intelligence_package_${pkg.id}.pdf`)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20 transition-colors"
              >
                <Icon name="picture_as_pdf" className="text-[18px]" /> View Package (PDF)
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main layout: graph + right column */}
        <div className="flex flex-col xl:flex-row gap-stack-lg items-start">
          {/* Ring subgraph */}
          <motion.div
            variants={item}
            className="w-full xl:flex-1 glass-panel relative overflow-hidden min-h-[480px]"
          >
            <div className="graph-bg absolute inset-0" />
            <div className="absolute top-4 left-5 z-10 flex items-center gap-2 font-sans text-[10px] font-bold text-outline uppercase tracking-[0.2em]">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary-container glow-dot text-secondary-container" />
              Ring Network
            </div>
            <div className="relative z-[1] w-full h-full min-h-[480px]">
              <GraphView
                nodes={ring.subgraph.nodes}
                edges={ring.subgraph.edges}
                onSelect={(id) => router.push(`/intelligence/entity/${id}`)}
              />
            </div>
          </motion.div>

          {/* Right column */}
          <div className="w-full xl:w-[400px] flex flex-col gap-stack-lg">
            {/* Members / Entities */}
            <motion.section variants={item} whileHover={hoverLift} className="glass-panel p-stack-lg">
              <h3 className="font-sans text-[11px] font-bold text-outline uppercase tracking-[0.2em] mb-stack-md">
                Members / Entities ({ring.members.length})
              </h3>
              <div className="space-y-1.5 max-h-72 overflow-y-auto custom-scrollbar pr-1">
                {ring.members.map((m) => {
                  const color = entityColor(m);
                  return (
                    <button
                      key={m.id}
                      onClick={() => router.push(`/intelligence/entity/${m.id}`)}
                      className="w-full flex items-center justify-between gap-3 p-2.5 bg-white/5 hover:bg-white/[0.08] rounded-xl border border-transparent hover:border-white/10 transition-colors text-left group"
                    >
                      <span className="flex items-center gap-2.5 min-w-0">
                        <span className="w-2 h-2 rounded-full shrink-0 glow-dot" style={{ backgroundColor: color, color }} />
                        <span className="font-mono text-[12px] text-on-surface truncate group-hover:text-white transition-colors">{m.label}</span>
                      </span>
                      <span
                        className="text-[9px] font-bold px-2 py-0.5 rounded uppercase tracking-wider shrink-0"
                        style={{ color, backgroundColor: `${color}1a`, border: `1px solid ${color}33` }}
                      >
                        {m.type}
                      </span>
                    </button>
                  );
                })}
              </div>
            </motion.section>

            {/* Linked Complaints */}
            <motion.section variants={item} whileHover={hoverLift} className="glass-panel p-stack-lg">
              <h3 className="font-sans text-[11px] font-bold text-outline uppercase tracking-[0.2em] mb-stack-md">
                Linked Complaints ({ring.complaints.length})
              </h3>
              <div className="space-y-1.5 max-h-72 overflow-y-auto custom-scrollbar pr-1">
                {ring.complaints.length === 0 && (
                  <p className="font-sans text-on-surface-variant/60 text-[12px]">No correlated complaints.</p>
                )}
                {ring.complaints.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => router.push(`/investigations/${c.id}`)}
                    className="w-full flex items-center justify-between gap-3 p-2.5 bg-white/5 hover:bg-white/[0.08] rounded-xl border border-white/10 hover:border-secondary-container/30 transition-colors text-left"
                  >
                    <span className="min-w-0">
                      <span className="flex items-center gap-2">
                        <span className="font-heading text-[12px] text-secondary-container">{shortId(c.id)}</span>
                        {c.status && (
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${statusBadge(c.status)}`}>{c.status}</span>
                        )}
                      </span>
                      <span className="block text-[11px] text-on-surface-variant truncate mt-0.5">{c.scam_category || c.source_type}</span>
                      <span className="block text-[10px] text-on-surface-variant/60 tabular-nums mt-0.5">{formatDateTime(c.created_at || undefined)}</span>
                    </span>
                    {c.threat_score != null && (
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded shrink-0 ${severityBadge(c.severity_band || undefined)}`}>{c.threat_score}</span>
                    )}
                  </button>
                ))}
              </div>
            </motion.section>

            {/* Sticky actions */}
            <motion.div variants={item} className="sticky bottom-4 flex flex-col gap-stack-sm">
              <button
                onClick={generatePackage}
                disabled={busy !== null}
                className="btn-bloom flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl text-on-primary font-heading font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {busy === "package"
                  ? <Icon name="progress_activity" className="animate-spin text-[18px]" />
                  : <Icon name="description" className="text-[18px]" />}
                Export Intelligence Package
              </button>
              <button
                onClick={exportEvidence}
                disabled={busy !== null}
                className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 font-semibold text-sm text-on-surface hover:bg-white/10 hover:border-secondary-container/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {busy === "export"
                  ? <Icon name="progress_activity" className="animate-spin text-[18px]" />
                  : <Icon name="download" className="text-[18px]" />}
                Export Evidence Bundle
              </button>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function MetricTile({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="glass-panel p-stack-md flex items-center gap-3">
      <div className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
        <Icon name={icon} className="text-secondary-container text-[20px]" />
      </div>
      <div className="min-w-0">
        <p className="font-sans text-[9px] font-bold text-outline uppercase tracking-wider">{label}</p>
        <p className="font-heading text-xl font-bold text-on-surface mt-0.5 truncate">{value}</p>
      </div>
    </div>
  );
}
