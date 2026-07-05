import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "low" | "moderate" | "high" | "critical" | "processing" | "indexed" | "escalated" | "assigned" | "default";
}

const Badge: React.FC<BadgeProps> = ({ className, variant = "default", children, ...props }) => {
  const baseStyles = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider";
  
  const variants = {
    // Severity Bands (background opacity is 12% / 0.12)
    low: "bg-severity-low/12 text-severity-low",
    moderate: "bg-severity-moderate/12 text-severity-moderate",
    high: "bg-severity-high/12 text-severity-high",
    critical: "bg-severity-critical/12 text-severity-critical",
    
    // Status/Metadata Bands
    processing: "bg-brand-primary/12 text-brand-primary animate-pulse",
    indexed: "bg-severity-low/12 text-severity-low",
    escalated: "bg-severity-critical/12 text-severity-critical",
    assigned: "bg-brand-primary/12 text-brand-primary",
    default: "bg-bg-surface-sunken text-text-secondary"
  };

  return (
    <span
      className={twMerge(
        clsx(baseStyles, variants[variant], className)
      )}
      {...props}
    >
      {children}
    </span>
  );
};

export default Badge;
