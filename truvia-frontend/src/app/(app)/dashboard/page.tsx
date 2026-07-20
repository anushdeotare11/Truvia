"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  motion,
  animate,
  useInView,
  useReducedMotion,
  type Variants,
} from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { DashboardStats, Report, PredictiveAlert, GeoBreakdown, ScoreDistribution, TimelineEvent } from "@/lib/types";
import { severityBadge, severityText, reportTitle, formatDateTime, shortId } from "@/lib/format";

// ─── Count-up number (respects reduced motion) ─────────────────────────────
function CountUp({ value, className }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setDisplay(value);
      return;
    }
    const controls = animate(0, value, {
      duration: 1.2,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(v),
    });
    return () => controls.stop();
  }, [inView, value, reduce]);

  return (
    <span ref={ref} className={className}>
      {Math.round(display).toLocaleString()}
    </span>
  );
}

// ─── Circular index ring (AVG INDEX) ───────────────────────────────────────
function IndexRing({ value, size = 132 }: { value: number; size?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const reduce = useReducedMotion();
  const [progress, setProgress] = useState(0);

  const r = 54;
  const circumference = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, value));
  const offset = circumference - (circumference * (clamped * progress)) / 100;

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setProgress(1);
      return;
    }
    const controls = animate(0, 1, {
      duration: 1.3,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setProgress(v),
    });
    return () => controls.stop();
  }, [inView, reduce]);

  return (
    <div ref={ref} className="relative" style={{ width: size, height: size }}>
      <svg className="w-full h-full -rotate-90" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={r} fill="transparent" stroke="#292a2e" strokeWidth="9" />
        <circle
          cx="64"
          cy="64"
          r={r}
          fill="transparent"
          stroke="#00f4fe"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ filter: "drop-shadow(0 0 8px rgba(0,244,254,0.6))" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-heading text-[38px] font-bold tracking-tight text-secondary-container leading-none"
          style={{ textShadow: "0 0 14px rgba(0,244,254,0.35)" }}
        >
          {Math.round(clamped * progress)}
        </span>
        <span className="text-outline text-[10px] uppercase tracking-[0.2em] mt-1">Avg Index</span>
      </div>
    </div>
  );
}

// Progress-bar fills for scam vectors (cyan → periwinkle → amber, cycling).
const VECTOR_FILLS = [
  { bg: "linear-gradient(90deg,#00dce5,#00f4fe)", glow: "rgba(0,244,254,0.5)", text: "text-secondary-container" },
  { bg: "linear-gradient(90deg,#658aff,#b5c4ff)", glow: "rgba(181,196,255,0.5)", text: "text-primary" },
  { bg: "linear-gradient(90deg,#e07314,#ffb787)", glow: "rgba(255,183,135,0.5)", text: "text-tertiary" },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [alerts, setAlerts] = useState<PredictiveAlert[]>([]);
  const [geoData, setGeoData] = useState<GeoBreakdown[]>([]);
  const [scoreDistData, setScoreDistData] = useState<ScoreDistribution[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reduce = useReducedMotion();

  useEffect(() => {
    (async () => {
      try {
        const [s, r, a, geo, scoreDist, tl] = await Promise.all([
          api.get<DashboardStats>("/cases/stats"),
          api.get<Report[]>("/reports?limit=8"),
          api.get<PredictiveAlert[]>("/alerts/predictive"),
          api.get<GeoBreakdown[]>("/dashboard/geo-breakdown"),
          api.get<ScoreDistribution[]>("/dashboard/score-distribution"),
          api.get<TimelineEvent[]>("/dashboard/timeline"),
        ]);
        setStats(s);
        setReports(r);
        setAlerts(a);
        setGeoData(geo);
        setScoreDistData(scoreDist);
        setTimeline(tl);
      } catch {
        setError("Failed to load dashboard data.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <PageLoader />;
  if (error || !stats)
    return <div className="p-margin-page text-error font-body-md">{error ?? "No data."}</div>;

  const criticalCount = alerts.filter((a) => a.severity === "critical").length;

  // Scam vector distribution from recent reports.
  const catCounts: Record<string, number> = {};
  reports.forEach((r) => {
    const c = r.threat_scores?.[0]?.scam_category;
    if (c) catCounts[c] = (catCounts[c] || 0) + 1;
  });
  const totalCat = Object.values(catCounts).reduce((a, b) => a + b, 0) || 1;
  const vectors = Object.entries(catCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([name, count], i) => ({
      name,
      pct: Math.round((count / totalCat) * 100),
      color: ["bg-primary", "bg-secondary", "bg-tertiary", "bg-error"][i % 4],
      text: ["text-primary", "text-secondary", "text-tertiary", "text-error"][i % 4],
    }));

  const kpis = [
    { label: "Total Complaints", value: stats.total_reports, icon: "forum", accent: "" },
    { label: "Active Investigations", value: stats.total_cases, icon: "manage_search", accent: "" },
    {
      label: "Critical Threats",
      value: criticalCount,
      icon: "warning",
      accent: "border-l-4 border-l-error",
      valueClass: "text-error",
    },
    { label: "High-Risk Entities", value: stats.high_risk_entities, icon: "hub", accent: "", valueClass: "text-tertiary" },
  ];

  const brief = alerts[0];

  const SEVERITY_COLORS = ["#1F9D6B", "#4da2ff", "#E8A33D", "#D6303C", "#991B1B"];

  // ─── Motion variants (disabled under reduced-motion) ─────────────────────
  const container: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.08, delayChildren: reduce ? 0 : 0.04 } },
  };
  const fadeUp: Variants = reduce
    ? { hidden: { opacity: 1 }, show: { opacity: 1 } }
    : {
        hidden: { opacity: 0, y: 18 },
        show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
      };
  const rowFade: Variants = reduce
    ? { hidden: { opacity: 1 }, show: { opacity: 1 } }
    : {
        hidden: { opacity: 0, y: 8 },
        show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
      };

  // Border accent + icon per alert severity.
  const alertAccent = (sev: string) => {
    switch (sev.toLowerCase()) {
      case "critical":
        return "border-l-error";
      case "high":
        return "border-l-tertiary";
      default:
        return "border-l-secondary-container";
    }
  };

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="max-w-container-max mx-auto p-gutter space-y-gutter"
    >
      {/* Title */}
      <motion.div variants={fadeUp} className="flex flex-wrap items-end justify-between gap-stack-md">
        <div>
          <h1 className="font-heading text-[38px] font-bold tracking-tight text-primary">
            National Threat Monitor
          </h1>
          <p className="font-body-md text-on-surface-variant mt-1 flex items-center gap-2">
            <span className="w-2 h-2 bg-secondary-container rounded-full glow-dot pulse" />
            Operational status: <span className="text-secondary-container font-bold">OPTIMAL</span>
          </p>
        </div>
        <Link href="/investigations" className="btn-bloom h-10 px-stack-md text-on-primary rounded-lg flex items-center gap-2 font-label-md font-bold">
          <Icon name="manage_search" className="text-[18px]" />
          VIEW INVESTIGATIONS
        </Link>
      </motion.div>

      {/* KPI grid */}
      <motion.div variants={container} className="grid grid-cols-2 lg:grid-cols-4 gap-gutter">
        {kpis.map((k, i) => (
          <motion.div
            key={k.label}
            variants={fadeUp}
            className={`glass-panel p-6 relative overflow-hidden group transition-transform duration-300 hover:-translate-y-1 ${
              i === 0 ? "cyan-glow" : ""
            } ${k.accent}`}
          >
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
              <Icon name={k.icon} className="text-[64px]" />
            </div>
            <div className="flex justify-between items-start mb-stack-md">
              <span className="font-label-md text-on-surface-variant">{k.label}</span>
            </div>
            <CountUp
              value={k.value}
              className={`font-heading text-5xl font-bold tracking-tight leading-none ${k.valueClass ?? "text-on-surface"}`}
            />
          </motion.div>
        ))}
      </motion.div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-gutter">
        {/* Left */}
        <div className="col-span-12 lg:col-span-8 space-y-gutter">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
            {/* Trend chart */}
            <motion.div variants={fadeUp} className="glass-panel p-6">
              <div className="flex items-start justify-between mb-stack-md">
                <div>
                  <p className="font-label-md text-[10px] uppercase tracking-[0.2em] text-outline">Live Signal</p>
                  <span className="font-heading text-headline-sm text-on-surface">Complaint Trend</span>
                </div>
                <span className="font-label-md text-[10px] font-bold text-secondary-container bg-secondary-container/10 border border-secondary-container/20 px-2 py-1 rounded-full">
                  24H CYCLE
                </span>
              </div>
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={stats.daily_metrics} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#00f4fe" stopOpacity={0.45} />
                        <stop offset="100%" stopColor="#00f4fe" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#292a2e" vertical={false} />
                    <XAxis dataKey="date" stroke="#8d90a0" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#8d90a0" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        background: "#1e1f23",
                        border: "1px solid #343538",
                        borderRadius: 12,
                        color: "#e3e2e7",
                        fontSize: 12,
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="reports"
                      stroke="#00f4fe"
                      strokeWidth={2}
                      fill="url(#trendFill)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            {/* Scam vector distribution */}
            <motion.div variants={fadeUp} className="glass-panel p-6">
              <div className="mb-stack-md">
                <p className="font-label-md text-[10px] uppercase tracking-[0.2em] text-outline">Threat Mix</p>
                <span className="font-heading text-headline-sm text-on-surface">Scam Vector Distribution</span>
              </div>
              <div className="space-y-stack-md">
                {vectors.length === 0 && (
                  <p className="font-body-md text-on-surface-variant/60 text-[12px]">No recent data.</p>
                )}
                {vectors.map((v, i) => {
                  const fill = VECTOR_FILLS[i % VECTOR_FILLS.length];
                  return (
                    <div key={v.name} className="space-y-1.5">
                      <div className="flex justify-between font-label-md text-[11px]">
                        <span className="truncate max-w-[70%] text-on-surface">{v.name}</span>
                        <span className={fill.text}>{v.pct}%</span>
                      </div>
                      <div className="w-full bg-white/5 h-2.5 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full"
                          style={{ background: fill.bg, boxShadow: `0 0 10px ${fill.glow}` }}
                          initial={{ width: 0 }}
                          animate={{ width: `${v.pct}%` }}
                          transition={{ duration: reduce ? 0 : 0.9, ease: [0.16, 1, 0.3, 1] }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </div>

          {/* Incident table */}
          <motion.div variants={fadeUp} className="glass-panel overflow-hidden">
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-6 bg-secondary-container rounded-full" />
                <h2 className="font-heading text-headline-sm text-on-surface">Recent Incidents</h2>
              </div>
              <Link href="/reports" className="font-label-md text-[11px] text-secondary-container font-bold uppercase tracking-wider hover:text-primary transition-colors">
                View All
              </Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant">ID</th>
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant">SUBJECT</th>
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant">THREAT</th>
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant">STATUS</th>
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant hidden md:table-cell">
                      TIME
                    </th>
                  </tr>
                </thead>
                <motion.tbody variants={container} className="font-body-md text-on-surface">
                  {reports.map((r) => {
                    const sev = r.threat_scores?.[0]?.severity_band;
                    return (
                      <motion.tr
                        key={r.id}
                        variants={rowFade}
                        className="border-b border-white/5 hover:bg-white/[0.03] transition-colors"
                      >
                        <td className="p-4 font-heading font-semibold text-secondary-container">{shortId(r.id)}</td>
                        <td className="p-4 font-semibold max-w-[240px] truncate">{reportTitle(r)}</td>
                        <td className="p-4">
                          <span className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase ${severityBadge(sev)}`}>
                            {sev ?? "—"}
                          </span>
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex items-center gap-2 font-bold text-sm ${severityText(sev)}`}>
                            <span className={`w-1.5 h-1.5 rounded-full glow-dot pulse ${sev === "critical" ? "bg-error" : sev === "high" ? "bg-tertiary" : "bg-secondary-container"}`} />
                            {r.status}
                          </span>
                        </td>
                        <td className="p-4 text-on-surface-variant text-sm tabular-nums hidden md:table-cell">
                          {formatDateTime(r.created_at)}
                        </td>
                      </motion.tr>
                    );
                  })}
                  {reports.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-on-surface-variant">
                        No incidents recorded.
                      </td>
                    </tr>
                  )}
                </motion.tbody>
              </table>
            </div>
          </motion.div>
        </div>

        {/* Right */}
        <div className="col-span-12 lg:col-span-4 space-y-gutter">
          {/* AI Brief */}
          <motion.div variants={fadeUp} className="glass-panel p-6 relative overflow-hidden">
            <div className="absolute -right-4 -top-4 w-32 h-32 bg-secondary-container/5 rounded-full blur-3xl" />
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-stack-md">
                <div className="w-10 h-10 rounded-lg bg-primary-container/20 border border-primary/20 flex items-center justify-center">
                  <Icon name="psychology" className="text-primary text-[20px]" />
                </div>
                <div>
                  <h2 className="font-heading font-bold text-primary uppercase tracking-wider text-[13px]">
                    Neural Analysis
                  </h2>
                  <p className="text-[10px] text-on-surface-variant">Daily Intelligence Brief</p>
                </div>
              </div>
              {brief ? (
                <div className="space-y-stack-md">
                  <p className="font-body-md text-on-surface leading-relaxed">
                    Monitoring detects a{" "}
                    <span className="text-secondary-container font-bold">
                      {brief.velocity_metric.trend_percentage}% surge
                    </span>{" "}
                    in {brief.title.replace("Velocity Surge: ", "")} over the last fortnight.
                  </p>
                  <div className="bg-white/[0.03] p-4 rounded-lg border-l-4 border-secondary-container">
                    <p className="text-sm italic text-on-surface-variant">{brief.description}</p>
                  </div>
                </div>
              ) : (
                <p className="font-body-md text-on-surface-variant">No predictive signals today.</p>
              )}
            </div>
          </motion.div>

          {/* Priority alerts */}
          <motion.div variants={fadeUp} className="glass-panel flex flex-col max-h-[460px] overflow-hidden">
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2 text-error">
                <Icon name="warning" className="text-[20px]" fill />
                <h2 className="font-heading font-bold uppercase tracking-widest text-[13px]">Priority Alerts</h2>
              </div>
              <span className="flex items-center gap-1.5 bg-error/15 text-error px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-error glow-dot pulse" />
                Live
              </span>
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              {alerts.map((a, i) => {
                // Alert titles are "Velocity Surge: {category}" (alerts.py). Drill into
                // the pre-filtered Complaint Table for that category (App Flow §9).
                const category = a.title.replace(/^Velocity Surge:\s*/, "").trim();
                return (
                  <Link
                    key={i}
                    href={`/reports?category=${encodeURIComponent(category)}`}
                    className={`block p-4 border-b border-white/5 border-l-4 ${alertAccent(a.severity)} hover:bg-white/[0.03] transition-colors group`}
                  >
                    <div className="flex justify-between mb-2">
                      <span className={`flex items-center gap-1.5 font-label-md text-[10px] uppercase font-bold ${severityText(a.severity)}`}>
                        <Icon name="warning" className="text-[14px]" fill />
                        {a.severity}
                      </span>
                      <span className="font-label-md text-[10px] text-outline tabular-nums">
                        {a.velocity_metric.count_14d} / 14d
                      </span>
                    </div>
                    <h3 className="font-body-md font-bold text-on-surface flex items-center gap-1">
                      {a.title}
                      <Icon
                        name="arrow_forward"
                        className="text-[14px] text-secondary-container opacity-0 group-hover:opacity-100 transition-opacity"
                      />
                    </h3>
                    <p className="text-[12px] text-on-surface-variant mt-1 leading-snug line-clamp-3">
                      {a.description}
                    </p>
                  </Link>
                );
              })}
              {alerts.length === 0 && (
                <p className="p-4 font-body-md text-on-surface-variant">No active alerts.</p>
              )}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Analytics Grid - Geo, Score Distribution, Timeline */}
      <motion.div variants={container} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-gutter">
        {/* City Distribution (dot-row list) */}
        <motion.section variants={fadeUp} className="glass-panel p-6">
          <h3 className="font-heading text-headline-sm text-on-surface mb-stack-md">City Distribution</h3>
          {geoData.length === 0 ? (
            <p className="font-body-md text-on-surface-variant/60 text-[12px]">No data.</p>
          ) : (
            <div className="space-y-stack-sm">
              {geoData.slice(0, 8).map((g, i) => (
                <div
                  key={g.city}
                  className="flex items-center gap-3 bg-white/[0.03] rounded-2xl border border-white/5 px-4 py-3"
                >
                  <span
                    className="w-2.5 h-2.5 rounded-full glow-dot shrink-0"
                    style={{ backgroundColor: SEVERITY_COLORS[i % SEVERITY_COLORS.length] }}
                  />
                  <span className="font-body-md text-on-surface truncate flex-1">{g.city}</span>
                  <span className="font-heading font-bold text-secondary-container tabular-nums">{g.count}</span>
                </div>
              ))}
            </div>
          )}
        </motion.section>

        {/* Threat Score Distribution (ring) */}
        <motion.section variants={fadeUp} className="glass-panel p-6 flex flex-col items-center">
          <h3 className="font-heading text-headline-sm text-on-surface mb-stack-md self-start">Threat Score Distribution</h3>
          <IndexRing value={stats.avg_threat_score} />
          {scoreDistData.length > 0 && (
            <div className="mt-stack-md w-full space-y-1.5">
              {scoreDistData.map((d, i) => (
                <div key={d.range} className="flex items-center gap-2 text-[11px]">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: SEVERITY_COLORS[i % SEVERITY_COLORS.length] }}
                  />
                  <span className="text-on-surface-variant flex-1 tabular-nums">{d.range}</span>
                  <span className="text-on-surface font-bold tabular-nums">{d.count}</span>
                </div>
              ))}
            </div>
          )}
        </motion.section>

        {/* Threat Timeline */}
        <motion.section variants={fadeUp} className="glass-panel p-6 max-h-96 overflow-y-auto custom-scrollbar">
          <h3 className="font-heading text-headline-sm text-on-surface mb-stack-md">Threat Timeline</h3>
          {timeline.length === 0 ? (
            <p className="font-body-md text-on-surface-variant/60 text-[12px]">No data.</p>
          ) : (
            <div className="space-y-stack-sm">
              {timeline.slice(0, 20).map((evt) => (
                <div key={evt.id} className="flex items-center gap-stack-sm">
                  <div className={`w-2 h-2 rounded-full glow-dot ${evt.severity === "critical" ? "bg-error" : evt.severity === "high" ? "bg-tertiary" : "bg-secondary-container"}`} />
                  <span className="text-body-sm text-on-surface-variant tabular-nums">{evt.created_at ? new Date(evt.created_at).toLocaleString() : "N/A"}</span>
                  <span className="text-body-sm text-on-surface">{evt.scam_category || "Report"}</span>
                  <span className={`text-[10px] uppercase font-bold px-1 rounded ${evt.severity === "critical" ? "text-error bg-error/10" : evt.severity === "high" ? "text-tertiary bg-tertiary/10" : "text-secondary-container bg-secondary-container/10"}`}>
                    {evt.severity || "pending"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </motion.section>
      </motion.div>
    </motion.div>
  );
}
