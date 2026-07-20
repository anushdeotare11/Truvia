"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Icon } from "./Icon";
import { useAuth } from "@/lib/auth";

// Officer/Intelligence "oversight" surfaces an admin can cross into (App Flow §9).
// When an admin is viewing one of these, the header shows a persistent "Admin View"
// badge to signal they are outside their own /admin/* console.
const OVERSIGHT_PREFIXES = ["/dashboard", "/investigations", "/my-cases", "/reports", "/intelligence", "/threat-intel"];

export function Header({
  title,
  onMenuClick,
}: {
  title: string;
  onMenuClick: () => void;
}) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const showAdminView =
    user?.role === "admin" &&
    OVERSIGHT_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/") || pathname.startsWith(p + "?"));

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function handleLogout() {
    // §10.4 Logout confirmation. Uses the same native-confirm gate the app
    // already uses for its other confirmations, rather than a new dialog pattern.
    if (!confirm("Log out of Truvia?")) return;
    await logout();
    router.push("/auth");
  }

  return (
    <header className="fixed top-0 right-0 h-header-height w-full lg:w-[calc(100%-260px)] bg-surface/80 backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-stack-md gap-stack-md z-40">
      <div className="flex items-center gap-stack-md flex-1 min-w-0">
        <button
          className="lg:hidden p-2 text-on-surface-variant hover:text-primary transition-colors"
          onClick={onMenuClick}
          aria-label="Open menu"
        >
          <Icon name="menu" />
        </button>
        <span className="font-heading font-semibold text-primary hidden sm:block whitespace-nowrap text-[18px]">
          {title}
        </span>
        {showAdminView && (
          <span
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-tertiary/15 text-tertiary border border-tertiary/30 text-[10px] font-bold uppercase tracking-wider whitespace-nowrap"
            title="You are viewing an officer/intelligence surface as an administrator"
          >
            <Icon name="visibility" className="text-[14px]" fill />
            Admin View
          </span>
        )}
        <div className="relative w-full max-w-md hidden md:block">
          <Icon
            name="search"
            className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]"
          />
          <input
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 font-body-md text-on-surface placeholder:text-outline focus:ring-1 focus:ring-secondary-container/50 focus:border-secondary-container/30 outline-none transition-all"
            placeholder="Search cases, entities, reports..."
            type="text"
          />
        </div>
      </div>

      <div className="flex items-center gap-stack-md">
        <button className="relative p-2 text-on-surface-variant hover:text-primary transition-colors rounded-lg hover:bg-white/5">
          <Icon name="notifications" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-secondary-container rounded-full border-2 border-surface" />
        </button>
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-stack-sm pl-stack-md border-l border-white/10"
          >
            <span className="font-label-md text-on-surface-variant hidden sm:block max-w-[140px] truncate">
              {user?.name ?? ""}
            </span>
            <div className="w-8 h-8 rounded-full bg-primary/15 border border-primary/30 flex items-center justify-center text-primary">
              <Icon name="account_circle" className="text-[20px]" />
            </div>
          </button>
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-surface-container border border-white/10 rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-50">
              <div className="p-stack-md border-b border-white/10">
                <p className="font-body-md text-on-surface font-semibold truncate">
                  {user?.name}
                </p>
                <p className="font-label-md text-[11px] text-on-surface-variant truncate">
                  {user?.email}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-stack-md px-stack-md py-stack-sm text-on-surface-variant hover:bg-white/5 hover:text-error transition-colors"
              >
                <Icon name="logout" className="text-[20px]" />
                <span className="font-body-md">Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
