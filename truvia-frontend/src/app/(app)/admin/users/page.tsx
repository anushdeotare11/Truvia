"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { AdminUsersPage, AdminUser, InviteResult } from "@/lib/types";
import { formatDate } from "@/lib/format";

function roleBadge(role: string) {
  if (role === "admin") return "bg-error/10 text-error border border-error/20";
  if (role === "officer") return "bg-primary/10 text-primary border border-primary/20";
  return "bg-secondary/10 text-secondary border border-secondary/20";
}
function statusPill(s: string) {
  if (s === "active") return "bg-primary/10 text-primary border border-primary/20";
  if (s === "suspended") return "bg-error/10 text-error border border-error/20";
  return "bg-warning/10 text-warning border border-warning/20"; // pending_invite
}

export default function UserManagementPage() {
  const router = useRouter();
  const [data, setData] = useState<AdminUsersPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [showInvite, setShowInvite] = useState(false);
  const [toast, setToast] = useState<{ msg: string; kind: "ok" | "err" } | null>(null);
  const notify = (msg: string, kind: "ok" | "err") => { setToast({ msg, kind }); setTimeout(() => setToast(null), 5000); };

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
      if (role) params.role = role;
      if (status) params.status = status;
      if (search.trim()) params.search = search.trim();
      setData(await api.get<AdminUsersPage>("/admin/users", { params }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load users.");
    } finally { setLoading(false); }
  }, [role, status, search, page]);

  useEffect(() => { load(); }, [load]);

  const hasFilters = !!(role || status || search.trim());
  const clearFilters = () => { setRole(""); setStatus(""); setSearch(""); setPage(1); };

  const toggleSuspend = async (u: AdminUser) => {
    const suspend = u.status !== "suspended";
    if (suspend && !confirm(`Suspend ${u.name}? They will immediately lose access.`)) return;
    try {
      await api.post(`/admin/users/${u.id}/suspend`, { suspend });
      notify(suspend ? "User suspended" : "User reactivated", "ok");
      load();
    } catch (e) { notify(e instanceof ApiError ? e.message : "Action failed", "err"); }
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="p-stack-lg">
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium ${toast.kind === "ok" ? "bg-primary/10 text-primary border-primary/30" : "bg-error/10 text-error border-error/30"}`}>{toast.msg}</div>
      )}
      <div className="flex items-center justify-between mb-stack-lg flex-wrap gap-stack-md">
        <div className="flex items-center gap-stack-md">
          <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
            <Icon name="group" className="text-primary text-[26px]" />
          </div>
          <div>
            <h1 className="font-headline-md text-on-surface">User Management</h1>
            <p className="text-body-md text-on-surface-variant">Manage all platform accounts.</p>
          </div>
        </div>
        <button onClick={() => setShowInvite(true)} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-on-primary font-bold text-sm hover:opacity-90">
          <Icon name="person_add" className="text-[18px]" /> Invite Officer/Admin
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-stack-sm mb-stack-md">
        <div className="flex items-center gap-2 bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 flex-1 min-w-[220px]">
          <Icon name="search" className="text-outline text-[20px]" />
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search name or email"
            className="bg-transparent outline-none flex-1 text-body-md text-on-surface placeholder:text-outline" />
        </div>
        <select value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }}
          className="bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 text-body-md text-on-surface">
          <option value="">All roles</option>
          <option value="citizen">Citizen</option>
          <option value="officer">Officer</option>
          <option value="admin">Admin</option>
        </select>
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 text-body-md text-on-surface">
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="pending_invite">Pending invite</option>
        </select>
        {hasFilters && (
          <button onClick={clearFilters} className="px-3 py-2 rounded-xl text-sm font-bold text-on-surface-variant hover:text-on-surface">Clear filters</button>
        )}
      </div>

      {loading ? <PageLoader /> : error ? (
        <div className="card-obsidian p-stack-lg border-l-4 border-l-error flex items-center justify-between">
          <p className="text-body-md text-on-surface-variant">{error}</p>
          <button onClick={load} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm">Retry</button>
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="card-obsidian p-stack-lg text-center py-16">
          <Icon name="group_off" className="text-outline text-[44px] mb-3" />
          <p className="text-body-md text-on-surface-variant">{hasFilters ? "No users match these filters" : "No users found"}</p>
          {hasFilters && <button onClick={clearFilters} className="mt-3 px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm">Clear filters</button>}
        </div>
      ) : (
        <div className="card-obsidian overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[10px] uppercase tracking-widest text-outline border-b border-outline-variant/30">
                <th className="p-3">Name</th><th className="p-3">Email</th><th className="p-3">Role</th>
                <th className="p-3">Status</th><th className="p-3">Created</th><th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((u) => (
                <tr key={u.id} onClick={() => router.push(`/admin/users/${u.id}`)}
                  className="border-b border-outline-variant/20 hover:bg-surface-container/40 cursor-pointer transition-colors">
                  <td className="p-3 text-on-surface font-medium">{u.name}</td>
                  <td className="p-3 text-on-surface-variant font-mono text-[12px]">{u.email}</td>
                  <td className="p-3"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${roleBadge(u.role)}`}>{u.role}</span></td>
                  <td className="p-3"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${statusPill(u.status)}`}>{u.status.replace("_", " ")}</span></td>
                  <td className="p-3 text-on-surface-variant text-[12px]">{formatDate(u.created_at || undefined)}</td>
                  <td className="p-3 text-right" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => toggleSuspend(u)} title={u.status === "suspended" ? "Reactivate" : "Suspend"}
                      className="p-1.5 rounded-lg hover:bg-surface-container">
                      <Icon name={u.status === "suspended" ? "person" : "person_off"} className={u.status === "suspended" ? "text-primary" : "text-error"} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between p-3 text-[12px] text-on-surface-variant">
            <span>{data.total} users</span>
            <div className="flex items-center gap-2">
              <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="px-3 py-1 rounded-lg bg-surface-container disabled:opacity-40">Prev</button>
              <span>Page {page} / {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} className="px-3 py-1 rounded-lg bg-surface-container disabled:opacity-40">Next</button>
            </div>
          </div>
        </div>
      )}

      {showInvite && <InviteModal onClose={() => setShowInvite(false)} onDone={() => { setShowInvite(false); load(); }} notify={notify} />}
    </div>
  );
}

function InviteModal({ onClose, onDone, notify }: { onClose: () => void; onDone: () => void; notify: (m: string, k: "ok" | "err") => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("officer");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<InviteResult | null>(null);

  const submit = async () => {
    setErr(null); setBusy(true);
    try {
      const res = await api.post<InviteResult>("/admin/users/invite", { name, email, role });
      setResult(res);
      notify(`Invitation created for ${email}`, "ok");
    } catch (e) { setErr(e instanceof ApiError ? e.message : "Invite failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="card-obsidian p-stack-lg w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-stack-md">
          <h3 className="font-headline-sm text-on-surface">Invite Officer / Admin</h3>
          <button onClick={onClose} className="text-outline hover:text-on-surface"><Icon name="close" /></button>
        </div>
        {result ? (
          <div className="space-y-stack-md">
            <p className="text-body-md text-on-surface">Account created with status <span className="font-bold">pending invite</span>. No email service is configured — share this one-time setup link:</p>
            <div className="p-3 bg-surface-container-lowest/70 border border-outline-variant/30 rounded-xl break-all font-mono text-[12px] text-primary">{result.setup_url}</div>
            <p className="text-[11px] text-on-surface-variant">Expires in {result.expires_in_hours}h.</p>
            <button onClick={onDone} className="w-full py-2.5 rounded-xl bg-primary text-on-primary font-bold text-sm">Done</button>
          </div>
        ) : (
          <div className="space-y-stack-md">
            {err && <div className="p-2 rounded-lg bg-error/10 text-error text-[12px]">{err}</div>}
            <Field label="Name"><input value={name} onChange={(e) => setName(e.target.value)} className="w-full bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 text-body-md text-on-surface outline-none" /></Field>
            <Field label="Email"><input value={email} onChange={(e) => setEmail(e.target.value)} className="w-full bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 text-body-md text-on-surface outline-none" /></Field>
            <Field label="Role">
              <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 text-body-md text-on-surface outline-none">
                <option value="officer">Officer</option>
                <option value="admin">Admin</option>
              </select>
            </Field>
            <button disabled={busy || !name || !email} onClick={submit}
              className="w-full py-2.5 rounded-xl bg-primary text-on-primary font-bold text-sm disabled:opacity-50 flex items-center justify-center gap-2">
              {busy && <Icon name="progress_activity" className="animate-spin text-[18px]" />} Send Invite
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-[10px] font-bold text-outline uppercase tracking-widest">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

