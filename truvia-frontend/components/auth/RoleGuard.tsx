"use client";

import React, { useEffect } from "react";
import { useAuth } from "@/context/auth-context";
import { useRouter } from "next/navigation";
import { ShieldAlert, Loader2 } from "lucide-react";
import Button from "@/components/ui/Button";

interface RoleGuardProps {
  children: React.ReactNode;
  allowedRoles: ("citizen" | "officer" | "admin")[];
}

export default function RoleGuard({ children, allowedRoles }: RoleGuardProps) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-canvas text-text-primary">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-10 w-10 text-brand-primary animate-spin" />
          <p className="text-sm font-semibold tracking-wide text-text-secondary uppercase">
            Verifying security privileges...
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null; // Redirecting in useEffect
  }

  if (!allowedRoles.includes(user.role)) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-bg-canvas p-6 text-center">
        <div className="w-full max-w-md p-8 bg-bg-surface border border-border-default rounded-lg shadow-md space-y-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-severity-critical/10 text-severity-critical">
            <ShieldAlert className="h-10 w-10" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold tracking-tight text-text-primary">
              Access Denied
            </h2>
            <p className="text-sm text-text-secondary">
              Your account role ({user.role}) does not have permission to view this page. Access is restricted to authorized personnel.
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => {
              if (user.role === "citizen") {
                router.push("/fraud-shield");
              } else if (user.role === "officer") {
                router.push("/officer/dashboard");
              } else if (user.role === "admin") {
                router.push("/admin/users");
              }
            }}
            className="w-full"
          >
            Return to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
