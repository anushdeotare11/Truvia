"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { Report } from "@/lib/types";
import {
  statusBadge,
  reportTitle,
  formatDateTime,
  shortId,
  severityText,
  severityStroke,
} from "@/lib/format";

const PAGE_SIZE = 10;
const STATUSES = ["", "submitted", "processing", "scored", "escalated", "dismissed", "failed"];
const SOURCE_TYPES = ["", "text", "screenshot", "audio"];

// Material icon per report source type.
function sourceIcon(type?: string): string {
  switch (type) {
    case "screenshot":
      return "screenshot";
    case "audio":
      return "audio_file";
    default:
      return "description";
  }
}

function ReportsInner() {
  const searchParams = useSearchParams();
  const reduceMotion = useReducedMotion();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [sourceType, setSourceType] = useState("");
  // Pre-filter by scam category when arriving from a Dashboard emerging-trend row
  // (?category=…, App Flow §9). Applied server-side via the /reports category param.
  const [category, setCategory] = useState(searchParams.get("category") ?? "");
  // Pre-filter by city when arriving from the Geospatial priority view (?city=…, Module 6).
  const [city, setCity] = useState(searchParams.get("city") ?? "");
  const [hasMore, setHasMore] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (status) params.set("status", status);
      if (sourceType) params.set("source_type", sourceType);
      if (category) params.set("category", category);
      if (city) params.set("city", city);
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(page * PAGE_SIZE));
      const data = await api.get<Report[]>(`/reports?${params.toString()}`);
      setReports(data);
      setHasMore(data.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load reports.");
    } finally {
      setLoading(false);
    }
  }, [search, status, sourceType, category, city, page]);

  useEffect(() => {
    load();
  }, [load]);

  async function downloadPdf(id: string) {
    try {
      await api.download(`/reports/${id}/pdf`, `truvia-report-${id.slice(0, 8)}.pdf`);
    } catch {
      setError("Could not download PDF.");
    }
  }

  async function exportCsv() {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    if (sourceType) params.set("source_type", sourceType);
    if (category) params.set("category", category);
    if (city) params.set("city", city);
    try {
      await api.download(`/reports/export?${params.toString()}`, "truvia-complaints-export.csv");
    } catch {
      setError("Could not export CSV.");
    }
  }

  return (
    <div className="relative p-gutter flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-background">
      {/* Ambient void backdrop */}
      <div className="pointer-events-none absolute inset-0 -z-10 opacity-60 grid-overlay" />

      {/* Header */}
      <section className="flex flex-wrap items-end justify-between gap-stack-md mb-stack-md">
        <div className="space-y-1.5">
          <p className="text-label-sm uppercase tracking-widest text-secondary-container/80">
            Registry / Intelligence
          </p>
          <h1 className="font-heading text-headline-lg md:text-display-lg text-on-surface leading-none">
            Reports Registry
          </h1>
          <p className="font-body-md text-on-surface-variant">
            Archive of investigation documents and citizen threat assessments.
          </p>
        </div>
        <div className="flex items-center gap-stack-sm">
          <button
            onClick={exportCsv}
            className="h-10 px-stack-md rounded-xl flex items-center gap-2 text-label-md font-medium uppercase text-on-surface-variant border border-white/10 hover:bg-white/5 hover:text-on-surface transition-all"
            title="Export current filtered view as CSV"
          >
            <Icon name="download" className="text-[18px]" />
            Export CSV
          </button>
          <button
            onClick={load}
            className="btn-bloom h-10 px-stack-md rounded-xl flex items-center gap-2 text-label-md font-bold uppercase text-on-primary"
            title="Refresh the current view"
          >
            <Icon name="sync" className="text-[18px]" />
            Sync Data
          </button>
        </div>
      </section>

      {/* Search + status filter pills */}
      <section className="mb-stack-md">
        <div className="glass-panel rounded-3xl p-stack-md flex flex-col gap-stack-md">
          <div className="flex flex-col md:flex-row gap-stack-md md:items-center">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Icon
                name="search"
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[20px] text-on-surface-variant"
              />
              <input
                className="input-glass w-full h-11 rounded-xl pl-11 pr-4 text-body-md text-on-surface placeholder:text-outline/50 outline-none"
                placeholder="Search by message text, keywords…"
                value={search}
                onChange={(e) => {
                  setPage(0);
                  setSearch(e.target.value);
                }}
              />
            </div>
            {/* Source type glass select */}
            <div className="relative min-w-[180px]">
              <select
                value={sourceType}
                onChange={(e) => {
                  setPage(0);
                  setSourceType(e.target.value);
                }}
                className="input-glass w-full h-11 rounded-xl pl-4 pr-9 text-body-md text-on-surface capitalize appearance-none outline-none cursor-pointer"
              >
                {SOURCE_TYPES.map((s) => (
                  <option key={s} value={s} className="bg-surface-container text-on-surface">
                    {s === "" ? "All Types" : s}
                  </option>
                ))}
              </select>
              <Icon
                name="expand_more"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[20px] text-on-surface-variant pointer-events-none"
              />
            </div>
          </div>

          {/* Status pills */}
          <div className="flex flex-wrap items-center gap-2">
            {STATUSES.map((s) => {
              const active = status === s;
              return (
                <button
                  key={s || "all"}
                  onClick={() => {
                    setPage(0);
                    setStatus(s);
                  }}
                  className={`rounded-full px-4 py-1.5 text-label-md capitalize transition-all ${
                    active
                      ? "bg-primary/15 text-primary border border-primary/30"
                      : "bg-white/5 text-on-surface-variant border border-white/10 hover:text-on-surface"
                  }`}
                >
                  {s === "" ? "All Status" : s}
                </button>
              );
            })}
          </div>

          {/* Contextual filter chips (category / city) */}
          {(category || city) && (
            <div className="flex flex-wrap items-center gap-stack-sm pt-1">
              {category && (
                <span className="inline-flex items-center gap-1.5 pl-3 pr-1.5 py-1 rounded-full bg-primary/15 text-primary text-label-md capitalize border border-primary/30">
                  {category}
                  <button
                    onClick={() => {
                      setPage(0);
                      setCategory("");
                    }}
                    className="p-0.5 rounded-full hover:bg-primary/20 transition-colors"
                    title="Clear category filter"
                    aria-label="Clear category filter"
                  >
                    <Icon name="close" className="text-[14px]" />
                  </button>
                </span>
              )}
              {city && (
                <span className="inline-flex items-center gap-1.5 pl-3 pr-1.5 py-1 rounded-full bg-secondary-container/15 text-secondary-container text-label-md border border-secondary-container/30">
                  {city}
                  <button
                    onClick={() => {
                      setPage(0);
                      setCity("");
                    }}
                    className="p-0.5 rounded-full hover:bg-secondary-container/20 transition-colors"
                    title="Clear city filter"
                    aria-label="Clear city filter"
                  >
                    <Icon name="close" className="text-[14px]" />
                  </button>
                </span>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Table */}
      <section className="flex-1 overflow-hidden">
        <div className="glass-panel rounded-3xl h-full flex flex-col overflow-hidden">
          <div className="overflow-auto custom-scrollbar flex-1">
            {loading ? (
              <PageLoader />
            ) : error ? (
              <div className="p-6 text-error font-body-md">{error}</div>
            ) : (
              <table className="w-full border-collapse text-left">
                <thead className="sticky top-0 z-10 bg-surface-container/80 backdrop-blur-xl">
                  <tr className="border-b border-white/5">
                    {["ID", "Incident Title", "Type", "Status", "Date", "Threat", "Action"].map((h) => (
                      <th
                        key={h}
                        className={`px-stack-md py-4 text-label-sm uppercase tracking-widest text-on-surface-variant whitespace-nowrap ${
                          h === "Action" ? "text-right" : ""
                        }`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {reports.map((r, i) => {
                    const sev = r.threat_scores?.[0]?.severity_band;
                    const subtitle = r.cleaned_text?.trim().replace(/\s+/g, " ");
                    return (
                      <motion.tr
                        key={r.id}
                        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={
                          reduceMotion
                            ? { duration: 0 }
                            : { duration: 0.4, delay: Math.min(i * 0.04, 0.4), ease: [0.16, 1, 0.3, 1] }
                        }
                        className="border-b border-white/5 hover:bg-white/[0.03] transition-colors"
                      >
                        {/* ID */}
                        <td className="px-stack-md py-4 align-top">
                          <span className="font-heading text-body-sm text-secondary-container">
                            {shortId(r.id)}
                          </span>
                        </td>
                        {/* Two-line title */}
                        <td className="px-stack-md py-4 align-top max-w-[320px]">
                          <div className="flex flex-col">
                            <span className="text-body-md font-medium text-on-surface truncate">
                              {reportTitle(r)}
                            </span>
                            {subtitle && (
                              <span className="text-label-md text-outline truncate">{subtitle}</span>
                            )}
                          </div>
                        </td>
                        {/* Source type + icon */}
                        <td className="px-stack-md py-4 align-top">
                          <span className="inline-flex items-center gap-2 text-on-surface-variant">
                            <Icon name={sourceIcon(r.source_type)} className="text-[20px]" />
                            <span className="text-label-md uppercase tracking-tight">{r.source_type}</span>
                          </span>
                        </td>
                        {/* Status chip */}
                        <td className="px-stack-md py-4 align-top">
                          <span
                            className={`inline-flex items-center px-3 py-1 rounded-lg text-label-sm uppercase ${statusBadge(
                              r.status
                            )}`}
                          >
                            {r.status}
                          </span>
                        </td>
                        {/* Date */}
                        <td className="px-stack-md py-4 align-top text-label-md text-on-surface-variant tabular-nums whitespace-nowrap">
                          {formatDateTime(r.created_at)}
                        </td>
                        {/* Threat dot + label */}
                        <td className="px-stack-md py-4 align-top">
                          <span className="inline-flex items-center gap-2">
                            <span
                              className="w-2 h-2 rounded-full"
                              style={{
                                backgroundColor: severityStroke(sev),
                                boxShadow: `0 0 8px ${severityStroke(sev)}`,
                              }}
                            />
                            <span className={`text-label-md font-medium capitalize ${severityText(sev)}`}>
                              {sev ?? "—"}
                            </span>
                          </span>
                        </td>
                        {/* Action: PDF download */}
                        <td className="px-stack-md py-4 align-top text-right whitespace-nowrap">
                          <button
                            onClick={() => downloadPdf(r.id)}
                            className="p-2 rounded-lg text-on-surface-variant border border-white/10 hover:bg-white/10 hover:text-primary transition-colors"
                            title="Export PDF"
                          >
                            <Icon name="picture_as_pdf" className="text-[18px]" />
                          </button>
                        </td>
                      </motion.tr>
                    );
                  })}
                  {reports.length === 0 && (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-on-surface-variant font-body-md">
                        No reports match your filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          <div className="px-gutter py-4 border-t border-white/5 bg-surface-container-low/40 flex items-center justify-between">
            <span className="text-label-md text-on-surface-variant">
              Page <span className="text-on-surface font-bold tabular-nums">{page + 1}</span>
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-2 rounded-lg border border-white/10 text-on-surface hover:bg-white/10 transition-colors disabled:opacity-20 disabled:hover:bg-transparent"
                aria-label="Previous page"
              >
                <Icon name="chevron_left" />
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
                className="p-2 rounded-lg border border-white/10 text-on-surface hover:bg-white/10 transition-colors disabled:opacity-20 disabled:hover:bg-transparent"
                aria-label="Next page"
              >
                <Icon name="chevron_right" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <ReportsInner />
    </Suspense>
  );
}
