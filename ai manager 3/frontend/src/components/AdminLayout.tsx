"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { AdminSidebar } from "@/components/AdminSidebar";
import { Loader2, ShieldAlert, Sparkles, Building2, UserCircle } from "lucide-react";

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    } else if (!isLoading && isAuthenticated && user?.role !== "admin") {
      router.push("/dashboard");
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
          Authenticating Bank Staff Session...
        </p>
      </div>
    );
  }

  if (!isAuthenticated || user?.role !== "admin") {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100">
      {/* Top Admin Navbar */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-4 sm:px-8 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/admin" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-100 tracking-tight text-base">FinTrack AI</span>
                <span className="text-[10px] uppercase font-extrabold tracking-wider px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                  Bank Staff
                </span>
              </div>
            </div>
          </Link>

          <div className="hidden lg:flex items-center gap-2 pl-4 border-l border-slate-800">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Read-Only Data Isolation Active
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex flex-col text-right">
            <span className="text-xs font-semibold text-slate-200">{user.name || "Staff Admin"}</span>
            <span className="text-[11px] text-slate-400">{user.email}</span>
          </div>
          <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
            <UserCircle className="w-5 h-5 text-indigo-400" />
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex bg-slate-950">
        <AdminSidebar />
        <main className="flex-1 p-4 sm:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

