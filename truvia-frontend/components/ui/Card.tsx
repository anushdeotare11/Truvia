import React, { forwardRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, hoverable = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={twMerge(
          clsx(
            "bg-bg-surface border border-border-default rounded-lg p-6 transition-all duration-150 shadow-[0_1px_2px_rgba(11,30,57,0.06)] dark:shadow-none",
            hoverable && "hover:border-brand-primary/50 hover:bg-bg-surface-hover hover:scale-[1.01] cursor-pointer",
            className
          )
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

export default Card;
