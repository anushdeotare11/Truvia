"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/auth-context";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Link from "next/link";
import { Shield } from "lucide-react";

export default function LoginPage() {
  const { login, error, isLoading, clearError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [validationErrors, setValidationErrors] = useState<{ email?: string; password?: string }>({});

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    
    // Simple client-side validation
    const errors: { email?: string; password?: string } = {};
    if (!email) errors.email = "Email is required";
    if (!password) errors.password = "Password is required";
    
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }
    
    setValidationErrors({});
    try {
      await login(email, password);
    } catch (err) {
      // Error handled by AuthContext
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg-canvas px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-primary text-text-on-brand shadow-md">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-3xl font-bold tracking-tight text-text-primary">
            Truvia
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            AI-Powered Digital Public Safety Intelligence Platform
          </p>
        </div>

        {/* Login Form Card */}
        <Card className="p-8">
          <h2 className="text-xl font-bold text-text-primary mb-6">
            Log in to your account
          </h2>

          {error && (
            <div className="mb-4 rounded-md bg-severity-critical/10 p-3 border border-severity-critical/20 flex items-start gap-2">
              <svg
                className="h-5 w-5 text-severity-critical shrink-0 mt-0.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span className="text-sm font-medium text-severity-critical">{error}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <Input
              label="Email Address"
              type="email"
              placeholder="e.g. citizen@truvia.org"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (validationErrors.email) {
                  setValidationErrors((prev) => ({ ...prev, email: undefined }));
                }
              }}
              error={validationErrors.email}
              disabled={isLoading}
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (validationErrors.password) {
                  setValidationErrors((prev) => ({ ...prev, password: undefined }));
                }
              }}
              error={validationErrors.password}
              disabled={isLoading}
            />

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer text-text-secondary">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-border-default text-brand-primary focus:ring-brand-primary/35"
                />
                Remember me
              </label>
              <Link
                href="/forgot-password"
                className="font-medium text-brand-primary hover:underline"
              >
                Forgot password?
              </Link>
            </div>

            <Button
              type="submit"
              className="w-full mt-2"
              isLoading={isLoading}
            >
              Sign In
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-text-secondary">
            New citizen?{" "}
            <Link
              href="/register"
              className="font-semibold text-brand-primary hover:underline"
            >
              Register here
            </Link>
          </div>
        </Card>
        
        {/* Footer info */}
        <p className="text-center text-xs text-text-secondary">
          Restricted access for authorized citizens and cybercrime officers only.
        </p>
      </div>
    </div>
  );
}
