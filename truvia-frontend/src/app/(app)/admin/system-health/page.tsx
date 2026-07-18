"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { SystemHealth } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

function statusColor(s: string) {
  if (s === "healthy") return { dot: "bg-primary", text: "text-primary", bd: "border-l-primary" };
  if (s === "degraded") return { dot: "bg-warning", text: "text-warning", bd: "border-l-warning" };
  return { dot: "bg-error", text: "text-error", bd: "border-l-error" }; // down
}

export default function SystemHealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [auto, setAuto] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try { setHealth(await api.get<SystemHealth>("/admin/system-health")); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Unable to reach system health service"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (auto) { timer.current = setInterval(load, 10000); }
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [auto, load]);

  const retry = async (jobId: string) => {
    try { await api.post(`/admin/system-health/retry/${jobId}`, {}); setToast("Task requeued"); setTimeout(() => setToast(null), 4000); load(); }
    catch (e) { setToast(e instanceof ApiError ? e.message : "Requeue failed"); setTimeout(() => setToast(null), 4000); }
  };

  if (loading) return <PageLoader />;

  // The one screen where a fetch failure is itself the primary signal.
  if (error) {
    return (
      <div className="p-stack-lg">
        <div className="card-obsidian p-stack-lg border-l-4 border-l-error flex items-center justify-between">
          <div className="flex items-center gap-stack-md">
            <Icon name="cloud_off" className="text-error text-[28px]" />
            <div>
              <h3 className="font-headline-sm text-on-surface">Unable to reach system health service</h3>
              <p className="text-body-md text-on-surface-variant">{error}</p>
            </div>
          </div>
          <button onClick={load} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm">Retry</button>
        </div>
      </div>
    );
  }

  const h = health!;
  return (
    <div className="p-stack-lg flex flex-col gap-stack-lg">
      {toast && <div className="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border bg-primary/10 text-primary border-primary/30 text-sm font-medium">{toast}</div>}

      <div className="flex items-center justify-between flex-wrap gap-stack-md">
        <div className="flex items-center gap-stack-md">
          <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20"><Icon name="monitor_heart" className="text-primary text-[26px]" /></div>
          <div>
            <h1 className="font-headline-md text-on-surface">System Health</h1>
            <p className="text-body-md text-on-surface-variant">Updated {formatDateTime(h.generated_at)}</p>
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-on-surface-variant cursor-pointer">
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> Auto-refresh (10s)
          <button onClick={load} className="ml-2 p-2 rounded-lg hover:bg-surface-container"><Icon name="refresh" className="text-primary" /></button>
        </label>
      </div>

      {/* Agent cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-stack-md">
        {h.agents.map((a) => {
          const c = statusColor(a.status);
          return (
            <div key={a.key} className={`card-obsidian p-stack-lg border-l-4 ${c.bd}`}>
              <div className="flex items-center justify-between mb-stack-sm">
                <span className="text-body-md font-bold text-on-surface">{a.name}</span>
                <span className="flex items-center gap-1.5"><span className={`w-2.5 h-2.5 rounded-full ${c.dot}`} /><span className={`text-[11px] font-bold uppercase ${c.text}`}>{a.status}</span></span>
              </div>
              <p className="text-[11px] text-on-surface-variant mb-stack-md">{a.provider || "—"}</p>
              <div className="grid grid-cols-3 gap-2">
                <Mini label="Avg latency" value={a.avg_latency_ms != null ? `${a.avg_latency_ms}ms` : "—"} />
                <Mini label="Runs 1h" value={String(a.runs_last_hour)} />
                <Mini label="Errors 1h" value={String(a.errors_last_hour)} danger={a.errors_last_hour > 0} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Queue */}
      <div className="card-obsidian p-stack-lg">
        <h3 className="text-[11px] font-bold text-outline uppercase tracking-[0.2em] mb-stack-md">Task Queue</h3>
        {h.queue.available ? (
          <div className="grid grid-cols-3 gap-stack-md">
            <Cell label="Pipeline queue depth" value={String(h.queue.pipeline_queue_depth)} />
            <Cell label="In progress" value={String(h.queue.in_progress)} />
            <Cell label="Failed" value={String(h.queue.failed_count)} />
          </div>
        ) : (
          <div className="flex items-center gap-2 text-warning"><Icon name="warning" /><span className="text-body-md">{h.queue.reason || "Task queue unavailable"}</span></div>
        )}
      </div>

      {/* Failed tasks */}
      <div className="card-obsidian p-stack-lg">
        <h3 className="text-[11px] font-bold text-outline uppercase tracking-[0.2em] mb-stack-md">Recent Failed Tasks</h3>
        {h.failed_tasks.length === 0 ? (
          <p className="text-body-md text-on-surface-variant">No failed tasks in the selected window</p>
        ) : (
          <div className="space-y-1.5">
            {h.failed_tasks.map((t) => (
              <div key={t.job_id} className="flex items-center justify-between p-3 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-xl">
                <div className="min-w-0">
                  <p className="text-body-md text-on-surface font-mono text-[12px] truncate">{t.func || t.job_id}</p>
                  <p className="text-[11px] text-error truncate">{t.error || "—"}</p>
                  <p className="text-[10px] text-on-surface-variant">{formatDateTime(t.failed_at || undefined)}</p>
                </div>
                <button onClick={() => retry(t.job_id)} className="px-3 py-1.5 rounded-lg bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20 flex items-center gap-1">
                  <Icon name="replay" className="text-[16px]" /> Retry
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Mini({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return <div className="p-2 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-lg text-center"><p className="text-[8px] font-bold text-outline uppercase">{label}</p><p className={`text-sm font-bold ${danger ? "text-error" : "text-on-surface"}`}>{value}</p></div>;
}
function Cell({ label, value }: { label: string; value: string }) {
  return <div className="p-stack-md bg-surface-container-lowest/50 border border-outline-variant/30 rounded-xl text-center"><p className="text-[9px] font-bold text-outline uppercase">{label}</p><p className="text-2xl font-bold text-on-surface mt-1">{value}</p></div>;
}
