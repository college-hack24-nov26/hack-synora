"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { formatCurrency } from "@/lib/formatters";
import { AdminLayout } from "@/components/AdminLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Users,
  TrendingUp,
  AlertTriangle,
  Download,
  Activity,
  FileCheck2,
  PieChart as PieChartIcon,
  ShieldCheck,
  ArrowRight,
  Loader2,
  RefreshCw,
  Building2,
  IndianRupee,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from "recharts";

interface OverviewData {
  total_customers: number;
  active_customers_30d: number;
  total_tracked_spend_this_month: number;
  avg_monthly_spend_per_customer: number;
  total_transactions: number;
  import_success_rate: number;
  consented_customers_count: number;
  demo_customers_count: number;
  top_risk_customers: Array<{
    customer_id: string;
    name: string;
    masked_email: string;
    segment?: string;
    alert_type: string;
    severity: string;
    reason: string;
  }>;
}

interface AnalyticsData {
  spend_by_category: Array<{
    category_name: string;
    color: string;
    total_spend_minor: number;
    percentage: number;
  }>;
  monthly_spend_trend: Array<{
    month: string;
    spend_minor: number;
    transactions_count: number;
  }>;
  customer_segments: Array<{
    segment: string;
    customer_count: number;
    total_spend_minor: number;
  }>;
}

export default function AdminOverviewPage() {
  const { data: overview, isLoading: overviewLoading, refetch: refetchOverview } = useQuery<OverviewData>({
    queryKey: ["admin_overview"],
    queryFn: () => apiRequest<OverviewData>("/admin/overview"),
  });

  const { data: analytics, isLoading: analyticsLoading } = useQuery<AnalyticsData>({
    queryKey: ["admin_analytics"],
    queryFn: () => apiRequest<AnalyticsData>("/admin/analytics"),
  });

  const handleDownloadCsv = async () => {
    try {
      const token = localStorage.getItem("auth_token");
      const res = await fetch("http://localhost:8000/api/v1/admin/export/customers.csv", {
        headers: {
          Authorization: token ? `Bearer ${token}` : "",
        },
      });
      if (!res.ok) throw new Error("Failed to export CSV");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `masked_customers_summary_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      alert("Error downloading customer CSV export.");
    }
  };

  const trendChartData = (analytics?.monthly_spend_trend || []).map((m) => ({
    name: m.month,
    spend: Math.round(m.spend_minor / 100),
    txCount: m.transactions_count,
  }));

  const categoryChartData = (analytics?.spend_by_category || []).slice(0, 6).map((c) => ({
    name: c.category_name,
    value: Math.round(c.total_spend_minor / 100),
    color: c.color || "#6366f1",
  }));

  const segmentChartData = (analytics?.customer_segments || []).map((s) => ({
    name: s.segment,
    customers: s.customer_count,
    spend: Math.round(s.total_spend_minor / 100),
  }));

  return (
    <AdminLayout>
      <div className="space-y-8">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-md bg-indigo-950/80 border border-indigo-800 text-indigo-300 text-xs font-semibold mb-2">
              <Building2 className="w-3.5 h-3.5 text-indigo-400" />
              <span>Bank Staff Executive Dashboard</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Customer Analytics & Risk Overview
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Read-only aggregate metrics for demo customers and clients with active data sharing consent.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchOverview()}
              className="border-slate-700 text-slate-300 hover:bg-slate-800 bg-slate-900"
            >
              <RefreshCw className="w-4 h-4 mr-1.5" />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={handleDownloadCsv}
              className="bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30"
            >
              <Download className="w-4 h-4 mr-1.5" />
              Download Customers CSV
            </Button>
          </div>
        </div>

        {/* KPI Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Customers */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Visible Customers
              </span>
              <div className="p-2 rounded-xl bg-indigo-950 text-indigo-400 border border-indigo-800/60">
                <Users className="w-4 h-4" />
              </div>
            </div>
            <div>
              <p className="text-2xl sm:text-3xl font-extrabold text-white">
                {overviewLoading ? "..." : overview?.total_customers ?? 0}
              </p>
              <p className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                <span className="text-indigo-400 font-semibold">{overview?.demo_customers_count ?? 0} Demo</span>
                <span>•</span>
                <span className="text-emerald-400 font-semibold">{overview?.consented_customers_count ?? 0} Consented</span>
              </p>
            </div>
          </div>

          {/* Active 30 Days */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                30-Day Active Clients
              </span>
              <div className="p-2 rounded-xl bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                <Activity className="w-4 h-4" />
              </div>
            </div>
            <div>
              <p className="text-2xl sm:text-3xl font-extrabold text-white">
                {overviewLoading ? "..." : overview?.active_customers_30d ?? 0}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                With recent debits/credits in last 30 days
              </p>
            </div>
          </div>

          {/* Month Tracked Spend */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Total Month Spend
              </span>
              <div className="p-2 rounded-xl bg-purple-950 text-purple-400 border border-purple-800/60">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div>
              <p className="text-2xl sm:text-3xl font-extrabold text-white">
                {overviewLoading ? "..." : formatCurrency(overview?.total_tracked_spend_this_month)}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Avg {formatCurrency(overview?.avg_monthly_spend_per_customer)} / client
              </p>
            </div>
          </div>

          {/* Import Success Rate */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Import Pipeline
              </span>
              <div className="p-2 rounded-xl bg-amber-950 text-amber-400 border border-amber-800/60">
                <FileCheck2 className="w-4 h-4" />
              </div>
            </div>
            <div>
              <p className="text-2xl sm:text-3xl font-extrabold text-white">
                {overviewLoading ? "..." : `${overview?.import_success_rate ?? 100}%`}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {overview?.total_transactions ?? 0} total transactions indexed
              </p>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Monthly Spend Trend */}
          <div className="lg:col-span-2 p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">6-Month Client Spend Trend</h3>
                <p className="text-xs text-slate-400">Monthly aggregate debit transactions (in ₹)</p>
              </div>
              <Badge variant="outline" className="bg-slate-800 text-slate-300 border-slate-700">
                Aggregate
              </Badge>
            </div>

            <div className="h-64 w-full">
              {analyticsLoading ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                </div>
              ) : trendChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                    <YAxis
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                      tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "12px", color: "#fff" }}
                      formatter={(val: any) => [`₹${Number(val).toLocaleString("en-IN")}`, "Monthly Spend"]}
                    />
                    <Area type="monotone" dataKey="spend" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#spendGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                  No trend data available
                </div>
              )}
            </div>
          </div>

          {/* Category Donut */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
            <div>
              <h3 className="text-base font-bold text-white">Spend by Category</h3>
              <p className="text-xs text-slate-400">Top spending categories this month</p>
            </div>

            <div className="h-48 w-full flex items-center justify-center">
              {analyticsLoading ? (
                <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
              ) : categoryChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryChartData}
                      innerRadius={50}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {categoryChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "12px", color: "#fff" }}
                      formatter={(val: any) => [`₹${Number(val).toLocaleString("en-IN")}`, "Spend"]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-xs text-slate-500">No category data</p>
              )}
            </div>

            <div className="space-y-1.5 max-h-24 overflow-y-auto pr-1">
              {categoryChartData.slice(0, 4).map((c) => (
                <div key={c.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c.color }} />
                    <span className="text-slate-300 truncate max-w-[120px]">{c.name}</span>
                  </div>
                  <span className="font-semibold text-slate-200">₹{c.value.toLocaleString("en-IN")}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Segments and Risk Clients Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Customer Segments Bar Chart */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
            <div>
              <h3 className="text-base font-bold text-white">Customer Segments Distribution</h3>
              <p className="text-xs text-slate-400">Total spend and client counts per persona segment</p>
            </div>

            <div className="h-56 w-full">
              {analyticsLoading ? (
                <div className="h-full flex items-center justify-center">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                </div>
              ) : segmentChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={segmentChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                    <YAxis
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                      tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "12px", color: "#fff" }}
                      formatter={(val: any) => [`₹${Number(val).toLocaleString("en-IN")}`, "Monthly Spend"]}
                    />
                    <Bar dataKey="spend" fill="#818cf8" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-xs text-slate-500">No segment data</p>
              )}
            </div>
          </div>

          {/* Top Risk Alerts List */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">Active Risk Flags</h3>
                <p className="text-xs text-slate-400">Rule-based anomalies detected across clients</p>
              </div>
              <Link
                href="/admin/risk-alerts"
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                <span>View all</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-3">
              {overview?.top_risk_customers && overview.top_risk_customers.length > 0 ? (
                overview.top_risk_customers.map((c) => (
                  <Link
                    key={c.customer_id}
                    href={`/admin/customers/${c.customer_id}`}
                    className="block p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-slate-200">{c.name}</span>
                        <span className="text-xs text-slate-500 font-mono">({c.masked_email})</span>
                      </div>
                      <Badge
                        variant={c.severity === "high" ? "danger" : "warning"}
                        className="text-[10px] uppercase font-bold"
                      >
                        {c.alert_type.replace(/_/g, " ")}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">
                      {c.reason}
                    </p>
                  </Link>
                ))
              ) : (
                <div className="py-8 text-center text-slate-500 text-xs">
                  No active risk flags detected.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
