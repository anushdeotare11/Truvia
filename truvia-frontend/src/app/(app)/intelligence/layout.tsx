"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { homeForRole } from "@/lib/nav";
import { PageLoader } from "@/components/AppShell";

/**
 * Threat Intelligence Engine is restricted to officer/admin (App Flow §2.5).
 * The backend enforces this too (deps.require_officer -> 403); this guard keeps
 * citizens from ever rendering the surface client-side.
 */
export default function IntelligenceLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user && !["officer", "admin"].includes(user.role)) {
      router.replace(homeForRole(user.role));
    }
  }, [loading, user, router]);

  if (loading || !user || !["officer", "admin"].includes(user.role)) {
    return <PageLoader />;
  }
  return <>{children}</>;
}
