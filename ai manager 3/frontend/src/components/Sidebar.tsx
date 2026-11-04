"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Receipt,
  CreditCard,
  Tags,
  FileSpreadsheet,
  PieChart,
  ShieldCheck,
  Settings,
  Lock,
} from "lucide-react";

const navigation = [
  { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { name: "Transactions", href: "/transactions", icon: Receipt },
  { name: "Accounts", href: "/accounts", icon: CreditCard },
  { name: "Categories", href: "/categories", icon: Tags },
  { name: "Import Statements", href: "/import", icon: FileSpreadsheet, badge: "AI" },
  { name: "Analytics & Trends", href: "/analytics", icon: PieChart },
];

const privacyNavigation = [
  { name: "Privacy & Trust", href: "/privacy", icon: ShieldCheck, badge: "6 Promises" },
  { name: "Privacy Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-200 bg-white min-h-[calc(100vh-4rem)] p-4 flex flex-col justify-between hidden md:flex">
      <div className="space-y-4">
        <div className="space-y-1">
          <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
            Workspace
          </p>
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group",
                  isActive
                    ? "bg-blue-50 text-blue-700 font-semibold shadow-sm shadow-blue-100"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      "w-4 h-4 transition-colors",
                      isActive ? "text-blue-600" : "text-slate-400 group-hover:text-slate-600"
                    )}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-md bg-blue-100 text-blue-700">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>

        <div className="space-y-1 pt-2 border-t border-slate-100">
          <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
            Trust & Security
          </p>
          {privacyNavigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group",
                  isActive
                    ? "bg-blue-50 text-blue-700 font-semibold shadow-sm shadow-blue-100"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      "w-4 h-4 transition-colors",
                      isActive ? "text-blue-600" : "text-slate-400 group-hover:text-slate-600"
                    )}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-md bg-emerald-100 text-emerald-800">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </div>

      {/* Indian Banking & Compliance banner */}
      <Link href="/privacy" className="block group">
        <div className="p-3.5 rounded-2xl bg-gradient-to-br from-slate-50 to-blue-50/50 border border-slate-200/60 text-xs transition-colors group-hover:border-blue-300">
          <div className="flex items-center gap-2 font-bold text-slate-800 mb-1">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Encrypted & India Ready</span>
          </div>
          <p className="text-slate-500 text-[11px] leading-relaxed">
            Protected by our 6 Privacy & Trust promises. Zero funds movement.
          </p>
        </div>
      </Link>
    </aside>
  );
}

