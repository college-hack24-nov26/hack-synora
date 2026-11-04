"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  DataIsolationSection,
  WhoCanUseItSection,
  HowDataIsStoredSection,
  HowWeCategorizeSection,
} from "@/components/TrustSections";
import {
  Wallet,
  ShieldCheck,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export default function HomePage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between text-slate-900 selection:bg-blue-100 selection:text-blue-900">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
              <Wallet className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold text-slate-900 tracking-tight text-base sm:text-lg">
                AI Personal Finance
              </span>
              <span className="text-[10px] uppercase font-bold tracking-widest text-blue-600 block -mt-1">
                Manager
              </span>
            </div>
          </Link>

          <nav className="flex items-center gap-2 sm:gap-4">
            <Link
              href="/privacy"
              className="text-xs sm:text-sm font-semibold text-slate-600 hover:text-blue-600 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Privacy & Trust</span>
            </Link>

            {isAuthenticated ? (
              <Link href="/dashboard">
                <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs sm:text-sm">
                  Go to Dashboard <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                </Button>
              </Link>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/login">
                  <Button variant="outline" size="sm" className="text-xs sm:text-sm">
                    Log In
                  </Button>
                </Link>
                <Link href="/register">
                  <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs sm:text-sm">
                    Get Started Free
                  </Button>
                </Link>
              </div>
            )}
          </nav>
        </div>
      </header>

      {/* Main Landing Page Content */}
      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-12 pb-16 md:pt-20 md:pb-24 border-b border-slate-200/80 bg-gradient-to-b from-white to-slate-50">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center">
            <Badge variant="default" className="mb-4 bg-blue-50 text-blue-700 border border-blue-200">
              <Sparkles className="w-3.5 h-3.5 mr-1 text-blue-600" />
              Next-Gen AI Finance & Statement Analytics
            </Badge>

            <h1 className="text-3xl sm:text-5xl md:text-6xl font-black text-slate-900 tracking-tight leading-tight sm:leading-tight">
              Smart Financial Tracking With{" "}
              <span className="text-blue-600 underline decoration-blue-300 underline-offset-8">
                Guaranteed Privacy
              </span>
            </h1>

            <p className="mt-5 text-base sm:text-lg md:text-xl text-slate-600 max-w-3xl mx-auto leading-relaxed">
              Track multi-bank accounts, analyze spending, forecast monthly budgets, and import statements in memory with zero cloud disk retention and absolute tenant data isolation.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link href="/register" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white font-semibold text-base shadow-md shadow-blue-500/20 px-8">
                  Get Started Free <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
              <Link href="/privacy" className="w-full sm:w-auto">
                <Button variant="outline" size="lg" className="w-full sm:w-auto text-base border-slate-300 text-slate-700 hover:bg-slate-100">
                  <ShieldCheck className="w-4 h-4 mr-2 text-emerald-600" />
                  Explore Our 6 Privacy Promises
                </Button>
              </Link>
            </div>

            {/* Quick trust metrics */}
            <div className="mt-12 grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto pt-8 border-t border-slate-200/60">
              <div className="text-center">
                <div className="text-lg font-bold text-slate-900">End-to-End</div>
                <div className="text-xs text-slate-500">AES-128 Encryption</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-slate-900">Read-Only</div>
                <div className="text-xs text-slate-500">Zero Money Movement</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-slate-900">In-Memory</div>
                <div className="text-xs text-slate-500">No Statement Storage</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-slate-900">Per-User</div>
                <div className="text-xs text-slate-500">Isolated Tenancy</div>
              </div>
            </div>
          </div>
        </section>

        {/* Section A: "Your data stays yours" */}
        <section className="py-12 bg-slate-50 border-b border-slate-200/80">
          <div className="max-w-6xl mx-auto px-4">
            <DataIsolationSection />
          </div>
        </section>

        {/* Structured Transaction Storage Demonstration */}
        <section className="py-12 bg-white border-b border-slate-200/80">
          <div className="max-w-6xl mx-auto px-4">
            <HowDataIsStoredSection />
          </div>
        </section>

        {/* How We Categorize 3-Step Pipeline */}
        <section className="py-12 bg-slate-50 border-b border-slate-200/80">
          <div className="max-w-6xl mx-auto px-4">
            <HowWeCategorizeSection />
          </div>
        </section>

        {/* Section B: "Who can use it?" */}
        <section className="py-12 bg-slate-50">
          <div className="max-w-6xl mx-auto px-4">
            <WhoCanUseItSection />
          </div>
        </section>

        {/* Bottom Call to Action */}
        <section className="py-16 bg-gradient-to-br from-slate-900 to-slate-800 text-white text-center">
          <div className="max-w-3xl mx-auto px-4">
            <h2 className="text-2xl sm:text-4xl font-black tracking-tight mb-4">
              Take Control of Your Personal Finances Today
            </h2>
            <p className="text-slate-300 text-sm sm:text-base mb-8 max-w-xl mx-auto">
              Join thousands of users managing budgets, expenses, and forecasts securely. No bank login credentials required.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link href="/register" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white font-semibold">
                  Create Your Free Account
                </Button>
              </Link>
              <Link href="/privacy" className="w-full sm:w-auto">
                <Button variant="outline" size="lg" className="w-full sm:w-auto border-slate-600 text-slate-200 hover:bg-slate-800">
                  Read Privacy Architecture
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-8 text-center text-xs text-slate-500">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-blue-600 flex items-center justify-center text-white">
              <Wallet className="w-3.5 h-3.5" />
            </div>
            <span className="font-bold text-slate-800">AI Personal Finance Manager</span>
          </div>
          <p>© {new Date().getFullYear()} AI Personal Finance Manager. All rights reserved. Read-only & analytical.</p>
          <div className="flex items-center gap-4 font-semibold text-slate-600">
            <Link href="/privacy" className="hover:text-blue-600">Privacy & Trust</Link>
            <Link href="/login" className="hover:text-blue-600">Log In</Link>
            <Link href="/register" className="hover:text-blue-600">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
