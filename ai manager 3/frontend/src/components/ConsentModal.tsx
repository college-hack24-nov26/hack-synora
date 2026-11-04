"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { CONSENT_COPY, ConsentContent } from "@/lib/consentCopy";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  ShieldCheck,
  ShieldAlert,
  Eye,
  TrendingUp,
  Ban,
  SlidersHorizontal,
  Wallet,
  X,
  ExternalLink,
  CheckCircle2,
  Lock,
  Globe,
} from "lucide-react";

export interface ConsentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAllow: () => void;
  consentType: "sms_import" | "statement_upload";
  isLoading?: boolean;
  initialLocale?: "en" | "hi" | "mr";
}

export function ConsentModal({
  isOpen,
  onClose,
  onAllow,
  consentType,
  isLoading = false,
  initialLocale = "en",
}: ConsentModalProps) {
  const [locale, setLocale] = useState<"en" | "hi" | "mr">(initialLocale);
  const modalRef = useRef<HTMLDivElement>(null);
  const allowButtonRef = useRef<HTMLButtonElement>(null);

  const copy: ConsentContent =
    CONSENT_COPY[locale]?.[consentType] || CONSENT_COPY.en[consentType];

  // Esc key and focus management
  useEffect(() => {
    if (!isOpen) return;

    // Focus primary button when modal opens
    const timer = setTimeout(() => {
      allowButtonRef.current?.focus();
    }, 50);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      // Simple focus trap
      if (e.key === "Tab" && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;

        const firstElement = focusable[0];
        const lastElement = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleKeyDown);
      clearTimeout(timer);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-modal-title"
      aria-describedby="consent-modal-desc"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 overflow-y-auto"
    >
      {/* Dimmed backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Card */}
      <div
        ref={modalRef}
        className="relative bg-white rounded-3xl shadow-2xl border border-slate-200/90 w-full max-w-xl max-h-[92vh] flex flex-col z-10 animate-in fade-in zoom-in-95 duration-200"
      >
        {/* Header with App Logo & Close */}
        <div className="p-5 sm:p-6 pb-4 border-b border-slate-100 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shadow-md shadow-blue-500/25 shrink-0">
              <Wallet className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-black uppercase tracking-wider text-blue-600">
                  FinTrack AI
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Permission Request
                </span>
              </div>
              <h2
                id="consent-modal-title"
                className="text-lg sm:text-xl font-black text-slate-900 tracking-tight leading-snug"
              >
                {copy.title}
              </h2>
              <p id="consent-modal-desc" className="text-xs text-slate-500 mt-1 leading-relaxed">
                {copy.subtitle}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {/* Quick Language Toggle */}
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-[11px] font-bold">
              {(["en", "hi", "mr"] as const).map((lang) => (
                <button
                  key={lang}
                  type="button"
                  onClick={() => setLocale(lang)}
                  className={`px-2 py-0.5 rounded-md uppercase transition-colors ${
                    locale === lang
                      ? "bg-white text-blue-700 shadow-xs"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                  aria-label={`Switch language to ${lang}`}
                >
                  {lang}
                </button>
              ))}
            </div>

            <button
              onClick={onClose}
              type="button"
              className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors ml-1"
              aria-label="Close permission dialog"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Scrollable Content Sections */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4 text-xs leading-relaxed">
          {/* Section 1: What we will access */}
          <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200/80">
            <h3 className="font-bold text-blue-900 text-xs sm:text-sm flex items-center gap-2 mb-2">
              <Eye className="w-4 h-4 text-blue-600 shrink-0" />
              {copy.whatWeAccessTitle}
            </h3>
            <ul className="space-y-1.5 text-slate-700 pl-6 list-disc">
              {copy.whatWeAccessPoints.map((point, idx) => (
                <li key={idx}>{point}</li>
              ))}
            </ul>
          </div>

          {/* Section 2: What we use it for */}
          <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200/80">
            <h3 className="font-bold text-emerald-900 text-xs sm:text-sm flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-emerald-600 shrink-0" />
              {copy.whatWeUseItForTitle}
            </h3>
            <ul className="space-y-1.5 text-slate-700 pl-6 list-disc">
              {copy.whatWeUseItForPoints.map((point, idx) => (
                <li key={idx}>{point}</li>
              ))}
            </ul>
          </div>

          {/* Section 3: What we will NOT do */}
          <div className="p-3.5 rounded-2xl bg-rose-50/70 border border-rose-200/80">
            <h3 className="font-bold text-rose-900 text-xs sm:text-sm flex items-center gap-2 mb-2">
              <Ban className="w-4 h-4 text-rose-600 shrink-0" />
              {copy.whatWeWillNotDoTitle}
            </h3>
            <ul className="space-y-1.5 text-slate-700 pl-6 list-disc">
              {copy.whatWeWillNotDoPoints.map((point, idx) => (
                <li key={idx}>{point}</li>
              ))}
            </ul>
          </div>

          {/* Section 4: Your control */}
          <div className="p-3.5 rounded-2xl bg-purple-50/70 border border-purple-200/80">
            <h3 className="font-bold text-purple-900 text-xs sm:text-sm flex items-center gap-2 mb-2">
              <SlidersHorizontal className="w-4 h-4 text-purple-600 shrink-0" />
              {copy.yourControlTitle}
            </h3>
            <ul className="space-y-1.5 text-slate-700 pl-6 list-disc">
              {copy.yourControlPoints.map((point, idx) => (
                <li key={idx}>{point}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Footer with Links and Clear Action Buttons */}
        <div className="p-5 sm:p-6 pt-3 border-t border-slate-100 bg-slate-50/50 rounded-b-3xl flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-[11px] text-slate-500 font-medium">
            <Link
              href="/privacy"
              target="_blank"
              className="hover:text-blue-600 underline underline-offset-2 flex items-center gap-1"
            >
              {copy.privacyPolicyText} <ExternalLink className="w-3 h-3" />
            </Link>
            <span>•</span>
            <Link
              href="/privacy"
              target="_blank"
              className="hover:text-blue-600 underline underline-offset-2"
            >
              {copy.termsText}
            </Link>
          </div>

          {/* Primary & Secondary Action: Single Clear Choice, Nothing Pre-Checked */}
          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <Button
              type="button"
              variant="outline"
              size="md"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 sm:flex-initial text-slate-700 border-slate-300 hover:bg-slate-100 font-medium text-xs sm:text-sm"
            >
              {copy.notNowButtonText}
            </Button>

            <Button
              ref={allowButtonRef}
              type="button"
              size="md"
              onClick={onAllow}
              isLoading={isLoading}
              className="flex-1 sm:flex-initial bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs sm:text-sm shadow-md shadow-blue-500/20"
            >
              <CheckCircle2 className="w-4 h-4 mr-1.5" />
              {copy.allowButtonText}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

