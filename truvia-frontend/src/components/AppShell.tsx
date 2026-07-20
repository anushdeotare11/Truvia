"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { Icon } from "./Icon";
import { useAuth } from "@/lib/auth";
import { NAV_ITEMS, homeForRole } from "@/lib/nav";

function titleForPath(pathname: string): string {
  const match = NAV_ITEMS.find(
    (i) => pathname === i.href || pathname.startsWith(i.href + "/")
  );
  return match?.name ?? "Truvia Intelligence";
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  // Redirect unauthenticated users to the auth page.
  useEffect(() => {
    if (!loading && !user) {
      router.replace("/auth");
    }
  }, [loading, user, router]);

  // Enforce role-based access to the current route.
  useEffect(() => {
    if (loading || !user) return;
    const match = NAV_ITEMS.find(
      (i) => pathname === i.href || pathname.startsWith(i.href + "/")
    );
    if (match && !match.roles.includes(user.role)) {
      router.replace(homeForRole(user.role));
    }
  }, [loading, user, pathname, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-stack-md">
          <div className="w-12 h-12 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
          <span className="font-label-md text-on-surface-variant uppercase tracking-widest text-[11px]">
            Authenticating
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <Header title={titleForPath(pathname)} onMenuClick={() => setMenuOpen(true)} />
      <main className="lg:ml-sidebar-width pt-header-height min-h-screen">
        {children}
      </main>
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center py-stack-lg">
      <div className="flex items-center gap-stack-md text-on-surface-variant">
        <Icon name="progress_activity" className="animate-spin text-accent" />
        <span className="font-label-md uppercase tracking-widest text-[11px]">Loading</span>
      </div>
    </div>
  );
}
