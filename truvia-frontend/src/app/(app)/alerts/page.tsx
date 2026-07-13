"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { PredictiveAlert, PublicAlert, GraphOverview, GraphNode } from "@/lib/types";
import { severityBadge, severityText } from "@/lib/format";

export default function AlertsPage() {
  const { user } = useAuth();
  const isOfficer = user?.role === "officer" || user?.role === "admin";

  const [predictive, setPredictive] = useState<PredictiveAlert[]>([]);
  const [publicAlerts, setPublicAlerts] = useState<PublicAlert[]>([]);
  const [blocklist, setBlocklist] = useState<GraphNode[]>([]);
  const [ringCount, setRingCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const publicP = api.get<PublicAlert[]>("/alerts/public");
        const tasks: Promise<unknown>[] = [publicP];
        let predictiveP: Promise<PredictiveAlert[]> | null = null;
        let graphP: Promise<GraphOverview> | null = null;
        if (isOfficer) {
          predictiveP = api.get<PredictiveAlert[]>("/alerts/predictive");
          graphP = api.get<GraphOverview>("/graph/overview");
          tasks.push(predictiveP, graphP);
        }
        await Promise.allSettled(tasks);
        setPublicAlerts(await publicP.catch(() => []));
        if (predictiveP) setPredictive(await predictiveP.catch(() => []));
        if (graphP) {
          const g = await graphP.catch(() => null);
          if (g) {
            const top = [...g.nodes].sort((a, b) => b.risk_score - a.risk_score).slice(0, 12);
            setBlocklist(top);
            setRingCount(new Set(g.nodes.map((n) => n.group)).size);
          }
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [isOfficer]);

  if (loading) return <PageLoader />;

  const activeCount = predictive.length + publicAlerts.length;

  return (
    <div className="p-gutter space-y-gutter">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-stack-md">
        <div className="flex items-center gap-stack-sm">
          <span className="font-label-md bg-error/20 text-error px-stack-sm py-1 rounded">LIVE FEED</span>
          <span className="text-body-md text-on-surface-variant flex items-center gap-stack-sm">
            <span className="w-2 h-2 bg-error rounded-full inline-block animate-pulse" />
            {activeCount} Active Advisories
          </span>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-gutter">
        {/* Critical / Predictive feed */}
        <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden flex flex-col">
          <div className="px-stack-md py-stack-md border-b border-outline-variant flex items-center justify-between">
            <div className="flex items-center gap-stack-sm">
              <Icon name="campaign" className="text-error" />
              <h3 className="font-headline-sm text-[16px]">
                {isOfficer ? "Predictive Threat Feed" : "Public Safety Advisories"}
              </h3>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {isOfficer &&
              predictive.map((a, i) => (
                <div
                  key={`p-${i}`}
                  className="p-stack-md border-b border-outline-variant hover:bg-surface-container-high/50 transition-colors relative"
                >
                  <div
                    className={`absolute left-0 top-0 bottom-0 w-1 ${
                      a.severity === "critical" ? "bg-error" : a.severity === "high" ? "bg-tertiary" : "bg-secondary"
                    }`}
                  />
                  <div className="flex justify-between items-start mb-1">
                    <span
                      className={`font-label-md px-1.5 py-0.5 rounded text-[10px] uppercase ${severityBadge(
                        a.severity
                      )}`}
                    >
                      {a.severity}
                    </span>
                    <span className="font-label-md text-[12px] text-on-surface-variant">
                      +{a.velocity_metric.trend_percentage}% • {a.velocity_metric.count_14d}/14d
                    </span>
                  </div>
                  <h4 className="font-headline-sm text-[16px] text-on-surface mb-1">{a.title}</h4>
                  <p className="text-body-md text-on-surface-variant">{a.description}</p>
                </div>
              ))}

            {/* Public advisories (shown to everyone) */}
            {publicAlerts.map((a) => (
              <div
                key={a.id}
                className="p-stack-md border-b border-outline-variant hover:bg-surface-container-high/50 transition-colors relative"
              >
                <div
                  className={`absolute left-0 top-0 bottom-0 w-1 ${
                    a.severity === "critical" ? "bg-error" : "bg-tertiary"
                  }`}
                />
                <div className="flex justify-between items-start mb-1">
                  <span
                    className={`font-label-md px-1.5 py-0.5 rounded text-[10px] uppercase ${severityBadge(
                      a.severity
                    )}`}
                  >
                    {a.severity}
                  </span>
                  <span className="font-label-md text-[12px] text-on-surface-variant">{a.date}</span>
                </div>
                <h4 className="font-headline-sm text-[16px] text-on-surface mb-1">{a.title}</h4>
                <p className="text-body-md text-on-surface-variant">{a.description}</p>
              </div>
            ))}

            {activeCount === 0 && (
              <p className="p-6 text-center font-body-md text-on-surface-variant">No active advisories.</p>
            )}
          </div>
        </div>

        {/* Right: fraud rings + timeline */}
        <div className="col-span-12 lg:col-span-4 space-y-gutter">
          {isOfficer && (
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-card-padding">
              <div className="flex items-center gap-stack-sm mb-stack-md">
                <Icon name="hub" className="text-primary" />
                <h3 className="font-headline-sm text-[16px]">Fraud Rings</h3>
              </div>
              <div className="flex items-center justify-center py-stack-md">
                <div className="relative w-32 h-32 flex items-center justify-center">
                  <div className="absolute w-20 h-20 border border-error/30 rounded-full animate-ping" />
                  <div className="w-16 h-16 bg-error/80 rounded-full flex flex-col items-center justify-center text-on-error shadow-lg">
                    <span className="text-headline-sm font-bold">{ringCount}</span>
                    <span className="text-[9px] uppercase">clusters</span>
                  </div>
                </div>
              </div>
              <p className="text-[12px] text-on-surface-variant text-center leading-tight">
                Connected-component clusters detected across the entity graph.
              </p>
            </div>
          )}

          {/* Timeline of advisories */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
            <div className="px-stack-md py-stack-md border-b border-outline-variant">
              <h3 className="font-headline-sm text-[16px] flex items-center gap-stack-sm">
                <Icon name="history" />
                Notification Timeline
              </h3>
            </div>
            <div className="p-stack-md">
              <div className="space-y-stack-md relative before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[1px] before:bg-outline-variant/50">
                {[...predictive, ...publicAlerts].slice(0, 6).map((a, i) => {
                  const title = "title" in a ? a.title : "";
                  const sev = a.severity;
                  return (
                    <div key={i} className="relative pl-8">
                      <div
                        className={`absolute left-0 top-1 w-[24px] h-[24px] bg-background border rounded-full flex items-center justify-center z-10 ${
                          sev === "critical" ? "border-error" : "border-primary"
                        }`}
                      >
                        <div
                          className={`w-1.5 h-1.5 rounded-full ${sev === "critical" ? "bg-error" : "bg-primary"}`}
                        />
                      </div>
                      <p className={`text-body-md font-bold ${severityText(sev)}`}>{title}</p>
                      <p className="text-[11px] text-on-surface-variant uppercase font-label-md">{sev} priority</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* High-risk blocklist (officer) */}
        {isOfficer && (
          <div className="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden flex flex-col max-h-[400px]">
            <div className="px-stack-md py-stack-md border-b border-outline-variant">
              <h3 className="font-headline-sm text-[16px] flex items-center gap-stack-sm">
                <Icon name="block" />
                High Risk Blocklist
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 bg-surface-container-low z-10">
                  <tr>
                    {["Identifier", "Type", "Score"].map((h) => (
                      <th
                        key={h}
                        className="px-stack-md py-stack-sm font-label-md text-on-surface-variant text-[10px] uppercase border-b border-outline-variant"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {blocklist.map((n) => (
                    <tr key={n.id} className="hover:bg-surface-container-high transition-colors">
                      <td className="px-stack-md py-stack-sm font-mono text-[12px] max-w-[180px] truncate">
                        {n.label}
                      </td>
                      <td className="px-stack-md py-stack-sm text-[11px] capitalize">{n.type}</td>
                      <td className="px-stack-md py-stack-sm">
                        <span className="bg-error/10 text-error px-1.5 rounded font-bold text-xs">
                          {Math.round(n.risk_score)}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {blocklist.length === 0 && (
                    <tr>
                      <td colSpan={3} className="p-4 text-center text-on-surface-variant text-[12px]">
                        No entities in blocklist.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Trending scam scripts */}
        <div
          className={`col-span-12 ${
            isOfficer ? "lg:col-span-6" : "lg:col-span-12"
          } bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden flex flex-col max-h-[400px]`}
        >
          <div className="px-stack-md py-stack-md border-b border-outline-variant flex items-center justify-between">
            <h3 className="font-headline-sm text-[16px] flex items-center gap-stack-sm">
              <Icon name="terminal" className="text-tertiary" />
              Trending Scam Scripts
            </h3>
          </div>
          <div className="p-stack-md space-y-stack-md overflow-y-auto custom-scrollbar">
            {(isOfficer ? predictive : publicAlerts).slice(0, 4).map((a, i) => {
              const title = a.title;
              return (
                <div key={i} className="p-stack-sm bg-surface-container rounded border border-outline-variant">
                  <div className="flex justify-between items-center mb-unit">
                    <span className="font-label-md text-[12px] text-on-surface uppercase">{title}</span>
                    <span className={`text-[10px] font-bold ${severityText(a.severity)}`}>
                      {a.severity.toUpperCase()}
                    </span>
                  </div>
                  <div className="bg-black/80 text-[#50FA7B] p-stack-sm font-mono text-[11px] rounded border border-outline-variant/30">
                    &quot;{a.description.slice(0, 120)}...&quot;
                  </div>
                </div>
              );
            })}
            {(isOfficer ? predictive : publicAlerts).length === 0 && (
              <p className="text-center text-on-surface-variant text-[12px]">No trending scripts.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
