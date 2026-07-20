"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "./Icon";
import { useAuth } from "@/lib/auth";
import { navForRole } from "@/lib/nav";

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const items = user ? navForRole(user.role) : [];

  // Role-based primary CTA (label + destination). Citizens file reports;
  // officers/admins open case work.
  const cta =
    user?.role === "citizen"
      ? { label: "New Report", href: "/fraud-shield", icon: "add" }
      : { label: "New Case", href: "/investigations", icon: "add" };

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-[55] lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed left-0 top-0 h-screen w-sidebar-width bg-surface-container-lowest/90 backdrop-blur-2xl border-r border-white/5 shadow-[20px_0_40px_rgba(0,0,0,0.5)] flex flex-col z-[60] transition-transform duration-300 ${
          open ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0`}
      >
        {/* Logo lockup */}
        <div className="px-card-padding pt-stack-lg pb-stack-md flex items-center gap-stack-sm">
          <div className="w-10 h-10 bg-primary/15 border border-primary/25 rounded-lg flex items-center justify-center">
            <Icon name="security" className="text-primary text-[24px]" fill />
          </div>
          <div className="flex flex-col">
            <span className="text-headline-sm font-heading font-bold text-primary tracking-tight leading-tight">
              TRUVIA
            </span>
            <span className="font-label-md text-[10px] text-on-surface-variant -mt-0.5 uppercase tracking-widest">
              Intelligence
            </span>
          </div>
        </div>

        {/* Profile card */}
        <div className="px-stack-md pb-stack-md">
          <div className="rounded-2xl bg-white/[0.03] border border-white/5 p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-surface-container-highest flex items-center justify-center text-on-surface-variant shrink-0">
              <Icon name="account_circle" className="text-[24px]" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-heading font-bold text-on-surface truncate leading-tight">
                {user?.name ?? "—"}
              </span>
              <span className="text-[10px] uppercase tracking-wider text-outline truncate">
                {user?.role ?? ""}
              </span>
            </div>
          </div>
        </div>

        <nav className="flex-1 mt-stack-sm px-stack-sm space-y-1 overflow-y-auto custom-scrollbar">
          {items.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={`${item.name}-${item.href}`}
                href={item.href}
                onClick={onClose}
                className={`flex items-center gap-4 px-4 py-3 rounded-xl transition-all ${
                  active
                    ? "bg-primary-container/20 text-primary border-l-4 border-primary shadow-lg shadow-primary/10 translate-x-1"
                    : "text-on-surface-variant hover:bg-white/5 hover:text-on-surface"
                }`}
              >
                <Icon name={item.icon} fill={active} />
                <span className="font-body-md">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-stack-md border-t border-white/5 space-y-stack-sm">
          <Link
            href={cta.href}
            onClick={onClose}
            className="w-full py-3 rounded-2xl bg-gradient-to-r from-primary to-secondary-container text-on-primary-container font-label-md primary-glow hover:scale-[1.02] transition-transform flex items-center justify-center gap-2"
          >
            <Icon name={cta.icon} className="text-[20px]" />
            {cta.label}
          </Link>
          {user?.role === "admin" && (
            <Link
              href="/admin/system-health"
              onClick={onClose}
              className="flex items-center justify-center gap-2 py-2 text-[11px] uppercase tracking-widest text-on-surface-variant hover:text-secondary-container transition-colors"
            >
              <Icon name="monitor_heart" className="text-[16px]" />
              System Status
            </Link>
          )}
        </div>
      </aside>
    </>
  );
}
