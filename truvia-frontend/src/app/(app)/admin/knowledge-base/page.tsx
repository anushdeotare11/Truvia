"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { KbDocument } from "@/lib/types";
import { formatDate } from "@/lib/format";

const INPUT = "w-full bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 text-body-md text-on-surface outline-none";
const SOURCES = ["RBI", "MHA", "NCRP", "CERT-In", "NPCI", "custom"];

function statusPill(s: string) {
  if (s === "indexed") return "bg-primary/10 text-primary border border-primary/20";
  if (s === "failed") return "bg-error/10 text-error border border-error/20";
  return "bg-warning/10 text-warning border border-warning/20"; // processing
}

export default function KnowledgeBasePage() {
  const router = useRouter();
  const [docs, setDocs] = useState<KbDocument[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState("");
  const [status, setStatus] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [toast, setToast] = useState<{ msg: string; kind: "ok" | "err" } | null>(null);
  const notify = (msg: string, kind: "ok" | "err") => { setToast({ msg, kind }); setTimeout(() => setToast(null), 4000); };

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params: Record<string, string> = {};
      if (source) params.source = source;
      if (status) params.status = status;
      setDocs(await api.get<KbDocument[]>("/admin/knowledge-base", { params }));
    } catch (e) { setError(e instanceof ApiError ? e.message : "Failed to load documents."); }
    finally { setLoading(false); }
  }, [source, status]);

  useEffect(() => { load(); }, [load]);

  const reindex = async (id: string) => {
    try { await api.post(`/admin/knowledge-base/${id}/reindex`, {}); notify("Document re-indexed", "ok"); load(); }
    catch (e) { notify(e instanceof ApiError ? e.message : "Re-index failed", "err"); }
  };
  const remove = async (d: KbDocument) => {
    if (!confirm(`Remove "${d.title}"? The AI Assistant will no longer cite it.`)) return;
    try { await api.delete(`/admin/knowledge-base/${d.id}`); notify("Document removed", "ok"); load(); }
    catch (e) { notify(e instanceof ApiError ? e.message : "Remove failed", "err"); }
  };

  return (
    <div className="p-stack-lg">
      {toast && <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium ${toast.kind === "ok" ? "bg-primary/10 text-primary border-primary/30" : "bg-error/10 text-error border-error/30"}`}>{toast.msg}</div>}

      <div className="flex items-center justify-between mb-stack-lg flex-wrap gap-stack-md">
        <div className="flex items-center gap-stack-md">
          <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20"><Icon name="menu_book" className="text-primary text-[26px]" /></div>
          <div>
            <h1 className="font-headline-md text-on-surface">Knowledge Base</h1>
            <p className="text-body-md text-on-surface-variant">Regulatory sources grounding the AI Assistant.</p>
          </div>
        </div>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-on-primary font-bold text-sm hover:opacity-90">
          <Icon name="add" className="text-[18px]" /> Add Document
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-stack-sm mb-stack-md">
        <select value={source} onChange={(e) => setSource(e.target.value)} className="bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 text-body-md text-on-surface">
          <option value="">All sources</option>
          {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 text-body-md text-on-surface">
          <option value="">All statuses</option>
          <option value="indexed">Indexed</option>
          <option value="processing">Processing</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {loading ? <PageLoader /> : error ? (
        <div className="card-obsidian p-stack-lg border-l-4 border-l-error flex items-center justify-between">
          <p className="text-body-md text-on-surface-variant">{error}</p>
          <button onClick={load} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm">Retry</button>
        </div>
      ) : !docs || docs.length === 0 ? (
        <div className="card-obsidian p-stack-lg text-center py-16">
          <Icon name="library_books" className="text-outline text-[44px] mb-3" />
          <p className="text-body-md text-on-surface-variant mb-3">No knowledge base documents yet — the AI Assistant will have limited grounding until sources are added.</p>
          <button onClick={() => setShowAdd(true)} className="px-4 py-2 rounded-xl bg-primary text-on-primary font-bold text-sm">Add Document</button>
        </div>
      ) : (
        <div className="card-obsidian overflow-hidden">
          <table className="w-full text-left">
            <thead><tr className="text-[10px] uppercase tracking-widest text-outline border-b border-outline-variant/30">
              <th className="p-3">Source</th><th className="p-3">Title</th><th className="p-3">Ingested</th><th className="p-3">Status</th><th className="p-3 text-right">Actions</th>
            </tr></thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} onClick={() => router.push(`/admin/knowledge-base/${d.id}`)} className="border-b border-outline-variant/20 hover:bg-surface-container/40 cursor-pointer transition-colors">
                  <td className="p-3"><span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase bg-primary/10 text-primary border border-primary/20">{d.source}</span></td>
                  <td className="p-3 text-on-surface font-medium">{d.title}</td>
                  <td className="p-3 text-on-surface-variant text-[12px]">{formatDate(d.ingested_at || undefined)}</td>
                  <td className="p-3"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${statusPill(d.status)}`}>{d.status}</span></td>
                  <td className="p-3 text-right" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => reindex(d.id)} title="Re-index" className="p-1.5 rounded-lg hover:bg-surface-container"><Icon name="refresh" className="text-primary" /></button>
                    <button onClick={() => remove(d)} title="Remove" className="p-1.5 rounded-lg hover:bg-surface-container"><Icon name="delete" className="text-error" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && <AddDocModal onClose={() => setShowAdd(false)} onDone={() => { setShowAdd(false); load(); }} notify={notify} />}
    </div>
  );
}

function AddDocModal({ onClose, onDone, notify }: { onClose: () => void; onDone: () => void; notify: (m: string, k: "ok" | "err") => void }) {
  const [src, setSrc] = useState("RBI");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    setErr(null); setBusy(true);
    try {
      await api.post("/admin/knowledge-base", { source: src, title, content, source_url: url || null });
      notify("Document added — indexing complete", "ok"); onDone();
    } catch (e) { setErr(e instanceof ApiError ? e.message : "Add failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="card-obsidian p-stack-lg w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-stack-md">
          <h3 className="font-headline-sm text-on-surface">Add Document</h3>
          <button onClick={onClose} className="text-outline hover:text-on-surface"><Icon name="close" /></button>
        </div>
        <div className="space-y-stack-md">
          {err && <div className="p-2 rounded-lg bg-error/10 text-error text-[12px]">{err}</div>}
          <label className="block"><span className="text-[10px] font-bold text-outline uppercase tracking-widest">Source</span>
            <select value={src} onChange={(e) => setSrc(e.target.value)} className={`${INPUT} mt-1`}>
              {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select></label>
          <label className="block"><span className="text-[10px] font-bold text-outline uppercase tracking-widest">Title</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={`${INPUT} mt-1`} /></label>
          <label className="block"><span className="text-[10px] font-bold text-outline uppercase tracking-widest">Content</span>
            <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={7} className={`${INPUT} mt-1 resize-y`} placeholder="Paste the document text to chunk, embed and index." /></label>
          <label className="block"><span className="text-[10px] font-bold text-outline uppercase tracking-widest">Source URL (optional)</span>
            <input value={url} onChange={(e) => setUrl(e.target.value)} className={`${INPUT} mt-1`} /></label>
          <button disabled={busy || !title || !content} onClick={submit} className="w-full py-2.5 rounded-xl bg-primary text-on-primary font-bold text-sm disabled:opacity-50 flex items-center justify-center gap-2">
            {busy && <Icon name="progress_activity" className="animate-spin text-[18px]" />} Add &amp; Index
          </button>
        </div>
      </div>
    </div>
  );
}
