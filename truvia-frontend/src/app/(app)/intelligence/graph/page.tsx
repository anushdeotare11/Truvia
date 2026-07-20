"use client";

import { useEffect, useState, useCallback, Suspense, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { GraphView } from "@/components/GraphView";
import { api, ApiError } from "@/lib/api";
import type { GraphOverview, EntityProfile, EntitySearchResult, GraphNode, GraphEdge } from "@/lib/types";
import { severityBadge, severityText, formatDateTime } from "@/lib/format";

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

// Semantic dot color for the intelligence timeline (matches the graph node legend).
function timelineDot(sev?: string | null) {
  switch ((sev || "").toLowerCase()) {
    case "critical":
    case "high":
      return "bg-error";
    case "moderate":
      return "bg-tertiary";
    default:
      return "bg-secondary-container";
  }
}

function GraphHomeInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const focusId = searchParams.get("focus");
  const reduce = useReducedMotion();
  const off = (v: number) => (reduce ? 0 : v);

  const [graph, setGraph] = useState<GraphOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(focusId);
  const [panelEntity, setPanelEntity] = useState<EntityProfile | null>(null);
  const [panelLoading, setPanelLoading] = useState(false);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<EntitySearchResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const g = await api.get<GraphOverview>("/graph/overview", { params: { top_n_clusters: "8" } });
      setGraph(g);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load the intelligence graph.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openPanel = useCallback(async (id: string) => {
    setSelectedId(id);
    setPanelLoading(true);
    try {
      const e = await api.get<EntityProfile>(`/graph/entity/${id}`);
      setPanelEntity(e);
    } catch {
      setPanelEntity(null);
    } finally {
      setPanelLoading(false);
    }
  }, []);

  useEffect(() => {
    if (focusId) openPanel(focusId);
  }, [focusId, openPanel]);

  // If the focused entity isn't part of the cluster overview, pull its local
  // subgraph and merge it in so the node genuinely exists on the canvas and can
  // be centered/highlighted (App Flow §9 "auto-centers/highlights").
  useEffect(() => {
    if (!focusId || !graph) return;
    if (graph.nodes.some((n) => n.id === focusId)) return;
    let cancelled = false;
    api
      .get<{ nodes: GraphNode[]; edges: GraphEdge[] }>(`/graph/entity/${focusId}/subgraph`, { params: { depth: "1" } })
      .then((sg) => {
        if (cancelled || !sg?.nodes?.length) return;
        setGraph((prev) => {
          if (!prev) return prev;
          const nodeIds = new Set(prev.nodes.map((n) => n.id));
          const mergedNodes = [...prev.nodes];
          for (const n of sg.nodes) if (!nodeIds.has(n.id)) mergedNodes.push(n);
          const key = (e: GraphEdge) => `${e.source}->${e.target}`;
          const edgeKeys = new Set(prev.edges.map(key));
          const mergedEdges = [...prev.edges];
          for (const e of sg.edges) if (!edgeKeys.has(key(e))) mergedEdges.push(e);
          return { ...prev, nodes: mergedNodes, edges: mergedEdges };
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [focusId, graph]);

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (query.trim().length < 1) { setResults([]); return; }
    searchTimer.current = setTimeout(async () => {
      try {
        const r = await api.get<EntitySearchResult[]>("/graph/search", { params: { q: query.trim() } });
        setResults(r);
        setShowResults(true);
      } catch { setResults([]); }
    }, 250);
  }, [query]);

  const closePanel = useCallback(() => { setSelectedId(null); setPanelEntity(null); }, []);

  if (loading) return <PageLoader />;

  if (error) {
    return (
      <div className="p-stack-lg">
        <div className="card-obsidian p-stack-lg border-l-4 border-l-error flex items-center justify-between">
          <div className="flex items-center gap-stack-md">
            <Icon name="error" className="text-error text-[28px]" />
            <div>
              <h3 className="font-headline-sm text-on-surface">Couldn&apos;t load graph</h3>
              <p className="text-body-md text-on-surface-variant">{error}</p>
            </div>
          </div>
          <button onClick={load} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const isEmpty = !graph || graph.nodes.length === 0;

  return (
    <div className="relative w-full h-[calc(100vh-64px)] min-h-[560px] overflow-hidden bg-background">
      {/* ── Full-bleed graph canvas on the void ── */}
      <div className="absolute inset-0 graph-bg">
        {isEmpty ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-8">
            <Icon name="hub" className="text-outline text-[52px] mb-4" />
            <h3 className="font-heading text-headline-sm text-on-surface mb-1">The intelligence graph is still building</h3>
            <p className="text-body-md text-on-surface-variant max-w-md">
              As more reports come in, connections between entities will appear here.
            </p>
          </div>
        ) : (
          <GraphView
            nodes={graph!.nodes}
            edges={graph!.edges}
            selectedId={selectedId}
            onSelect={openPanel}
          />
        )}
      </div>

      {/* ── Floating stats pill (top-center) ── */}
      {!isEmpty && (
        <motion.div
          initial={{ opacity: 0, y: off(-16) }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className={`absolute top-6 left-6 right-6 z-30 flex justify-center pointer-events-none transition-[padding] duration-300 ${selectedId ? "xl:pr-[430px]" : ""}`}
        >
          <div className="glass-panel !rounded-full px-8 py-3 flex items-center gap-8 pointer-events-auto shadow-2xl">
            <Stat label="Nodes" value={graph!.nodes.length} tone="text-primary" />
            <span className="h-8 w-px bg-white/10" />
            <Stat label="Clusters" value={graph!.cluster_count ?? 0} tone="text-tertiary" />
            <span className="h-8 w-px bg-white/10" />
            <Stat label="Edges" value={graph!.edges.length} tone="text-secondary-container" />
          </div>
        </motion.div>
      )}

      {/* ── Floating Controls panel (top-left) ── */}
      <motion.div
        initial={{ opacity: 0, x: off(-24) }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        className="absolute top-6 left-6 z-30 obsidian-panel rounded-2xl p-4 w-[300px] max-w-[calc(100%-3rem)]"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-label-md font-heading font-bold text-on-surface uppercase tracking-[0.2em]">Controls</h2>
          <Icon name="insights" className="text-primary text-[20px]" />
        </div>

        {/* Entity search */}
        <div className="relative">
          <div className="flex items-center gap-2 bg-surface-container-lowest/70 border border-white/10 rounded-xl px-3 py-2 focus-within:border-secondary-container/50 transition-colors">
            <Icon name="search" className="text-outline text-[20px]" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setShowResults(true)}
              placeholder="Search entities…"
              className="bg-transparent outline-none flex-1 min-w-0 text-body-md text-on-surface placeholder:text-outline"
            />
          </div>
          {showResults && results.length > 0 && (
            <div className="absolute z-20 mt-1 w-full bg-surface-container-lowest border border-white/10 rounded-xl shadow-2xl overflow-hidden custom-scrollbar max-h-64 overflow-y-auto">
              {results.map((r) => (
                <button
                  key={r.id}
                  onClick={() => { setShowResults(false); setQuery(""); openPanel(r.id); }}
                  className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/5 transition-colors text-left"
                >
                  <span className="flex items-center gap-2 min-w-0">
                    <Icon name={iconForType(r.type)} className="text-primary text-[18px]" />
                    <span className="font-mono text-[12px] text-on-surface truncate">{r.value}</span>
                  </span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${severityBadge(r.risk_tier)}`}>{r.risk_tier}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* View Fraud Rings */}
        <Link
          href="/intelligence/rings"
          className="mt-3 flex items-center gap-2 px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-sm font-bold text-on-surface transition-colors"
        >
          <Icon name="groups" className="text-error text-[20px]" /> View Fraud Rings
        </Link>

        {/* Legend */}
        <div className="pt-4 mt-4 border-t border-white/10">
          <p className="text-label-sm font-bold text-outline uppercase tracking-[0.15em] mb-3">Legend</p>
          <div className="grid grid-cols-2 gap-y-2.5 gap-x-3">
            <LegendDot color="bg-error" label="High-risk" />
            <LegendDot color="bg-tertiary" label="Hub / cluster" />
            <LegendDot color="bg-secondary-container" label="Individual" />
            <LegendDot color="bg-primary" label="Phone" />
          </div>
        </div>
      </motion.div>

      {/* ── Zoom / view controls (bottom-left) ── */}
      {!isEmpty && (
        <motion.div
          initial={{ opacity: 0, y: off(16) }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
          className="absolute bottom-8 left-6 z-30 flex flex-col gap-2"
        >
          <button
            onClick={closePanel}
            title="Reset view"
            aria-label="Reset view"
            className="w-10 h-10 obsidian-panel !rounded-xl flex items-center justify-center text-on-surface hover:text-secondary-container transition-colors"
          >
            <Icon name="center_focus_strong" className="text-[20px]" />
          </button>
          <button
            onClick={load}
            title="Refresh graph"
            aria-label="Refresh graph"
            className="w-10 h-10 obsidian-panel !rounded-xl flex items-center justify-center text-on-surface hover:text-secondary-container transition-colors"
          >
            <Icon name="refresh" className="text-[20px]" />
          </button>
        </motion.div>
      )}

      {/* ── Right detail panel ── */}
      <AnimatePresence>
        {selectedId && (
          <motion.aside
            key="detail-panel"
            initial={{ opacity: 0, x: off(48) }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: off(48) }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="absolute top-6 right-6 bottom-6 z-40 w-[calc(100%-3rem)] sm:w-[400px] obsidian-panel electric-edge rounded-[2rem] flex flex-col overflow-hidden shadow-2xl"
          >
            {panelLoading ? (
              <div className="flex-1 flex items-center justify-center"><PageLoader /></div>
            ) : !panelEntity ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
                <Icon name="search_off" className="text-outline text-[40px] mb-3" />
                <p className="text-body-md text-on-surface-variant">Entity not found.</p>
                <button onClick={closePanel} className="mt-4 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm font-bold text-on-surface hover:bg-white/10 transition-colors">Close</button>
              </div>
            ) : (
              <>
                {/* Header */}
                <div className="p-6 border-b border-white/10 bg-white/[0.02]">
                  <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold px-3 py-1 rounded-md uppercase tracking-widest ${severityBadge(panelEntity.risk_tier)}`}>
                        {panelEntity.risk_tier}
                      </span>
                      {panelEntity.in_ring && (
                        <span className="text-[10px] font-bold px-3 py-1 rounded-md uppercase tracking-widest bg-error/15 text-error border border-error/20 pulse">
                          In fraud ring
                        </span>
                      )}
                    </div>
                    <button
                      onClick={closePanel}
                      className="text-outline hover:text-on-surface transition-colors"
                      aria-label="Close"
                    >
                      <Icon name="close" />
                    </button>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 shrink-0 bg-white/5 rounded-2xl flex items-center justify-center border border-white/10">
                      <Icon name={iconForType(panelEntity.type)} className="text-primary text-[26px]" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-heading text-headline-sm font-bold text-on-surface break-all leading-tight">{panelEntity.value}</h3>
                      <p className="text-label-sm text-on-surface-variant uppercase tracking-widest mt-0.5">{panelEntity.type}</p>
                    </div>
                  </div>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-8">
                  {/* Metric cards */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-white/5 rounded-xl border border-white/5 p-4">
                      <p className="text-label-sm font-bold text-on-surface-variant uppercase tracking-widest mb-1.5">Connections</p>
                      <p className="text-[28px] font-heading font-bold text-primary leading-none">{panelEntity.connection_count}</p>
                    </div>
                    <div className="bg-white/5 rounded-xl border border-white/5 p-4">
                      <p className="text-label-sm font-bold text-on-surface-variant uppercase tracking-widest mb-1.5">Risk Score</p>
                      <div className="flex items-baseline gap-1">
                        <p className={`text-[28px] font-heading font-bold leading-none ${severityText(panelEntity.risk_tier)}`}>{Math.round(panelEntity.risk_score)}</p>
                        <span className="text-label-sm text-on-surface-variant">/100</span>
                      </div>
                    </div>
                  </div>

                  {/* Intelligence Timeline / linked reports */}
                  <div>
                    <h4 className="flex items-center gap-2 text-label-md font-bold text-on-surface uppercase tracking-widest mb-5">
                      Intelligence Timeline
                      <span className="h-px flex-1 bg-white/10" />
                    </h4>
                    {panelEntity.complaints.length === 0 ? (
                      <p className="text-body-sm text-on-surface-variant">No correlated complaints recorded for this entity yet.</p>
                    ) : (
                      <div className="space-y-0">
                        {panelEntity.complaints.slice(0, 6).map((c, i, arr) => (
                          <button
                            key={c.id}
                            onClick={() => router.push(`/investigations/${c.id}`)}
                            className="w-full flex gap-4 text-left group"
                          >
                            <div className="flex flex-col items-center">
                              <span className={`w-3 h-3 rounded-full ${timelineDot(c.severity_band)} ring-4 ring-white/5`} />
                              {i < Math.min(arr.length, 6) - 1 && <span className="w-px flex-1 bg-white/10 my-1.5" />}
                            </div>
                            <div className="pb-5 min-w-0">
                              <p className="text-body-sm font-medium text-on-surface truncate group-hover:text-primary transition-colors">
                                {c.scam_category || c.source_type}
                              </p>
                              <p className="text-label-sm text-on-surface-variant">
                                {formatDateTime(c.created_at || undefined)}
                                {c.status ? ` • ${c.status}` : ""}
                              </p>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Linked Identifiers */}
                  <div>
                    <h4 className="flex items-center gap-2 text-label-md font-bold text-on-surface uppercase tracking-widest mb-4">
                      Linked Identifiers
                      <span className="h-px flex-1 bg-white/10" />
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      <IdentifierChip label={`TYPE: ${panelEntity.type}`} />
                      <IdentifierChip label={`SEEN: ${panelEntity.occurrence_count}×`} />
                      <IdentifierChip label={`LINKS: ${panelEntity.connection_count}`} />
                      {panelEntity.in_ring && <IdentifierChip label="FRAUD RING" />}
                    </div>
                  </div>
                </div>

                {/* Sticky footer action (existing navigation preserved) */}
                <div className="p-6 bg-surface-container-low/80 backdrop-blur-md border-t border-white/10">
                  <button
                    onClick={() => router.push(`/intelligence/entity/${panelEntity.id}`)}
                    className="btn-bloom w-full py-3.5 rounded-2xl text-on-primary-container font-bold text-sm flex items-center justify-center gap-2"
                  >
                    <Icon name="description" className="text-[18px]" />
                    View Full Profile
                  </button>
                </div>
              </>
            )}
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  );
}

function Stat({ label, value, tone = "text-on-surface" }: { label: string; value: number; tone?: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-label-sm font-bold text-on-surface-variant uppercase tracking-wider">{label}</span>
      <span className={`text-headline-sm font-heading font-bold leading-none ${tone}`}>{value.toLocaleString()}</span>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-2">
      <span className={`w-2.5 h-2.5 rounded-full ${color} glow-dot`} />
      <span className="text-body-sm text-on-surface-variant">{label}</span>
    </span>
  );
}

function IdentifierChip({ label }: { label: string }) {
  return (
    <span className="px-3 py-1.5 bg-white/5 rounded-lg text-label-sm font-medium text-on-surface border border-white/5 hover:bg-white/10 transition-colors cursor-default max-w-full truncate">
      {label}
    </span>
  );
}

export default function GraphHomePage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <GraphHomeInner />
    </Suspense>
  );
}
