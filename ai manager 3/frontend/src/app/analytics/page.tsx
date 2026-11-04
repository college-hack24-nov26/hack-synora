"use client";

import React from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { formatCurrency } from "@/lib/formatters";
import { useAuth } from "@/context/AuthContext";
import { AppLayout } from "@/components/AppLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  TrendingUp,
  Sparkles,
  PieChart as PieIcon,
  Lightbulb,
  ArrowDownRight,
  ArrowUpRight,
  ShieldCheck,
  Calendar,
  AlertTriangle,
  HelpCircle,
  FileSpreadsheet,
  CheckCircle2,
  Clock,
  Target,
  ArrowRight,
  Loader2,
  RefreshCw,
  Check,
  X,
} from "lucide-react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from "recharts";

interface CategoryPrediction {
  category_id: string | null;
  category_name: string;
  color: string;
  icon: string;
  spent_so_far_minor: number;
  predicted_minor: number;
  percentage_of_total: number;
  budget_limit_minor?: number | null;
  budget_exceeded: boolean;
}

interface MonthlyPrediction {
  has_enough_data: boolean;
  confidence: "none" | "low" | "medium" | "high";
  message?: string | null;
  current_month: string;
  days_elapsed: number;
  days_in_month: number;
  days_remaining: number;
  spent_so_far_minor: number;
  predicted_total_minor: number;
  lower_bound_minor: number;
  upper_bound_minor: number;
  projected_remaining_minor: number;
  daily_run_rate_minor: number;
  historical_baseline_minor: number;
  completed_months_count: number;
  vs_last_month_pct?: number | null;
  vs_last_month_diff_minor?: number | null;
  last_month_total_minor?: number | null;
  drivers: string[];
  recurring_expenses_detected: {
    merchant: string;
    typical_amount_minor: number;
    typical_day: number;
    already_billed_this_month: boolean;
  }[];
  category_breakdown: CategoryPrediction[];
}

interface ForecastHistoryItem {
  month: string;
  month_label: string;
  actual_minor: number;
  predicted_minor?: number | null;
  lower_bound_minor?: number | null;
  upper_bound_minor?: number | null;
  is_current: boolean;
}

interface SavingsSuggestionItem {
  id: string;
  type: string;
  title: string;
  detail: string;
  estimated_saving_minor: number;
  status: "new" | "accepted" | "dismissed";
  created_at: string;
}

export default function AnalyticsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // 1. Fetch current month prediction
  const {
    data: prediction,
    isLoading: predictionLoading,
    error: predictionError,
  } = useQuery<MonthlyPrediction>({
    queryKey: ["prediction-current-month"],
    queryFn: () => apiRequest<MonthlyPrediction>("/analytics/forecast/current-month"),
  });

  // 1b. Fetch AI Savings Suggestions & Insights
  const {
    data: insights = [],
    isLoading: insightsLoading,
  } = useQuery<SavingsSuggestionItem[]>({
    queryKey: ["analytics-insights"],
    queryFn: () => apiRequest<SavingsSuggestionItem[]>("/analytics/insights"),
  });

  const refreshInsightsMutation = useMutation({
    mutationFn: () => apiRequest<SavingsSuggestionItem[]>("/analytics/insights/refresh", { method: "POST" }),
    onSuccess: (newData) => {
      queryClient.setQueryData(["analytics-insights"], newData);
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "accepted" | "dismissed" }) =>
      apiRequest(`/analytics/insights/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["analytics-insights"] });
    },
  });

  // 2. Fetch forecast history
  const {
    data: history = [],
    isLoading: historyLoading,
  } = useQuery<ForecastHistoryItem[]>({
    queryKey: ["prediction-history"],
    queryFn: () => apiRequest<ForecastHistoryItem[]>("/analytics/forecast/history?months=6"),
  });

  // 3. Fetch spending by category
  const { data: categoryAnalytics = [] } = useQuery<any[]>({
    queryKey: ["analytics-by-category"],
    queryFn: () => apiRequest<any[]>("/analytics/by-category"),
  });

  // Prepare chart series
  const chartData = history.map((item, idx) => {
    const isCurrent = item.is_current;
    const actualVal = item.actual_minor ? Number(item.actual_minor) / 100 : 0;
    const predVal = item.predicted_minor ? Number(item.predicted_minor) / 100 : null;
    const lowVal = item.lower_bound_minor ? Number(item.lower_bound_minor) / 100 : null;
    const upVal = item.upper_bound_minor ? Number(item.upper_bound_minor) / 100 : null;

    return {
      month: item.month_label,
      actual: actualVal,
      projected: isCurrent ? predVal : null,
      range: isCurrent && lowVal !== null && upVal !== null ? [lowVal, upVal] : null,
      lowerBound: lowVal,
      upperBound: upVal,
      isCurrent,
    };
  });

  // Format month name
  const currentMonthDate = prediction?.current_month
    ? new Date(`${prediction.current_month}-01T00:00:00`)
    : new Date();
  const currentMonthName = currentMonthDate.toLocaleString("default", { month: "long" });

  const spentPercent =
    prediction && prediction.predicted_total_minor > 0
      ? Math.min(
          100,
          Math.round((prediction.spent_so_far_minor / prediction.predicted_total_minor) * 100)
        )
      : 0;

  return (
    <AppLayout>
      <div className="space-y-8 animate-in fade-in duration-300">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="info" className="text-[10px] uppercase font-bold tracking-wider">
                Statistical Intelligence
              </Badge>
              <Badge variant="default" className="text-[10px] font-semibold text-slate-500">
                Deterministic Model v1-stat
              </Badge>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Monthly Spending Prediction
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Estimating your final total for {currentMonthName} based on historical habits, current pace, and recurring expenses.
            </p>
          </div>

          <Link href="/import">
            <Button variant="outline" size="sm" className="shrink-0">
              <FileSpreadsheet className="w-4 h-4 mr-1.5" />
              Upload Latest Statement
            </Button>
          </Link>
        </div>

        {/* Prediction Loading State */}
        {predictionLoading ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-1 p-6 animate-pulse bg-slate-100 h-80" />
            <Card className="lg:col-span-2 p-6 animate-pulse bg-slate-100 h-80" />
          </div>
        ) : !prediction?.has_enough_data ? (
          /* Cold Start Empty State */
          <Card className="border-dashed border-2 border-slate-300 bg-gradient-to-b from-white to-slate-50 p-8 sm:p-12 text-center">
            <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4 border border-blue-200">
              <Sparkles className="w-7 h-7" />
            </div>
            <Badge variant="warning" className="mb-2">
              Cold Start • Need More Data
            </Badge>
            <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mb-2">
              Not enough data yet
            </h2>
            <p className="text-sm text-slate-600 max-w-lg mx-auto mb-6 leading-relaxed">
              {prediction?.message ||
                "Import at least 1 month of completed transactions to unlock deterministic statistical spending predictions, run-rate pacing, and recurring expense alerts."}
            </p>
            <div className="flex items-center justify-center gap-3">
              <Link href="/import">
                <Button variant="primary" size="md">
                  <FileSpreadsheet className="w-4 h-4 mr-2" />
                  Import Bank Statement (CSV / PDF / SMS)
                </Button>
              </Link>
            </div>
          </Card>
        ) : (
          /* Active Predictions View */
          <>
            {/* Top Row: This Month's Prediction Card + Why This Prediction */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Card 1: This Month's Prediction */}
              <Card className="lg:col-span-1 bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-900 text-white border-0 shadow-xl flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between text-indigo-300 mb-3">
                    <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                      <Target className="w-4 h-4 text-indigo-400" />
                      This Month's Prediction
                    </span>

                    {/* Confidence Badge */}
                    {prediction.confidence === "high" && (
                      <Badge variant="success" className="text-[10px] bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                        High Confidence (5+ mos)
                      </Badge>
                    )}
                    {prediction.confidence === "medium" && (
                      <Badge variant="info" className="text-[10px] bg-blue-500/20 text-blue-300 border-blue-500/30">
                        Medium Confidence (3-4 mos)
                      </Badge>
                    )}
                    {prediction.confidence === "low" && (
                      <Badge variant="warning" className="text-[10px] bg-amber-500/20 text-amber-300 border-amber-500/30">
                        Low Confidence (1-2 mos)
                      </Badge>
                    )}
                  </div>

                  {/* Predicted Total Amount */}
                  <div className="text-3xl sm:text-4xl font-black text-white tracking-tight">
                    {formatCurrency(prediction.predicted_total_minor, user?.currency)}
                  </div>

                  {/* Min - Max Range */}
                  <p className="text-xs text-indigo-200/90 mt-1.5 font-medium">
                    Estimated Range: {formatCurrency(prediction.lower_bound_minor, user?.currency)} –{" "}
                    {formatCurrency(prediction.upper_bound_minor, user?.currency)}
                  </p>

                  {/* Progress Bar: Spent so far vs Predicted */}
                  <div className="mt-6 space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-300">
                      <span>Spent so far</span>
                      <span className="font-bold text-white">
                        {formatCurrency(prediction.spent_so_far_minor, user?.currency)} ({spentPercent}%)
                      </span>
                    </div>

                    <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700/60">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500"
                        style={{ width: `${spentPercent}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {prediction.days_remaining} days left in {currentMonthName}
                      </span>
                      <span>
                        ~{formatCurrency(prediction.projected_remaining_minor, user?.currency)} remaining
                      </span>
                    </div>
                  </div>
                </div>

                {/* Bottom stats: vs last month comparison */}
                <div className="mt-6 pt-5 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-xs text-slate-400">vs Last Month:</span>
                  {prediction.vs_last_month_pct !== null && prediction.vs_last_month_pct !== undefined ? (
                    prediction.vs_last_month_pct > 0 ? (
                      <Badge variant="danger" className="font-bold">
                        <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
                        +{prediction.vs_last_month_pct}% higher
                      </Badge>
                    ) : prediction.vs_last_month_pct < 0 ? (
                      <Badge variant="success" className="font-bold">
                        <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />
                        {prediction.vs_last_month_pct}% lower
                      </Badge>
                    ) : (
                      <Badge variant="default" className="font-semibold text-slate-300">
                        Identical pace
                      </Badge>
                    )
                  ) : (
                    <span className="text-xs text-slate-500">First month</span>
                  )}
                </div>
              </Card>

              {/* Card 2: Why This Prediction? (Drivers) */}
              <Card className="lg:col-span-2 flex flex-col justify-between">
                <div>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
                        <Sparkles className="w-5 h-5 text-indigo-600" />
                        Why this prediction?
                      </CardTitle>
                      <span className="text-xs text-slate-400 font-medium">
                        Explainable Logic
                      </span>
                    </div>
                    <CardDescription>
                      Deterministic drivers calculated from your transaction patterns.
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-3 pt-0">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {prediction.drivers.map((driver, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-700 leading-relaxed flex items-start gap-2.5"
                        >
                          <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                          <span>{driver}</span>
                        </div>
                      ))}
                    </div>

                    {/* Detected Recurring Expenses banner */}
                    {prediction.recurring_expenses_detected.length > 0 && (
                      <div className="mt-4 p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-100">
                        <div className="flex items-center justify-between text-xs font-bold text-indigo-900 mb-2">
                          <span className="flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5 text-indigo-600" />
                            Detected Recurring Expenses ({prediction.recurring_expenses_detected.length})
                          </span>
                          <span className="text-[11px] font-normal text-indigo-700">
                            Tracked automatically
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {prediction.recurring_expenses_detected.map((rec, i) => (
                            <span
                              key={i}
                              className={`text-[11px] px-2.5 py-1 rounded-lg border font-medium flex items-center gap-1.5 ${
                                rec.already_billed_this_month
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : "bg-white text-indigo-800 border-indigo-200"
                              }`}
                            >
                              <span className="font-semibold">{rec.merchant}:</span>
                              <span>~{formatCurrency(rec.typical_amount_minor, user?.currency)}</span>
                              {rec.already_billed_this_month ? (
                                <Badge variant="success" className="text-[9px] px-1 py-0">
                                  Billed
                                </Badge>
                              ) : (
                                <span className="text-[10px] text-indigo-600">
                                  (due ~day {rec.typical_day})
                                </span>
                              )}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </div>

                <div className="px-6 pb-4 pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                  <span>Weighted Average Baseline: {formatCurrency(prediction.historical_baseline_minor, user?.currency)}</span>
                  <span>Daily Pace: {formatCurrency(prediction.daily_run_rate_minor, user?.currency)}/day</span>
                </div>
              </Card>
            </div>

            {/* Middle Row: Trend Chart (ComposedChart with Projected Point & Shaded Range) */}
            <Card>
              <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-blue-600" />
                    Spending Trajectory & Historical Trend
                  </CardTitle>
                  <CardDescription>
                    Actual monthly debits over the last 6 months, plus {currentMonthName}'s projected final total with uncertainty range.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-0.5 bg-blue-600 rounded" />
                    Actual Spent
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-0.5 bg-indigo-500 border-dashed border-t-2 border-indigo-500" />
                    Projected
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 bg-indigo-100 border border-indigo-300 rounded-sm" />
                    Min-Max Range
                  </span>
                </div>
              </CardHeader>

              <CardContent>
                <div className="h-72 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 15, right: 15, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                      <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#64748b" }} />
                      <YAxis
                        tick={{ fontSize: 11, fill: "#64748b" }}
                        tickFormatter={(val) => `₹${val.toLocaleString()}`}
                      />
                      <Tooltip
                        formatter={(val: any, name: string) => {
                          if (Array.isArray(val)) {
                            return [`₹${val[0].toLocaleString()} – ₹${val[1].toLocaleString()}`, "Estimated Range"];
                          }
                          return [`₹${Number(val).toLocaleString()}`, name === "actual" ? "Actual Spent" : "Projected Total"];
                        }}
                        contentStyle={{
                          backgroundColor: "#0f172a",
                          color: "#fff",
                          borderRadius: "12px",
                          border: "none",
                          fontSize: "12px",
                        }}
                      />

                      {/* Uncertainty Shaded Range Area for current month */}
                      <Area
                        type="monotone"
                        dataKey="range"
                        fill="#6366f1"
                        fillOpacity={0.15}
                        stroke="#818cf8"
                        strokeDasharray="4 4"
                        name="Confidence Range"
                      />

                      {/* Actual spending line */}
                      <Line
                        type="monotone"
                        dataKey="actual"
                        stroke="#2563eb"
                        strokeWidth={3}
                        dot={{ r: 4, fill: "#2563eb", strokeWidth: 2, stroke: "#ffffff" }}
                        activeDot={{ r: 6 }}
                        name="Actual"
                      />

                      {/* Projected end-of-month point */}
                      <Line
                        type="monotone"
                        dataKey="projected"
                        stroke="#6366f1"
                        strokeWidth={2.5}
                        strokeDasharray="5 5"
                        dot={{ r: 6, fill: "#6366f1", strokeWidth: 2, stroke: "#ffffff" }}
                        name="Projected Total"
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Bottom Row: Top Category Breakdown with Budget Warning */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Category Breakdown Table/Bars */}
              <Card className="lg:col-span-2">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base sm:text-lg">
                        Predicted Spending by Category
                      </CardTitle>
                      <CardDescription>
                        Estimated monthly demand per category vs your configured spending limits.
                      </CardDescription>
                    </div>
                    <Badge variant="outline" className="text-xs font-medium">
                      Top 5 Categories
                    </Badge>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4 pt-0">
                  {prediction.category_breakdown.slice(0, 5).map((cat, idx) => (
                    <div
                      key={cat.category_id || idx}
                      className="p-3.5 rounded-xl border border-slate-200/80 bg-white hover:border-slate-300 transition-all space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-3 h-3 rounded-full shrink-0"
                            style={{ backgroundColor: cat.color }}
                          />
                          <span className="font-bold text-slate-900 text-sm">
                            {cat.category_name}
                          </span>
                          <span className="text-xs text-slate-400">
                            ({cat.percentage_of_total}% of total)
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          {cat.budget_exceeded && (
                            <Badge variant="danger" className="text-[10px] flex items-center gap-1 font-bold">
                              <AlertTriangle className="w-3 h-3" />
                              Over Budget
                            </Badge>
                          )}
                          <span className="text-sm font-extrabold text-slate-900">
                            {formatCurrency(cat.predicted_minor, user?.currency)}
                          </span>
                        </div>
                      </div>

                      {/* Progress bar */}
                      <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-300"
                          style={{
                            width: `${Math.min(100, Math.round((cat.spent_so_far_minor / (cat.predicted_minor || 1)) * 100))}%`,
                            backgroundColor: cat.color || "#2563eb",
                          }}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-500">
                        <span>
                          Spent: {formatCurrency(cat.spent_so_far_minor, user?.currency)}
                        </span>
                        {cat.budget_limit_minor ? (
                          <span className={cat.budget_exceeded ? "text-rose-600 font-semibold" : "text-slate-500"}>
                            Budget Limit: {formatCurrency(cat.budget_limit_minor, user?.currency)}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">No budget set</span>
                        )}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* AI Spending Insights & Savings Suggestions Card */}
              <Card className="lg:col-span-1 bg-gradient-to-b from-slate-50 to-white flex flex-col justify-between">
                <div>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Sparkles className="w-4 h-4 text-purple-600" />
                        AI Savings Suggestions
                      </CardTitle>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => refreshInsightsMutation.mutate()}
                        isLoading={refreshInsightsMutation.isPending}
                        className="text-xs h-7 px-2 text-slate-500 hover:text-purple-600"
                        title="Regenerate Insights"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${refreshInsightsMutation.isPending ? "animate-spin" : ""}`} />
                      </Button>
                    </div>
                    <CardDescription>
                      Algorithmic recommendations to reduce monthly burn based on verified transaction patterns.
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-3 pt-0">
                    {insightsLoading ? (
                      <div className="py-8 flex flex-col items-center justify-center text-slate-400 gap-2">
                        <Loader2 className="w-5 h-5 animate-spin text-purple-600" />
                        <span className="text-xs">Analyzing financial aggregates...</span>
                      </div>
                    ) : insights.length === 0 ? (
                      <div className="p-4 rounded-xl border border-dashed border-slate-200 text-center space-y-2">
                        <Lightbulb className="w-6 h-6 text-amber-500 mx-auto opacity-70" />
                        <p className="text-xs font-semibold text-slate-700">No suggestions yet</p>
                        <p className="text-[11px] text-slate-400">
                          Import recent statements or enable AI processing consent in Settings to generate suggestions.
                        </p>
                      </div>
                    ) : (
                      insights.map((sugg) => (
                        <div
                          key={sugg.id}
                          className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-sm space-y-2 transition-all hover:border-slate-300"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <span className="font-bold text-slate-800 text-xs leading-snug">
                              {sugg.title}
                            </span>
                            {sugg.estimated_saving_minor > 0 && (
                              <Badge variant="success" className="text-[10px] shrink-0">
                                Save ~{formatCurrency(sugg.estimated_saving_minor, user?.currency)}
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 leading-relaxed">
                            {sugg.detail}
                          </p>

                          <div className="flex items-center justify-between pt-1 border-t border-slate-50">
                            {sugg.status === "accepted" ? (
                              <Badge variant="success" className="text-[10px]">
                                Accepted
                              </Badge>
                            ) : sugg.status === "dismissed" ? (
                              <Badge variant="default" className="text-[10px]">
                                Dismissed
                              </Badge>
                            ) : (
                              <div className="flex items-center gap-1.5 w-full justify-end">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 px-2 text-[10px] text-slate-500 hover:text-rose-600 hover:bg-rose-50"
                                  onClick={() => updateStatusMutation.mutate({ id: sugg.id, status: "dismissed" })}
                                  isLoading={updateStatusMutation.isPending && updateStatusMutation.variables?.id === sugg.id}
                                >
                                  <X className="w-3 h-3 mr-0.5" /> Dismiss
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-6 px-2 text-[10px] text-emerald-700 hover:bg-emerald-50 border-emerald-200"
                                  onClick={() => updateStatusMutation.mutate({ id: sugg.id, status: "accepted" })}
                                  isLoading={updateStatusMutation.isPending && updateStatusMutation.variables?.id === sugg.id}
                                >
                                  <Check className="w-3 h-3 mr-0.5" /> Accept
                                </Button>
                              </div>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </div>

                <div className="p-3.5 border-t border-slate-100 bg-slate-50/50 rounded-b-2xl">
                  <p className="text-[10px] text-slate-400 text-center leading-tight">
                    Suggestions are automated estimates for budgeting guidance, not certified financial advice.
                  </p>
                </div>
              </Card>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
