"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { Report } from "@/lib/types";
import { severityBadge, statusBadge, reportTitle, formatDate, shortId } from "@/lib/format";

const PAGE_SIZE = 10;
const STATUSES = ["", "submitted", "processing", "scored", "escalated", "dismissed", "failed"];
const SOURCE_TYPES = ["", "text", "screenshot", "audio"];

function ReportsInner() {
  const searchParams = useSearchParams();
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
  }, [search, status, sourceType, category, page]);

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
    try {
      await api.download(`/reports/export?${params.toString()}`, "truvia-complaints-export.csv");
    } catch {
      setError("Could not export CSV.");
    }
  }

  return (
    <div className="p-gutter flex flex-col h-[calc(100vh-64px)] overflow-hidden">
      <section className="flex flex-wrap items-end justify-between gap-stack-md mb-stack-md">
        <div>
          <h1 className="font-headline-md text-on-surface">Intelligence Reports</h1>
          <p className="font-body-md text-on-surface-variant">
            Archive of investigation documents and citizen threat assessments.
          </p>
        </div>
        <button
          onClick={exportCsv}
          className="h-10 px-stack-md bg-primary-container text-white rounded-lg flex items-center gap-2 font-label-md font-bold uppercase hover:brightness-110 transition-all"
          title="Export current filtered view as CSV"
        >
          <Icon name="download" className="text-[18px]" />
          Export CSV
        </button>
      </section>

      {/* Filters */}
      <section className="mb-stack-md">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md flex flex-wrap items-end gap-gutter">
          <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
            <label className="font-label-md text-on-surface-variant/70 uppercase">Search</label>
            <div className="relative">
              <input
                className="bg-surface-container-high border border-outline-variant/30 text-on-surface rounded-lg text-body-md focus:ring-1 focus:ring-primary w-full h-10 pl-9 pr-3 outline-none"
                placeholder="Search message text..."
                value={search}
                onChange={(e) => {
                  setPage(0);
                  setSearch(e.target.value);
                }}
              />
              <Icon
                name="search"
                className="absolute left-2.5 top-2.5 text-[18px] text-on-surface-variant"
              />
            </div>
          </div>
          <div className="flex flex-col gap-1.5 min-w-[160px]">
            <label className="font-label-md text-on-surface-variant/70 uppercase">Status</label>
            <select
              value={status}
              onChange={(e) => {
                setPage(0);
                setStatus(e.target.value);
              }}
              className="bg-surface-container-high border-outline-variant/30 text-on-surface rounded-lg text-body-md focus:ring-1 focus:ring-primary h-10 px-stack-md capitalize"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s === "" ? "All Statuses" : s}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5 min-w-[160px]">
            <label className="font-label-md text-on-surface-variant/70 uppercase">Source Type</label>
            <select
              value={sourceType}
              onChange={(e) => {
                setPage(0);
                setSourceType(e.target.value);
              }}
              className="bg-surface-container-high border-outline-variant/30 text-on-surface rounded-lg text-body-md focus:ring-1 focus:ring-primary h-10 px-stack-md capitalize"
            >
              {SOURCE_TYPES.map((s) => (
                <option key={s} value={s}>
                  {s === "" ? "All Types" : s}
                </option>
              ))}
            </select>
          </div>
        </div>
        {category && (
          <div className="mt-stack-sm flex items-center gap-stack-sm">
            <span className="font-label-md text-on-surface-variant/70 uppercase text-[11px]">Category</span>
            <span className="inline-flex items-center gap-1.5 pl-3 pr-1.5 py-1 rounded-full bg-primary/15 text-primary text-[12px] font-bold capitalize">
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
          </div>
        )}
      </section>

      {/* Table */}
      <section className="flex-1 overflow-hidden">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl h-full flex flex-col overflow-hidden">
          <div className="overflow-auto custom-scrollbar flex-1">
            {loading ? (
              <PageLoader />
            ) : error ? (
              <div className="p-6 text-error font-body-md">{error}</div>
            ) : (
              <table className="w-full border-collapse">
                <thead className="sticky top-0 bg-surface-container-high z-10">
                  <tr className="text-left border-b border-outline-variant">
                    {["ID", "Title", "Type", "Status", "Date", "Threat", "Actions"].map((h) => (
                      <th
                        key={h}
                        className={`px-stack-md py-4 font-label-md text-on-surface-variant/60 uppercase whitespace-nowrap ${
                          h === "Actions" ? "text-right" : ""
                        }`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/30">
                  {reports.map((r) => {
                    const sev = r.threat_scores?.[0]?.severity_band;
                    return (
                      <tr key={r.id} className="hover:bg-surface-container-high/40 transition-colors">
                        <td className="px-stack-md py-4 font-mono text-body-sm text-primary">{shortId(r.id)}</td>
                        <td className="px-stack-md py-4 font-semibold text-body-md text-on-surface max-w-[280px] truncate">
                          {reportTitle(r)}
                        </td>
                        <td className="px-stack-md py-4 text-body-sm text-on-surface-variant capitalize">
                          {r.source_type}
                        </td>
                        <td className="px-stack-md py-4">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${statusBadge(
                              r.status
                            )}`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="px-stack-md py-4 text-body-sm text-on-surface-variant">
                          {formatDate(r.created_at)}
                        </td>
                        <td className="px-stack-md py-4">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase ${severityBadge(
                              sev
                            )}`}
                          >
                            {sev ?? "—"}
                          </span>
                        </td>
                        <td className="px-stack-md py-4 text-right whitespace-nowrap">
                          <button
                            onClick={() => downloadPdf(r.id)}
                            className="p-2 hover:bg-surface-container-highest rounded-lg text-on-surface-variant hover:text-primary transition-colors"
                            title="Export PDF"
                          >
                            <Icon name="picture_as_pdf" className="text-[18px]" />
                          </button>
                        </td>
                      </tr>
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
          <div className="px-gutter py-4 border-t border-outline-variant flex items-center justify-between">
            <span className="font-body-md text-on-surface-variant text-[13px]">
              Page <span className="text-on-surface font-bold">{page + 1}</span>
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-2 rounded-lg hover:bg-surface-container-highest transition-colors disabled:opacity-20 text-on-surface"
              >
                <Icon name="chevron_left" />
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
                className="p-2 rounded-lg hover:bg-surface-container-highest transition-colors disabled:opacity-20 text-on-surface"
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
