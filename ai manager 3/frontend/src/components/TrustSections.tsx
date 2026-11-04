"use client";

import React from "react";
import {
  KeyRound,
  UserCheck,
  Database,
  Server,
  ArrowRight,
  ArrowDown,
  GraduationCap,
  Briefcase,
  Store,
  ShieldCheck,
  CheckCircle2,
  Receipt,
  Fingerprint,
  Calendar,
  Tag,
  IndianRupee,
  Lock,
  Sparkles,
  SlidersHorizontal,
  CheckCheck,
  Quote,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export function DataIsolationSection() {
  const steps = [
    {
      number: "1",
      title: "Authentication",
      description: "You log in securely and get a personal token",
      icon: KeyRound,
      color: "bg-blue-50 text-blue-600 border-blue-200",
      pill: "Step 1",
    },
    {
      number: "2",
      title: "Authorization",
      description: "The system checks that you only ask for your own records",
      icon: UserCheck,
      color: "bg-indigo-50 text-indigo-600 border-indigo-200",
      pill: "Step 2",
    },
    {
      number: "3",
      title: "Database",
      description: "Every record is tied to your unique ID",
      icon: Database,
      color: "bg-emerald-50 text-emerald-600 border-emerald-200",
      pill: "Step 3",
    },
    {
      number: "4",
      title: "Backend",
      description: "Only your data is returned to you",
      icon: Server,
      color: "bg-purple-50 text-purple-600 border-purple-200",
      pill: "Step 4",
    },
  ];

  return (
    <section aria-labelledby="data-isolation-heading" className="w-full my-12">
      <div className="text-center max-w-3xl mx-auto mb-8">
        <Badge variant="default" className="mb-2 bg-blue-100 text-blue-800 hover:bg-blue-100">
          <ShieldCheck className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
          Multi-User Isolation
        </Badge>
        <h2
          id="data-isolation-heading"
          className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight"
        >
          Your data stays yours
        </h2>
        <p className="mt-2 text-sm sm:text-base text-slate-600 font-medium">
          Thousands of users can use the app at the same time, and each one only sees their own finances.
        </p>
      </div>

      {/* Horizontal step diagram on desktop, vertically stacked on mobile */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 max-w-6xl mx-auto px-4">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          return (
            <React.Fragment key={step.number}>
              <div className="w-full md:flex-1 bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow relative">
                <div className="flex items-center justify-between mb-3">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center border ${step.color}`}
                    aria-label={`${step.title} icon`}
                  >
                    <Icon className="w-5 h-5" aria-hidden="true" />
                  </div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    {step.pill}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-1.5">
                  <span className="text-blue-600 font-extrabold">{step.number}.</span> {step.title}
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                  {step.description}
                </p>
              </div>

              {/* Arrow connector */}
              {idx < steps.length - 1 && (
                <div
                  className="flex items-center justify-center text-slate-400 py-1 md:py-0 md:px-1 shrink-0"
                  aria-hidden="true"
                >
                  <ArrowRight className="hidden md:block w-5 h-5 text-slate-400" />
                  <ArrowDown className="md:hidden w-5 h-5 text-slate-400" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </section>
  );
}

export function WhoCanUseItSection() {
  const personas = [
    {
      title: "Students",
      description: "Track pocket money, fees and daily spending, and learn to save",
      icon: GraduationCap,
      color: "bg-amber-50 text-amber-600 border-amber-200",
      highlight: "Simple budgeting",
    },
    {
      title: "Working professionals",
      description: "Automatic expense categorization, monthly budgets and savings tips",
      icon: Briefcase,
      color: "bg-blue-50 text-blue-600 border-blue-200",
      highlight: "Zero hassle",
    },
    {
      title: "Small businesses / freelancers",
      description: "Separate accounts for business spending, clear spending reports and cash-flow predictions",
      icon: Store,
      color: "bg-emerald-50 text-emerald-600 border-emerald-200",
      highlight: "Account segregation",
    },
  ];

  return (
    <section aria-labelledby="who-can-use-heading" className="w-full my-12">
      <div className="text-center max-w-2xl mx-auto mb-8">
        <Badge variant="default" className="mb-2 bg-emerald-100 text-emerald-800 hover:bg-emerald-100">
          Designed for Everyone
        </Badge>
        <h2
          id="who-can-use-heading"
          className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight"
        >
          Who can use it?
        </h2>
        <p className="mt-2 text-sm sm:text-base text-slate-600">
          Built to give anyone clarity and confidence with their money, regardless of financial scale.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto px-4">
        {personas.map((item) => {
          const Icon = item.icon;
          return (
            <Card
              key={item.title}
              className="bg-white border-slate-200 hover:border-slate-300 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div
                    className={`w-12 h-12 rounded-2xl flex items-center justify-center border ${item.color}`}
                    aria-label={`${item.title} illustration icon`}
                  >
                    <Icon className="w-6 h-6" aria-hidden="true" />
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                    {item.highlight}
                  </span>
                </div>
                <CardTitle className="text-lg font-bold text-slate-900 mb-2">
                  {item.title}
                </CardTitle>
                <p className="text-sm text-slate-600 leading-relaxed">
                  {item.description}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center text-xs text-slate-500 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mr-1.5 shrink-0" aria-hidden="true" />
                Tailored views and exports
              </div>
            </Card>
          );
        })}
      </div>

      <p className="text-center text-sm font-medium text-slate-700 mt-8 max-w-xl mx-auto px-4">
        Easy to start, with no complicated setup: sign up and add your first statement in minutes.
      </p>
    </section>
  );
}

export function HowDataIsStoredSection() {
  const fields = [
    {
      num: 1,
      name: "Transaction ID",
      icon: Receipt,
      color: "bg-blue-50 text-blue-600 border-blue-200",
      description: "Unique UUID primary key",
      example: "9f8b2c41-8e7a-42d3-b108-62a5b6c93401",
      badge: "Indexed UUID",
    },
    {
      num: 2,
      name: "User ID",
      icon: Fingerprint,
      color: "bg-purple-50 text-purple-600 border-purple-200",
      description: "Owner FK to users, CASCADE delete",
      example: "usr_d4a19b88-2829-485f-b704-e058c69ad847",
      badge: "Tenant Scoped",
    },
    {
      num: 3,
      name: "Merchant Info",
      icon: Store,
      color: "bg-amber-50 text-amber-600 border-amber-200",
      description: "Encrypted raw text + cleaned name",
      example: "Swiggy Delivery (Raw: UPI-SWIGGY-192348)",
      badge: "Encrypted at Rest",
    },
    {
      num: 4,
      name: "Date of Transaction",
      icon: Calendar,
      color: "bg-emerald-50 text-emerald-600 border-emerald-200",
      description: "Stored in UTC, shown in your timezone",
      example: "04 Nov 2026, 01:15 PM (2026-11-04T07:45:00Z)",
      badge: "UTC / Localized",
    },
    {
      num: 5,
      name: "Category of Expense",
      icon: Tag,
      color: "bg-indigo-50 text-indigo-600 border-indigo-200",
      description: "Foreign key to category record",
      example: "Food & Dining (icon: utenvils, color: #10b981)",
      badge: "Categorized",
    },
    {
      num: 6,
      name: "Money Sent",
      icon: IndianRupee,
      color: "bg-rose-50 text-rose-600 border-rose-200",
      description: "Exact integer minor units (paise) + direction",
      example: "₹450.00 (45,000 paise, direction: debit)",
      badge: "Lossless Precision",
    },
  ];

  return (
    <section aria-labelledby="structured-storage-heading" className="w-full my-12">
      <div className="text-center max-w-3xl mx-auto mb-8">
        <Badge variant="default" className="mb-2 bg-purple-100 text-purple-800 hover:bg-purple-100">
          <Database className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
          Structured Storage & History
        </Badge>
        <h2
          id="structured-storage-heading"
          className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight"
        >
          How your data is stored
        </h2>
        <p className="mt-2 text-sm sm:text-base text-slate-600 font-medium">
          Every transaction record follows a strict, verifiable schema engineered for complete user isolation and cryptographic security.
        </p>
      </div>

      {/* Structured Card with Fake Data Demonstration */}
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-md overflow-hidden">
          {/* Card Header simulating a database record inspector */}
          <div className="bg-slate-900 text-white p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center border border-blue-400/30">
                <Receipt className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs uppercase font-bold tracking-wider text-slate-400 block">
                  Structured Transaction Record
                </span>
                <span className="font-mono text-sm font-semibold text-slate-200">
                  Transaction schema · 6 core parameters
                </span>
              </div>
            </div>
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <Lock className="w-3 h-3 mr-1" /> Multi-Tenant Isolated
            </span>
          </div>

          {/* 6 Core Fields Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-100">
            <div className="p-4 sm:p-6 space-y-4">
              {fields.slice(0, 3).map((f) => {
                const Icon = f.icon;
                return (
                  <div key={f.name} className="flex items-start gap-3.5">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border ${f.color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                          {f.num}. {f.name}
                        </span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                          {f.badge}
                        </span>
                      </div>
                      <p className="font-mono text-xs font-bold text-slate-900 mt-0.5 truncate">
                        {f.example}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {f.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="p-4 sm:p-6 space-y-4">
              {fields.slice(3, 6).map((f) => {
                const Icon = f.icon;
                return (
                  <div key={f.name} className="flex items-start gap-3.5">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border ${f.color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                          {f.num}. {f.name}
                        </span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                          {f.badge}
                        </span>
                      </div>
                      <p className="font-mono text-xs font-bold text-slate-900 mt-0.5 truncate">
                        {f.example}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {f.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Mandatory User Isolation Caption Box */}
          <div className="bg-slate-50 p-4 sm:p-5 border-t border-slate-200/90 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <p className="text-xs sm:text-sm font-semibold text-slate-700 leading-snug">
              Every user has a unique ID, and every transaction is stored under that ID only. Your history is separate from everyone else&apos;s.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function HowWeCategorizeSection() {
  const steps = [
    {
      step: 1,
      title: "Predefined Rules",
      badge: "Highest Priority",
      icon: SlidersHorizontal,
      color: "bg-blue-50 text-blue-600 border-blue-200",
      description:
        "First, we check your own custom Merchant Rules, then built-in rules for common Indian merchants and UPI codes (e.g. Swiggy → Food, Uber → Transport, Bescom → Utilities).",
      indicator: "category_source: rule (100% confidence)",
    },
    {
      step: 2,
      title: "Smart Model Suggestions",
      badge: "Fallback ML",
      icon: Sparkles,
      color: "bg-indigo-50 text-indigo-600 border-indigo-200",
      description:
        "If no rule matches, our model analyzes minimal non-PII details (merchant, description, amount, direction). Ambiguous items (<60% confidence) are flagged for your review.",
      indicator: "category_source: ml (confidence score)",
    },
    {
      step: 3,
      title: "Your Corrections Always Win",
      badge: "Absolute Control",
      icon: CheckCheck,
      color: "bg-emerald-50 text-emerald-600 border-emerald-200",
      description:
        "Whenever you change a category, your choice takes immediate precedence and you can set it to always apply to that merchant for future statements.",
      indicator: "category_source: user (overrides all)",
    },
  ];

  return (
    <section aria-labelledby="how-we-categorize-heading" className="w-full my-12">
      <div className="text-center max-w-3xl mx-auto mb-8">
        <Badge variant="default" className="mb-2 bg-indigo-100 text-indigo-800 hover:bg-indigo-100">
          <Sparkles className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
          Transparent Expense Separation
        </Badge>
        <h2
          id="how-we-categorize-heading"
          className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight"
        >
          How are my expenses separated?
        </h2>
        <p className="mt-2 text-sm sm:text-base text-slate-600 font-medium">
          A predictable 3-tier pipeline designed for clarity, data isolation, and user control.
        </p>
      </div>

      {/* 3-Step Visual Diagram */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 max-w-5xl mx-auto px-4">
        {steps.map((s, idx) => {
          const Icon = s.icon;
          return (
            <div
              key={s.step}
              className="bg-white rounded-2xl border border-slate-200/90 p-5 sm:p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between relative"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div
                    className={`w-11 h-11 rounded-xl flex items-center justify-center border ${s.color}`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                    Step {s.step}
                  </span>
                </div>

                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-base font-extrabold text-slate-900">{s.title}</h3>
                </div>

                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed mb-4">
                  {s.description}
                </p>
              </div>

              <div className="pt-3 border-t border-slate-100">
                <span className="font-mono text-[11px] font-semibold text-slate-500 block">
                  {s.indicator}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Mandatory Plain-Language Quote Box */}
      <div className="max-w-4xl mx-auto px-4 mt-8">
        <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-br from-indigo-50/80 via-blue-50/60 to-white border border-indigo-200/80 shadow-sm flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-sm">
            <Quote className="w-5 h-5" />
          </div>
          <div className="space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 block">
              Core Promise on Expense Categorization
            </span>
            <p className="text-xs sm:text-sm text-slate-800 font-semibold leading-relaxed">
              &ldquo;Our system uses predefined rules and model-based suggestions to sort your transactions into categories. Each transaction is stored with its own ID under your user ID, and we look at its details (merchant, description, amount and date) to decide the category. You can always correct it.&rdquo;
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

