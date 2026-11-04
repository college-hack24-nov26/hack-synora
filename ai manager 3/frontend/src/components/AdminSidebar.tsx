"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  AlertTriangle,
  FileSpreadsheet,
  ShieldCheck,
  Lock,
  LogOut,
  Building2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const adminNavItems = [
  { name: "Overview", href: "/admin", icon: LayoutDashboard },
  { name: "Customers 360", href: "/admin/customers", icon: Users },
  { name: "Risk Alerts", href: "/admin/risk-alerts", icon: AlertTriangle, badge: "Live" },
  { name: "Statement Ingestion", href: "/admin/imports", icon: FileSpreadsheet },
  { name: "Access Audit Log", href: "/admin/audit-log", icon: ShieldCheck },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 text-slate-300 min-h-[calc(100vh-4rem)] p-4 flex flex-col justify-between hidden md:flex">
      <div className="space-y-6">
        {/* Admin context chip */}
        <div className="px-3 py-2.5 rounded-xl bg-indigo-950/60 border border-indigo-800/40 text-indigo-300 flex items-center gap-2.5">
          <Building2 className="w-4 h-4 text-indigo-400 shrink-0" />
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wider text-indigo-300">Bank Staff Portal</p>
            <p className="text-[11px] text-indigo-400/80 truncate">Read-Only Operations</p>
          </div>
        </div>

        {/* Navigation */}
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">
            Admin Monitoring
          </p>
          {adminNavItems.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/admin" && pathname?.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group",
                  isActive
                    ? "bg-indigo-600 text-white font-semibold shadow-md shadow-indigo-900/40"
                    : "text-slate-400 hover:bg-slate-800/80 hover:text-white"
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      "w-4 h-4 transition-colors",
                      isActive ? "text-white" : "text-slate-500 group-hover:text-slate-300"
                    )}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-400 border border-amber-500/30">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </div>

      {/* Compliance Notice & Logout */}
      <div className="space-y-3 pt-4 border-t border-slate-800">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-slate-300">
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span>Audit Logging Active</span>
          </div>
          <p className="text-[10px] text-slate-500 leading-tight">
            Every customer lookup is logged with timestamp & staff ID.
          </p>
        </div>

        <button
          onClick={() => logout()}
          className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out Admin</span>
        </button>
      </div>
    </aside>
  );
}

