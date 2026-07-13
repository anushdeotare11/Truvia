"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { GraphView } from "@/components/GraphView";
import { api } from "@/lib/api";
import type { GraphOverview, EntityDetails } from "@/lib/types";
import { severityBadge, formatDateTime } from "@/lib/format";

function ThreatIntelInner() {
  const searchParams = useSearchParams();
  const initialEntity = searchParams.get("entity");

  const [graph, setGraph] = useState<GraphOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(initialEntity);
  const [entity, setEntity] = useState<EntityDetails | null>(null);
  const [entityLoading, setEntityLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const g = await api.get<GraphOverview>("/graph/overview");
        setGraph(g);
        if (!selectedId && g.nodes.length > 0) {
          const top = [...g.nodes].sort((a, b) => b.risk_score - a.risk_score)[0];
          setSelectedId(top.id);
        }
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadEntity = useCallback(async (id: string) => {
    setEntityLoading(true);
    try {
      const e = await api.get<EntityDetails>(`/entities/${id}`);
      setEntity(e);
    } catch {
      setEntity(null);
    } finally {
      setEntityLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedId) loadEntity(selectedId);
  }, [selectedId, loadEntity]);

  if (loading) return <PageLoader />;

  const ringCount = graph ? new Set(graph.nodes.map((n) => n.group)).size : 0;

  return (
    <div className="p-stack-lg flex flex-col xl:flex-row gap-stack-lg xl:h-[calc(100vh-64px)] overflow-hidden">
      {/* Left: graph */}
      <div className="flex-1 flex flex-col gap-stack-lg min-h-[520px] overflow-hidden">
        <div className="flex-1 graph-bg border border-outline-variant/30 rounded-2xl relative overflow-hidden shadow-2xl min-h-[420px]">
          {/* Legend */}
          <div className="absolute top-stack-md right-stack-md z-10 bg-surface-container-lowest/60 backdrop-blur-md border border-outline-variant/30 rounded-xl p-stack-md w-48">
            <p className="text-[10px] font-bold text-outline tracking-widest mb-stack-sm">GRAPH LEGEND</p>
            <div className="space-y-stack-sm">
              <LegendDot color="#ffb4ab" label="High-Risk Entity" />
              <LegendDot color="#c1c1ff" label="Phone / Device" />
              <LegendDot color="#edc221" label="UPI Handle" />
              <LegendDot color="#adaefe" label="Domain" />
            </div>
          </div>

          <GraphView
            nodes={graph?.nodes ?? []}
            edges={graph?.edges ?? []}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />

          {/* Stats */}
          <div className="absolute bottom-stack-md left-stack-md right-stack-md flex items-end justify-between pointer-events-none">
            <div className="bg-surface-container-lowest/50 backdrop-blur-lg p-stack-md border border-outline-variant/30 rounded-xl flex items-center gap-stack-lg">
              <div>
                <p className="text-[10px] font-bold text-outline uppercase tracking-wider">Active Nodes</p>
                <p className="text-2xl font-bold text-on-surface">{graph?.nodes.length ?? 0}</p>
              </div>
              <div className="h-8 w-[1px] bg-outline-variant/30" />
              <div>
                <p className="text-[10px] font-bold text-outline uppercase tracking-wider">Clusters</p>
                <p className="text-2xl font-bold text-on-surface">{ringCount}</p>
              </div>
              <div className="h-8 w-[1px] bg-outline-variant/30" />
              <div>
                <p className="text-[10px] font-bold text-outline uppercase tracking-wider">Engine</p>
                <p className="text-body-md font-bold text-primary">{graph?.engine ?? "—"}</p>
              </div>
            </div>
          </div>
        </div>

        {/* AI insight */}
        <div className="card-obsidian p-stack-md flex gap-stack-md border-l-4 border-l-primary/50">
          <div className="flex-none flex flex-col items-center justify-center px-4">
            <div className="w-14 h-14 bg-primary-container/20 rounded-2xl flex items-center justify-center border border-primary-container/30">
              <Icon name="auto_awesome" className="text-primary text-[28px]" fill />
            </div>
            <p className="text-[10px] font-bold text-primary tracking-tighter mt-1">AI INSIGHT</p>
          </div>
          <div className="flex-1">
            <h3 className="font-headline-sm text-on-surface mb-1">Network Correlation Summary</h3>
            <p className="text-body-md text-on-surface-variant leading-relaxed">
              The engine identified <span className="text-primary font-bold">{ringCount}</span> connected
              fraud clusters across <span className="text-primary font-bold">{graph?.nodes.length ?? 0}</span>{" "}
              entities and <span className="text-primary font-bold">{graph?.edges.length ?? 0}</span>{" "}
              co-occurrence links. Select any node to inspect its intelligence profile and relationships.
            </p>
          </div>
        </div>
      </div>

      {/* Right: entity profile */}
      <div className="w-full xl:w-[400px] flex flex-col gap-stack-lg xl:overflow-y-auto custom-scrollbar">
        <section className="card-obsidian p-stack-lg">
          {entityLoading ? (
            <PageLoader />
          ) : !entity ? (
            <p className="font-body-md text-on-surface-variant text-center py-stack-lg">
              Select a node to view its profile.
            </p>
          ) : (
            <>
              <div className="flex items-center justify-between mb-stack-md">
                <h3 className="text-[11px] font-bold text-outline uppercase tracking-[0.2em]">Entity Profile</h3>
                <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase ${severityBadge(entity.risk_tier)}`}>
                  {entity.risk_tier}
                </span>
              </div>
              <div className="flex items-center gap-stack-md mb-stack-lg">
                <div className="w-16 h-16 bg-surface-container rounded-2xl flex items-center justify-center border border-outline-variant/30">
                  <Icon
                    name={
                      entity.type === "phone"
                        ? "smartphone"
                        : entity.type === "upi"
                        ? "account_balance_wallet"
                        : entity.type === "email"
                        ? "mail"
                        : "fingerprint"
                    }
                    className="text-primary text-[32px]"
                  />
                </div>
                <div className="min-w-0">
                  <p className="font-mono text-on-surface leading-tight break-all">{entity.raw_value}</p>
                  <p className="text-label-md text-on-surface-variant uppercase mt-1">{entity.type}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-stack-md mb-stack-lg">
                <Stat label="Risk Score" value={`${Math.round(entity.risk_score)}`} suffix="/100" />
                <Stat label="Occurrences" value={String(entity.occurrence_count)} />
              </div>

              <h4 className="text-[10px] font-bold text-outline uppercase tracking-widest mb-stack-sm">
                Relationship Explorer
              </h4>
              <div className="space-y-1.5 mb-stack-md">
                {entity.subgraph.nodes
                  .filter((n) => n.id !== entity.id)
                  .slice(0, 8)
                  .map((n) => (
                    <button
                      key={n.id}
                      onClick={() => setSelectedId(n.id)}
                      className="w-full flex items-center justify-between p-3 bg-surface-container/30 hover:bg-surface-container transition-all rounded-xl border border-transparent hover:border-outline-variant/30"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="p-2 bg-primary/10 rounded-lg">
                          <Icon
                            name={n.type === "upi" ? "account_balance_wallet" : n.type === "email" ? "mail" : "smartphone"}
                            className="text-[18px] text-primary"
                          />
                        </div>
                        <span className="text-body-md font-medium text-on-surface truncate font-mono">{n.label}</span>
                      </div>
                      <span className="text-label-md text-outline uppercase">{n.type}</span>
                    </button>
                  ))}
                {entity.subgraph.nodes.filter((n) => n.id !== entity.id).length === 0 && (
                  <p className="font-body-md text-on-surface-variant/60 text-[12px]">No direct connections.</p>
                )}
              </div>

              <h4 className="text-[10px] font-bold text-outline uppercase tracking-widest mb-stack-sm">
                Linked Reports ({entity.linked_reports.length})
              </h4>
              <div className="space-y-1.5">
                {entity.linked_reports.slice(0, 6).map((r) => (
                  <div
                    key={r.id}
                    className="flex items-center justify-between p-2.5 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-lg"
                  >
                    <span className="font-mono text-[11px] text-on-surface capitalize">{r.source_type}</span>
                    <span className="text-[10px] text-on-surface-variant">{formatDateTime(r.created_at)}</span>
                  </div>
                ))}
                {entity.linked_reports.length === 0 && (
                  <p className="font-body-md text-on-surface-variant/60 text-[12px]">No linked reports.</p>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-stack-sm text-[11px] font-medium text-on-surface">
      <span
        className="w-2.5 h-2.5 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
      />
      {label}
    </div>
  );
}

function Stat({ label, value, suffix }: { label: string; value: string; suffix?: string }) {
  return (
    <div className="p-stack-md bg-surface-container-lowest/50 border border-outline-variant/30 rounded-xl">
      <p className="text-[10px] font-bold text-outline uppercase mb-1">{label}</p>
      <p className="text-3xl font-bold text-on-surface">
        {value}
        {suffix && <span className="text-sm text-outline font-normal">{suffix}</span>}
      </p>
    </div>
  );
}

export default function ThreatIntelPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <ThreatIntelInner />
    </Suspense>
  );
}
