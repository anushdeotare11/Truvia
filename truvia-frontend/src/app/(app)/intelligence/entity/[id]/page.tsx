"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { GraphView } from "@/components/GraphView";
import { RiskGauge } from "@/components/RiskGauge";
import { api, ApiError } from "@/lib/api";
import type { EntityProfile, EntityRiskScore, GraphEdge, GraphNode, IntelligencePackageResult } from "@/lib/types";
import { severityBadge, formatDateTime, formatDate } from "@/lib/format";

type Tab = "overview" | "connections" | "complaints" | "risk";

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
  const [tab, setTab] = useState<Tab>("overview");

  // lazy-loaded per tab
  const [risk, setRisk] = useState<EntityRiskScore | null>(null);
  const [subgraph, setSubgraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [depth, setDepth] = useState(1);
  const [showNetwork, setShowNetwork] = useState(false);

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

  // lazy load risk history when tab opened
  useEffect(() => {
    if ((tab === "risk" || tab === "overview") && !risk) {
      api.get<EntityRiskScore>(`/graph/entity/${entityId}/risk-score`).then(setRisk).catch(() => {});
    }
  }, [tab, risk, entityId]);

  // lazy load subgraph for connections/network
  const loadSubgraph = useCallback(async (d: number) => {
    try {
      setSubgraph(await api.get(`/graph/entity/${entityId}/subgraph`, { params: { depth: String(d) } }));
    } catch { setSubgraph(null); }
  }, [entityId]);

  useEffect(() => {
    if ((tab === "connections" || showNetwork) && !subgraph) loadSubgraph(depth);
  }, [tab, showNetwork, subgraph, depth, loadSubgraph]);

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
      <div className="p-stack-lg">
        <div className="card-obsidian p-stack-lg border-l-4 border-l-error flex items-center justify-between">
          <p className="text-body-md text-on-surface-variant">{error || "Entity not found."}</p>
          <button onClick={load} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20">Retry</button>
        </div>
      </div>
    );
  }

  const neighbors = subgraph?.nodes.filter((n) => n.id !== entity.id) ?? [];

  return (
    <div className="p-stack-lg flex flex-col gap-stack-lg">
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium ${toast.kind === "ok" ? "bg-primary/10 text-primary border-primary/30" : "bg-error/10 text-error border-error/30"}`}>{toast.msg}</div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-stack-md">
        <div className="flex items-center gap-stack-md">
          <button onClick={goBack} className="text-outline hover:text-on-surface"><Icon name="arrow_back" /></button>
          <div className="w-14 h-14 bg-surface-container rounded-2xl flex items-center justify-center border border-outline-variant/30">
            <Icon name={iconForType(entity.type)} className="text-primary text-[28px]" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="font-headline-md text-on-surface font-mono break-all">{entity.value}</h1>
              <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase ${severityBadge(entity.risk_tier)}`}>{entity.risk_tier}</span>
            </div>
            <p className="text-body-md text-on-surface-variant uppercase">{entity.type}</p>
          </div>
        </div>
        <div className="flex items-center gap-stack-sm">
          <button onClick={() => setShowNetwork((s) => !s)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-container border border-outline-variant/40 font-bold text-sm text-on-surface hover:bg-surface-container-high">
            <Icon name="account_tree" className="text-[18px]" /> {showNetwork ? "Hide" : "View"} Risk Network
          </button>
          <button
            onClick={generatePackage}
            disabled={!entity.in_ring || busy}
            title={entity.in_ring ? "" : "Available only when the entity is part of a detected fraud ring"}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-on-primary font-bold text-sm hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed">
            {busy ? <Icon name="progress_activity" className="animate-spin text-[18px]" /> : <Icon name="description" className="text-[18px]" />}
            Generate Intelligence Package
          </button>
        </div>
      </div>

      {pkg && (
        <div className="card-obsidian p-stack-md flex items-center justify-between border-l-4 border-l-primary">
          <p className="text-body-md text-on-surface">Package <span className="font-mono">{pkg.case_number}</span> v{pkg.version} generated.</p>
          <button onClick={() => api.download(pkg.download_url, `intelligence_package_${pkg.id}.pdf`)} className="px-3 py-1.5 rounded-lg bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20">View Package (PDF)</button>
        </div>
      )}

      {/* Risk network (in-place canvas) */}
      {showNetwork && (
        <div className="graph-bg border border-outline-variant/30 rounded-2xl relative overflow-hidden shadow-2xl min-h-[380px]">
          <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
            <span className="text-[10px] font-bold text-outline uppercase tracking-widest mr-1">Depth</span>
            {[1, 2, 3].map((d) => (
              <button key={d} onClick={() => changeDepth(d)}
                className={`w-7 h-7 rounded-lg text-xs font-bold transition-colors ${depth === d ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant hover:text-on-surface"}`}>{d}</button>
            ))}
          </div>
          {subgraph ? (
            <GraphView nodes={subgraph.nodes} edges={subgraph.edges} selectedId={entity.id} onSelect={(id) => id !== entity.id && router.push(`/intelligence/entity/${id}`)} />
          ) : <PageLoader />}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-outline-variant/30">
        {(["overview", "connections", "complaints", "risk"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-bold capitalize border-b-2 -mb-px transition-colors ${tab === t ? "border-primary text-primary" : "border-transparent text-on-surface-variant hover:text-on-surface"}`}>
            {t === "risk" ? "Risk History" : t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <div className="flex flex-col md:flex-row gap-stack-lg">
          <div className="card-obsidian p-stack-lg flex flex-col items-center justify-center md:w-64">
            <RiskGauge value={entity.risk_score} severity={entity.risk_tier} />
            <p className="text-[10px] font-bold text-outline uppercase tracking-widest mt-2">Aggregate Risk</p>
          </div>
          <div className="card-obsidian p-stack-lg flex-1">
            <h3 className="text-[11px] font-bold text-outline uppercase tracking-[0.2em] mb-stack-md">Contributing Factors</h3>
            {!risk ? <PageLoader /> : risk.factors.length === 0 ? (
              <p className="text-body-md text-on-surface-variant">No contributing factors computed yet.</p>
            ) : (
              <div className="space-y-stack-sm">
                {risk.factors.map((f, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-xl">
                    <Icon name="bolt" className="text-primary text-[20px] mt-0.5" />
                    <div>
                      <p className="text-body-md font-bold text-on-surface">{f.factor}</p>
                      <p className="text-[12px] text-on-surface-variant">{f.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="grid grid-cols-4 gap-2 mt-stack-lg">
              <Cell label="Occurrences" value={String(entity.occurrence_count)} />
              <Cell label="Connections" value={String(entity.connection_count)} />
              <Cell label="Complaints" value={String(entity.complaint_count)} />
              <Cell label="In Ring" value={entity.in_ring ? "Yes" : "No"} />
            </div>
          </div>
        </div>
      )}

      {tab === "connections" && (
        <div className="card-obsidian p-stack-lg">
          <div className="flex items-center gap-2 mb-stack-md">
            <span className="text-[10px] font-bold text-outline uppercase tracking-widest">Depth</span>
            {[1, 2, 3].map((d) => (
              <button key={d} onClick={() => changeDepth(d)}
                className={`w-7 h-7 rounded-lg text-xs font-bold ${depth === d ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant"}`}>{d}</button>
            ))}
          </div>
          {!subgraph ? <PageLoader /> : neighbors.length === 0 ? (
            <p className="text-body-md text-on-surface-variant">No connections detected for this entity yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {neighbors.map((n) => (
                <button key={n.id} onClick={() => router.push(`/intelligence/entity/${n.id}`)}
                  className="flex items-center justify-between p-3 bg-surface-container/30 hover:bg-surface-container rounded-xl border border-transparent hover:border-outline-variant/30 transition-colors">
                  <span className="flex items-center gap-2 min-w-0">
                    <Icon name={iconForType(n.type)} className="text-primary text-[18px]" />
                    <span className="font-mono text-[12px] text-on-surface truncate">{n.label}</span>
                  </span>
                  <span className="text-[10px] text-outline uppercase">{n.type}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "complaints" && (
        <div className="card-obsidian p-stack-lg">
          {entity.complaints.length === 0 ? (
            <p className="text-body-md text-on-surface-variant">This entity has not appeared in any other complaints.</p>
          ) : (
            <div className="space-y-1.5">
              {entity.complaints.map((c) => (
                <button key={c.id} onClick={() => router.push(`/investigations/${c.id}`)}
                  className="w-full flex items-center justify-between p-3 bg-surface-container-lowest/50 hover:bg-surface-container rounded-xl border border-outline-variant/30 transition-colors text-left">
                  <span className="min-w-0">
                    <span className="block text-body-md text-on-surface truncate">{c.scam_category || c.source_type}</span>
                    <span className="block text-[10px] text-on-surface-variant">{formatDateTime(c.created_at || undefined)}</span>
                  </span>
                  {c.threat_score != null && (
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${severityBadge(c.severity_band || undefined)}`}>{c.threat_score}</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "risk" && (
        <div className="card-obsidian p-stack-lg">
          {!risk ? <PageLoader /> : risk.history.length === 0 ? (
            <p className="text-body-md text-on-surface-variant">No risk history recorded for this entity yet.</p>
          ) : (
            <div className="space-y-1.5">
              {risk.history.map((h, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-xl">
                  <span className="text-body-md text-on-surface">{h.category || "—"}</span>
                  <span className="flex items-center gap-3">
                    <span className="text-[11px] text-on-surface-variant">{formatDate(h.date || undefined)}</span>
                    <span className="text-sm font-bold text-primary">{h.score}</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-2 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-xl text-center">
      <p className="text-[9px] font-bold text-outline uppercase">{label}</p>
      <p className="text-lg font-bold text-on-surface">{value}</p>
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
