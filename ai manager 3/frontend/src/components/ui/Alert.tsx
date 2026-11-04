import React from "react";
import { AlertCircle, CheckCircle2, Info, XCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface AlertProps {
  type?: "info" | "success" | "warning" | "error";
  title?: string;
  message: string;
  className?: string;
  onClose?: () => void;
}

export function Alert({ type = "info", title, message, className, onClose }: AlertProps) {
  const styles = {
    info: {
      bg: "bg-blue-50 border-blue-200 text-blue-900",
      icon: <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />,
    },
    success: {
      bg: "bg-emerald-50 border-emerald-200 text-emerald-900",
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />,
    },
    warning: {
      bg: "bg-amber-50 border-amber-200 text-amber-900",
      icon: <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />,
    },
    error: {
      bg: "bg-rose-50 border-rose-200 text-rose-900",
      icon: <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />,
    },
  };

  const current = styles[type];

  return (
    <div
      className={cn(
        "flex gap-3 p-4 rounded-xl border text-sm leading-relaxed",
        current.bg,
        className
      )}
    >
      {current.icon}
      <div className="flex-1">
        {title && <h5 className="font-semibold text-sm mb-0.5">{title}</h5>}
        <div className="text-xs sm:text-sm">{message}</div>
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-lg opacity-60 hover:opacity-100 hover:bg-black/5 transition-opacity"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

