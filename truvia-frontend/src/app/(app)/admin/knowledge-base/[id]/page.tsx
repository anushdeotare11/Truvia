"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { KbDocument } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

function statusPill(s: string) {
  if (s === "indexed") return "bg-primary/10 text-primary border border-primary/20";
  if (s === "failed") return "bg-error/10 text-error border border-error/20";
  return "bg-warning/10 text-warning border border-warning/20";
}

export default function KbDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = String(params.id);
  const [doc, setDoc] = useState<KbDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ msg: string; kind: "ok" | "err" } | null>(null);
  const notify = (msg: string, kind: "ok" | "err") => { setToast({ msg, kind }); setTimeout(() => setToast(null), 4000); };

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setDoc(await api.get<KbDocument>(`/admin/knowledge-base/${id}`)); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Failed to load document."); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const reindex = async () => {
    setBusy(true);
    try { await api.post(`/admin/knowledge-base/${id}/reindex`, {}); notify("Document re-indexed", "ok"); load(); }
    catch (e) { notify(e instanceof ApiError ? e.message : "Re-index failed", "err"); }
    finally { setBusy(false); }
  };
  const remove = async () => {
    if (!doc || !confirm(`Remove this document from the knowledge base? The AI Assistant will no longer cite it.`)) return;
    try { await api.delete(`/admin/knowledge-base/${id}`); router.push("/admin/knowledge-base"); }
    catch (e) { notify(e instanceof ApiError ? e.message : "Remove failed", "err"); }
  };

  if (loading) return <PageLoader />;
  if (error || !doc) {
    return <div className="p-stack-lg"><div className="card-obsidian p-stack-lg border-l-4 border-l-error flex items-center justify-between">
      <p className="text-body-md text-on-surface-variant">{error || "Document not found."}</p>
      <button onClick={load} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm">Retry</button>
    </div></div>;
  }

  return (
    <div className="p-stack-lg flex flex-col gap-stack-lg">
      {toast && <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium ${toast.kind === "ok" ? "bg-primary/10 text-primary border-primary/30" : "bg-error/10 text-error border-error/30"}`}>{toast.msg}</div>}

      <div className="flex items-center justify-between flex-wrap gap-stack-md">
        <div className="flex items-center gap-stack-md">
          <button onClick={() => router.push("/admin/knowledge-base")} className="text-outline hover:text-on-surface"><Icon name="arrow_back" /></button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-headline-md text-on-surface">{doc.title}</h1>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${statusPill(doc.status)}`}>{doc.status}</span>
            </div>
            <p className="text-body-md text-on-surface-variant">{doc.source}{doc.source_url ? ` · ${doc.source_url}` : ""}</p>
          </div>
        </div>
        <div className="flex items-center gap-stack-sm">
          <button onClick={reindex} disabled={busy} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-container border border-outline-variant/40 font-bold text-sm text-on-surface disabled:opacity-50">
            {busy ? <Icon name="progress_activity" className="animate-spin text-[18px]" /> : <Icon name="refresh" className="text-[18px]" />} Re-index
          </button>
          <button onClick={remove} className="flex items-center gap-2 px-4 py-2 rounded-xl border border-error/30 text-error font-bold text-sm"><Icon name="delete" className="text-[18px]" /> Remove</button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-stack-md">
        <Cell label="Chunks" value={String(doc.chunk_count)} />
        <Cell label="Times cited in chat" value={String(doc.times_cited)} />
        <Cell label="Version" value={String(doc.version)} />
        <Cell label="Ingested" value={formatDateTime(doc.ingested_at || undefined)} />
      </div>

      <div className="card-obsidian p-stack-lg">
        <h3 className="text-[11px] font-bold text-outline uppercase tracking-[0.2em] mb-stack-md">Raw Content</h3>
        <pre className="whitespace-pre-wrap text-body-md text-on-surface-variant font-mono text-[12px] leading-relaxed max-h-[480px] overflow-y-auto custom-scrollbar">{doc.content}</pre>
      </div>
    </div>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return <div className="card-obsidian p-stack-md text-center"><p className="text-[9px] font-bold text-outline uppercase">{label}</p><p className="text-xl font-bold text-on-surface mt-1">{value}</p></div>;
}
