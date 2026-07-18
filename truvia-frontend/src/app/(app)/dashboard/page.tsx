"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
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

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [alerts, setAlerts] = useState<PredictiveAlert[]>([]);
  const [geoData, setGeoData] = useState<GeoBreakdown[]>([]);
  const [scoreDistData, setScoreDistData] = useState<ScoreDistribution[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    { label: "High-Risk Entities", value: stats.high_risk_entities, icon: "hub", accent: "" },
  ];

  const brief = alerts[0];

  const SEVERITY_COLORS = ["#1F9D6B", "#5d5fef", "#E8A33D", "#D6303C", "#991B1B"];

  return (
    <div className="p-gutter space-y-gutter">
      {/* Title */}
      <div className="flex flex-wrap items-end justify-between gap-stack-md">
        <div>
          <h1 className="text-display-lg text-primary text-[36px]">National Threat Monitor</h1>
          <p className="font-body-md text-on-surface-variant mt-1 flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full glow-dot" />
            Operational status: <span className="text-secondary font-bold">OPTIMAL</span>
          </p>
        </div>
        <Link
          href="/investigations"
          className="h-10 px-stack-md bg-primary-container text-white rounded-lg flex items-center gap-2 font-label-md font-bold hover:brightness-110 transition-all"
        >
          <Icon name="manage_search" className="text-[18px]" />
          VIEW INVESTIGATIONS
        </Link>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-gutter">
        {kpis.map((k) => (
          <div key={k.label} className={`bento-card p-card-padding relative overflow-hidden group ${k.accent}`}>
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
              <Icon name={k.icon} className="text-[64px]" />
            </div>
            <div className="flex justify-between items-start mb-stack-md">
              <span className="font-label-md text-on-surface-variant">{k.label}</span>
            </div>
            <span className={`text-[36px] font-bold leading-none ${k.valueClass ?? "text-on-surface"}`}>
              {k.value}
            </span>
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-gutter">
        {/* Left */}
        <div className="col-span-12 lg:col-span-8 space-y-gutter">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
            {/* Trend chart */}
            <div className="bento-card p-card-padding">
              <div className="flex items-center justify-between mb-stack-md">
                <span className="font-label-md text-on-surface">Complaint Trend</span>
                <Icon name="show_chart" className="text-primary text-[18px]" />
              </div>
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={stats.daily_metrics} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#c1c1ff" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#c1c1ff" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a292f" vertical={false} />
                    <XAxis dataKey="date" stroke="#908fa0" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#908fa0" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        background: "#1f1f25",
                        border: "1px solid #464555",
                        borderRadius: 8,
                        color: "#e4e1e9",
                        fontSize: 12,
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="reports"
                      stroke="#c1c1ff"
                      strokeWidth={2}
                      fill="url(#trendFill)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Scam vector distribution */}
            <div className="bento-card p-card-padding">
              <div className="flex items-center justify-between mb-stack-md">
                <span className="font-label-md text-on-surface">Scam Vector Distribution</span>
              </div>
              <div className="space-y-stack-md">
                {vectors.length === 0 && (
                  <p className="font-body-md text-on-surface-variant/60 text-[12px]">No recent data.</p>
                )}
                {vectors.map((v) => (
                  <div key={v.name} className="space-y-1">
                    <div className="flex justify-between font-label-md text-[11px]">
                      <span className="truncate max-w-[70%]">{v.name}</span>
                      <span className={v.text}>{v.pct}%</span>
                    </div>
                    <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                      <div className={`${v.color} h-full glow-dot`} style={{ width: `${v.pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Incident table */}
          <div className="bento-card overflow-hidden">
            <div className="p-card-padding border-b border-outline-variant flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-6 bg-primary rounded-full" />
                <h2 className="font-headline-sm text-on-surface">Recent Incidents</h2>
              </div>
              <Link href="/reports" className="font-label-md text-[11px] text-secondary font-bold uppercase">
                View All
              </Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-low/30 border-b border-outline-variant">
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant">ID</th>
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant">SUBJECT</th>
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant">THREAT</th>
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant">STATUS</th>
                    <th className="p-4 font-label-md text-[11px] text-on-surface-variant hidden md:table-cell">
                      TIME
                    </th>
                  </tr>
                </thead>
                <tbody className="font-body-md text-on-surface">
                  {reports.map((r) => {
                    const sev = r.threat_scores?.[0]?.severity_band;
                    return (
                      <tr
                        key={r.id}
                        className="border-b border-outline-variant/30 hover:bg-surface-container-high transition-colors"
                      >
                        <td className="p-4 font-label-md text-primary">{shortId(r.id)}</td>
                        <td className="p-4 font-semibold max-w-[240px] truncate">{reportTitle(r)}</td>
                        <td className="p-4">
                          <span
                            className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase ${severityBadge(sev)}`}
                          >
                            {sev ?? "—"}
                          </span>
                        </td>
                        <td className={`p-4 font-bold text-sm ${severityText(sev)}`}>{r.status}</td>
                        <td className="p-4 text-on-surface-variant text-sm hidden md:table-cell">
                          {formatDateTime(r.created_at)}
                        </td>
                      </tr>
                    );
                  })}
                  {reports.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-on-surface-variant">
                        No incidents recorded.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right */}
        <div className="col-span-12 lg:col-span-4 space-y-gutter">
          {/* AI Brief */}
          <div className="bento-card p-card-padding relative overflow-hidden">
            <div className="absolute -right-4 -top-4 w-32 h-32 bg-primary/5 rounded-full blur-3xl" />
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-stack-md">
                <div className="w-10 h-10 rounded-lg bg-primary-container flex items-center justify-center">
                  <Icon name="psychology" className="text-primary text-[20px]" />
                </div>
                <div>
                  <h2 className="font-label-md text-primary uppercase font-bold tracking-wider">
                    Neural Analysis
                  </h2>
                  <p className="text-[10px] text-on-surface-variant">Daily Intelligence Brief</p>
                </div>
              </div>
              {brief ? (
                <div className="space-y-stack-md">
                  <p className="font-body-md text-on-surface leading-relaxed">
                    Monitoring detects a{" "}
                    <span className="text-primary font-bold">
                      {brief.velocity_metric.trend_percentage}% surge
                    </span>{" "}
                    in {brief.title.replace("Velocity Surge: ", "")} over the last fortnight.
                  </p>
                  <div className="bg-surface-container-high/50 p-4 rounded-lg border-l-4 border-primary">
                    <p className="text-sm italic text-on-surface-variant">{brief.description}</p>
                  </div>
                </div>
              ) : (
                <p className="font-body-md text-on-surface-variant">No predictive signals today.</p>
              )}
            </div>
          </div>

          {/* Priority alerts */}
          <div className="bento-card flex flex-col max-h-[460px]">
            <div className="p-card-padding border-b border-outline-variant flex items-center justify-between">
              <div className="flex items-center gap-2 text-error">
                <Icon name="warning" className="text-[20px]" fill />
                <h2 className="font-label-md font-bold uppercase tracking-widest">Priority Alerts</h2>
              </div>
              <span className="bg-error text-on-error px-2 py-0.5 rounded-full text-[10px] font-black">
                ACTIVE
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
                    className="block p-4 border-b border-outline-variant/30 hover:bg-surface-container-high/50 transition-colors group"
                  >
                    <div className="flex justify-between mb-2">
                      <span className={`font-label-md text-[10px] uppercase font-bold ${severityText(a.severity)}`}>
                        {a.severity}
                      </span>
                      <span className="font-label-md text-[10px] text-outline">
                        {a.velocity_metric.count_14d} / 14d
                      </span>
                    </div>
                    <h3 className="font-body-md font-bold text-on-surface flex items-center gap-1">
                      {a.title}
                      <Icon
                        name="arrow_forward"
                        className="text-[14px] text-primary opacity-0 group-hover:opacity-100 transition-opacity"
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
          </div>
        </div>
      </div>

      {/* Analytics Grid - Geo, Score Distribution, Timeline */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-gutter">
        {/* Geo Bar Chart */}
        <section className="bento-card p-card-padding">
          <h3 className="font-headline-sm text-on-surface mb-stack-md">City Distribution</h3>
          {geoData.length === 0 ? (
            <p className="font-body-md text-on-surface-variant/60 text-[12px]">No data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={geoData}>
                <XAxis dataKey="city" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    background: "#1f1f25",
                    border: "1px solid #464555",
                    borderRadius: 8,
                    color: "#e4e1e9",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="count" fill="#5d5fef" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        {/* Score Distribution Histogram */}
        <section className="bento-card p-card-padding">
          <h3 className="font-headline-sm text-on-surface mb-stack-md">Threat Score Distribution</h3>
          {scoreDistData.length === 0 ? (
            <p className="font-body-md text-on-surface-variant/60 text-[12px]">No data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={scoreDistData}>
                <XAxis dataKey="range" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    background: "#1f1f25",
                    border: "1px solid #464555",
                    borderRadius: 8,
                    color: "#e4e1e9",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {scoreDistData.map((_, i) => (
                    <Cell key={i} fill={SEVERITY_COLORS[i % SEVERITY_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        {/* Threat Timeline */}
        <section className="bento-card p-card-padding max-h-96 overflow-y-auto custom-scrollbar">
          <h3 className="font-headline-sm text-on-surface mb-stack-md">Threat Timeline</h3>
          {timeline.length === 0 ? (
            <p className="font-body-md text-on-surface-variant/60 text-[12px]">No data.</p>
          ) : (
            <div className="space-y-stack-sm">
              {timeline.slice(0, 20).map((evt) => (
                <div key={evt.id} className="flex items-center gap-stack-sm">
                  <div className={`w-2 h-2 rounded-full ${evt.severity === "critical" ? "bg-error" : evt.severity === "high" ? "bg-warning" : "bg-primary"}`} />
                  <span className="text-body-sm text-on-surface-variant">{evt.created_at ? new Date(evt.created_at).toLocaleString() : "N/A"}</span>
                  <span className="text-body-sm text-on-surface">{evt.scam_category || "Report"}</span>
                  <span className={`text-[10px] uppercase font-bold px-1 rounded ${evt.severity === "critical" ? "text-error bg-error/10" : evt.severity === "high" ? "text-warning bg-warning/10" : "text-primary bg-primary/10"}`}>
                    {evt.severity || "pending"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
