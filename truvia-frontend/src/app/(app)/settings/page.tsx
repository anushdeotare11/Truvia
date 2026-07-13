"use client";

import { useEffect, useState, FormEvent } from "react";
import { Icon } from "@/components/Icon";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { User } from "@/lib/types";
import { formatDate } from "@/lib/format";

type Tab = "profile" | "security" | "roles" | "preferences";

export default function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [tab, setTab] = useState<Tab>("profile");

  const tabs: { id: Tab; label: string; adminOnly?: boolean }[] = [
    { id: "profile", label: "User Profile" },
    { id: "security", label: "Security" },
    { id: "roles", label: "Role Management", adminOnly: true },
    { id: "preferences", label: "Preferences" },
  ];

  return (
    <div className="p-gutter max-w-6xl mx-auto">
      <header className="mb-stack-lg">
        <h1 className="font-headline-lg text-on-surface">System Settings</h1>
        <p className="font-body-md text-on-surface-variant mt-1">
          Configure your profile, security protocols, and platform access.
        </p>
      </header>

      <div className="mb-stack-lg border-b border-outline-variant flex gap-gutter overflow-x-auto">
        {tabs
          .filter((t) => !t.adminOnly || isAdmin)
          .map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-1 pb-stack-sm font-label-md uppercase whitespace-nowrap border-b-2 transition-colors ${
                tab === t.id
                  ? "text-primary border-primary"
                  : "text-on-surface-variant border-transparent hover:text-primary"
              }`}
            >
              {t.label}
            </button>
          ))}
      </div>

      {tab === "profile" && <ProfileTab user={user} />}
      {tab === "security" && <SecurityTab />}
      {tab === "roles" && isAdmin && <RolesTab currentUserId={user?.id} />}
      {tab === "preferences" && <PreferencesTab />}
    </div>
  );
}

function ProfileTab({ user }: { user: User | null }) {
  if (!user) return null;
  return (
    <div className="grid grid-cols-12 gap-gutter">
      <section className="col-span-12 lg:col-span-8 space-y-stack-md">
        <div className="bg-surface-container-lowest border border-outline-variant p-card-padding rounded-xl">
          <h2 className="font-headline-sm text-on-surface mb-stack-lg border-b border-outline-variant pb-stack-md">
            Profile Details
          </h2>
          <div className="flex items-center gap-gutter mb-stack-lg">
            <div className="w-20 h-20 rounded-xl bg-primary-container flex items-center justify-center">
              <Icon name="account_circle" className="text-white text-[48px]" />
            </div>
            <div className="space-y-1">
              <p className="font-headline-sm text-on-surface">{user.name}</p>
              <p className="font-body-md text-on-surface-variant capitalize">{user.role}</p>
              <p className="font-label-md text-secondary">{user.email}</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-stack-md">
            <ReadonlyField label="Full Name" value={user.name} />
            <ReadonlyField label="Role" value={user.role} />
            <ReadonlyField label="Email" value={user.email} />
            <ReadonlyField label="Account Status" value={user.status} />
            <ReadonlyField label="Member Since" value={formatDate(user.created_at)} />
          </div>
          <p className="mt-stack-md font-label-md text-[11px] text-on-surface-variant/60">
            Profile fields are managed by your command administrator.
          </p>
        </div>
      </section>
      <aside className="col-span-12 lg:col-span-4 space-y-stack-md">
        <div className="bg-primary-container text-on-primary-container p-card-padding rounded-xl border border-primary/20">
          <div className="flex items-center gap-stack-sm mb-stack-md">
            <Icon name="shield" className="text-primary text-[20px]" />
            <h3 className="font-label-md uppercase tracking-widest text-[11px] text-primary">System Integrity</h3>
          </div>
          <div className="space-y-stack-md">
            <div className="flex justify-between items-end">
              <span className="font-body-md opacity-80">Security Level</span>
              <span className="font-label-md text-primary-fixed-dim">High-Assurance</span>
            </div>
            <div className="h-1.5 bg-background/50 rounded-full overflow-hidden">
              <div className="h-full bg-primary w-[92%] shadow-[0_0_8px_rgba(193,193,255,0.4)]" />
            </div>
            <p className="text-[12px] opacity-70 leading-relaxed italic">
              All connections encrypted. No anomalies detected in the current session.
            </p>
          </div>
        </div>
      </aside>
    </div>
  );
}

function SecurityTab() {
  return (
    <div className="grid grid-cols-12 gap-gutter">
      <section className="col-span-12 lg:col-span-8 space-y-stack-md">
        <div className="bg-surface-container-lowest border border-outline-variant p-card-padding rounded-xl">
          <h2 className="font-headline-sm text-on-surface mb-stack-lg border-b border-outline-variant pb-stack-md">
            Authentication
          </h2>
          <div className="flex items-center justify-between p-stack-md bg-surface-container-low border border-outline-variant rounded-xl">
            <div className="flex items-center gap-gutter">
              <Icon name="phonelink_lock" className="text-primary text-[40px]" />
              <div>
                <p className="font-body-lg font-bold text-on-surface">Session Encryption</p>
                <p className="font-body-md text-on-surface-variant">
                  JWT bearer tokens with rotating refresh cookies (TLS 1.3 / AES-256).
                </p>
              </div>
            </div>
            <span className="font-label-md text-[11px] bg-primary-container text-on-primary-container px-stack-md py-stack-sm rounded-full border border-primary/20">
              ACTIVE
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}

function RolesTab({ currentUserId }: { currentUserId?: string }) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("officer");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    try {
      const data = await api.get<User[]>("/auth/users");
      setUsers(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggleStatus(u: User) {
    const next = u.status === "suspended" ? "active" : "suspended";
    try {
      await api.post(`/auth/users/${u.id}/status`, { status: next });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update status.");
    }
  }

  async function submitInvite(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/auth/users/invite", {
        name: inviteName,
        email: inviteEmail,
        role: inviteRole,
      });
      setInviteOpen(false);
      setInviteName("");
      setInviteEmail("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Invite failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
      <div className="p-card-padding border-b border-outline-variant flex items-center justify-between">
        <h2 className="font-headline-sm text-on-surface">User & Role Management</h2>
        <button
          onClick={() => setInviteOpen((v) => !v)}
          className="bg-primary text-on-primary px-stack-md py-stack-sm rounded-lg font-label-md hover:brightness-110 flex items-center gap-stack-sm"
        >
          <Icon name="person_add" className="text-[18px]" />
          Invite User
        </button>
      </div>

      {error && <div className="p-stack-md text-error font-body-md">{error}</div>}

      {inviteOpen && (
        <form onSubmit={submitInvite} className="p-card-padding border-b border-outline-variant grid grid-cols-1 md:grid-cols-4 gap-stack-md items-end bg-surface-container-low/40">
          <div className="space-y-1">
            <label className="font-label-md text-[11px] uppercase text-on-surface-variant">Name</label>
            <input
              required
              value={inviteName}
              onChange={(e) => setInviteName(e.target.value)}
              className="w-full bg-surface-container-high border border-outline-variant rounded-lg px-stack-md py-stack-sm text-body-md outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="font-label-md text-[11px] uppercase text-on-surface-variant">Email</label>
            <input
              required
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="w-full bg-surface-container-high border border-outline-variant rounded-lg px-stack-md py-stack-sm text-body-md outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="font-label-md text-[11px] uppercase text-on-surface-variant">Role</label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="w-full bg-surface-container-high border border-outline-variant rounded-lg px-stack-md py-stack-sm text-body-md capitalize"
            >
              <option value="officer">Officer</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="h-10 bg-secondary-container text-on-secondary-container rounded-lg font-label-md font-bold uppercase disabled:opacity-60"
          >
            {submitting ? "Inviting..." : "Send Invite"}
          </button>
        </form>
      )}

      <div className="overflow-x-auto">
        {loading ? (
          <div className="p-6 text-on-surface-variant font-body-md">Loading users...</div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-low/30">
                {["Name", "Email", "Role", "Status", "Action"].map((h) => (
                  <th
                    key={h}
                    className={`px-stack-md py-stack-md font-label-md text-[11px] text-on-surface-variant uppercase ${
                      h === "Action" ? "text-right" : ""
                    }`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-outline-variant/30 hover:bg-surface-container-low transition-colors">
                  <td className="px-stack-md py-stack-md font-body-md text-on-surface">{u.name}</td>
                  <td className="px-stack-md py-stack-md font-body-md text-on-surface-variant">{u.email}</td>
                  <td className="px-stack-md py-stack-md font-label-md text-primary uppercase text-[11px]">{u.role}</td>
                  <td className="px-stack-md py-stack-md">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        u.status === "suspended"
                          ? "bg-error/10 text-error border border-error/20"
                          : "bg-primary/10 text-primary border border-primary/20"
                      }`}
                    >
                      {u.status}
                    </span>
                  </td>
                  <td className="px-stack-md py-stack-md text-right">
                    <button
                      onClick={() => toggleStatus(u)}
                      disabled={u.id === currentUserId}
                      className="font-label-md text-[11px] uppercase text-on-surface-variant hover:text-error transition-colors disabled:opacity-30"
                    >
                      {u.status === "suspended" ? "Reactivate" : "Suspend"}
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-on-surface-variant font-body-md">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function PreferencesTab() {
  const [prefs, setPrefs] = useState({ securityAlerts: true, summaries: false, publicAlerts: true });

  useEffect(() => {
    const stored = window.localStorage.getItem("truvia_prefs");
    if (stored) {
      try {
        setPrefs(JSON.parse(stored));
      } catch {
        /* ignore */
      }
    }
  }, []);

  function toggle(key: keyof typeof prefs) {
    setPrefs((p) => {
      const next = { ...p, [key]: !p[key] };
      window.localStorage.setItem("truvia_prefs", JSON.stringify(next));
      return next;
    });
  }

  const rows: { key: keyof typeof prefs; title: string; desc: string }[] = [
    { key: "securityAlerts", title: "Security Alerts", desc: "Notify me of login attempts from new devices." },
    { key: "summaries", title: "Intelligence Summaries", desc: "Weekly analytical wrap-ups for your sector." },
    { key: "publicAlerts", title: "Public Advisories", desc: "Receive public safety fraud advisories." },
  ];

  return (
    <div className="bg-surface-container-lowest border border-outline-variant p-card-padding rounded-xl max-w-2xl">
      <h2 className="font-headline-sm text-on-surface mb-stack-lg border-b border-outline-variant pb-stack-md">
        Notification Preferences
      </h2>
      <div className="space-y-stack-md">
        {rows.map((r) => (
          <div key={r.key} className="flex items-center justify-between p-stack-sm border-b border-outline-variant/30 last:border-0">
            <div>
              <p className="font-body-lg font-semibold text-on-surface">{r.title}</p>
              <p className="font-body-md text-on-surface-variant">{r.desc}</p>
            </div>
            <button
              onClick={() => toggle(r.key)}
              className={`w-12 h-6 rounded-full relative transition-colors ${
                prefs[r.key] ? "bg-primary-container" : "bg-surface-container-highest"
              }`}
              aria-pressed={prefs[r.key]}
            >
              <div
                className={`absolute top-1 w-4 h-4 rounded-full transition-all ${
                  prefs[r.key] ? "right-1 bg-on-primary-container" : "left-1 bg-outline"
                }`}
              />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReadonlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <label className="font-label-md text-[11px] text-on-surface-variant uppercase tracking-wider">{label}</label>
      <div className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-stack-md py-stack-sm font-body-md text-on-surface capitalize">
        {value || "—"}
      </div>
    </div>
  );
}
