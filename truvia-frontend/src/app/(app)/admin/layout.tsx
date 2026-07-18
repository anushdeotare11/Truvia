"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { homeForRole } from "@/lib/nav";
import { PageLoader } from "@/components/AppShell";

/** Admin console is admin-only (App Flow §2.5). Backend also enforces via
 * deps.require_admin (403); this guard prevents non-admins rendering the shell. */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user && user.role !== "admin") {
      router.replace(homeForRole(user.role));
    }
  }, [loading, user, router]);

  if (loading || !user || user.role !== "admin") return <PageLoader />;
  return <>{children}</>;
}
