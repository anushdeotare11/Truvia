"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { useAuth } from "@/lib/auth";
import { homeForRole } from "@/lib/nav";

const FEATURES = [
  {
    icon: "insights",
    title: "Cognitive Threat Mapping",
    body: "Neural analysis of multi-source intelligence identifies emerging fraud vectors in real-time.",
  },
  {
    icon: "hub",
    title: "Cross-Agency Sync",
    body: "Encrypted channels for seamless inter-departmental collaboration and tactical data sharing.",
  },
  {
    icon: "verified_user",
    title: "Citizen Protocol",
    body: "Automated personal defense layers intercept and neutralize digital fraud before it reaches you.",
  },
];

const STEPS = [
  { n: "01", title: "Data Ingestion", body: "Heterogeneous data normalization from screenshots, audio, and text evidence." },
  { n: "02", title: "Heuristic Analysis", body: "Autonomous pattern recognition engines identify micro-anomalies and scam markers." },
  { n: "03", title: "Tactical Alert", body: "High-fidelity intelligence delivered with evidentiary verification to relevant operators." },
];

const METRICS = [
  { label: "Reports Analyzed", value: "150K+" },
  { label: "Threats Neutralized", value: "4.2M+" },
  { label: "Avg Latency", value: "0.8s" },
  { label: "Integrity Index", value: "99.9%" },
];

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace(homeForRole(user.role));
    }
  }, [loading, user, router]);

  return (
    <div className="bg-background text-on-background min-h-screen">
      {/* Top Nav */}
      <nav className="fixed top-0 left-0 w-full h-header-height bg-surface-container-lowest/80 backdrop-blur-md border-b border-outline-variant z-50 flex items-center justify-between px-stack-lg lg:px-margin-page">
        <div className="flex items-center gap-stack-sm">
          <span className="text-headline-md font-extrabold text-primary tracking-tighter">TRUVIA</span>
          <span className="font-label-md text-[10px] text-on-surface-variant ml-stack-sm uppercase tracking-[0.2em] border-l border-outline-variant pl-stack-sm hidden sm:block">
            Command Center
          </span>
        </div>
        <div className="hidden md:flex items-center gap-stack-lg">
          <a className="font-label-md text-on-surface-variant hover:text-primary transition-colors" href="#features">MODULES</a>
          <a className="font-label-md text-on-surface-variant hover:text-primary transition-colors" href="#how-it-works">PROTOCOLS</a>
        </div>
        <Link
          href="/auth"
          className="bg-primary-container text-white px-stack-md py-stack-sm font-label-md rounded hover:brightness-110 transition-all active:scale-[0.98]"
        >
          OPERATOR LOGIN
        </Link>
      </nav>

      <main className="pt-header-height">
        {/* Hero */}
        <section className="relative min-h-[720px] flex items-center overflow-hidden hero-gradient">
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage:
                "linear-gradient(#c1c1ff 1px, transparent 1px), linear-gradient(90deg, #c1c1ff 1px, transparent 1px)",
              backgroundSize: "32px 32px",
            }}
          />
          <div className="container mx-auto px-stack-lg lg:px-margin-page grid grid-cols-1 lg:grid-cols-2 gap-stack-lg relative z-10">
            <div className="flex flex-col justify-center space-y-stack-md">
              <div className="inline-flex items-center gap-stack-sm bg-primary-container/20 border border-primary-container/40 px-stack-sm py-1 rounded w-fit">
                <Icon name="terminal" className="text-primary text-[16px]" fill />
                <span className="font-label-md text-[11px] text-primary-fixed-dim uppercase tracking-wider">
                  System Status: Active
                </span>
              </div>
              <h1 className="text-white text-[44px] lg:text-[60px] leading-[1.05] font-extrabold tracking-tight">
                Next-Gen{" "}
                <span className="text-primary drop-shadow-[0_0_15px_rgba(193,193,255,0.3)]">
                  Public Safety
                </span>{" "}
                Intelligence
              </h1>
              <p className="font-body-lg text-on-surface-variant max-w-xl leading-relaxed">
                Deploying AI-powered predictive analytics to empower law enforcement and establishing an
                unbreachable digital shield for citizen fraud protection.
              </p>
              <div className="flex flex-wrap gap-stack-md pt-stack-md">
                <Link
                  href="/auth"
                  className="bg-primary text-on-primary px-stack-lg py-stack-md font-headline-sm text-[16px] rounded flex items-center gap-stack-sm hover:shadow-[0_0_20px_rgba(193,193,255,0.4)] transition-all"
                >
                  <Icon name="shield_with_heart" />
                  Citizen Shield
                </Link>
                <Link
                  href="/auth"
                  className="border border-outline text-on-surface px-stack-lg py-stack-md font-headline-sm text-[16px] rounded hover:bg-surface-bright/10 transition-all flex items-center gap-stack-sm"
                >
                  <Icon name="security" className="text-primary" />
                  Agency Access
                </Link>
              </div>
            </div>
            <div className="hidden lg:flex items-center justify-center relative">
              <div className="absolute w-[500px] h-[500px] bg-primary/10 rounded-full blur-[120px] -z-10" />
              <div className="relative w-full max-w-xl glowing-border bg-surface-container-lowest rounded-xl overflow-hidden shadow-2xl">
                <div className="h-8 bg-surface-container-high border-b border-outline-variant flex items-center px-stack-md gap-stack-sm">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-error/40" />
                    <div className="w-2.5 h-2.5 rounded-full bg-tertiary/40" />
                    <div className="w-2.5 h-2.5 rounded-full bg-primary/40" />
                  </div>
                  <div className="mx-auto font-label-md text-[10px] text-on-surface-variant">
                    SECURE_DASHBOARD_LIVE
                  </div>
                </div>
                <div className="p-stack-lg space-y-stack-md">
                  <div className="grid grid-cols-2 gap-stack-md">
                    {METRICS.slice(0, 2).map((m) => (
                      <div key={m.label} className="bento-card p-card-padding">
                        <p className="font-label-md text-[10px] text-on-surface-variant uppercase">{m.label}</p>
                        <p className="text-data-lg text-primary drop-shadow-[0_0_8px_rgba(193,193,255,0.2)]">
                          {m.value}
                        </p>
                      </div>
                    ))}
                  </div>
                  <div className="bento-card p-card-padding">
                    <div className="flex items-center justify-between mb-stack-md">
                      <span className="font-label-md text-on-surface text-[11px]">THREAT TREND</span>
                      <Icon name="analytics" className="text-primary text-[18px]" />
                    </div>
                    <div className="h-24 flex items-end gap-1.5">
                      {[30, 55, 40, 85, 60, 95, 70].map((h, i) => (
                        <div
                          key={i}
                          className="flex-1 bg-primary/30 border-t-2 border-primary rounded-t"
                          style={{ height: `${h}%` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Metrics bar */}
        <section className="bg-surface-container-lowest border-y border-outline-variant py-stack-lg">
          <div className="container mx-auto px-stack-lg lg:px-margin-page flex flex-wrap justify-between items-center gap-stack-lg">
            {METRICS.map((m) => (
              <div key={m.label} className="flex flex-col">
                <span className="font-label-md text-on-surface-variant text-[11px] uppercase tracking-widest">
                  {m.label}
                </span>
                <span className="text-headline-md text-primary drop-shadow-[0_0_8px_rgba(193,193,255,0.2)]">
                  {m.value}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Features */}
        <section className="py-stack-lg bg-surface-dim" id="features">
          <div className="container mx-auto px-stack-lg lg:px-margin-page">
            <div className="text-center max-w-2xl mx-auto mb-stack-lg">
              <span className="font-label-md text-primary tracking-[0.3em] uppercase text-[11px]">
                System Capabilities
              </span>
              <h2 className="text-headline-lg text-white mt-stack-sm">
                Engineered for High-Density Intelligence
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-stack-lg">
              {FEATURES.map((f) => (
                <div
                  key={f.title}
                  className="group p-card-padding border border-outline-variant bg-surface-container-low hover:bg-surface-container transition-all duration-300 rounded-lg"
                >
                  <div className="w-12 h-12 rounded bg-primary-container/20 flex items-center justify-center mb-stack-md group-hover:scale-110 transition-transform">
                    <Icon name={f.icon} className="text-primary" fill />
                  </div>
                  <h3 className="font-headline-sm text-white mb-stack-sm">{f.title}</h3>
                  <p className="font-body-md text-on-surface-variant leading-relaxed">{f.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="py-stack-lg bg-surface-container-lowest border-y border-outline-variant" id="how-it-works">
          <div className="container mx-auto px-stack-lg lg:px-margin-page">
            <div className="mb-stack-lg">
              <h2 className="text-headline-lg text-white">Precision Protocol</h2>
              <p className="font-body-md text-on-surface-variant mt-stack-sm">
                Operational lifecycle of intelligence from ingestion to action.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-stack-lg">
              {STEPS.map((s) => (
                <div key={s.n} className="flex gap-stack-md group">
                  <div className="flex-shrink-0 w-8 h-8 rounded border border-primary text-primary flex items-center justify-center font-label-md text-[14px] group-hover:bg-primary group-hover:text-on-primary transition-colors">
                    {s.n}
                  </div>
                  <div>
                    <h4 className="font-headline-sm text-white text-[18px]">{s.title}</h4>
                    <p className="font-body-md text-on-surface-variant">{s.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-stack-lg bg-surface-dim relative overflow-hidden">
          <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-primary/5 rounded-full blur-[100px]" />
          <div className="container mx-auto px-stack-lg lg:px-margin-page text-center">
            <div className="max-w-4xl mx-auto border border-outline-variant p-stack-lg rounded-xl bg-surface-container-lowest/50 backdrop-blur-sm glowing-border">
              <h2 className="text-headline-lg text-white mb-stack-md">Ready to Deploy Intelligence?</h2>
              <p className="font-body-md text-on-surface-variant max-w-xl mx-auto mb-stack-lg">
                Join the premier network for digital defense and predictive public safety enforcement.
              </p>
              <div className="flex flex-col sm:flex-row justify-center gap-stack-md">
                <Link
                  href="/auth"
                  className="bg-primary-container text-white px-stack-lg py-stack-md font-headline-sm text-[16px] rounded hover:brightness-110 transition-all border border-primary/20"
                >
                  Enroll in Citizen Shield
                </Link>
              </div>
            </div>
          </div>
        </section>

        <footer className="bg-surface-container-lowest border-t border-outline-variant py-stack-lg">
          <div className="container mx-auto px-stack-lg lg:px-margin-page flex flex-col md:flex-row justify-between items-center gap-stack-md">
            <span className="text-headline-md font-extrabold text-primary tracking-tighter">TRUVIA</span>
            <div className="flex gap-stack-lg font-label-md text-[10px] text-on-surface-variant uppercase tracking-widest">
              <span>© 2026 TRUVIA COMMAND</span>
              <span>PRIVACY</span>
              <span>TERMS</span>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
