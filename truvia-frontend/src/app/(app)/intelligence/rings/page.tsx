"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { RingSummary } from "@/lib/types";
import { severityBadge, formatDate } from "@/lib/format";

type SortKey = "risk" | "size" | "recency";

export default function FraudRingsPage() {
  const router = useRouter();
  const reduce = useReducedMotion();
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

  // ─── Motion variants (respect reduced-motion) ───
  const container: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduce ? 0 : 0.06, delayChildren: reduce ? 0 : 0.04 } },
  };
  const item: Variants = {
    hidden: { opacity: 0, y: reduce ? 0 : 18 },
    show: { opacity: 1, y: 0, transition: { duration: reduce ? 0 : 0.45, ease: [0.16, 1, 0.3, 1] } },
  };
  const hoverLift = reduce ? undefined : { y: -4 };

  return (
    <div className="relative min-h-screen bg-background p-margin-page">
      {/* ── Header ── */}
      <motion.header
        initial={{ opacity: 0, y: reduce ? 0 : -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduce ? 0 : 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="flex items-start justify-between flex-wrap gap-stack-md mb-stack-lg"
      >
        <div className="flex items-start gap-stack-md min-w-0">
          <div className="w-12 h-12 bg-error/10 rounded-2xl flex items-center justify-center border border-error/20 shrink-0">
            <Icon name="groups" className="text-error text-[26px]" />
          </div>
          <div className="min-w-0">
            {/* Breadcrumb */}
            <nav className="flex items-center gap-1.5 font-sans text-[11px] uppercase tracking-[0.18em] text-outline mb-1.5">
              <Link href="/intelligence/graph" className="hover:text-on-surface-variant transition-colors">Intelligence</Link>
              <span className="text-outline-variant">/</span>
              <span className="text-on-surface-variant">Fraud Rings</span>
            </nav>
            <h1 className="font-heading text-headline-lg text-on-surface">Detected Fraud Rings</h1>
            <p className="font-sans text-body-md text-on-surface-variant mt-1">
              Clusters of correlated entities flagged by community detection.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-stack-md flex-wrap">
          {/* Back to graph */}
          <Link
            href="/intelligence/graph"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 font-semibold text-sm text-on-surface hover:bg-white/10 hover:border-secondary-container/40 transition-colors"
          >
            <Icon name="hub" className="text-secondary-container text-[20px]" /> Intelligence Graph
          </Link>

          {/* Sort toggle */}
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
      </motion.header>

      {/* ── Content ── */}
      {loading ? (
        <PageLoader />
      ) : error ? (
        <div className="obsidian-panel electric-edge p-stack-lg flex items-center justify-between flex-wrap gap-stack-md">
          <div className="flex items-center gap-stack-md">
            <Icon name="error" className="text-error text-[28px]" />
            <p className="font-sans text-body-md text-on-surface-variant">{error}</p>
          </div>
          <button
            onClick={() => load(sort)}
            className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20 transition-colors"
          >
            Retry
          </button>
        </div>
      ) : !rings || rings.length === 0 ? (
        <div className="obsidian-panel p-stack-lg flex flex-col items-center text-center py-16">
          <Icon name="hub" className="text-outline text-[48px] mb-3" />
          <h3 className="font-heading text-headline-sm text-on-surface mb-1">No fraud rings have been detected yet</h3>
          <p className="font-sans text-body-md text-on-surface-variant max-w-md">
            Rings appear here once enough correlated reports accumulate for the clustering job to detect a community.
          </p>
        </div>
      ) : (
        <motion.div
          key={sort}
          variants={container}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-stack-md"
        >
          {rings.map((r) => {
            const hot = ["critical", "high"].includes((r.risk_tier || "").toLowerCase());
            return (
              <motion.button
                key={r.id}
                variants={item}
                whileHover={hoverLift}
                onClick={() => router.push(`/intelligence/rings/${r.id}`)}
                className={`glass-panel p-stack-lg text-left transition-colors hover:border-secondary-container/40 ${hot ? "electric-edge" : ""}`}
              >
                <div className="flex items-center justify-between gap-3 mb-stack-md">
                  <span className="font-mono text-[12px] text-on-surface-variant truncate">{r.id}</span>
                  <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider shrink-0 ${severityBadge(r.risk_tier)}`}>
                    {r.risk_tier}
                  </span>
                </div>

                <p className="font-heading text-headline-sm text-on-surface mb-stack-md truncate">
                  {r.dominant_category || "Uncategorized ring"}
                </p>

                <div className="grid grid-cols-3 gap-2 mb-stack-md">
                  <StatTile label="Entities" value={r.member_count} />
                  <StatTile label="Complaints" value={r.complaint_count} />
                  <StatTile label="Risk" value={Math.round(r.aggregate_risk_score)} />
                </div>

                <div className="flex items-center justify-between font-sans text-[11px] text-on-surface-variant/70 tabular-nums">
                  <span>First: {formatDate(r.first_activity_at || undefined)}</span>
                  <span>Last: {formatDate(r.last_activity_at || undefined)}</span>
                </div>
              </motion.button>
            );
          })}
        </motion.div>
      )}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-2 bg-white/5 border border-white/10 rounded-xl text-center">
      <p className="font-sans text-[9px] font-bold text-outline uppercase tracking-wider">{label}</p>
      <p className="font-heading text-lg font-bold text-on-surface tabular-nums">{value}</p>
    </div>
  );
}
