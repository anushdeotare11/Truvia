"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/auth-context";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Link from "next/link";
import { Shield } from "lucide-react";

export default function RegisterPage() {
  const { register, error, isLoading, clearError } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  
  const [validationErrors, setValidationErrors] = useState<{
    name?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
    acknowledged?: string;
  }>({});

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    // Client-side validations
    const errors: typeof validationErrors = {};
    if (!name) errors.name = "Full name is required";
    if (!email) errors.email = "Email is required";
    if (!password) {
      errors.password = "Password is required";
    } else if (password.length < 6) {
      errors.password = "Password must be at least 6 characters";
    }
    if (password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match";
    }
    if (!acknowledged) {
      errors.acknowledged = "You must acknowledge safety regulations to register";
    }

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    setValidationErrors({});
    try {
      await register(name, email, password, phone || undefined);
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

        {/* Register Form Card */}
        <Card className="p-8">
          <h2 className="text-xl font-bold text-text-primary mb-6">
            Create Citizen Account
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

          <form onSubmit={handleRegister} className="space-y-4">
            <Input
              label="Full Name"
              placeholder="e.g. Rahul Sharma"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (validationErrors.name) {
                  setValidationErrors((prev) => ({ ...prev, name: undefined }));
                }
              }}
              error={validationErrors.name}
              disabled={isLoading}
            />

            <Input
              label="Email Address"
              type="email"
              placeholder="e.g. rahul.sharma@example.com"
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
              label="Phone Number (Optional)"
              type="tel"
              placeholder="e.g. +91 98765 43210"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
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

            <Input
              label="Confirm Password"
              type="password"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                if (validationErrors.confirmPassword) {
                  setValidationErrors((prev) => ({ ...prev, confirmPassword: undefined }));
                }
              }}
              error={validationErrors.confirmPassword}
              disabled={isLoading}
            />

            <div className="flex flex-col gap-1.5 mt-2">
              <label className="flex items-start gap-2.5 cursor-pointer text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={acknowledged}
                  onChange={(e) => {
                    setAcknowledged(e.target.checked);
                    if (validationErrors.acknowledged) {
                      setValidationErrors((prev) => ({ ...prev, acknowledged: undefined }));
                    }
                  }}
                  className="h-4 w-4 mt-0.5 rounded border-border-default text-brand-primary focus:ring-brand-primary/35"
                />
                <span className="leading-tight">
                  I acknowledge that Truvia is a public safety platform. All reports submitted represent real evidence of fraud or scam activities.
                </span>
              </label>
              {validationErrors.acknowledged && (
                <span className="text-xs text-severity-critical font-medium">
                  {validationErrors.acknowledged}
                </span>
              )}
            </div>

            <Button
              type="submit"
              className="w-full mt-2"
              isLoading={isLoading}
            >
              Register & Sign In
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-text-secondary">
            Already registered?{" "}
            <Link
              href="/login"
              className="font-semibold text-brand-primary hover:underline"
            >
              Sign in here
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
