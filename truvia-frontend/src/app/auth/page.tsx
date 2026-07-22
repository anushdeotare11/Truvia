"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Icon } from "@/components/Icon";
import { useAuth } from "@/lib/auth";
import { homeForRole } from "@/lib/nav";
import { api, setToken, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

type Tab = "login" | "signup";
type RoleMode = "citizen" | "agency";

export default function AuthPage() {
  const { user, loading, register, refreshUser } = useAuth();
  const router = useRouter();
  const reduceMotion = useReducedMotion();

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
    if (!loading && user && !submitting) {
      if (roleMode === "agency" && user.role === "citizen") return;
      if (roleMode === "citizen" && user.role !== "citizen") return;
      router.replace(homeForRole(user.role));
    }
  }, [loading, user, router, roleMode, submitting]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      if (tab === "login") {
        // Step 1: Authenticate with API without setting global token state yet
        const tokenRes = await api.post<{ access_token: string }>("/auth/login", {
          email: email.trim(),
          password,
        });

        // Step 2: Fetch user profile using the token
        const me = await fetch("/api/v1/auth/me", {
          headers: { Authorization: `Bearer ${tokenRes.access_token}` },
        }).then((r) => r.json() as Promise<User>);

        // Step 3: Strict Role-Tab Check BEFORE persisting login session
        if (roleMode === "agency" && me.role === "citizen") {
          setError("Access Denied: This is a Citizen account. Please switch to the Citizen tab to sign in.");
          setSubmitting(false);
          return;
        }
        if (roleMode === "citizen" && me.role !== "citizen") {
          setError("Access Denied: This account is registered for Law Enforcement. Please switch to the Law Enforcement tab to sign in.");
          setSubmitting(false);
          return;
        }

        // Step 4: Role matches tab! Persist token and navigate
        setToken(tokenRes.access_token);
        await refreshUser();
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
        const tokenRes = await api.post<{ access_token: string }>("/auth/login", {
          email: email.trim(),
          password,
        });
        setToken(tokenRes.access_token);
        await refreshUser();
        router.replace("/fraud-shield");
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

  // ─── Motion setup (respects reduced-motion) ───
  const cardVariants: Variants = {
    hidden: reduceMotion ? { opacity: 0 } : { opacity: 0, y: 20, scale: 0.98 },
    show: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: reduceMotion
        ? { duration: 0.2 }
        : { duration: 0.6, ease: [0.16, 1, 0.3, 1], staggerChildren: 0.08, delayChildren: 0.1 },
    },
  };
  const itemVariants: Variants = {
    hidden: reduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { duration: reduceMotion ? 0.2 : 0.5, ease: [0.16, 1, 0.3, 1] } },
  };

  return (
    <div className="bg-background text-on-surface min-h-screen flex items-center justify-center relative overflow-hidden px-margin-page">
      {/* ─── Animated radial background glow behind card ─── */}
      <motion.div
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 left-1/2 -z-10 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(79,123,255,0.15) 0%, transparent 70%)",
          filter: "blur(80px)",
        }}
        animate={reduceMotion ? undefined : { opacity: [0.3, 0.6, 0.3], scale: [1, 1.08, 1] }}
        transition={reduceMotion ? undefined : { duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* ─── Central Glass Card ─── */}
      <motion.main
        variants={cardVariants}
        initial="hidden"
        animate="show"
        className="glass-panel relative w-full max-w-[400px] overflow-hidden rounded-[24px] p-6 md:p-8"
      >
        {/* Top-left glass shine */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-1/2 -left-1/2 h-full w-full rotate-45 bg-gradient-to-br from-white/10 to-transparent"
        />

        {/* ─── Back to Home ─── */}
        <motion.div variants={itemVariants} className="relative mb-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 font-sans text-label-md uppercase tracking-widest text-outline transition-colors hover:text-secondary-fixed-dim"
          >
            <Icon name="arrow_back" className="text-[18px]" />
            Back to Home
          </Link>
        </motion.div>

        {/* ─── Header ─── */}
        <motion.div variants={itemVariants} className="relative mb-6 flex flex-col items-center text-center">
          <Link href="/" className="group inline-flex flex-col items-center">
            <h1 className="flex items-center gap-2 font-heading text-headline-lg tracking-tighter">
              <Icon name="shield" className="text-[34px] text-primary" fill />
              <span className="bg-gradient-to-r from-primary to-secondary-container bg-clip-text text-transparent">
                Truvia
              </span>
            </h1>
            <p className="mt-2 font-sans text-label-sm uppercase tracking-[0.2em] text-outline opacity-80">
              Premier Public Safety Network
            </p>
          </Link>
        </motion.div>

        {/* ─── Login / Sign-up tabs ─── */}
        <motion.div variants={itemVariants} className="relative mb-4 flex border-b border-white/5">
          {(["login", "signup"] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => {
                setTab(t);
                setError(null);
                setInfo(null);
              }}
              className={`relative flex-1 pb-3 pt-1 font-sans text-label-md uppercase tracking-widest transition-colors ${
                tab === t ? "text-secondary-fixed-dim" : "text-outline hover:text-on-surface"
              }`}
            >
              {t === "login" ? "Login" : "Sign Up"}
              {tab === t && (
                <motion.span
                  layoutId="auth-tab-underline"
                  className="absolute -bottom-px left-0 right-0 h-0.5 rounded-full bg-secondary-fixed-dim"
                  transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
            </button>
          ))}
        </motion.div>

        {/* ─── Citizen / Agency pill switcher ─── */}
        <motion.div variants={itemVariants} className="relative mb-4 flex rounded-full bg-white/5 p-1">
          {/* Sliding indicator */}
          <motion.div
            aria-hidden="true"
            className="absolute bottom-1 top-1 w-[calc(50%-4px)] rounded-full bg-white/10"
            animate={{ x: roleMode === "citizen" ? 0 : "calc(100% + 8px)" }}
            transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 350, damping: 30 }}
          />
          {(["citizen", "agency"] as RoleMode[]).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRoleMode(r)}
              className={`relative z-10 flex flex-1 items-center justify-center gap-1.5 rounded-full py-2.5 font-sans text-label-md uppercase tracking-widest transition-colors ${
                roleMode === r ? "text-on-surface" : "text-outline hover:text-on-surface"
              }`}
            >
              <Icon name={r === "citizen" ? "person" : "policy"} className="text-[18px]" />
              {r === "citizen" ? "Citizen" : "Agency"}
            </button>
          ))}
        </motion.div>

        {/* ─── Context note ─── */}
        <motion.div
          variants={itemVariants}
          className="mb-4 rounded-r-lg border-l-2 border-secondary-fixed-dim/60 bg-white/[0.03] py-2 pl-3 pr-2"
        >
          <p className="font-sans text-label-md text-on-surface-variant">
            {roleMode === "citizen"
              ? "Standard encryption active for public users. Report and track fraud attempts securely."
              : "Authorized personnel only. Agency logins are audited and monitored."}
          </p>
        </motion.div>

        {/* ─── Form ─── */}
        <motion.form variants={itemVariants} className="space-y-4" onSubmit={handleSubmit}>
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
            <div className="flex items-start gap-stack-sm rounded-lg border border-primary/20 bg-primary-container/10 p-stack-sm">
              <Icon name="security_update_good" className="text-[20px] text-primary" />
              <div>
                <p className="font-sans text-body-md font-semibold text-primary">Multi-Factor Reminder</p>
                <p className="font-sans text-label-md text-on-surface-variant">
                  Agency-issued credentials required. Contact your command center for access.
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-start gap-stack-sm rounded-lg border border-error/30 bg-error/10 p-stack-sm">
              <Icon name="error" className="text-[18px] text-error" />
              <p className="font-sans text-body-md text-error">{error}</p>
            </div>
          )}
          {info && (
            <div className="flex items-start gap-stack-sm rounded-lg border border-tertiary/30 bg-tertiary/10 p-stack-sm">
              <Icon name="info" className="text-[18px] text-tertiary" />
              <p className="font-sans text-body-md text-tertiary">{info}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="btn-bloom mt-2 flex w-full items-center justify-center gap-3 rounded-xl py-3 font-heading uppercase tracking-tight text-on-primary-fixed transition-all active:scale-[0.98] disabled:opacity-60"
          >
            <Icon
              name={submitting ? "progress_activity" : tab === "login" ? "encrypted" : "how_to_reg"}
              className={`text-[20px] ${submitting ? "animate-spin" : ""}`}
              fill
            />
            <span className="text-[18px]">
              {submitting ? "Processing" : tab === "login" ? "Secure Login" : "Create Account"}
            </span>
          </button>
        </motion.form>

        {/* ─── Switch tab helper ─── */}
        <motion.div variants={itemVariants} className="mt-5 text-center">
          <p className="font-sans text-body-sm text-outline">
            {tab === "login" ? "New to Truvia? " : "Already registered? "}
            <button
              type="button"
              onClick={() => {
                setTab(tab === "login" ? "signup" : "login");
                setError(null);
                setInfo(null);
              }}
              className="ml-1 font-semibold text-secondary-fixed-dim underline-offset-4 transition-colors hover:underline"
            >
              {tab === "login" ? "Create an Account" : "Login"}
            </button>
          </p>
        </motion.div>

        {/* ─── Demo access ─── */}
        <motion.div variants={itemVariants} className="mt-4 border-t border-white/5 pt-4">
          <p className="mb-stack-sm font-sans text-[10px] uppercase tracking-widest text-outline">Demo Access</p>
          <div className="flex gap-stack-sm">
            <button
              type="button"
              onClick={() => fillDemo("citizen")}
              className="flex-1 rounded-lg border border-white/5 bg-white/[0.03] py-2.5 font-sans text-[11px] text-on-surface transition-colors hover:border-secondary-fixed-dim/30 hover:bg-white/[0.06]"
            >
              Citizen Demo
            </button>
            <button
              type="button"
              onClick={() => fillDemo("officer")}
              className="flex-1 rounded-lg border border-white/5 bg-white/[0.03] py-2.5 font-sans text-[11px] text-on-surface transition-colors hover:border-secondary-fixed-dim/30 hover:bg-white/[0.06]"
            >
              Officer Demo
            </button>
          </div>
        </motion.div>

        {/* ─── TLS footer strip ─── */}
        <motion.div
          variants={itemVariants}
          className="mt-5 flex items-center justify-center gap-1.5 opacity-50"
        >
          <Icon name="verified_user" className="text-[14px] text-tertiary" fill />
          <span className="font-sans text-[9px] uppercase tracking-[0.2em] text-outline">
            TLS 1.3 / AES-256 Encryption Active
          </span>
        </motion.div>
      </motion.main>
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
    <div className="group space-y-2">
      <label className="block font-sans text-label-sm uppercase tracking-wider text-outline transition-colors group-focus-within:text-secondary-fixed-dim">
        {label}
      </label>
      <div className="relative">
        <Icon
          name={icon}
          className="absolute left-0 top-1/2 -translate-y-1/2 text-[20px] text-outline/50 transition-colors group-focus-within:text-secondary-fixed-dim"
        />
        <input
          className="input-glass w-full rounded-none bg-transparent py-3 pl-8 pr-4 font-sans text-body-md text-on-surface outline-none placeholder:text-outline/30"
          placeholder={placeholder}
          type={type}
          value={value}
          required={required}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </div>
  );
}
