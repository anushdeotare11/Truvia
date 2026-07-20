"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { PredictiveAlert, PublicAlert, GraphOverview, GraphNode } from "@/lib/types";
import { severityBadge, severityText } from "@/lib/format";

// Left border accent per severity tier (Obsidian Glass semantic colors).
function borderAccent(sev?: string): string {
  switch ((sev || "").toLowerCase()) {
    case "critical":
      return "border-l-error";
    case "high":
      return "border-l-tertiary";
    default:
      return "border-l-secondary-container";
  }
}

// Map a 0–100 risk score to a severity tier for the blocklist chips.
function riskTier(score: number): string {
  if (score >= 80) return "critical";
  if (score >= 50) return "high";
  return "moderate";
}

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

  const reduce = useReducedMotion();
  const listVariants: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.06 } },
  };
  const rowVariants: Variants = reduce
    ? { hidden: { opacity: 1 }, show: { opacity: 1 } }
    : {
        hidden: { opacity: 0, y: 14 },
        show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" } },
      };
  const panelVariants: Variants = reduce
    ? { hidden: { opacity: 1 }, show: { opacity: 1 } }
    : {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
      };

  if (loading) return <PageLoader />;

  const activeCount = predictive.length + publicAlerts.length;
  const feedTitle = isOfficer ? "Predictive Threat Feed" : "Public Safety Advisories";

  return (
    <div className="relative p-gutter space-y-gutter">
      {/* Void background */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_18%_-5%,rgba(101,138,255,0.10),transparent_55%),radial-gradient(circle_at_100%_105%,rgba(0,244,254,0.07),transparent_50%)]"
      />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-stack-md">
        <div className="flex items-center gap-stack-md">
          <span className="font-mono text-label-sm bg-error/20 text-error px-stack-sm py-1 rounded flex items-center gap-stack-sm uppercase">
            <span className="w-2 h-2 rounded-full bg-error pulse inline-block" />
            Live Feed
          </span>
          <h1 className="font-heading text-headline-md text-on-surface">Alerts Center</h1>
        </div>
        <span className="text-body-md text-on-surface-variant flex items-center gap-stack-sm">
          <span className="w-2 h-2 bg-secondary-container rounded-full inline-block pulse" />
          {activeCount} Active {activeCount === 1 ? "Advisory" : "Advisories"}
        </span>
      </div>

      <div className="grid grid-cols-12 gap-gutter">
        {/* LEFT — Main feed */}
        <motion.section
          variants={panelVariants}
          initial="hidden"
          animate="show"
          className="col-span-12 lg:col-span-8 glass-panel overflow-hidden flex flex-col"
        >
          <div className="px-card-padding py-stack-md border-b border-white/[0.06] flex items-center gap-stack-sm">
            <div className="w-9 h-9 rounded-lg bg-error/15 border border-error/25 flex items-center justify-center">
              <Icon name="campaign" className="text-error" />
            </div>
            <h3 className="font-heading text-headline-sm text-on-surface">{feedTitle}</h3>
          </div>

          <motion.div
            variants={listVariants}
            initial="hidden"
            animate="show"
            className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-white/[0.04]"
          >
            {/* Predictive alerts (officers) */}
            {isOfficer &&
              predictive.map((a, i) => (
                <motion.article
                  key={`p-${i}`}
                  variants={rowVariants}
                  className={`flex gap-stack-md p-stack-md border-l-4 ${borderAccent(
                    a.severity
                  )} hover:bg-white/[0.03] transition-colors`}
                >
                  <div className="shrink-0 w-10 h-10 rounded-lg bg-white/[0.04] border border-outline-variant/40 flex items-center justify-center">
                    <Icon name="trending_up" className={severityText(a.severity)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start gap-stack-sm mb-1">
                      <span
                        className={`font-mono text-label-sm px-1.5 py-0.5 rounded uppercase ${severityBadge(
                          a.severity
                        )}`}
                      >
                        {a.severity}
                      </span>
                      <span className="font-mono text-body-sm text-on-surface-variant whitespace-nowrap">
                        +{a.velocity_metric.trend_percentage}% · {a.velocity_metric.count_14d}/14d
                      </span>
                    </div>
                    <h4 className="font-heading text-body-lg font-semibold text-on-surface mb-1">{a.title}</h4>
                    <p className="text-body-md text-on-surface-variant">{a.description}</p>
                  </div>
                </motion.article>
              ))}

            {/* Public advisories (everyone) */}
            {publicAlerts.map((a) => (
              <motion.article
                key={a.id}
                variants={rowVariants}
                className={`flex gap-stack-md p-stack-md border-l-4 ${borderAccent(
                  a.severity
                )} hover:bg-white/[0.03] transition-colors`}
              >
                <div className="shrink-0 w-10 h-10 rounded-lg bg-white/[0.04] border border-outline-variant/40 flex items-center justify-center">
                  <Icon name="warning" className={severityText(a.severity)} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-start gap-stack-sm mb-1">
                    <span
                      className={`font-mono text-label-sm px-1.5 py-0.5 rounded uppercase ${severityBadge(
                        a.severity
                      )}`}
                    >
                      {a.severity}
                    </span>
                    <span className="font-mono text-body-sm text-on-surface-variant whitespace-nowrap">{a.date}</span>
                  </div>
                  <h4 className="font-heading text-body-lg font-semibold text-on-surface mb-1">{a.title}</h4>
                  <p className="text-body-md text-on-surface-variant">{a.description}</p>
                </div>
              </motion.article>
            ))}

            {activeCount === 0 && (
              <div className="flex flex-col items-center justify-center gap-stack-sm py-16 px-stack-md text-center">
                <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-outline-variant/40 flex items-center justify-center">
                  <Icon name="notifications_off" className="text-on-surface-variant text-[28px]" />
                </div>
                <p className="font-heading text-body-lg text-on-surface">No trending alerts right now</p>
                <p className="text-body-md text-on-surface-variant max-w-sm">
                  The feed is quiet. New advisories will appear here as soon as they are detected.
                </p>
              </div>
            )}
          </motion.div>
        </motion.section>

        {/* RIGHT — High-risk blocklist (officers only) */}
        {isOfficer && (
          <motion.section
            variants={panelVariants}
            initial="hidden"
            animate="show"
            className="col-span-12 lg:col-span-4 glass-panel overflow-hidden flex flex-col"
          >
            <div className="px-card-padding py-stack-md border-b border-white/[0.06] flex items-center gap-stack-sm">
              <div className="w-9 h-9 rounded-lg bg-primary/15 border border-primary/25 flex items-center justify-center">
                <Icon name="block" className="text-primary" />
              </div>
              <h3 className="font-heading text-headline-sm text-on-surface">High-Risk Blocklist</h3>
            </div>

            {/* Detected fraud ring count */}
            <div className="px-card-padding py-stack-md border-b border-white/[0.06] flex items-center gap-stack-md">
              <div className="shrink-0 w-12 h-12 rounded-xl bg-error/15 border border-error/30 flex flex-col items-center justify-center pulse">
                <span className="font-heading text-headline-sm text-error leading-none">{ringCount}</span>
              </div>
              <div className="min-w-0">
                <p className="font-heading text-body-lg text-on-surface">Fraud rings detected</p>
                <p className="text-body-sm text-on-surface-variant leading-snug">
                  Connected-component clusters across the entity graph.
                </p>
              </div>
            </div>

            <motion.div
              variants={listVariants}
              initial="hidden"
              animate="show"
              className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-white/[0.04]"
            >
              {blocklist.map((n) => (
                <motion.div
                  key={n.id}
                  variants={rowVariants}
                  className="flex items-center gap-stack-md px-card-padding py-stack-sm hover:bg-white/[0.03] transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-body-sm text-on-surface truncate">{n.label}</p>
                    <p className="text-label-sm uppercase text-on-surface-variant capitalize">{n.type}</p>
                  </div>
                  <span
                    className={`font-mono text-label-sm px-2 py-0.5 rounded ${severityBadge(
                      riskTier(n.risk_score)
                    )}`}
                  >
                    {Math.round(n.risk_score)}
                  </span>
                </motion.div>
              ))}

              {blocklist.length === 0 && (
                <div className="flex flex-col items-center justify-center gap-stack-sm py-14 px-stack-md text-center">
                  <div className="w-12 h-12 rounded-2xl bg-white/[0.04] border border-outline-variant/40 flex items-center justify-center">
                    <Icon name="shield" className="text-on-surface-variant" />
                  </div>
                  <p className="font-heading text-body-md text-on-surface">No entities in blocklist</p>
                  <p className="text-body-sm text-on-surface-variant max-w-[220px]">
                    High-risk identifiers will surface here as the graph grows.
                  </p>
                </div>
              )}
            </motion.div>
          </motion.section>
        )}
      </div>
    </div>
  );
}
