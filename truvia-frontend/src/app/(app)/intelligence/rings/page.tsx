"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { RingSummary } from "@/lib/types";
import { severityBadge, formatDate } from "@/lib/format";

type SortKey = "risk" | "size" | "recency";

export default function FraudRingsPage() {
  const router = useRouter();
  const [rings, setRings] = useState<RingSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("risk");

  const load = useCallback(async (s: SortKey) => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get<RingSummary[]>("/graph/rings", { params: { sort: s, limit: "100" } });
      setRings(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load fraud rings.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(sort); }, [load, sort]);

  return (
    <div className="p-stack-lg">
      <div className="flex items-center justify-between mb-stack-lg flex-wrap gap-stack-md">
        <div className="flex items-center gap-stack-md">
          <div className="w-12 h-12 bg-error/10 rounded-2xl flex items-center justify-center border border-error/20">
            <Icon name="groups" className="text-error text-[26px]" />
          </div>
          <div>
            <h1 className="font-headline-md text-on-surface">Detected Fraud Rings</h1>
            <p className="text-body-md text-on-surface-variant">Clusters of correlated entities flagged by community detection.</p>
          </div>
        </div>
        <div className="flex items-center gap-1 bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl p-1">
          {(["risk", "size", "recency"] as SortKey[]).map((s) => (
            <button
              key={s}
              onClick={() => setSort(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide transition-colors ${sort === s ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-on-surface"}`}
            >
              {s === "risk" ? "Risk" : s === "size" ? "Size" : "Recency"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <PageLoader />
      ) : error ? (
        <div className="card-obsidian p-stack-lg border-l-4 border-l-error flex items-center justify-between">
          <p className="text-body-md text-on-surface-variant">{error}</p>
          <button onClick={() => load(sort)} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20">Retry</button>
        </div>
      ) : !rings || rings.length === 0 ? (
        <div className="card-obsidian p-stack-lg flex flex-col items-center text-center py-16">
          <Icon name="hub" className="text-outline text-[48px] mb-3" />
          <h3 className="font-headline-sm text-on-surface mb-1">No fraud rings have been detected yet</h3>
          <p className="text-body-md text-on-surface-variant max-w-md">Rings appear here once enough correlated reports accumulate for the clustering job to detect a community.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-stack-md">
          {rings.map((r) => (
            <button
              key={r.id}
              onClick={() => router.push(`/intelligence/rings/${r.id}`)}
              className="card-obsidian p-stack-lg text-left hover:border-primary/40 transition-colors border border-outline-variant/30"
            >
              <div className="flex items-center justify-between mb-stack-md">
                <span className="font-mono text-[12px] text-on-surface-variant">{r.id}</span>
                <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase ${severityBadge(r.risk_tier)}`}>{r.risk_tier}</span>
              </div>
              <p className="font-headline-sm text-on-surface mb-stack-md">{r.dominant_category || "Uncategorized ring"}</p>
              <div className="grid grid-cols-3 gap-2 mb-stack-md">
                <Cell label="Entities" value={r.member_count} />
                <Cell label="Complaints" value={r.complaint_count} />
                <Cell label="Risk" value={Math.round(r.aggregate_risk_score)} />
              </div>
              <div className="flex items-center justify-between text-[11px] text-on-surface-variant">
                <span>First: {formatDate(r.first_activity_at || undefined)}</span>
                <span>Last: {formatDate(r.last_activity_at || undefined)}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Cell({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-2 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-xl text-center">
      <p className="text-[9px] font-bold text-outline uppercase">{label}</p>
      <p className="text-lg font-bold text-on-surface">{value}</p>
    </div>
  );
}
