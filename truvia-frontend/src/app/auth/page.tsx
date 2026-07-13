"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import { useAuth } from "@/lib/auth";
import { homeForRole } from "@/lib/nav";
import { ApiError } from "@/lib/api";

type Tab = "login" | "signup";
type RoleMode = "citizen" | "agency";

export default function AuthPage() {
  const { user, loading, login, register } = useAuth();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>("login");
  const [roleMode, setRoleMode] = useState<RoleMode>("citizen");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.replace(homeForRole(user.role));
    }
  }, [loading, user, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      if (tab === "login") {
        const me = await login(email.trim(), password);
        router.replace(homeForRole(me.role));
      } else {
        if (roleMode === "agency") {
          setInfo(
            "Agency accounts are provisioned by an administrator. Please sign up as a citizen or contact your command center."
          );
          setSubmitting(false);
          return;
        }
        await register({ email: email.trim(), password, name: name.trim(), phone: phone.trim() || undefined });
        const me = await login(email.trim(), password);
        router.replace(homeForRole(me.role));
      }
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Something went wrong. Please try again.");
      setSubmitting(false);
    }
  }

  function fillDemo(kind: "citizen" | "officer") {
    setTab("login");
    setRoleMode(kind === "citizen" ? "citizen" : "agency");
    setEmail(kind === "citizen" ? "citizen@truvia.org" : "officer@truvia.org");
    setPassword("password");
    setError(null);
    setInfo(null);
  }

  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col items-center relative">
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: "radial-gradient(circle, #908fa0 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      />
      <main className="flex-grow flex flex-col items-center justify-center w-full px-gutter relative z-10 py-stack-lg">
        <Link href="/" className="mb-stack-lg text-center">
          <h1 className="text-display-lg tracking-tight uppercase flex items-center justify-center gap-2">
            <Icon name="shield_with_heart" className="text-[40px] text-primary" fill />
            <span className="text-primary">TRUVIA</span>
          </h1>
          <p className="font-label-md text-on-surface-variant mt-1 tracking-[0.2em]">
            PREMIER PUBLIC SAFETY NETWORK
          </p>
        </Link>

        <div className="glass-panel border border-outline-variant w-full max-w-[440px] overflow-hidden rounded-xl">
          {/* Tabs */}
          <div className="flex border-b border-outline-variant">
            {(["login", "signup"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => {
                  setTab(t);
                  setError(null);
                  setInfo(null);
                }}
                className={`flex-1 py-stack-md font-label-md border-b-2 transition-all uppercase tracking-widest ${
                  tab === t
                    ? "border-primary text-primary"
                    : "border-transparent text-on-surface-variant hover:text-primary"
                }`}
              >
                {t === "login" ? "Login" : "Sign Up"}
              </button>
            ))}
          </div>

          <div className="p-card-padding space-y-stack-md">
            {/* Role selector */}
            <div className="flex gap-1 p-1 bg-surface-container-lowest rounded-lg border border-outline-variant/30">
              {(["citizen", "agency"] as RoleMode[]).map((r) => (
                <button
                  key={r}
                  onClick={() => setRoleMode(r)}
                  className={`flex-1 flex items-center justify-center gap-1 py-stack-sm rounded font-body-md transition-all ${
                    roleMode === r
                      ? "bg-primary text-on-primary shadow-md"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  <Icon name={r === "citizen" ? "person" : "policy"} className="text-[18px]" />
                  {r === "citizen" ? "Citizen" : "Agency"}
                </button>
              ))}
            </div>

            <div className="bg-secondary-container/20 border-l-4 border-secondary p-stack-sm rounded-r">
              <p className="font-label-md text-on-secondary-container">
                {roleMode === "citizen"
                  ? "Standard encryption active for public users. Report and track fraud attempts securely."
                  : "Authorized personnel only. Agency logins are audited and monitored."}
              </p>
            </div>

            <form className="space-y-stack-md" onSubmit={handleSubmit}>
              {tab === "signup" && roleMode === "citizen" && (
                <>
                  <Field
                    label="Full Name"
                    icon="badge"
                    type="text"
                    value={name}
                    onChange={setName}
                    placeholder="Rahul Sharma"
                    required
                  />
                  <Field
                    label="Phone (optional)"
                    icon="call"
                    type="text"
                    value={phone}
                    onChange={setPhone}
                    placeholder="+91 90000 00000"
                  />
                </>
              )}
              <Field
                label={roleMode === "agency" ? "Agency Email" : "Email Address"}
                icon="alternate_email"
                type="email"
                value={email}
                onChange={setEmail}
                placeholder="name@example.com"
                required
              />
              <Field
                label="Password"
                icon="lock"
                type="password"
                value={password}
                onChange={setPassword}
                placeholder="••••••••"
                required
              />

              {roleMode === "agency" && (
                <div className="flex items-start gap-stack-sm p-stack-sm bg-primary-container/10 rounded-lg border border-primary/20">
                  <Icon name="security_update_good" className="text-primary text-[20px]" />
                  <div>
                    <p className="text-body-md font-semibold text-primary">Multi-Factor Reminder</p>
                    <p className="font-label-md text-on-surface-variant">
                      Agency-issued credentials required. Contact your command center for access.
                    </p>
                  </div>
                </div>
              )}

              {error && (
                <div className="flex items-start gap-stack-sm p-stack-sm bg-error/10 rounded-lg border border-error/30">
                  <Icon name="error" className="text-error text-[18px]" />
                  <p className="font-body-md text-error">{error}</p>
                </div>
              )}
              {info && (
                <div className="flex items-start gap-stack-sm p-stack-sm bg-tertiary/10 rounded-lg border border-tertiary/30">
                  <Icon name="info" className="text-tertiary text-[18px]" />
                  <p className="font-body-md text-tertiary">{info}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full bg-primary text-on-primary py-stack-sm rounded-lg font-label-md flex items-center justify-center gap-stack-sm hover:brightness-110 transition-all active:scale-[0.98] uppercase tracking-widest shadow-lg shadow-primary/20 disabled:opacity-60"
              >
                <Icon
                  name={submitting ? "progress_activity" : tab === "login" ? "encrypted" : "how_to_reg"}
                  className={`text-[18px] ${submitting ? "animate-spin" : ""}`}
                />
                {submitting ? "Processing" : tab === "login" ? "Secure Login" : "Create Account"}
              </button>
            </form>

            <div className="pt-stack-sm text-center">
              <p className="font-label-md text-on-surface-variant">
                {tab === "login" ? "New to Truvia? " : "Already registered? "}
                <button
                  onClick={() => {
                    setTab(tab === "login" ? "signup" : "login");
                    setError(null);
                    setInfo(null);
                  }}
                  className="text-secondary font-semibold hover:text-primary transition-colors"
                >
                  {tab === "login" ? "Create an Account" : "Login"}
                </button>
              </p>
            </div>

            {/* Demo credentials helper */}
            <div className="pt-stack-sm border-t border-outline-variant/30">
              <p className="font-label-md text-[10px] text-on-surface-variant uppercase tracking-widest mb-stack-sm">
                Demo Access
              </p>
              <div className="flex gap-stack-sm">
                <button
                  onClick={() => fillDemo("citizen")}
                  className="flex-1 py-stack-sm bg-surface-container-high rounded-lg font-label-md text-[11px] text-on-surface hover:bg-surface-variant transition-colors"
                >
                  Citizen Demo
                </button>
                <button
                  onClick={() => fillDemo("officer")}
                  className="flex-1 py-stack-sm bg-surface-container-high rounded-lg font-label-md text-[11px] text-on-surface hover:bg-surface-variant transition-colors"
                >
                  Officer Demo
                </button>
              </div>
            </div>
          </div>

          <div className="bg-surface-container-lowest/50 py-stack-sm px-card-padding border-t border-outline-variant/30 flex items-center justify-center gap-1">
            <Icon name="verified_user" className="text-tertiary text-[14px]" fill />
            <span className="font-label-md text-on-surface-variant text-[9px] uppercase tracking-[0.2em]">
              TLS 1.3 / AES-256 Encryption Active
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}

function Field({
  label,
  icon,
  type,
  value,
  onChange,
  placeholder,
  required,
}: {
  label: string;
  icon: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div className="space-y-1">
      <label className="font-label-md text-on-surface-variant uppercase tracking-wider block">
        {label}
      </label>
      <div className="relative">
        <input
          className="w-full bg-surface-container-low border border-outline-variant/50 rounded-lg px-stack-md py-stack-sm focus:border-primary focus:ring-1 focus:ring-primary transition-all outline-none text-body-md font-mono text-on-surface placeholder-on-surface-variant/30"
          placeholder={placeholder}
          type={type}
          value={value}
          required={required}
          onChange={(e) => onChange(e.target.value)}
        />
        <Icon
          name={icon}
          className="absolute right-stack-md top-1/2 -translate-y-1/2 text-outline text-[20px]"
        />
      </div>
    </div>
  );
}
