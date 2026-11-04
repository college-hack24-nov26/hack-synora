"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/Button";
import { LogOut, User as UserIcon, Wallet, Bell, Sparkles, ShieldCheck, Settings } from "lucide-react";

export function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-30 px-4 sm:px-8 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-slate-900 text-base sm:text-lg tracking-tight block leading-tight">
              Finance<span className="text-blue-600">AI</span>
            </span>
            <span className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase block">
              Personal Wealth
            </span>
          </div>
        </Link>
      </div>

      <div className="flex items-center gap-3">
        {user && (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-xs font-medium text-slate-600">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Currency: <strong>{user.currency || "INR"} (₹)</strong></span>
            <span className="text-slate-300">|</span>
            <span>{user.timezone || "Asia/Kolkata"}</span>
          </div>
        )}

        {user ? (
          <div className="flex items-center gap-2">
            <Link href="/privacy">
              <Button
                variant="ghost"
                size="sm"
                title="Privacy & Trust (6 Promises)"
                className="text-slate-500 hover:text-blue-600 hover:bg-blue-50 hidden sm:flex items-center gap-1.5"
              >
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-semibold">Trust & Privacy</span>
              </Button>
            </Link>
            <Link href="/settings">
              <Button
                variant="ghost"
                size="sm"
                title="Privacy Settings"
                className="text-slate-500 hover:text-slate-800 hover:bg-slate-100"
              >
                <Settings className="w-4 h-4" />
              </Button>
            </Link>
            <div className="flex items-center gap-2.5 pl-2">
              <div className="w-9 h-9 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="hidden md:block text-left">
                <p className="text-xs font-bold text-slate-800 leading-none">{user.name}</p>
                <p className="text-[11px] text-slate-500 truncate max-w-[140px] leading-tight mt-0.5">{user.email}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              title="Sign Out"
              className="text-slate-500 hover:text-rose-600 hover:bg-rose-50"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/register">
              <Button variant="primary" size="sm">
                Get Started
              </Button>
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}

