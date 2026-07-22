"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  motion,
  useScroll,
  useSpring,
  useTransform,
  useMotionValue,
  useInView,
  animate,
  type Variants,
} from "framer-motion";
import { Icon } from "@/components/Icon";
import { useAuth } from "@/lib/auth";
import { homeForRole } from "@/lib/nav";

const EASE = [0.22, 1, 0.36, 1] as const;

const NAV = [
  { label: "Modules", href: "#modules" },
  { label: "Capabilities", href: "#features" },
  { label: "Protocol", href: "#how-it-works" },
];

const MODULES = [
  { icon: "shield_with_heart", tag: "For Citizens", title: "Citizen Fraud Shield", body: "Upload a suspicious screenshot, call recording, or message and receive an explainable threat verdict in seconds — with the exact red flags and the safe next step." },
  { icon: "dashboard", tag: "For Law Enforcement", title: "Intelligence Dashboard", body: "A command-center view of complaint volume, emerging scam velocity, and case depth — replacing manual spreadsheet triage with live signal." },
  { icon: "hub", tag: "For Analysts", title: "Threat Intelligence Engine", body: "A continuously-growing fraud graph that links entities across complaints, surfaces rings via community detection, and ranks high-risk actors." },
];

const FEATURES = [
  { icon: "insights", title: "Cognitive Threat Mapping", body: "Neural analysis of multi-source intelligence identifies emerging fraud vectors in real-time." },
  { icon: "graph_3", title: "Entity Correlation Graph", body: "Every report is decomposed into entities and linked into a persistent, queryable fraud network." },
  { icon: "verified_user", title: "Explainable Verdicts", body: "Every score ships with plain-language reasoning and cited RBI / CERT-In / MHA guidance." },
  { icon: "bolt", title: "Pre-Transaction Defense", body: "Real-time scoring during an active scam interaction — intervention before the money moves." },
  { icon: "description", title: "Court-Ready Packages", body: "Structured, evidentiary intelligence dossiers generated in one click for case escalation." },
  { icon: "trending_up", title: "Predictive Velocity", body: "Rolling complaint-velocity detection flags emerging scam categories before they spike." },
];

const STEPS = [
  { n: "01", title: "Data Ingestion", body: "Heterogeneous evidence — screenshots, audio, and text — normalized by the Input Processing agent." },
  { n: "02", title: "Heuristic Analysis", body: "Threat scoring, entity extraction, and graph correlation run across coordinated AI agents." },
  { n: "03", title: "Tactical Intelligence", body: "High-fidelity verdicts and court-ready packages delivered to citizens and operators." },
];

const METRICS = [
  { label: "Reports Analyzed", to: 150, decimals: 0, suffix: "K+" },
  { label: "Threats Neutralized", to: 4.2, decimals: 1, suffix: "M+" },
  { label: "Avg Latency", to: 0.8, decimals: 1, suffix: "s" },
  { label: "Integrity Index", to: 99.9, decimals: 1, suffix: "%" },
];

function CountUp({ to, decimals = 0, suffix = "" }: { to: number; decimals?: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, to, { duration: 1.6, ease: "easeOut", onUpdate: (v: number) => setVal(v) });
    return () => controls.stop();
  }, [inView, to]);
  return (
    <span ref={ref}>
      {val.toFixed(decimals)}
      {suffix}
    </span>
  );
}

function Reveal({ children, delay = 0, y = 28, className = "" }: { children: React.ReactNode; delay?: number; y?: number; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y, filter: "blur(8px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.75, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

const containerStagger: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.09 } } };
const itemUp: Variants = {
  hidden: { opacity: 0, y: 30, filter: "blur(6px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.7, ease: EASE } },
};

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [bannerOpen, setBannerOpen] = useState(true);

  useEffect(() => {
    if (!loading && user) router.replace(homeForRole(user.role));
  }, [loading, user, router]);

  // Hero mouse parallax
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const sx = useSpring(mx, { stiffness: 60, damping: 16 });
  const sy = useSpring(my, { stiffness: 60, damping: 16 });
  const rotateY = useTransform(sx, [-0.5, 0.5], [7, -7]);
  const rotateX = useTransform(sy, [-0.5, 0.5], [-5, 5]);

  function handleHeroMove(e: React.MouseEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    mx.set((e.clientX - r.left) / r.width - 0.5);
    my.set((e.clientY - r.top) / r.height - 0.5);
  }

  return (
    <div className="bg-background text-on-surface min-h-screen overflow-x-hidden">
      {/* ============ FIXED HEADER (banner + nav) ============ */}
      <div className="fixed top-0 left-0 w-full z-50">
        {bannerOpen && (
          <div className="h-10 bg-primary-container flex items-center justify-center relative px-stack-lg">
            <span className="text-[13px] font-medium text-on-primary-container text-center">
              Truvia is live for the ET AI Hackathon 2026 &raquo;
            </span>
            <button
              onClick={() => setBannerOpen(false)}
              aria-label="Dismiss announcement"
              className="absolute right-stack-md top-1/2 -translate-y-1/2 text-on-primary-container/80 hover:text-on-primary-container transition-colors"
            >
              <Icon name="close" className="text-[18px]" />
            </button>
          </div>
        )}
        <nav className="h-header-height bg-background/80 backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-stack-lg lg:px-margin-page">
          <div className="flex items-center gap-stack-sm">
            <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center neon-glow">
              <Icon name="shield_lock" className="text-primary text-[18px]" fill />
            </div>
            <span className="text-headline-md font-heading font-extrabold text-on-surface tracking-tight">Truvia</span>
          </div>
          <div className="hidden md:flex items-center gap-stack-lg absolute left-1/2 -translate-x-1/2">
            {NAV.map((n) => (
              <a
                key={n.href}
                href={n.href}
                className="group flex items-center gap-2 text-[14px] text-on-surface-variant hover:text-secondary-container transition-colors"
              >
                {n.label}
                <span className="w-4 h-4 rounded-[4px] border border-white/20 flex items-center justify-center text-[11px] leading-none text-white/50 group-hover:border-secondary-container group-hover:text-secondary-container transition-colors">
                  +
                </span>
              </a>
            ))}
          </div>
          <Link
            href="/auth"
            className="btn-primary btn-shimmer btn-shine btn-sm rounded-lg"
          >
            Get started
          </Link>
        </nav>
      </div>

      <main style={{ paddingTop: bannerOpen ? 104 : 64 }}>
        {/* ============ HERO ============ */}
        <section
          onMouseMove={handleHeroMove}
          className="bg-background relative min-h-[92svh] flex items-center overflow-hidden px-stack-lg"
        >
          <div className="absolute inset-0 grid-overlay opacity-60" />
          <div className="absolute inset-0 noise-overlay" />

          <div className="container mx-auto px-stack-lg lg:px-margin-page grid grid-cols-1 lg:grid-cols-2 gap-stack-lg items-center relative z-10">
            {/* LEFT: copy */}
            <div className="flex flex-col justify-center space-y-stack-md py-stack-lg">
              <motion.h1
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: EASE }}
                className="text-on-surface text-[40px] sm:text-[52px] lg:text-[60px] font-heading font-extrabold leading-[1.05] tracking-tight"
              >
                See the fraud
                <br />
                <span className="bg-gradient-to-r from-primary to-secondary-container bg-clip-text text-transparent">before it sees you.</span>
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.2, ease: EASE }}
                className="text-on-surface-variant text-[17px] lg:text-[19px] max-w-xl leading-relaxed"
              >
                Truvia turns unstructured complaints into structured, explainable, court-ready
                intelligence — a continuously-learning threat graph that stops fraud before the transfer.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.35, ease: EASE }}
                className="flex flex-wrap gap-stack-md pt-stack-sm"
              >
                <Link
                  href="/auth"
                  className="btn-bloom btn-shimmer text-on-primary-container font-heading font-semibold rounded-xl px-6 py-3 inline-flex items-center gap-2"
                >
                  <Icon name="shield_with_heart" />
                  Launch Citizen Shield
                </Link>
                <Link
                  href="/auth"
                  className="btn-shimmer inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-white/10 bg-white/5 text-on-surface hover:border-secondary-container/40 hover:text-secondary-container transition-colors"
                >
                  <Icon name="security" />
                  Agency Access
                </Link>
              </motion.div>
            </div>

            {/* RIGHT: live console */}
            <div className="flex justify-center lg:justify-end" style={{ perspective: 1200 }}>
              <motion.div
                style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
                initial={{ opacity: 0, scale: 0.94, y: 40 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.9, delay: 0.3, ease: EASE }}
                className="relative w-full max-w-2xl"
              >
                <div className="absolute -inset-8 bg-primary/20 rounded-[32px] blur-[100px] -z-10" />
                <div className="relative rounded-2xl overflow-hidden shadow-2xl primary-glow obsidian-panel float-slow">
                  <div className="scan-line" />
                  <div className="h-9 bg-black/40 border-b border-white/10 flex items-center px-stack-md gap-stack-sm">
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]/60" />
                      <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]/60" />
                      <div className="w-2.5 h-2.5 rounded-full bg-primary/60" />
                    </div>
                    <div className="mx-auto font-mono text-[10px] text-primary/70 tracking-widest">
                      TRUVIA · THREAT_INTEL_LIVE
                    </div>
                  </div>
                  <div className="p-stack-lg space-y-stack-md relative">
                    <div className="grid grid-cols-2 gap-stack-md">
                      <div className="rounded-xl bg-white/5 border border-white/10 p-card-padding">
                        <p className="font-mono text-[10px] text-primary/70 uppercase">Active Signals</p>
                        <p className="text-[40px] leading-none font-heading font-extrabold bg-gradient-to-r from-primary to-secondary-container bg-clip-text text-transparent">
                          <CountUp to={1284} />
                        </p>
                      </div>
                      <div className="rounded-xl bg-white/5 border border-white/10 p-card-padding">
                        <p className="font-mono text-[10px] text-primary/70 uppercase">Rings Detected</p>
                        <p className="text-[40px] leading-none font-heading font-extrabold bg-gradient-to-r from-primary to-secondary-container bg-clip-text text-transparent">
                          <CountUp to={37} />
                        </p>
                      </div>
                    </div>
                    <div className="rounded-xl bg-white/5 border border-white/10 p-card-padding">
                      <div className="flex items-center justify-between mb-stack-md">
                        <span className="font-mono text-[11px] text-on-surface-variant tracking-widest">THREAT VELOCITY</span>
                        <Icon name="monitoring" className="text-primary text-[18px]" />
                      </div>
                      <div className="h-36 flex items-end gap-1.5">
                        {[30, 55, 40, 85, 60, 95, 70, 82, 48].map((h, i) => (
                          <motion.div
                            key={i}
                            className="flex-1 rounded-t origin-bottom"
                            style={{ height: `${h}%`, background: "linear-gradient(to top, rgba(101,138,255,0.25), #b5c4ff)" }}
                            initial={{ scaleY: 0.1, opacity: 0.4 }}
                            animate={{ scaleY: 1, opacity: 1 }}
                            transition={{ duration: 0.7, delay: 0.5 + i * 0.06, ease: EASE }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* ============ METRICS ============ */}
        <section className="bg-surface border-y border-white/10 py-stack-lg">
          <div className="container mx-auto px-stack-lg lg:px-margin-page grid grid-cols-2 lg:grid-cols-4 gap-stack-lg">
            {METRICS.map((m, i) => (
              <Reveal key={m.label} delay={i * 0.08} className="flex flex-col items-center lg:items-start">
                <span className="text-headline-lg font-heading text-secondary-container drop-shadow-[0_0_12px_rgba(0,244,254,0.4)] font-extrabold">
                  <CountUp to={m.to} decimals={m.decimals} suffix={m.suffix} />
                </span>
                <span className="font-mono text-outline text-[11px] uppercase tracking-widest mt-1">{m.label}</span>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ============ MODULES ============ */}
        <section id="modules" className="bg-background py-24 relative">
          <div className="container mx-auto px-stack-lg lg:px-margin-page">
            <Reveal className="text-center max-w-2xl mx-auto mb-stack-lg">
              <span className="font-mono text-secondary-container tracking-[0.3em] uppercase text-[11px]">Three Modules · One Graph</span>
              <h2 className="text-headline-lg font-heading text-on-surface mt-stack-sm">An intelligence layer for everyone in the fight</h2>
            </Reveal>
            <motion.div variants={containerStagger} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-80px" }} className="grid grid-cols-1 md:grid-cols-3 gap-stack-lg">
              {MODULES.map((m) => (
                <motion.div
                  key={m.title}
                  variants={itemUp}
                  whileHover={{ y: -6 }}
                  className="group relative p-stack-lg rounded-2xl glass-panel overflow-hidden"
                >
                  <div className="absolute -top-16 -right-16 w-40 h-40 bg-secondary-container/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="w-14 h-14 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-stack-md group-hover:scale-110 transition-transform">
                    <Icon name={m.icon} className="text-secondary-container text-[26px]" fill />
                  </div>
                  <span className="font-mono text-[10px] text-secondary-container/70 uppercase tracking-widest">{m.tag}</span>
                  <h3 className="font-heading text-headline-sm text-on-surface mt-1 mb-stack-sm">{m.title}</h3>
                  <p className="text-body-md text-on-surface-variant leading-relaxed">{m.body}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ============ FEATURES ============ */}
        <section id="features" className="bg-surface border-y border-white/10 py-24">
          <div className="container mx-auto px-stack-lg lg:px-margin-page">
            <Reveal className="text-center max-w-2xl mx-auto mb-stack-lg">
              <span className="font-mono text-secondary-container tracking-[0.3em] uppercase text-[11px]">System Capabilities</span>
              <h2 className="text-headline-lg font-heading text-on-surface mt-stack-sm">Engineered for high-density intelligence</h2>
            </Reveal>
            <motion.div variants={containerStagger} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-80px" }} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-stack-md">
              {FEATURES.map((f) => (
                <motion.div
                  key={f.title}
                  variants={itemUp}
                  whileHover={{ y: -5 }}
                  className="group rounded-2xl glass-panel p-stack-lg"
                >
                  <div className="w-12 h-12 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center mb-stack-md group-hover:scale-110 group-hover:rotate-3 transition-transform">
                    <Icon name={f.icon} className="text-secondary-container" fill />
                  </div>
                  <h3 className="font-heading text-headline-sm text-on-surface mb-stack-sm">{f.title}</h3>
                  <p className="text-body-md text-on-surface-variant leading-relaxed">{f.body}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ============ HOW IT WORKS ============ */}
        <section id="how-it-works" className="bg-background py-24 relative overflow-hidden">
          <div className="container mx-auto px-stack-lg lg:px-margin-page relative z-10">
            <Reveal className="mb-stack-lg">
              <span className="font-mono text-secondary-container tracking-[0.3em] uppercase text-[11px]">Precision Protocol</span>
              <h2 className="text-headline-lg font-heading text-on-surface mt-stack-sm">From raw evidence to tactical intelligence</h2>
            </Reveal>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-stack-lg relative">
              {STEPS.map((s, i) => (
                <Reveal key={s.n} delay={i * 0.12} className="relative">
                  <div className="flex flex-col gap-stack-md p-stack-lg rounded-2xl glass-panel h-full">
                    <div className="w-12 h-12 rounded-xl border border-secondary-container/50 text-secondary-container flex items-center justify-center font-mono text-[16px] font-bold neon-glow">
                      {s.n}
                    </div>
                    <h4 className="font-heading text-headline-sm text-on-surface">{s.title}</h4>
                    <p className="text-body-md text-on-surface-variant leading-relaxed">{s.body}</p>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className="hidden md:block absolute top-1/2 -right-3 w-6 h-px bg-gradient-to-r from-secondary-container/60 to-transparent" />
                  )}
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ============ CTA ============ */}
        <section className="bg-background py-28 relative overflow-hidden">
          <div className="absolute inset-0 grid-overlay opacity-40" />
          <div className="container mx-auto px-stack-lg lg:px-margin-page relative z-10">
            <Reveal className="max-w-4xl mx-auto text-center p-stack-lg lg:p-margin-page rounded-3xl glass-panel primary-glow">
              <h2 className="text-headline-lg lg:text-display-lg font-heading bg-gradient-to-r from-primary to-secondary-container bg-clip-text text-transparent mb-stack-md">Ready to deploy intelligence?</h2>
              <p className="text-[17px] text-on-surface-variant max-w-xl mx-auto mb-stack-lg leading-relaxed">
                Join the premier network for digital defense and predictive public safety enforcement.
              </p>
              <div className="flex flex-col sm:flex-row justify-center gap-stack-md">
                <Link href="/auth" className="btn-bloom btn-shimmer text-on-primary-container font-heading font-semibold rounded-xl px-6 py-3 inline-flex items-center justify-center gap-2">
                  <Icon name="rocket_launch" />
                  Enroll in Citizen Shield
                </Link>
                <Link href="/auth" className="btn-shimmer inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl border border-white/10 bg-white/5 text-on-surface hover:border-secondary-container/40 hover:text-secondary-container transition-colors">
                  Request Agency Demo
                </Link>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ============ FOOTER ============ */}
        <footer className="bg-background border-t border-white/10 py-stack-lg">
          <div className="container mx-auto px-stack-lg lg:px-margin-page flex flex-col md:flex-row justify-between items-center gap-stack-md">
            <div className="flex items-center gap-stack-sm">
              <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
                <Icon name="shield_lock" className="text-primary text-[16px]" fill />
              </div>
              <span className="text-headline-md font-heading font-extrabold text-on-surface tracking-tight">Truvia</span>
            </div>
            <div className="flex gap-stack-lg font-mono text-[10px] text-outline uppercase tracking-widest">
              <span>© 2026 TRUVIA COMMAND</span>
              <span className="hover:text-secondary-container transition-colors cursor-pointer">PRIVACY</span>
              <span className="hover:text-secondary-container transition-colors cursor-pointer">TERMS</span>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
