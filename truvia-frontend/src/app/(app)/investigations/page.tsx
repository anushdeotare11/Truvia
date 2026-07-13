"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { CaseSummary } from "@/lib/types";
import { statusBadge, severityBadge, formatDate } from "@/lib/format";

export default function InvestigationsPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const data = await api.get<CaseSummary[]>("/cases");
        setCases(data);
      } catch {
        setError("Failed to load investigations.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = cases.filter(
    (c) =>
      !query ||
      c.case_number.toLowerCase().includes(query.toLowerCase()) ||
      (c.ai_summary ?? "").toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="p-gutter space-y-gutter">
      <div className="flex flex-wrap items-end justify-between gap-stack-md">
        <div>
          <h1 className="font-headline-md text-on-surface">Investigations</h1>
          <p className="font-body-md text-on-surface-variant">
            Active cyber-fraud cases and organized fraud-ring dossiers.
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Icon name="search" className="absolute left-3 top-2.5 text-on-surface-variant text-[18px]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search cases..."
            className="w-full bg-surface-container-high border border-outline-variant/30 rounded-lg pl-9 pr-3 h-10 text-body-md outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {loading ? (
        <PageLoader />
      ) : error ? (
        <div className="text-error font-body-md">{error}</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-gutter">
          {filtered.map((c) => (
            <Link
              key={c.id}
              href={`/investigations/${c.id}`}
              className="bento-card p-card-padding block group"
            >
              <div className="flex items-start justify-between mb-stack-md">
                <div className="flex items-center gap-stack-sm">
                  <div className="w-10 h-10 rounded-lg bg-primary-container/20 flex items-center justify-center">
                    <Icon name="folder_special" className="text-primary" />
                  </div>
                  <div>
                    <p className="font-mono text-body-md text-on-surface font-bold group-hover:text-primary transition-colors">
                      {c.case_number}
                    </p>
                    <p className="font-label-md text-[10px] text-on-surface-variant uppercase">
                      {c.case_type?.replace(/_/g, " ")}
                    </p>
                  </div>
                </div>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${severityBadge(
                    c.priority
                  )}`}
                >
                  {c.priority}
                </span>
              </div>
              <p className="font-body-md text-on-surface-variant text-[13px] line-clamp-3 mb-stack-md min-h-[54px]">
                {c.ai_summary || "AI summary pending..."}
              </p>
              <div className="flex items-center justify-between pt-stack-sm border-t border-outline-variant/40">
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${statusBadge(
                    c.status
                  )}`}
                >
                  {c.status?.replace(/_/g, " ")}
                </span>
                <span className="font-label-md text-[11px] text-on-surface-variant">
                  {formatDate(c.created_at)}
                </span>
              </div>
            </Link>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full text-center py-stack-lg text-on-surface-variant font-body-md">
              No investigations found.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
