"use client";

import { useEffect, useState, useCallback, Suspense, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { GraphView } from "@/components/GraphView";
import { api, ApiError } from "@/lib/api";
import type { GraphOverview, EntityProfile, EntitySearchResult, GraphNode, GraphEdge } from "@/lib/types";
import { severityBadge } from "@/lib/format";

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

function GraphHomeInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const focusId = searchParams.get("focus");

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
    <div className="p-stack-lg flex flex-col xl:flex-row gap-stack-lg xl:h-[calc(100vh-64px)] overflow-hidden">
      <div className="flex-1 flex flex-col gap-stack-lg min-h-[520px] overflow-hidden">
        <div className="flex items-center gap-stack-md">
          <div className="relative flex-1 max-w-md">
            <div className="flex items-center gap-2 bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2">
              <Icon name="search" className="text-outline text-[20px]" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => setShowResults(true)}
                placeholder="Search entities (phone, UPI, domain…)"
                className="bg-transparent outline-none flex-1 text-body-md text-on-surface placeholder:text-outline"
              />
            </div>
            {showResults && results.length > 0 && (
              <div className="absolute z-20 mt-1 w-full bg-surface-container-lowest border border-outline-variant/40 rounded-xl shadow-2xl overflow-hidden">
                {results.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => { setShowResults(false); setQuery(""); openPanel(r.id); }}
                    className="w-full flex items-center justify-between px-3 py-2 hover:bg-surface-container transition-colors text-left"
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
          <Link href="/intelligence/rings" className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-container hover:bg-surface-container-high border border-outline-variant/40 text-sm font-bold text-on-surface transition-colors">
            <Icon name="groups" className="text-error text-[20px]" /> View Fraud Rings
          </Link>
        </div>

        <div className="flex-1 graph-bg border border-outline-variant/30 rounded-2xl relative overflow-hidden shadow-2xl min-h-[420px]">
          {isEmpty ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-8">
              <Icon name="hub" className="text-outline text-[48px] mb-3" />
              <h3 className="font-headline-sm text-on-surface mb-1">The intelligence graph is still building</h3>
              <p className="text-body-md text-on-surface-variant max-w-md">
                As more reports come in, connections between entities will appear here.
              </p>
            </div>
          ) : (
            <>
              <div className="absolute top-stack-md left-stack-md z-10 bg-surface-container-lowest/60 backdrop-blur-md border border-outline-variant/30 rounded-xl px-3 py-2 flex items-center gap-4">
                <Stat label="Nodes" value={graph!.nodes.length} />
                <div className="h-6 w-px bg-outline-variant/30" />
                <Stat label="Clusters" value={graph!.cluster_count ?? 0} />
                <div className="h-6 w-px bg-outline-variant/30" />
                <Stat label="Edges" value={graph!.edges.length} />
              </div>
              <GraphView
                nodes={graph!.nodes}
                edges={graph!.edges}
                selectedId={selectedId}
                onSelect={openPanel}
              />
            </>
          )}
        </div>
      </div>

      {selectedId && (
        <aside className="w-full xl:w-[380px] card-obsidian p-stack-lg xl:overflow-y-auto custom-scrollbar relative">
          <button
            onClick={() => { setSelectedId(null); setPanelEntity(null); }}
            className="absolute top-3 right-3 text-outline hover:text-on-surface transition-colors"
            aria-label="Close"
          >
            <Icon name="close" />
          </button>
          {panelLoading ? (
            <PageLoader />
          ) : !panelEntity ? (
            <p className="text-body-md text-on-surface-variant text-center py-stack-lg">Entity not found.</p>
          ) : (
            <>
              <p className="text-[11px] font-bold text-outline uppercase tracking-[0.2em] mb-stack-md">Entity Preview</p>
              <div className="flex items-center gap-stack-md mb-stack-lg">
                <div className="w-14 h-14 bg-surface-container rounded-2xl flex items-center justify-center border border-outline-variant/30">
                  <Icon name={iconForType(panelEntity.type)} className="text-primary text-[28px]" />
                </div>
                <div className="min-w-0">
                  <p className="font-mono text-on-surface break-all leading-tight">{panelEntity.value}</p>
                  <p className="text-label-md text-on-surface-variant uppercase mt-1">{panelEntity.type}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 mb-stack-lg">
                <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase ${severityBadge(panelEntity.risk_tier)}`}>{panelEntity.risk_tier}</span>
                {panelEntity.in_ring && (
                  <span className="text-[10px] font-bold px-3 py-1 rounded-full uppercase bg-error/10 text-error border border-error/20">In fraud ring</span>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2 mb-stack-lg">
                <Metric label="Risk" value={Math.round(panelEntity.risk_score)} />
                <Metric label="Links" value={panelEntity.connection_count} />
                <Metric label="Complaints" value={panelEntity.complaint_count} />
              </div>
              <button
                onClick={() => router.push(`/intelligence/entity/${panelEntity.id}`)}
                className="w-full py-2.5 rounded-xl bg-primary text-on-primary font-bold text-sm hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
              >
                View Full Profile <Icon name="arrow_forward" className="text-[18px]" />
              </button>
            </>
          )}
        </aside>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-[9px] font-bold text-outline uppercase tracking-wider">{label}</p>
      <p className="text-lg font-bold text-on-surface leading-none">{value}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-2 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-xl text-center">
      <p className="text-[9px] font-bold text-outline uppercase">{label}</p>
      <p className="text-xl font-bold text-on-surface">{value}</p>
    </div>
  );
}

export default function GraphHomePage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <GraphHomeInner />
    </Suspense>
  );
}
