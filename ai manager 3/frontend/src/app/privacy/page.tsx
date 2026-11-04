"use client";

import React from "react";
import Link from "next/link";
import { AppLayout } from "@/components/AppLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  DataIsolationSection,
  WhoCanUseItSection,
  HowDataIsStoredSection,
  HowWeCategorizeSection,
} from "@/components/TrustSections";
import {
  ShieldCheck,
  Minimize2,
  Lock,
  UserCheck,
  Ban,
  FileSpreadsheet,
  CheckCircle2,
  ArrowRight,
  Settings,
  Sparkles,
  KeyRound,
  FileText,
} from "lucide-react";

export default function PrivacyPage() {
  const promises = [
    {
      id: 1,
      number: "01",
      title: "Explicit Permission Before Any Access",
      tagline: "We ask users for permission before accessing financial messages or uploading statements.",
      icon: ShieldCheck,
      color: "text-blue-600 bg-blue-50 border-blue-200",
      details: [
        "Granular consent is required at the point of use for SMS messages and statement uploads.",
        "Nothing is pre-checked or assumed; you must explicitly click 'Allow'.",
        "You can revoke your consent at any time from Privacy Settings.",
      ],
      backendEnforcement: "Protected by backend consent middleware returning HTTP 403 Forbidden on unconsented imports.",
    },
    {
      id: 2,
      number: "02",
      title: "Strict Financial Data Minimization",
      tagline: "We only process the financial data required for expense tracking and predictions.",
      icon: Minimize2,
      color: "text-emerald-600 bg-emerald-50 border-emerald-200",
      details: [
        "Only essential fields (amount, date, merchant, direction, category, last 4 digits) are saved.",
        "One-Time Passwords (OTPs), verification codes, and promotional messages are discarded immediately.",
        "Raw financial message text and full card numbers are never logged or stored.",
      ],
      backendEnforcement: "Enforced by automated regex sanitization, OTP discard filters, and card number redaction.",
    },
    {
      id: 3,
      number: "03",
      title: "Protected With Encryption in Transit and at Rest",
      tagline: "Financial records are protected with encryption in transit and at rest.",
      icon: Lock,
      color: "text-indigo-600 bg-indigo-50 border-indigo-200",
      details: [
        "Field-level encryption at rest using Fernet cryptography (AES-128 in CBC mode with HMAC).",
        "Raw merchant details, transaction descriptions, and uploaded filenames are stored in ciphertext.",
        "TLS/HTTPS encryption in transit with Strict-Transport-Security (HSTS) and anti-sniff headers.",
      ],
      backendEnforcement: "Backed by custom SQLAlchemy EncryptedText TypeDecorator and Fernet secret keys.",
    },
    {
      id: 4,
      number: "04",
      title: "Isolated Per-User Access Control",
      tagline: "Each user can access only their own financial information.",
      icon: UserCheck,
      color: "text-purple-600 bg-purple-50 border-purple-200",
      details: [
        "Every single database query and API endpoint is strictly filtered by your authenticated user ID.",
        "No user can ever view, query, modify, or delete another user's accounts, statements, or transactions.",
        "Bank staff can view only demo accounts or customers who have explicitly agreed to share their data. Access is read-only, masked and logged.",
        "Complete data export (JSON) and self-service account data erasure with password verification.",
      ],
      backendEnforcement: "Verified by automated multi-tenant isolation, 404 shielding on unconsented client records, and immutable audit logs.",
    },
    {
      id: 5,
      number: "05",
      title: "Zero Money Movement or Transaction Execution",
      tagline: "We never perform transactions or transfer money on behalf of users.",
      icon: Ban,
      color: "text-rose-600 bg-rose-50 border-rose-200",
      details: [
        "This platform is strictly an analytical, read-only dashboard.",
        "The application has zero code, credentials, or integrations to initiate payments, debits, or transfers.",
        "Your bank credentials and net-banking passwords are never asked for or handled.",
      ],
      backendEnforcement: "Read-only architecture by design with no payment gateway or fund-movement APIs.",
    },
    {
      id: 6,
      number: "06",
      title: "Flexible Statements & Completely Optional SMS",
      tagline: "SMS reading is optional; users can upload CSV or PDF instead.",
      icon: FileSpreadsheet,
      color: "text-amber-600 bg-amber-50 border-amber-200",
      details: [
        "You are never forced to share or paste SMS messages to use the finance manager.",
        "Full support for uploading digital bank statements in CSV and text-based PDF formats.",
        "Manual expense logging is always available for cash payments and offline spends.",
      ],
      backendEnforcement: "Independent ingestion pipelines for CSV, PDF, and manual entry with in-memory parsing.",
    },
  ];

  return (
    <AppLayout>
      <div className="space-y-8 max-w-5xl mx-auto pb-12">
        {/* Hero Header */}
        <div className="text-center sm:text-left space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold tracking-wide uppercase">
            <ShieldCheck className="w-4 h-4" />
            <span>Privacy & Trust Framework</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Our 6 Privacy & Trust Promises
          </h1>
          <p className="text-base text-slate-600 max-w-3xl leading-relaxed">
            Personal financial data is deeply sensitive. We built this application with privacy and security as structural guarantees, not afterthoughts. Every promise below is actively enforced by real code.
          </p>
        </div>

        {/* 6 Promises Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {promises.map((p) => {
            const Icon = p.icon;
            return (
              <Card key={p.id} className="flex flex-col justify-between hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-black tracking-widest text-slate-400">
                      PROMISE {p.number}
                    </span>
                    <div className={`p-2 rounded-xl border ${p.color}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                  </div>
                  <CardTitle className="text-lg font-bold text-slate-900 leading-snug">
                    {p.title}
                  </CardTitle>
                  <CardDescription className="text-slate-600 font-medium mt-1">
                    "{p.tagline}"
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-4 pt-0">
                  <ul className="space-y-2 text-xs text-slate-600">
                    {p.details.map((detail, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                        <span>{detail}</span>
                      </li>
                    ))}
                  </ul>

                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] text-slate-600 font-mono">
                    <span className="font-bold text-slate-700 block mb-0.5">Code Enforcement:</span>
                    {p.backendEnforcement}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Section A: Multi-User Isolation Flow */}
        <div className="pt-4 border-t border-slate-200">
          <DataIsolationSection />
        </div>

        {/* Structured Transaction Storage Demonstration */}
        <div className="pt-4 border-t border-slate-200">
          <HowDataIsStoredSection />
        </div>

        {/* How We Categorize Section */}
        <div className="pt-4 border-t border-slate-200">
          <HowWeCategorizeSection />
        </div>

        {/* Section B: Who Can Use It */}
        <div className="pt-4 border-t border-slate-200">
          <WhoCanUseItSection />
        </div>

        {/* Quick Actions Panel */}
        <Card className="bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 text-white border-0 shadow-xl">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6 p-2">
            <div className="space-y-2 text-center sm:text-left">
              <div className="inline-flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase tracking-widest">
                <KeyRound className="w-4 h-4" />
                <span>Your Data, Your Ownership</span>
              </div>
              <h3 className="text-xl font-bold text-white">
                Manage your permissions and exported records
              </h3>
              <p className="text-sm text-slate-300 max-w-xl">
                Review your active consent records, export your full financial history as JSON, or permanently wipe all statements at any time.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link href="/settings">
                <Button variant="primary" size="md" className="bg-blue-600 hover:bg-blue-500 text-white">
                  <Settings className="w-4 h-4 mr-2" />
                  Privacy Settings
                </Button>
              </Link>
              <Link href="/import">
                <Button variant="outline" size="md" className="bg-white/10 hover:bg-white/20 text-white border-white/20">
                  <FileText className="w-4 h-4 mr-2" />
                  Import Statements
                </Button>
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}

