"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { CaseSummary } from "@/lib/types";
import { statusBadge, severityBadge, formatDate } from "@/lib/format";

type View = "table" | "kanban";

// Map real case.status values into the three Kanban columns (§6.4).
const COLUMNS: { key: string; label: string; statuses: string[] }[] = [
  { key: "new", label: "New", statuses: ["open", "new"] },
  { key: "in_progress", label: "In Progress", statuses: ["under_investigation", "in_review", "assigned"] },
  { key: "resolved", label: "Resolved", statuses: ["closed", "resolved"] },
];

function columnForStatus(status: string): string {
  const s = (status || "").toLowerCase();
  const col = COLUMNS.find((c) => c.statuses.includes(s));
  return col ? col.key : "new";
}

export default function MyCasesPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("table");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<CaseSummary[]>("/cases?mine=true");
      setCases(data);
    } catch {
      setError("Failed to load your assigned cases.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <PageLoader />;

  return (
    <div className="p-gutter space-y-gutter">
      <div className="flex flex-wrap items-end justify-between gap-stack-md">
        <div>
          <h1 className="font-headline-md text-on-surface">My Assigned Cases</h1>
          <p className="font-body-md text-on-surface-variant">
            Investigations currently assigned to you.
          </p>
        </div>
        <div className="flex items-center gap-1 bg-surface-container-high rounded-lg p-1">
          <button
            onClick={() => setView("table")}
            className={`px-stack-md py-2 rounded-md font-label-md text-[11px] uppercase flex items-center gap-2 transition-colors ${
              view === "table" ? "bg-primary-container text-white" : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            <Icon name="table_rows" className="text-[16px]" />
            Table
          </button>
          <button
            onClick={() => setView("kanban")}
            className={`px-stack-md py-2 rounded-md font-label-md text-[11px] uppercase flex items-center gap-2 transition-colors ${
              view === "kanban" ? "bg-primary-container text-white" : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            <Icon name="view_kanban" className="text-[16px]" />
            Kanban
          </button>
        </div>
      </div>

      {error && <div className="text-error font-body-md">{error}</div>}

      {cases.length === 0 ? (
        <div className="bento-card p-card-padding text-center py-stack-lg space-y-stack-md">
          <Icon name="assignment_turned_in" className="text-outline text-5xl" />
          <p className="font-body-md text-on-surface-variant">You have no assigned cases yet.</p>
          <Link
            href="/investigations"
            className="inline-flex items-center gap-2 px-stack-md py-2 bg-primary-container text-white rounded-lg font-label-md uppercase text-[11px]"
          >
            <Icon name="manage_search" className="text-[16px]" />
            Browse all complaints
          </Link>
        </div>
      ) : view === "table" ? (
        <div className="bento-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-low/30 border-b border-outline-variant">
                  {["Case", "Type", "Priority", "Status", "Summary", "Opened"].map((h) => (
                    <th key={h} className="p-4 font-label-md text-[11px] text-on-surface-variant uppercase">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="font-body-md text-on-surface">
                {cases.map((c) => (
                  <tr key={c.id} className="border-b border-outline-variant/30 hover:bg-surface-container-high transition-colors">
                    <td className="p-4">
                      <Link href={`/investigations/${c.id}`} className="font-mono text-primary font-bold hover:underline">
                        {c.case_number}
                      </Link>
                    </td>
                    <td className="p-4 text-[12px] text-on-surface-variant capitalize">
                      {c.case_type?.replace(/_/g, " ")}
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${severityBadge(c.priority)}`}>
                        {c.priority}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${statusBadge(c.status)}`}>
                        {c.status?.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="p-4 max-w-[320px] truncate text-[13px] text-on-surface-variant">
                      {c.ai_summary || "—"}
                    </td>
                    <td className="p-4 text-[12px] text-on-surface-variant">{formatDate(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
          {COLUMNS.map((col) => {
            const items = cases.filter((c) => columnForStatus(c.status) === col.key);
            return (
              <div key={col.key} className="bento-card p-card-padding">
                <div className="flex items-center justify-between mb-stack-md">
                  <h3 className="font-label-md text-on-surface uppercase text-[12px] tracking-wider">{col.label}</h3>
                  <span className="bg-surface-container-high text-on-surface-variant px-2 py-0.5 rounded-full text-[11px] font-bold">
                    {items.length}
                  </span>
                </div>
                <div className="space-y-stack-sm min-h-[80px]">
                  {items.map((c) => (
                    <Link
                      key={c.id}
                      href={`/investigations/${c.id}`}
                      className="block p-stack-sm bg-surface-container-high rounded-lg border border-outline-variant/40 hover:border-primary/40 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-[11px] text-primary font-bold">{c.case_number}</span>
                        <span className={`px-1.5 rounded text-[9px] font-bold uppercase ${severityBadge(c.priority)}`}>
                          {c.priority}
                        </span>
                      </div>
                      <p className="text-[12px] text-on-surface-variant line-clamp-2">{c.ai_summary || "—"}</p>
                    </Link>
                  ))}
                  {items.length === 0 && (
                    <p className="text-[11px] text-on-surface-variant/50 italic">No cases</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
