"use client";

import { useEffect } from "react";
import { useAuth } from "@/context/auth-context";
import { useRouter } from "next/navigation";
import { Shield } from "lucide-react";

export default function RootPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.push("/login");
      } else {
        if (user.role === "citizen") {
          router.push("/fraud-shield");
        } else if (user.role === "officer") {
          router.push("/officer/dashboard");
        } else if (user.role === "admin") {
          router.push("/admin/users");
        }
      }
    }
  }, [user, isLoading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-canvas text-text-primary">
      <div className="flex flex-col items-center gap-4">
        <Shield className="h-12 w-12 text-brand-primary animate-pulse" />
        <p className="text-sm font-semibold tracking-wide text-text-secondary uppercase">
          Verifying security context...
        </p>
      </div>
    </div>
  );
}
