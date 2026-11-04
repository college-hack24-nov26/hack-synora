"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/formatters";
import { AdminLayout } from "@/components/AdminLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import {
  Users,
  ArrowLeft,
  ShieldCheck,
  Lock,
  Wallet,
  Receipt,
  PieChart as PieChartIcon,
  Target,
  Sparkles,
  FileSpreadsheet,
  AlertTriangle,
  UserX,
  UserCheck,
  Loader2,
  Calendar,
  Building2,
  CheckCircle2,
  Clock,
  ChevronLeft,
  ChevronRight,
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
} from "recharts";

interface Customer360Data {
  profile: {
    id: string;
    name: string;
    masked_email: string;
    currency: string;
    timezone: string;
    segment?: string;
    is_active: boolean;
    is_demo: boolean;
    created_at: string;
  };
  accounts: Array<{
    id: string;
    name: string;
    type: string;
    masked_account_number: string;
    opening_balance_minor: number;
    current_balance_minor: number;
  }>;
  transactions: Array<{
    id: string;
    txn_date: string;
    merchant_normalized?: string;
    amount_minor: number;
    direction: string;
    currency: string;
    category_name?: string;
    category_icon?: string;
    category_color?: string;
    category_source: string;
    category_confidence: number;
    source: string;
    needs_review: boolean;
  }>;
  total_transactions: number;
  category_breakdown: Array<{
    category_name: string;
    color?: string;
    total_spend_minor: number;
    percentage: number;
  }>;
  monthly_trend: Array<{
    month: string;
    spend_minor: number;
    transactions_count: number;
  }>;
  budgets: Array<{
    category_id: string;
    category_name: string;
    month: string;
    limit_minor: number;
    actual_spent_minor: number;
    status: string;
  }>;
  prediction?: {
    predicted_month_end_minor: number;
    spent_so_far_minor: number;
    days_elapsed: number;
    days_in_month: number;
    confidence_level: string;
    historical_baseline_minor: number;
    run_rate_projection_minor: number;
  };
  consent_status: Array<{
    id: string;
    consent_type: string;
    granted: boolean;
    granted_at: string;
    revoked_at?: string;
    policy_version: string;
  }>;
  imports: Array<{
    id: string;
    source_type: string;
    status: string;
    total_rows: number;
    parsed_rows: number;
    failed_rows: number;
    error_summary?: string;
    created_at: string;
  }>;
}

export default function Customer360Page() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const customerId = params?.id as string;

  const [activeTab, setActiveTab] = useState<
    "summary" | "transactions" | "analytics" | "budgets" | "prediction" | "consent"
  >("summary");
  const [txPage, setTxPage] = useState(1);
  const [statusModalOpen, setStatusModalOpen] = useState(false);

  const { data, isLoading, isError, error } = useQuery<Customer360Data>({
    queryKey: ["admin_customer_360", customerId, txPage],
    queryFn: () => apiRequest<Customer360Data>(`/admin/customers/${customerId}?page=${txPage}&limit=15`),
    enabled: !!customerId,
  });

  const statusMutation = useMutation({
    mutationFn: ({ is_active }: { is_active: boolean }) =>
      apiRequest(`/admin/customers/${customerId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin_customer_360", customerId] });
      queryClient.invalidateQueries({ queryKey: ["admin_customers"] });
      setStatusModalOpen(false);
    },
    onError: (err: any) => {
      alert(err.message || "Failed to update status.");
    },
  });

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="py-24 text-center text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-indigo-500 mb-3" />
          <p className="text-sm">Retrieving Customer 360 profile & auditing access...</p>
        </div>
      </AdminLayout>
    );
  }

  if (isError || !data) {
    return (
      <AdminLayout>
        <div className="py-16 max-w-lg mx-auto text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 text-rose-400 mx-auto flex items-center justify-center">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white">Customer Not Accessible (404)</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            This customer record does not exist or does not meet the bank staff data-sharing policy.
            Per strict multi-user privacy guarantees, customer financial records remain invisible without an active "share_with_bank" consent.
          </p>
          <Link href="/admin/customers">
            <Button size="sm" variant="outline" className="border-slate-800 text-slate-300">
              <ArrowLeft className="w-4 h-4 mr-1.5" />
              Return to Customer Registry
            </Button>
          </Link>
        </div>
      </AdminLayout>
    );
  }

  const { profile, accounts, transactions, total_transactions, category_breakdown, monthly_trend, budgets, prediction, consent_status, imports } = data;

  const totalTxPages = Math.ceil(total_transactions / 15) || 1;

  const trendData = monthly_trend.map((m) => ({
    name: m.month,
    spend: Math.round(m.spend_minor / 100),
  }));

  const catData = category_breakdown.map((c) => ({
    name: c.category_name,
    value: Math.round(c.total_spend_minor / 100),
    color: c.color || "#6366f1",
  }));

  return (
    <AdminLayout>
      <div className="space-y-6 pb-12">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Link href="/admin/customers" className="hover:text-indigo-400 transition-colors flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Customers Registry</span>
          </Link>
          <span>/</span>
          <span className="text-white font-medium">{profile.name}</span>
        </div>

        {/* Read-Only Compliance Banner */}
        <div className="p-4 rounded-2xl bg-indigo-950/60 border border-indigo-800/50 flex items-start gap-3 text-xs text-indigo-200">
          <Lock className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-white">
              Bank Staff Read-Only Access — {profile.is_demo ? "Demo Persona Profile" : "Consented Customer Profile"}
            </p>
            <p className="text-indigo-300/80 text-[11px] mt-0.5 leading-relaxed">
              This access is being logged under compliance policy with your administrative staff ID. Customer financial data cannot be edited, deleted, or transferred from this terminal.
            </p>
          </div>
        </div>

        {/* Profile Header Bar */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white font-bold text-lg shadow-md shadow-indigo-600/20">
              {profile.name.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">{profile.name}</h1>
                <Badge variant={profile.is_active ? "success" : "danger"} className="text-[10px]">
                  {profile.is_active ? "Active Account" : "Deactivated"}
                </Badge>
                {profile.is_demo ? (
                  <Badge variant="outline" className="bg-indigo-950 text-indigo-400 border-indigo-800 text-[10px]">
                    Demo Persona
                  </Badge>
                ) : (
                  <Badge variant="outline" className="bg-emerald-950 text-emerald-400 border-emerald-800 text-[10px]">
                    Consented Customer
                  </Badge>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1 font-mono">
                <span>{profile.masked_email}</span>
                <span>•</span>
                <span className="capitalize font-sans">{profile.segment || "General"}</span>
                <span>•</span>
                <span className="font-sans">Joined {formatDate(profile.created_at)}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setStatusModalOpen(true)}
              className={
                profile.is_active
                  ? "border-rose-900/60 text-rose-400 hover:bg-rose-950/60 bg-slate-900 text-xs"
                  : "border-emerald-900/60 text-emerald-400 hover:bg-emerald-950/60 bg-slate-900 text-xs"
              }
            >
              {profile.is_active ? (
                <>
                  <UserX className="w-3.5 h-3.5 mr-1.5" />
                  Deactivate Customer
                </>
              ) : (
                <>
                  <UserCheck className="w-3.5 h-3.5 mr-1.5" />
                  Reactivate Customer
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-1 overflow-x-auto text-xs font-semibold">
          {[
            { id: "summary", label: "Summary & Accounts", icon: Wallet },
            { id: "transactions", label: `Transactions (${total_transactions})`, icon: Receipt },
            { id: "analytics", label: "Categories & Trends", icon: PieChartIcon },
            { id: "budgets", label: "Budgets vs Actual", icon: Target },
            { id: "prediction", label: "Spending Prediction", icon: Sparkles },
            { id: "consent", label: "Consent & Ingestion", icon: ShieldCheck },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl transition-all whitespace-nowrap ${isActive
                    ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/30"
                    : "text-slate-400 hover:text-white hover:bg-slate-900"
                  }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab 1: Summary & Accounts */}
        {activeTab === "summary" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-xs uppercase font-semibold text-slate-400">Total Linked Accounts</span>
                <p className="text-2xl font-bold text-white">{accounts.length}</p>
                <p className="text-[11px] text-slate-400">Savings, current, credit cards & wallets</p>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-xs uppercase font-semibold text-slate-400">Current Month Spend</span>
                <p className="text-2xl font-bold text-white">
                  {formatCurrency(prediction?.spent_so_far_minor || 0)}
                </p>
                <p className="text-[11px] text-slate-400">Total non-deleted debit transactions</p>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-xs uppercase font-semibold text-slate-400">Projected Month-End</span>
                <p className="text-2xl font-bold text-indigo-400">
                  {formatCurrency(prediction?.predicted_month_end_minor || 0)}
                </p>
                <p className="text-[11px] text-slate-400">
                  Confidence: <span className="capitalize text-emerald-400 font-semibold">{prediction?.confidence_level || "Medium"}</span>
                </p>
              </div>
            </div>

            {/* Accounts List */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <h3 className="text-base font-bold text-white">Linked Customer Accounts</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {accounts.map((acc) => (
                  <div key={acc.id} className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-slate-200">{acc.name}</span>
                      <span className="font-mono text-xs text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/40">
                        {acc.masked_account_number}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-850">
                      <span>Type: <strong className="capitalize text-slate-300">{acc.type.replace(/_/g, " ")}</strong></span>
                      <span>Balance: <strong className="text-emerald-400">{formatCurrency(acc.current_balance_minor)}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Transactions */}
        {activeTab === "transactions" && (
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">Customer Transaction History</h3>
                <p className="text-xs text-slate-400">
                  Read-only view with normalized merchants and categorization details.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] uppercase font-bold text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Merchant</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-medium">
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-slate-850/60">
                      <td className="px-4 py-3 text-slate-400">{formatDate(tx.txn_date)}</td>
                      <td className="px-4 py-3 font-semibold text-white">
                        {tx.merchant_normalized || "Unspecified"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: tx.category_color || "#6b7280" }}
                          />
                          <span>{tx.category_name || "Uncategorized"}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[10px] uppercase font-semibold text-slate-400">
                          {tx.category_source}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[10px] uppercase font-bold text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                          {tx.source}
                        </span>
                      </td>
                      <td
                        className={`px-4 py-3 text-right font-bold ${tx.direction === "credit" ? "text-emerald-400" : "text-slate-100"
                          }`}
                      >
                        {tx.direction === "credit" ? "+" : "-"}
                        {formatCurrency(tx.amount_minor)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between text-xs text-slate-400 pt-3 border-t border-slate-800">
              <span>Page {txPage} of {totalTxPages}</span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={txPage <= 1}
                  onClick={() => setTxPage((p) => Math.max(1, p - 1))}
                  className="border-slate-800 bg-slate-950 text-slate-300 disabled:opacity-40"
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={txPage >= totalTxPages}
                  onClick={() => setTxPage((p) => p + 1)}
                  className="border-slate-800 bg-slate-950 text-slate-300 disabled:opacity-40"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Categories & Trends */}
        {activeTab === "analytics" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <h3 className="text-base font-bold text-white">6-Month Spending Trend</h3>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData}>
                    <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", color: "#fff" }} />
                    <Area type="monotone" dataKey="spend" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <h3 className="text-base font-bold text-white">Current Month Category Distribution</h3>
              <div className="h-64 w-full flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={catData} innerRadius={50} outerRadius={80} dataKey="value">
                      {catData.map((e, idx) => (
                        <Cell key={`cell-${idx}`} fill={e.color} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", color: "#fff" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Budgets */}
        {activeTab === "budgets" && (
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-white">Monthly Budgets & Category Thresholds</h3>
            {budgets.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {budgets.map((b) => {
                  const pct = Math.min(100, Math.round((b.actual_spent_minor / b.limit_minor) * 100));
                  return (
                    <div key={b.category_id} className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-white">{b.category_name}</span>
                        <Badge
                          variant={b.status === "exceeded" ? "danger" : b.status === "warning" ? "warning" : "success"}
                          className="text-[10px]"
                        >
                          {b.status}
                        </Badge>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${b.status === "exceeded" ? "bg-rose-500" : "bg-indigo-500"}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Spent: {formatCurrency(b.actual_spent_minor)}</span>
                        <span>Limit: {formatCurrency(b.limit_minor)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-500">No active budgets configured for this month.</p>
            )}
          </div>
        )}

        {/* Tab 5: Prediction */}
        {activeTab === "prediction" && prediction && (
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6">
            <div>
              <h3 className="text-base font-bold text-white">Deterministic Month-End Spend Projection</h3>
              <p className="text-xs text-slate-400">
                Explainable statistical model combining historical baseline weighted moving average and run-rate projections.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
                <span className="text-[11px] text-slate-400 uppercase font-semibold">Predicted Total</span>
                <p className="text-2xl font-bold text-indigo-400">{formatCurrency(prediction.predicted_month_end_minor)}</p>
              </div>
              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
                <span className="text-[11px] text-slate-400 uppercase font-semibold">Historical Baseline</span>
                <p className="text-xl font-bold text-slate-200">{formatCurrency(prediction.historical_baseline_minor)}</p>
              </div>
              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
                <span className="text-[11px] text-slate-400 uppercase font-semibold">Run-Rate Estimate</span>
                <p className="text-xl font-bold text-slate-200">{formatCurrency(prediction.run_rate_projection_minor)}</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/40 text-xs text-indigo-200 leading-relaxed">
              <strong>Progress:</strong> Day {prediction.days_elapsed} of {prediction.days_in_month} completed. As the month progresses, dynamic blending increases weighting toward the actual pacing run-rate.
            </div>
          </div>
        )}

        {/* Tab 6: Consent & Ingestion */}
        {activeTab === "consent" && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <h3 className="text-base font-bold text-white">Active Consent Records</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {consent_status.map((c) => (
                  <div key={c.id} className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-white capitalize">
                        {c.consent_type.replace(/_/g, " ")}
                      </span>
                      <Badge variant={c.granted ? "success" : "danger"} className="text-[10px]">
                        {c.granted ? "Granted" : "Revoked"}
                      </Badge>
                    </div>
                    <div className="text-xs text-slate-400 space-y-1">
                      <p>Granted At: {formatDate(c.granted_at)}</p>
                      <p>Policy Version: v{c.policy_version}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <h3 className="text-base font-bold text-white">Statement Ingestion Jobs</h3>
              {imports.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] uppercase font-bold text-slate-400">
                      <tr>
                        <th className="px-4 py-2.5">Date</th>
                        <th className="px-4 py-2.5">Format</th>
                        <th className="px-4 py-2.5">Status</th>
                        <th className="px-4 py-2.5">Parsed</th>
                        <th className="px-4 py-2.5">Failed</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80">
                      {imports.map((im) => (
                        <tr key={im.id}>
                          <td className="px-4 py-2.5 text-slate-400">{formatDate(im.created_at)}</td>
                          <td className="px-4 py-2.5 uppercase font-bold text-slate-200">{im.source_type}</td>
                          <td className="px-4 py-2.5">
                            <Badge variant={im.status === "done" ? "success" : "danger"} className="text-[10px]">
                              {im.status}
                            </Badge>
                          </td>
                          <td className="px-4 py-2.5 text-emerald-400">{im.parsed_rows}</td>
                          <td className="px-4 py-2.5 text-rose-400">{im.failed_rows}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-slate-500">No statement ingestion history.</p>
              )}
            </div>
          </div>
        )}

        {/* Deactivation Modal */}
        <Modal
          isOpen={statusModalOpen}
          onClose={() => setStatusModalOpen(false)}
          title={profile.is_active ? "Deactivate Customer Account" : "Reactivate Customer Account"}
        >
          <div className="space-y-4 text-slate-300 text-xs">
            <p>
              Confirm account status change for <strong className="text-white">{profile.name}</strong>?
            </p>
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setStatusModalOpen(false)}
                className="border-slate-700 text-slate-300"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => statusMutation.mutate({ is_active: !profile.is_active })}
                disabled={statusMutation.isPending}
                className={profile.is_active ? "bg-rose-600 text-white" : "bg-emerald-600 text-white"}
              >
                {statusMutation.isPending ? "Updating..." : profile.is_active ? "Deactivate" : "Reactivate"}
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </AdminLayout>
  );
}
