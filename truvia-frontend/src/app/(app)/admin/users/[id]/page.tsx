"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PageLoader } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { AdminUserDetail, ForceResetResult } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

const INPUT = "w-full bg-surface-container-lowest/70 border border-outline-variant/40 rounded-xl px-3 py-2 text-body-md text-on-surface outline-none";

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const uid = String(params.id);

  const [u, setU] = useState<AdminUserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [reset, setReset] = useState<ForceResetResult | null>(null);
  const [toast, setToast] = useState<{ msg: string; kind: "ok" | "err" } | null>(null);
  const notify = (msg: string, kind: "ok" | "err") => { setToast({ msg, kind }); setTimeout(() => setToast(null), 5000); };

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const d = await api.get<AdminUserDetail>(`/admin/users/${uid}`);
      setU(d); setName(d.name); setRole(d.role); setPhone(d.phone || "");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Failed to load user."); }
    finally { setLoading(false); }
  }, [uid]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy(true);
    try {
      await api.patch(`/admin/users/${uid}`, { name, role, phone });
      notify("User updated", "ok"); load();
    } catch (e) { notify(e instanceof ApiError ? e.message : "Save failed", "err"); }
    finally { setBusy(false); }
  };

  const toggleSuspend = async () => {
    if (!u) return;
    const suspend = u.status !== "suspended";
    if (suspend && !confirm(`Suspend this account? They will immediately lose access.`)) return;
    try {
      await api.post(`/admin/users/${uid}/suspend`, { suspend });
      notify(suspend ? "User suspended" : "User reactivated", "ok"); load();
    } catch (e) { notify(e instanceof ApiError ? e.message : "Action failed", "err"); }
  };

  const forceReset = async () => {
    try {
      const r = await api.post<ForceResetResult>(`/admin/users/${uid}/force-password-reset`, {});
      setReset(r); notify("Password reset link generated", "ok");
    } catch (e) { notify(e instanceof ApiError ? e.message : "Reset failed", "err"); }
  };

  if (loading) return <PageLoader />;
  if (error || !u) {
    return (
      <div className="p-stack-lg"><div className="card-obsidian p-stack-lg border-l-4 border-l-error flex items-center justify-between">
        <p className="text-body-md text-on-surface-variant">{error || "User not found."}</p>
        <button onClick={load} className="px-4 py-2 rounded-xl bg-primary/10 text-primary font-bold text-sm">Retry</button>
      </div></div>
    );
  }

  return (
    <div className="p-stack-lg flex flex-col gap-stack-lg">
      {toast && <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium ${toast.kind === "ok" ? "bg-primary/10 text-primary border-primary/30" : "bg-error/10 text-error border-error/30"}`}>{toast.msg}</div>}

      <div className="flex items-center gap-stack-md">
        <button onClick={() => router.push("/admin/users")} className="text-outline hover:text-on-surface"><Icon name="arrow_back" /></button>
        <div>
          <h1 className="font-headline-md text-on-surface">{u.name}</h1>
          <p className="font-mono text-[12px] text-on-surface-variant">{u.email}</p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-stack-lg">
        {/* Editable profile */}
        <div className="card-obsidian p-stack-lg flex-1 space-y-stack-md">
          <h3 className="text-[11px] font-bold text-outline uppercase tracking-[0.2em]">Profile</h3>
          <Field label="Name"><input value={name} onChange={(e) => setName(e.target.value)} className={INPUT} /></Field>
          <Field label="Email (read-only)"><input value={u.email} readOnly className={`${INPUT} opacity-60`} /></Field>
          <Field label="Phone"><input value={phone} onChange={(e) => setPhone(e.target.value)} className={INPUT} /></Field>
          <Field label="Role">
            <select value={role} onChange={(e) => setRole(e.target.value)} className={INPUT}>
              <option value="citizen">Citizen</option>
              <option value="officer">Officer</option>
              <option value="admin">Admin</option>
            </select>
          </Field>
          <div className="flex items-center gap-stack-sm pt-1">
            <button disabled={busy} onClick={save} className="px-4 py-2 rounded-xl bg-primary text-on-primary font-bold text-sm disabled:opacity-50">Save changes</button>
            <button onClick={toggleSuspend} className={`px-4 py-2 rounded-xl font-bold text-sm border ${u.status === "suspended" ? "border-primary/30 text-primary" : "border-error/30 text-error"}`}>
              {u.status === "suspended" ? "Reactivate account" : "Suspend account"}
            </button>
            <button onClick={forceReset} className="px-4 py-2 rounded-xl border border-outline-variant/40 text-on-surface font-bold text-sm">Reset password</button>
          </div>
          {reset && (
            <div className="p-3 bg-surface-container-lowest/70 border border-outline-variant/30 rounded-xl">
              <p className="text-[11px] text-on-surface-variant mb-1">No email service configured — share this reset link (expires {reset.expires_in_hours}h):</p>
              <p className="break-all font-mono text-[12px] text-primary">{reset.reset_url}</p>
            </div>
          )}
        </div>

        {/* Activity */}
        <div className="card-obsidian p-stack-lg lg:w-[360px] space-y-stack-md">
          <h3 className="text-[11px] font-bold text-outline uppercase tracking-[0.2em]">Activity</h3>
          <div className="grid grid-cols-2 gap-2">
            <Stat label="Status" value={u.status.replace("_", " ")} />
            <Stat label="Assigned cases" value={String(u.assigned_case_count)} />
          </div>
          <div>
            <p className="text-[10px] font-bold text-outline uppercase tracking-widest mb-2">Login history</p>
            <div className="space-y-1.5 max-h-72 overflow-y-auto custom-scrollbar">
              {u.activity.length === 0 && <p className="text-[12px] text-on-surface-variant/60">No login sessions recorded.</p>}
              {u.activity.map((a, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-lg text-[11px]">
                  <span className="text-on-surface">{a.device_label || "Session"}{a.revoked ? " (revoked)" : ""}</span>
                  <span className="text-on-surface-variant">{formatDateTime(a.issued_at || undefined)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="text-[10px] font-bold text-outline uppercase tracking-widest">{label}</span><div className="mt-1">{children}</div></label>;
}
function Stat({ label, value }: { label: string; value: string }) {
  return <div className="p-2 bg-surface-container-lowest/50 border border-outline-variant/30 rounded-xl text-center"><p className="text-[9px] font-bold text-outline uppercase">{label}</p><p className="text-lg font-bold text-on-surface capitalize">{value}</p></div>;
}
