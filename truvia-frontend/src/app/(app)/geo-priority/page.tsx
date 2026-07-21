"use client";

/**
 * Module 6: Geospatial Crime Pattern Intelligence — functional wiring (Spec §7).
 *
 * A ranked city priority table (map is explicitly optional and not built here).
 * Reuses the Complaint Table's table styling + filter pattern and the existing
 * ?city= drill-through into /reports. No layout/visual polish per §2.
 */
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { GeoPriorityRow } from "@/lib/types";

// Leaflet touches `window`, so the map is client-only (no SSR).
const GeoMap = dynamic(() => import("@/components/GeoMap"), {
  ssr: false,
  loading: () => <PageLoader />,
});

const DAYS_OPTIONS = [7, 14, 30, 60, 90];

function trendMeta(trend: string): { icon: string; cls: string } {
  if (trend === "rising") return { icon: "trending_up", cls: "text-error" };
  if (trend === "falling") return { icon: "trending_down", cls: "text-secondary" };
  return { icon: "trending_flat", cls: "text-on-surface-variant" };
}

export default function GeoPriorityPage() {
  const router = useRouter();
  const [rows, setRows] = useState<GeoPriorityRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [category, setCategory] = useState("");
  const [view, setView] = useState<"table" | "map">("table");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("days", String(days));
      if (category) params.set("category", category);
      const data = await api.get<GeoPriorityRow[]>(`/geo/priority?${params.toString()}`);
      setRows(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load geographic priority data.");
    } finally {
      setLoading(false);
    }
  }, [days, category]);

  useEffect(() => {
    load();
  }, [load]);

  function drillThrough(city: string) {
    // Reuse the existing Complaint Table ?city= filter (cross-module navigation).
    router.push(`/reports?city=${encodeURIComponent(city)}`);
  }

  return (
    <div className="p-gutter flex flex-col h-[calc(100vh-64px)] overflow-hidden">
      <section className="flex flex-wrap items-end justify-between gap-stack-md mb-stack-md">
        <div>
          <h1 className="font-headline-md text-on-surface">Geographic Priority</h1>
          <p className="font-body-md text-on-surface-variant">
            Cities ranked by recent, severity-weighted fraud activity — where to point patrol and
            investigation resources. Click a city to see its complaints.
          </p>
        </div>
        <div className="flex items-end gap-gutter">
          <div className="flex flex-col gap-1.5">
            <label className="font-label-md text-on-surface-variant/70 uppercase">Window</label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-surface-container-high border-outline-variant/30 text-on-surface rounded-lg text-body-md focus:ring-1 focus:ring-primary h-10 px-stack-md"
            >
              {DAYS_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  Last {d} days
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5 min-w-[200px]">
            <label className="font-label-md text-on-surface-variant/70 uppercase">Category</label>
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="All categories"
              className="bg-surface-container-high border border-outline-variant/30 text-on-surface rounded-lg text-body-md focus:ring-1 focus:ring-primary h-10 px-stack-md outline-none"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="font-label-md text-on-surface-variant/70 uppercase">View</label>
            <div className="flex h-10 rounded-lg overflow-hidden border border-outline-variant/30 bg-surface-container-high">
              <button
                type="button"
                onClick={() => setView("table")}
                className={`flex items-center gap-1.5 px-stack-md font-label-md text-body-sm transition-colors ${
                  view === "table" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-highest"
                }`}
              >
                <Icon name="table_rows" className="text-[18px]" />
                Table
              </button>
              <button
                type="button"
                onClick={() => setView("map")}
                className={`flex items-center gap-1.5 px-stack-md font-label-md text-body-sm transition-colors ${
                  view === "map" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-highest"
                }`}
              >
                <Icon name="map" className="text-[18px]" />
                Map
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="flex-1 overflow-hidden">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl h-full flex flex-col overflow-hidden">
          <div className="overflow-auto custom-scrollbar flex-1">
            {loading ? (
              <PageLoader />
            ) : error ? (
              <div className="p-6 text-error font-body-md">{error}</div>
            ) : view === "map" ? (
              <div className="h-full w-full p-3">
                <GeoMap rows={rows} onCityClick={drillThrough} />
              </div>
            ) : (
              <table className="w-full border-collapse">
                <thead className="sticky top-0 bg-surface-container-high z-10">
                  <tr className="text-left border-b border-outline-variant">
                    {["Rank", "City", "Priority Score", "Trend", "Dominant Category", "Complaints"].map((h) => (
                      <th
                        key={h}
                        className="px-stack-md py-4 font-label-md text-on-surface-variant/60 uppercase whitespace-nowrap"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/30">
                  {rows.map((r, i) => {
                    const tm = trendMeta(r.trend);
                    return (
                      <tr
                        key={r.city}
                        onClick={() => drillThrough(r.city)}
                        className="hover:bg-surface-container-high/40 transition-colors cursor-pointer"
                        title={`View complaints in ${r.city}`}
                      >
                        <td className="px-stack-md py-4 font-mono text-body-sm text-on-surface-variant">{i + 1}</td>
                        <td className="px-stack-md py-4 font-semibold text-body-md text-primary">{r.city}</td>
                        <td className="px-stack-md py-4">
                          <div className="flex items-center gap-stack-sm">
                            {/* basic bar-style intensity indicator */}
                            <div className="w-28 h-2 bg-surface-container-high rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full"
                                style={{ width: `${r.priority_score}%` }}
                              />
                            </div>
                            <span className="font-headline-sm text-on-surface text-[14px]">{r.priority_score}</span>
                          </div>
                        </td>
                        <td className="px-stack-md py-4">
                          <span className={`inline-flex items-center gap-1 font-label-md uppercase text-[11px] ${tm.cls}`}>
                            <Icon name={tm.icon} className="text-[18px]" />
                            {r.trend}
                          </span>
                        </td>
                        <td className="px-stack-md py-4 text-body-sm text-on-surface-variant">
                          {r.dominant_category || "—"}
                        </td>
                        <td className="px-stack-md py-4 text-body-sm text-on-surface">{r.complaint_count}</td>
                      </tr>
                    );
                  })}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-on-surface-variant font-body-md">
                        No complaint activity in this window.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
