import React, { forwardRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "tertiary" | "destructive" | "icon-only";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", isLoading, disabled, children, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center font-medium transition-all duration-150 rounded-md focus:outline-none focus:ring-3 focus:ring-brand-primary/35 disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]";
    
    const variants = {
      primary: "bg-brand-primary text-text-on-brand hover:bg-brand-primary-hover border border-transparent",
      secondary: "bg-transparent text-brand-primary hover:bg-brand-primary/10 border border-brand-primary",
      tertiary: "bg-transparent text-text-secondary hover:bg-bg-surface-hover hover:text-text-primary border border-transparent",
      destructive: "bg-severity-critical text-text-on-brand hover:bg-severity-critical/90 border border-transparent",
      "icon-only": "bg-transparent text-text-secondary hover:bg-bg-surface-hover hover:text-text-primary border border-transparent p-2 rounded-full active:scale-95"
    };

    const sizes = {
      sm: "h-8 px-3 text-sm",
      md: "h-10 px-4 text-base",
      lg: "h-12 px-6 text-lg"
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={twMerge(
          clsx(
            baseStyles,
            variants[variant],
            variant !== "icon-only" && sizes[size],
            className
          )
        )}
        {...props}
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <svg
              className="animate-spin h-5 w-5 text-current"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            {variant !== "icon-only" && <span>Loading...</span>}
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
