"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { GraphView } from "@/components/GraphView";
import { RiskGauge } from "@/components/RiskGauge";
import { api, ApiError } from "@/lib/api";
import type { EntityProfile, EntityRiskScore, GraphEdge, GraphNode, IntelligencePackageResult } from "@/lib/types";
import { severityBadge, statusBadge, formatDateTime, formatDate, shortId } from "@/lib/format";

// Node palette mirrors GraphView so connection chips read as the same entities.
const TYPE_COLOR: Record<string, string> = {
  phone: "#b5c4ff",
  upi: "#ffb787",
  domain: "#658aff",
  email: "#8d90a0",
  ip: "#00f4fe",
  device: "#00dce5",
};

function colorForNode(type?: string, risk?: number): string {
  if ((risk ?? 0) >= 80) return "#ffb4ab";
  return (type && TYPE_COLOR[type]) || "#b5c4ff";
}

function iconForType(type?: string) {
  if (type === "phone") return "smartphone";
  if (type === "upi") return "account_balance_wallet";
  if (type === "email") return "mail";
  if (type === "domain") return "language";
  if (type === "ip") return "dns";
  if (type === "device") return "fingerprint";
  if (type === "org") return "corporate_fare";
  return "hub";
}

function EntityExplorerInner() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const entityId = String(params.id);
  const reduce = useReducedMotion();

  // When arriving from an Officer Investigation View, the back button must return
  // to that specific complaint (App Flow §9), not a generic list. Otherwise fall
  // back to browser history.
  const from = searchParams.get("from");
  const goBack = useCallback(() => {
    if (from) router.push(from);
    else router.back();
  }, [from, router]);

  const [entity, setEntity] = useState<EntityProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [risk, setRisk] = useState<EntityRiskScore | null>(null);
  const [subgraph, setSubgraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [depth, setDepth] = useState(1);

  const [busy, setBusy] = useState(false);
  const [pkg, setPkg] = useState<IntelligencePackageResult | null>(null);
  const [toast, setToast] = useState<{ msg: string; kind: "ok" | "err" } | null>(null);

  const notify = (msg: string, kind: "ok" | "err") => { setToast({ msg, kind }); setTimeout(() => setToast(null), 4000); };

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      setEntity(await api.get<EntityProfile>(`/graph/entity/${entityId}`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load entity.");
    } finally { setLoading(false); }
  }, [entityId]);

  useEffect(() => { load(); }, [load]);

  // Risk factors + history power both the gauge context and the sparkline list.
  useEffect(() => {
    if (!risk) {
      api.get<EntityRiskScore>(`/graph/entity/${entityId}/risk-score`).then(setRisk).catch(() => {});
    }
  }, [risk, entityId]);

  // Subgraph feeds both the risk-network canvas and the connection chips.
  const loadSubgraph = useCallback(async (d: number) => {
    try {
      setSubgraph(await api.get(`/graph/entity/${entityId}/subgraph`, { params: { depth: String(d) } }));
    } catch { setSubgraph(null); }
  }, [entityId]);

  useEffect(() => { loadSubgraph(1); }, [loadSubgraph]);

  const changeDepth = (d: number) => { setDepth(d); loadSubgraph(d); };

  const generatePackage = async () => {
    setBusy(true);
    try {
      const res = await api.post<IntelligencePackageResult>("/graph/intelligence-package", { entity_id: entityId });
      setPkg(res);
      notify(`Intelligence Package generated (v${res.version})`, "ok");
    } catch (e) {
      notify(e instanceof ApiError ? e.message : "Package generation failed", "err");
    } finally { setBusy(false); }
  };

  if (loading) return <PageLoader />;
  if (error || !entity) {
    return (
      <div className="p-margin-page">
        <div className="obsidian-panel p-stack-lg border-l-4 border-l-error flex items-center justify-between">
          <p className="text-body-md text-on-surface-variant">{error || "Entity not found."}</p>
          <button onClick={load} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20">Retry</button>
        </div>
      </div>
    );
  }

  const neighbors = subgraph?.nodes.filter((n) => n.id !== entity.id) ?? [];

  const container: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.07, delayChildren: reduce ? 0 : 0.04 } },
  };
  const card: Variants = reduce
    ? { hidden: { opacity: 1 }, show: { opacity: 1 } }
    : {
        hidden: { opacity: 0, y: 18 },
        show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] } },
      };
  const lift = reduce ? "" : "hover:-translate-y-0.5";

  return (
    <div className="min-h-screen p-margin-page bg-background">
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium ${toast.kind === "ok" ? "bg-primary/10 text-primary border-primary/30" : "bg-error/10 text-error border-error/30"}`}>{toast.msg}</div>
      )}

      <motion.div variants={container} initial="hidden" animate="show" className="flex flex-col gap-stack-lg max-w-container-max mx-auto">
        {/* Header — breadcrumb + entity identity */}
        <motion.header variants={card} className="flex items-start justify-between flex-wrap gap-stack-md">
          <div className="flex items-start gap-stack-md min-w-0">
            <button onClick={goBack} aria-label="Go back"
              className="mt-1 w-9 h-9 shrink-0 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-outline hover:text-on-surface hover:bg-white/10 transition-colors">
              <Icon name="arrow_back" className="text-[20px]" />
            </button>
            <div className="min-w-0">
              <nav className="flex items-center gap-2 text-label-sm font-heading uppercase tracking-[0.18em] text-outline mb-2">
                <span>Intelligence</span>
                <Icon name="chevron_right" className="text-[14px]" />
                <span className="text-secondary-container">Entity</span>
              </nav>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="font-heading text-headline-lg text-on-surface font-mono break-all">{entity.value}</h1>
                <span className="text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider bg-white/5 text-on-surface-variant border border-white/10">
                  {entity.type}
                </span>
                <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider ${severityBadge(entity.risk_tier)}`}>
                  {entity.risk_tier}
                </span>
                {entity.in_ring && (
                  <span className="text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider bg-error/10 text-error border border-error/20">
                    In fraud ring
                  </span>
                )}
              </div>
            </div>
          </div>
        </motion.header>

        {pkg && (
          <motion.div variants={card} className="obsidian-panel p-stack-md flex items-center justify-between border-l-4 border-l-primary">
            <p className="text-body-md text-on-surface">Package <span className="font-mono text-secondary-container">{pkg.case_number}</span> v{pkg.version} generated.</p>
            <button onClick={() => api.download(pkg.download_url, `intelligence_package_${pkg.id}.pdf`)}
              className="px-3 py-1.5 rounded-lg bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20">View Package (PDF)</button>
          </motion.div>
        )}

        {/* Main split — risk network canvas + intelligence column */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-stack-lg">
          {/* Risk network subgraph */}
          <motion.section variants={card} className="glass-panel xl:col-span-2 relative overflow-hidden min-h-[520px] flex flex-col">
            <div className="flex items-center justify-between px-5 pt-5">
              <h2 className="text-label-sm font-heading font-bold uppercase tracking-[0.2em] text-on-surface flex items-center gap-2">
                <Icon name="account_tree" className="text-secondary-container text-[18px]" /> Risk Network
              </h2>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-outline uppercase tracking-widest mr-1">Depth</span>
                {[1, 2, 3].map((d) => (
                  <button key={d} onClick={() => changeDepth(d)}
                    className={`w-7 h-7 rounded-lg text-xs font-bold transition-colors ${depth === d ? "bg-primary text-on-primary" : "bg-white/5 text-on-surface-variant hover:text-on-surface"}`}>{d}</button>
                ))}
              </div>
            </div>
            <div className="graph-bg mt-4 flex-1 rounded-b-[24px] relative overflow-hidden border-t border-white/5">
              {subgraph ? (
                <GraphView nodes={subgraph.nodes} edges={subgraph.edges} selectedId={entity.id}
                  onSelect={(id) => id !== entity.id && router.push(`/intelligence/entity/${id}`)} />
              ) : <PageLoader />}
            </div>
          </motion.section>

          {/* Intelligence column */}
          <div className="flex flex-col gap-stack-md xl:col-span-1">
            {/* Metrics */}
            <motion.section variants={card} className="obsidian-panel p-stack-lg">
              <div className="flex items-center gap-stack-md">
                <RiskGauge value={entity.risk_score} severity={entity.risk_tier} size={112} />
                <div className="grid grid-cols-1 gap-2 flex-1">
                  <Tile label="Connections" value={String(entity.connection_count)} />
                  <Tile label="Occurrences" value={String(entity.occurrence_count)} />
                  <Tile label="Complaints" value={String(entity.complaint_count)} />
                </div>
              </div>
            </motion.section>

            {/* Contributing factors */}
            <motion.section variants={card} className="glass-panel p-stack-lg">
              <SectionTitle icon="bolt">Contributing Factors</SectionTitle>
              {!risk ? <PageLoader /> : risk.factors.length === 0 ? (
                <p className="text-body-md text-on-surface-variant">No contributing factors computed yet.</p>
              ) : (
                <div className="space-y-2">
                  {risk.factors.map((f, i) => (
                    <div key={i} className={`flex items-start gap-3 p-3 bg-white/5 border border-white/5 rounded-xl transition-transform ${lift}`}>
                      <Icon name="bolt" className="text-secondary-container text-[20px] mt-0.5" />
                      <div className="min-w-0">
                        <p className="text-body-md font-bold text-on-surface">{f.factor}</p>
                        <p className="text-[12px] text-on-surface-variant">{f.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.section>

            {/* Linked reports / complaints */}
            <motion.section variants={card} className="glass-panel p-stack-lg">
              <SectionTitle icon="folder_shared">Linked Reports / Complaints</SectionTitle>
              {entity.complaints.length === 0 ? (
                <p className="text-body-md text-on-surface-variant">This entity has not appeared in any other complaints.</p>
              ) : (
                <div className="space-y-1.5 max-h-72 overflow-y-auto custom-scrollbar pr-1">
                  {entity.complaints.map((c) => (
                    <button key={c.id} onClick={() => router.push(`/investigations/${c.id}`)}
                      className={`w-full flex items-center justify-between gap-3 p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 transition-all ${lift} text-left`}>
                      <span className="min-w-0">
                        <span className="flex items-center gap-2">
                          <span className="font-heading text-[12px] font-bold text-secondary-container tracking-wider">{shortId(c.id)}</span>
                          {c.status && (
                            <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${statusBadge(c.status)}`}>{c.status}</span>
                          )}
                        </span>
                        <span className="block text-body-md text-on-surface truncate mt-0.5">{c.scam_category || c.source_type}</span>
                        <span className="block text-[10px] text-on-surface-variant tabular-nums">{formatDateTime(c.created_at || undefined)}</span>
                      </span>
                      {c.threat_score != null && (
                        <span className={`shrink-0 text-[10px] font-bold px-2 py-0.5 rounded ${severityBadge(c.severity_band || undefined)}`}>{c.threat_score}</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </motion.section>

            {/* Linked identifiers / connections */}
            <motion.section variants={card} className="glass-panel p-stack-lg">
              <SectionTitle icon="lan">Linked Identifiers</SectionTitle>
              {!subgraph ? <PageLoader /> : neighbors.length === 0 ? (
                <p className="text-body-md text-on-surface-variant">No connections detected for this entity yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {neighbors.map((n) => {
                    const color = colorForNode(n.type, n.risk_score);
                    return (
                      <button key={n.id} onClick={() => router.push(`/intelligence/entity/${n.id}`)}
                        style={{ borderColor: `${color}55`, color }}
                        className={`flex items-center gap-2 max-w-full px-3 py-2 bg-white/5 hover:bg-white/10 rounded-lg border transition-all ${lift}`}>
                        <Icon name={iconForType(n.type)} className="text-[16px]" style={{ color }} />
                        <span className="font-mono text-[11px] text-on-surface truncate">{n.label}</span>
                        <span className="text-[9px] uppercase tracking-wider opacity-70">{n.type}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </motion.section>

            {/* Risk history */}
            <motion.section variants={card} className="glass-panel p-stack-lg">
              <SectionTitle icon="timeline">Risk History</SectionTitle>
              {!risk ? <PageLoader /> : risk.history.length === 0 ? (
                <p className="text-body-md text-on-surface-variant">No risk history recorded for this entity yet.</p>
              ) : (
                <div className="space-y-1.5 max-h-64 overflow-y-auto custom-scrollbar pr-1">
                  {risk.history.map((h, i) => (
                    <div key={i} className="flex items-center justify-between gap-3 p-3 bg-white/5 border border-white/5 rounded-xl">
                      <span className="text-body-md text-on-surface truncate">{h.category || "—"}</span>
                      <span className="flex items-center gap-3 shrink-0">
                        <span className="text-[11px] text-on-surface-variant tabular-nums">{formatDate(h.date || undefined)}</span>
                        <span className="text-sm font-bold text-secondary-container">{h.score}</span>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </motion.section>

            {/* Sticky export action */}
            <motion.div variants={card} className="xl:sticky xl:bottom-4 z-10">
              <button
                onClick={generatePackage}
                disabled={!entity.in_ring || busy}
                title={entity.in_ring ? "" : "Available only when the entity is part of a detected fraud ring"}
                className="btn-bloom w-full flex items-center justify-center gap-2 px-4 py-4 rounded-2xl text-on-primary-container font-heading font-bold text-sm disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0">
                {busy ? <Icon name="progress_activity" className="animate-spin text-[18px]" /> : <Icon name="description" className="text-[18px]" />}
                Export Intelligence Package
              </button>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function SectionTitle({ icon, children }: { icon: string; children: React.ReactNode }) {
  return (
    <h3 className="flex items-center gap-2 text-[11px] font-heading font-bold text-on-surface uppercase tracking-[0.2em] mb-stack-md">
      <Icon name={icon} className="text-secondary-container text-[16px]" />
      {children}
      <span className="h-px flex-1 bg-white/10" />
    </h3>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between px-3 py-2.5 bg-white/5 rounded-xl border border-white/5">
      <span className="text-[10px] font-bold text-outline uppercase tracking-widest">{label}</span>
      <span className="text-lg font-heading font-bold text-on-surface tabular-nums">{value}</span>
    </div>
  );
}

export default function EntityExplorerPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <EntityExplorerInner />
    </Suspense>
  );
}
