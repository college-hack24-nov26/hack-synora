import React from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", isLoading = false, children, disabled, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none rounded-xl";

    const variants = {
      primary:
        "bg-blue-600 hover:bg-blue-700 text-white shadow-sm shadow-blue-500/20 focus:ring-blue-500 active:scale-[0.98]",
      secondary:
        "bg-slate-100 hover:bg-slate-200 text-slate-800 focus:ring-slate-400 active:scale-[0.98]",
      outline:
        "border border-slate-300 hover:bg-slate-50 text-slate-700 focus:ring-slate-400 active:scale-[0.98]",
      danger:
        "bg-rose-600 hover:bg-rose-700 text-white shadow-sm shadow-rose-500/20 focus:ring-rose-500 active:scale-[0.98]",
      ghost:
        "text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:ring-slate-400",
    };

    const sizes = {
      sm: "text-xs px-3 py-1.5 gap-1.5",
      md: "text-sm px-4 py-2.5 gap-2",
      lg: "text-base px-6 py-3 gap-2.5",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && <Loader2 className="w-4 h-4 animate-spin text-current" />}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

