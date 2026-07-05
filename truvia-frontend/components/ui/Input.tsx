import React, { forwardRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  sizeVariant?: "md" | "lg";
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, helperText, error, sizeVariant = "md", type = "text", id, ...props }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
    
    return (
      <div className="flex flex-col gap-1.5 w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-semibold uppercase tracking-wider text-text-primary"
          >
            {label}
          </label>
        )}
        <input
          id={inputId}
          type={type}
          ref={ref}
          className={twMerge(
            clsx(
              "w-full px-3 transition-all duration-150 bg-bg-surface border rounded-md text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-3 focus:ring-brand-primary/35",
              sizeVariant === "md" ? "h-10 text-base" : "h-12 text-lg",
              error
                ? "border-severity-critical focus:border-severity-critical focus:ring-severity-critical/35"
                : "border-border-default focus:border-brand-primary",
              className
            )
          )}
          {...props}
        />
        {error ? (
          <span className="flex items-center gap-1 text-xs font-medium text-severity-critical">
            <svg
              className="w-3.5 h-3.5 fill-none stroke-current"
              viewBox="0 0 24 24"
              strokeWidth="2.5"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            {error}
          </span>
        ) : helperText ? (
          <span className="text-xs text-text-secondary">{helperText}</span>
        ) : null}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;
