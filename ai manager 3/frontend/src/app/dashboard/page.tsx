"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { formatCurrency } from "@/lib/formatters";
import { useAuth } from "@/context/AuthContext";
import { AppLayout } from "@/components/AppLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Alert } from "@/components/ui/Alert";
import {
  Wallet,
  Building2,
  TrendingUp,
  Tags,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
  ShieldCheck,
  CreditCard,
  FileSpreadsheet,
  AlertCircle,
  Loader2,
  Target,
  Clock,
  ArrowRight,
  Sparkles,
  Mail,
  CheckCircle2,
  MessageSquare,
  Send,
  Bot,
} from "lucide-react";

interface Account {
  id: string;
  name: string;
  type: string;
  last4?: string;
  opening_balance_minor: number;
  current_balance_minor?: number;
}

interface Category {
  id: string;
  name: string;
  user_id?: string | null;
  is_income: boolean;
  color?: string;
}

export default function DashboardPage() {
  const { user } = useAuth();

  // Fetch Accounts
  const {
    data: accounts = [],
    isLoading: accountsLoading,
    error: accountsError,
  } = useQuery<Account[]>({
    queryKey: ["accounts"],
    queryFn: () => apiRequest<Account[]>("/accounts"),
  });

  // Fetch Categories
  const {
    data: categories = [],
    isLoading: categoriesLoading,
  } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => apiRequest<Category[]>("/categories"),
  });

  // Fetch Monthly Spending Prediction
  const {
    data: prediction,
    isLoading: predictionLoading,
  } = useQuery<any>({
    queryKey: ["prediction-current-month"],
    queryFn: () => apiRequest<any>("/analytics/forecast/current-month"),
  });

  // Fetch Needs Review transactions
  const { data: needsReviewData } = useQuery<any>({
    queryKey: ["transactions-needs-review"],
    queryFn: () => apiRequest<any>("/transactions/needs-review?limit=5"),
  });

  // Assistant chat state
  const [assistantQuery, setAssistantQuery] = React.useState("");
  const [assistantResponse, setAssistantResponse] = React.useState<{
    question: string;
    answer: string;
    tool_used: string;
    data: any;
  } | null>(null);
  const [isAskingAssistant, setIsAskingAssistant] = React.useState(false);
  const [assistantError, setAssistantError] = React.useState<string | null>(null);

  const handleAskAssistant = async (queryText?: string) => {
    const q = queryText || assistantQuery;
    if (!q.trim()) return;
    setIsAskingAssistant(true);
    setAssistantError(null);
    try {
      const res = await apiRequest<{
        question: string;
        answer: string;
        tool_used: string;
        data: any;
      }>("/assistant/ask", {
        method: "POST",
        body: JSON.stringify({ question: q }),
      });
      setAssistantResponse(res);
      setAssistantQuery("");
    } catch (err: any) {
      setAssistantError(err.message || "Failed to query financial assistant. Please check if AI Processing consent is granted in Settings.");
    } finally {
      setIsAskingAssistant(false);
    }
  };

  // Calculate Net Worth / Total Balance in minor units (paise)
  const totalBalanceMinor = accounts.reduce(
    (sum, acc) => sum + (acc.current_balance_minor ?? acc.opening_balance_minor),
    0
  );

  const customCategoriesCount = categories.filter((c) => c.user_id !== null).length;
  const systemCategoriesCount = categories.filter((c) => c.user_id === null).length;

  return (
    <AppLayout>
      <div className="space-y-8 animate-in fade-in duration-300">
        {/* Welcome Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Financial Overview
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Welcome back, <strong className="text-slate-800">{user?.name}</strong>. Here is your portfolio snapshot.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/accounts">
              <Button variant="primary" size="sm">
                <Plus className="w-4 h-4 mr-1.5" />
                Add Account
              </Button>
            </Link>
            <Link href="/import">
              <Button variant="outline" size="sm">
                <FileSpreadsheet className="w-4 h-4 mr-1.5" />
                Import Statement
              </Button>
            </Link>
          </div>
        </div>

        {/* KPI Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Net Worth */}
          <Card className="relative overflow-hidden bg-gradient-to-br from-blue-600 to-indigo-700 text-white border-0 shadow-lg shadow-blue-500/20">
            <div className="flex items-center justify-between opacity-80 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Total Net Balance</span>
              <Wallet className="w-4 h-4" />
            </div>
            {accountsLoading ? (
              <div className="h-8 flex items-center">
                <Loader2 className="w-5 h-5 animate-spin" />
              </div>
            ) : (
              <div className="text-2xl sm:text-3xl font-black tracking-tight">
                {formatCurrency(totalBalanceMinor, user?.currency)}
              </div>
            )}
            <p className="text-[11px] text-blue-100/90 mt-2 flex items-center gap-1 font-medium">
              <span>Across {accounts.length} linked financial accounts</span>
            </p>
          </Card>

          {/* Active Accounts */}
          <Card>
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Linked Accounts</span>
              <Building2 className="w-4 h-4 text-blue-600" />
            </div>
            {accountsLoading ? (
              <div className="h-8 flex items-center">
                <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
              </div>
            ) : (
              <div className="text-2xl sm:text-3xl font-extrabold text-slate-900">
                {accounts.length}
              </div>
            )}
            <p className="text-[11px] text-slate-400 mt-2">
              Savings, Current, Cards & Wallets
            </p>
          </Card>

          {/* Categories */}
          <Card>
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Categories</span>
              <Tags className="w-4 h-4 text-emerald-600" />
            </div>
            {categoriesLoading ? (
              <div className="h-8 flex items-center">
                <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
              </div>
            ) : (
              <div className="text-2xl sm:text-3xl font-extrabold text-slate-900">
                {categories.length}
              </div>
            )}
            <p className="text-[11px] text-slate-400 mt-2">
              {systemCategoriesCount} default + {customCategoriesCount} custom
            </p>
          </Card>

          {/* Precision & Safety */}
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white border-0">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider">Data Architecture</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-lg font-bold text-white flex items-center gap-2">
              <span>Minor Units (Paise)</span>
            </div>
            <p className="text-[11px] text-slate-300 mt-2">
              Zero floating-point rounding errors
            </p>
          </Card>
        </div>

        {/* Review Suggestions Card */}
        {needsReviewData && needsReviewData.total > 0 && (
          <Card className="border-amber-200 bg-amber-50/70 p-5 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 border border-amber-300">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-0.5">
                    <h3 className="font-extrabold text-slate-900 text-sm sm:text-base">
                      Review Categorization Suggestions
                    </h3>
                    <Badge variant="warning" className="text-[10px]">
                      {needsReviewData.total} {needsReviewData.total === 1 ? "Item" : "Items"} Need Review
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-600 max-w-2xl leading-relaxed">
                    Our model encountered ambiguous merchant details or low classification confidence for {needsReviewData.total} transaction{needsReviewData.total === 1 ? "" : "s"}. Confirm or change their categories with one click to train your custom rules.
                  </p>
                </div>
              </div>

              <Link href="/transactions" className="shrink-0">
                <Button size="sm" className="bg-amber-600 hover:bg-amber-700 text-white font-medium text-xs sm:text-sm shadow-sm">
                  Review Suggestions <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                </Button>
              </Link>
            </div>
          </Card>
        )}

        {/* This Month's Prediction Summary Card */}
        {prediction?.has_enough_data && (
          <Card className="bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-900 text-white border-0 shadow-xl overflow-hidden relative">
            <div className="absolute right-0 top-0 translate-x-10 -translate-y-10 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
                    <Target className="w-4 h-4 text-indigo-400" />
                    This Month's Spending Prediction
                  </span>
                  {prediction.confidence === "high" && (
                    <Badge variant="success" className="text-[10px] bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                      High Confidence
                    </Badge>
                  )}
                  {prediction.confidence === "medium" && (
                    <Badge variant="info" className="text-[10px] bg-blue-500/20 text-blue-300 border-blue-500/30">
                      Medium Confidence
                    </Badge>
                  )}
                  {prediction.confidence === "low" && (
                    <Badge variant="warning" className="text-[10px] bg-amber-500/20 text-amber-300 border-amber-500/30">
                      Low Confidence
                    </Badge>
                  )}
                </div>

                <div className="flex flex-wrap items-baseline gap-3">
                  <div className="text-2xl sm:text-3xl font-black text-white">
                    {formatCurrency(prediction.predicted_total_minor, user?.currency)}
                  </div>
                  <span className="text-xs text-indigo-200/90 font-medium">
                    Range: {formatCurrency(prediction.lower_bound_minor, user?.currency)} – {formatCurrency(prediction.upper_bound_minor, user?.currency)}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="max-w-md space-y-1.5">
                  <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700/60 p-0.5">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(
                          100,
                          Math.round((prediction.spent_so_far_minor / (prediction.predicted_total_minor || 1)) * 100)
                        )}%`,
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-300">
                    <span>
                      {formatCurrency(prediction.spent_so_far_minor, user?.currency)} spent ({Math.min(
                        100,
                        Math.round((prediction.spent_so_far_minor / (prediction.predicted_total_minor || 1)) * 100)
                      )}%)
                    </span>
                    <span className="flex items-center gap-1 text-slate-400">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {prediction.days_remaining} days left
                    </span>
                  </div>
                </div>
              </div>

              {/* Action and vs last month badge */}
              <div className="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end gap-3 justify-between shrink-0">
                {prediction.vs_last_month_pct !== null && prediction.vs_last_month_pct !== undefined && (
                  prediction.vs_last_month_pct > 0 ? (
                    <Badge variant="danger" className="font-bold">
                      <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
                      +{prediction.vs_last_month_pct}% vs last month
                    </Badge>
                  ) : prediction.vs_last_month_pct < 0 ? (
                    <Badge variant="success" className="font-bold">
                      <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />
                      {prediction.vs_last_month_pct}% vs last month
                    </Badge>
                  ) : (
                    <Badge variant="default" className="text-slate-300 font-semibold">
                      Same as last month
                    </Badge>
                  )
                )}

                <Link href="/analytics">
                  <Button variant="primary" size="sm" className="bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs">
                    View Full Forecast & Drivers <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </Button>
                </Link>
              </div>
            </div>
          </Card>
        )}

        {/* Ask Your Finances AI Assistant */}
        <Card className="border-purple-200 bg-gradient-to-br from-purple-50/60 via-white to-indigo-50/40 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-purple-600 text-white flex items-center justify-center shadow-md shadow-purple-500/20">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  Ask Your Finances
                  <Badge variant="info" className="text-[10px] bg-purple-100 text-purple-700 border-purple-200">
                    Safe Predefined SQL
                  </Badge>
                </h3>
                <p className="text-xs text-slate-500">Ask natural language questions about your balances, spending, or cashflow.</p>
              </div>
            </div>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAskAssistant();
            }}
            className="flex gap-2 mb-3"
          >
            <input
              type="text"
              placeholder="e.g. How much did I spend on Food & Dining this month?"
              value={assistantQuery}
              onChange={(e) => setAssistantQuery(e.target.value)}
              className="flex-1 text-xs rounded-xl border border-slate-200 px-3.5 py-2.5 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
            />
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isAskingAssistant}
              disabled={!assistantQuery.trim()}
              className="bg-purple-600 hover:bg-purple-700 text-white text-xs px-4"
            >
              <Send className="w-3.5 h-3.5 mr-1" /> Ask
            </Button>
          </form>

          {/* Quick Prompt Chips */}
          <div className="flex flex-wrap gap-1.5 mb-2">
            {[
              "How much did I spend this month?",
              "What are my top expenses?",
              "Check my account balances",
              "What is my cashflow breakdown?",
            ].map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => handleAskAssistant(chip)}
                disabled={isAskingAssistant}
                className="text-[11px] font-medium px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-600 hover:border-purple-300 hover:text-purple-700 transition-colors"
              >
                {chip}
              </button>
            ))}
          </div>

          {assistantError && (
            <Alert type="error" message={assistantError} className="mt-3 text-xs" />
          )}

          {assistantResponse && (
            <div className="mt-3 p-3.5 rounded-xl bg-white border border-purple-100 shadow-sm space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-purple-700 uppercase tracking-wide">
                  Query: {assistantResponse.question}
                </span>
                <span className="text-[10px] text-slate-400">
                  Tool: {assistantResponse.tool_used}
                </span>
              </div>
              <p className="text-xs text-slate-800 leading-relaxed font-medium">
                {assistantResponse.answer}
              </p>
            </div>
          )}
        </Card>

        {/* Accounts Breakdown */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Your Bank Accounts</h2>
              <p className="text-xs text-slate-500">Live balances tracked in minor units</p>
            </div>
            <Link href="/accounts" className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1">
              View all <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {accountsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse h-32 bg-slate-100 border-0" />
              ))}
            </div>
          ) : accounts.length === 0 ? (
            <Card className="text-center py-12 px-4 border-dashed border-2 border-slate-200">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3">
                <CreditCard className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-800">No bank accounts linked yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
                Add your savings, current, credit cards or UPI wallet accounts to start tracking your cashflow.
              </p>
              <Link href="/accounts">
                <Button variant="primary" size="sm">
                  <Plus className="w-4 h-4 mr-1.5" />
                  Add First Account
                </Button>
              </Link>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {accounts.map((acc) => (
                <Card key={acc.id} className="hover:border-slate-300 transition-all">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm">{acc.name}</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {acc.last4 ? `•••• ${acc.last4}` : "No card number"}
                      </p>
                    </div>
                    <Badge variant="info" className="capitalize text-[10px]">
                      {acc.type.replace("_", " ")}
                    </Badge>
                  </div>
                  <div className="mt-4 pt-4 border-t border-slate-100 flex items-baseline justify-between">
                    <span className="text-xs text-slate-500">Balance</span>
                    <span className="text-base font-extrabold text-slate-900">
                      {formatCurrency(
                        acc.current_balance_minor ?? acc.opening_balance_minor,
                        user?.currency
                      )}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Ingestion & AI Insights Banner */}
        <div className="rounded-2xl bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50 p-6 border border-blue-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-blue-700 font-bold text-sm">
              <FileSpreadsheet className="w-4 h-4" />
              <span>Smart Indian Ingestion Engine</span>
            </div>
            <p className="text-xs text-slate-600 max-w-xl">
              Paste raw bank SMS alerts or upload statements from HDFC, SBI, ICICI, Axis, Kotak, or UPI apps. Our regex engine automatically normalizes merchants and flags recurring spends.
            </p>
          </div>
          <Link href="/import">
            <Button variant="primary" size="sm" className="whitespace-nowrap">
              Open Import Portal
            </Button>
          </Link>
        </div>
      </div>
    </AppLayout>
  );
}

