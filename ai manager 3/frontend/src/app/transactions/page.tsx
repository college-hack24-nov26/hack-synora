"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest, ApiException } from "@/lib/api";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/formatters";
import { AppLayout } from "@/components/AppLayout";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Alert } from "@/components/ui/Alert";
import {
  Receipt,
  Search,
  Filter,
  ArrowDownLeft,
  ArrowUpRight,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Trash2,
  FileSpreadsheet,
  Lock,
  Tag,
  RotateCcw,
  AlertTriangle,
  Check,
  Eye,
  ShieldCheck,
  Building,
  CreditCard,
  FileText,
  Clock,
  ExternalLink,
  Sparkles,
} from "lucide-react";

interface Category {
  id: string;
  name: string;
  icon?: string;
  color?: string;
  is_income?: boolean;
}

interface TransactionItem {
  id: string;
  merchant: string;
  txn_date: string;
  category?: {
    id: string;
    name: string;
    icon?: string;
    color?: string;
  } | null;
  amount_minor: number;
  direction: "debit" | "credit";
  currency: string;
  source: string;
  category_source?: string;
  category_confidence?: number;
  needs_review?: boolean;
}

interface TransactionDetail extends TransactionItem {
  user_id: string;
  account_id: string;
  merchant_raw?: string | null;
  description?: string | null;
  account?: {
    id: string;
    name: string;
    type: string;
    last4?: string | null;
  } | null;
  created_at: string;
  category_source?: string;
  category_confidence?: number;
  needs_review?: boolean;
}

interface TransactionListResponse {
  items: TransactionItem[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

interface TransactionSummary {
  total_spent_minor: number;
  total_income_minor: number;
  transaction_count: number;
  top_categories: {
    category_id: string;
    category_name: string;
    color?: string;
    icon?: string;
    total_spent_minor: number;
    count: number;
  }[];
}

export default function TransactionsPage() {
  const queryClient = useQueryClient();

  // Filters state
  const [page, setPage] = useState<number>(1);
  const [limit, setLimit] = useState<number>(10);
  const [search, setSearch] = useState<string>("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [direction, setDirection] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [minAmount, setMinAmount] = useState<string>("");
  const [maxAmount, setMaxAmount] = useState<string>("");
  const [needsReviewOnly, setNeedsReviewOnly] = useState<boolean>(false);

  // Modal states
  const [selectedTxnId, setSelectedTxnId] = useState<string | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState<boolean>(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState<boolean>(false);
  const [newCategoryId, setNewCategoryId] = useState<string>("");
  const [createRuleForMerchant, setCreateRuleForMerchant] = useState<boolean>(false);
  const [editSuccessMessage, setEditSuccessMessage] = useState<string | null>(null);

  // Fetch Categories for dropdown filter & edit modal
  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => apiRequest<Category[]>("/categories"),
  });

  // Convert rupee filter values to paise minor units
  const minAmountMinor = minAmount ? Math.round(parseFloat(minAmount) * 100) : undefined;
  const maxAmountMinor = maxAmount ? Math.round(parseFloat(maxAmount) * 100) : undefined;

  // Build query string for transactions
  const queryParams = new URLSearchParams();
  queryParams.set("page", page.toString());
  queryParams.set("limit", limit.toString());
  if (search.trim()) queryParams.set("search", search.trim());
  if (categoryId) queryParams.set("category_id", categoryId);
  if (direction) queryParams.set("direction", direction);
  if (startDate) queryParams.set("start_date", new Date(startDate).toISOString());
  if (endDate) {
    const end = new Date(endDate);
    end.setHours(23, 59, 59, 999);
    queryParams.set("end_date", end.toISOString());
  }
  if (minAmountMinor !== undefined && !isNaN(minAmountMinor)) {
    queryParams.set("min_amount_minor", minAmountMinor.toString());
  }
  if (maxAmountMinor !== undefined && !isNaN(maxAmountMinor)) {
    queryParams.set("max_amount_minor", maxAmountMinor.toString());
  }
  if (needsReviewOnly) {
    queryParams.set("needs_review", "true");
  }

  // Fetch Transactions list
  const {
    data: txData,
    isLoading: isTxLoading,
    error: txError,
  } = useQuery<TransactionListResponse>({
    queryKey: [
      "transactions",
      page,
      limit,
      search,
      categoryId,
      direction,
      startDate,
      endDate,
      minAmountMinor,
      maxAmountMinor,
      needsReviewOnly,
    ],
    queryFn: () => apiRequest<TransactionListResponse>(`/transactions?${queryParams.toString()}`),
  });

  // Fetch Summary for the current date range
  const summaryParams = new URLSearchParams();
  if (startDate) summaryParams.set("start_date", new Date(startDate).toISOString());
  if (endDate) {
    const end = new Date(endDate);
    end.setHours(23, 59, 59, 999);
    summaryParams.set("end_date", end.toISOString());
  }

  const { data: summaryData } = useQuery<TransactionSummary>({
    queryKey: ["transaction-summary", startDate, endDate],
    queryFn: () =>
      apiRequest<TransactionSummary>(`/transactions/summary?${summaryParams.toString()}`),
  });

  // Fetch detailed record when row is clicked
  const {
    data: txnDetail,
    isLoading: isDetailLoading,
    refetch: refetchDetail,
  } = useQuery<TransactionDetail>({
    queryKey: ["transaction-detail", selectedTxnId],
    queryFn: () => apiRequest<TransactionDetail>(`/transactions/${selectedTxnId}`),
    enabled: !!selectedTxnId && isDetailOpen,
  });

  // Mutation: Update Category with optional rule creation
  const updateCategoryMutation = useMutation({
    mutationFn: async ({
      txnId,
      catId,
      createRule,
    }: {
      txnId: string;
      catId: string;
      createRule: boolean;
    }) => {
      return apiRequest<TransactionDetail>(`/transactions/${txnId}`, {
        method: "PATCH",
        body: JSON.stringify({ category_id: catId || null, create_rule: createRule }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["transaction-summary"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-current-month"] });
      refetchDetail();
      setEditSuccessMessage("Category updated successfully! Your preference has been saved.");
      setTimeout(() => setEditSuccessMessage(null), 3500);
    },
  });

  // Mutation: Re-categorize transactions
  const recategorizeMutation = useMutation({
    mutationFn: async () => {
      return apiRequest("/transactions/recategorize", { method: "POST" });
    },
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["transaction-summary"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-current-month"] });
      setEditSuccessMessage(
        `Re-categorization complete: ${data?.updated_count || 0} transactions evaluated.`
      );
      setTimeout(() => setEditSuccessMessage(null), 3500);
    },
  });

  // Mutation: Delete Transaction
  const deleteMutation = useMutation({
    mutationFn: async (txnId: string) => {
      return apiRequest(`/transactions/${txnId}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["transaction-summary"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-current-month"] });
      setIsDeleteConfirmOpen(false);
      setIsDetailOpen(false);
      setSelectedTxnId(null);
    },
  });

  const handleRowClick = (txnId: string) => {
    setSelectedTxnId(txnId);
    setCreateRuleForMerchant(false);
    setEditSuccessMessage(null);
    setIsDetailOpen(true);
  };

  const handleResetFilters = () => {
    setSearch("");
    setCategoryId("");
    setDirection("");
    setStartDate("");
    setEndDate("");
    setMinAmount("");
    setMaxAmount("");
    setNeedsReviewOnly(false);
    setPage(1);
  };

  const renderCategorySourceBadge = (
    source?: string,
    confidence?: number,
    needsReview?: boolean
  ) => {
    if (needsReview) {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
          Needs review
        </span>
      );
    }
    switch (source) {
      case "user":
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700 border border-purple-200">
            You
          </span>
        );
      case "ml":
        const pct = Math.round((confidence || 0.8) * 100);
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
            Suggested by model ({pct}%)
          </span>
        );
      case "rule":
      default:
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            Rule
          </span>
        );
    }
  };

  const getSourceBadge = (source: string) => {
    switch (source.toLowerCase()) {
      case "sms":
        return <Badge variant="info">SMS</Badge>;
      case "csv":
        return <Badge variant="success">CSV</Badge>;
      case "pdf":
        return <Badge variant="warning">PDF</Badge>;
      default:
        return <Badge variant="outline">Manual</Badge>;
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1.5 rounded-lg bg-blue-100 text-blue-700">
                <Receipt className="w-5 h-5" />
              </span>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">
                Transaction History
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-slate-500">
              Structured multi-tenant transaction vault. Every record is cryptographically tied to your unique user ID.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={recategorizeMutation.isPending}
              onClick={() => recategorizeMutation.mutate()}
              className="text-xs text-indigo-700 border-indigo-200 hover:bg-indigo-50 font-medium"
            >
              <Sparkles className="w-4 h-4 mr-1.5 text-indigo-600" />
              {recategorizeMutation.isPending ? "Re-categorizing..." : "Re-run Categorization"}
            </Button>
            <Link href="/import">
              <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white font-medium shadow-sm">
                <FileSpreadsheet className="w-4 h-4 mr-1.5" />
                Import Statements
              </Button>
            </Link>
          </div>
        </div>

        {/* Summary Bar */}
        {summaryData && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-4 bg-white border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Total Spent
                  </p>
                  <p className="text-xl sm:text-2xl font-black text-rose-600 mt-1">
                    {formatCurrency(summaryData.total_spent_minor)}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                  <ArrowDownLeft className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-4 bg-white border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Total Income
                  </p>
                  <p className="text-xl sm:text-2xl font-black text-emerald-600 mt-1">
                    {formatCurrency(summaryData.total_income_minor)}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <ArrowUpRight className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-4 bg-white border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Total Transactions
                  </p>
                  <p className="text-xl sm:text-2xl font-black text-slate-800 mt-1">
                    {summaryData.transaction_count}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <Receipt className="w-5 h-5" />
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Filter Toolbar */}
        <Card className="p-4 sm:p-5 bg-white border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                Filters & Search
              </span>
              <button
                type="button"
                onClick={() => {
                  setNeedsReviewOnly(!needsReviewOnly);
                  setPage(1);
                }}
                className={`ml-3 px-2.5 py-1 rounded-full text-xs font-bold border transition-all flex items-center gap-1.5 ${
                  needsReviewOnly
                    ? "bg-amber-500 text-white border-amber-600 shadow-xs"
                    : "bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100"
                }`}
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Needs Review Filter</span>
                {needsReviewOnly && <span className="ml-1 text-[10px]">●</span>}
              </button>
            </div>
            <button
              onClick={handleResetFilters}
              className="text-xs font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1 transition-colors"
            >
              <RotateCcw className="w-3 h-3" /> Reset Filters
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Search merchant/description */}
            <div className="lg:col-span-2">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Merchant / Description
              </label>
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                <Input
                  placeholder="Search merchant..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="pl-9 h-9 text-xs"
                />
              </div>
            </div>

            {/* Category Dropdown */}
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Category
              </label>
              <select
                value={categoryId}
                onChange={(e) => {
                  setCategoryId(e.target.value);
                  setPage(1);
                }}
                className="w-full h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              >
                <option value="">All Categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Direction */}
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Direction
              </label>
              <select
                value={direction}
                onChange={(e) => {
                  setDirection(e.target.value);
                  setPage(1);
                }}
                className="w-full h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              >
                <option value="">All (Debits & Credits)</option>
                <option value="debit">Debits (Expenses)</option>
                <option value="credit">Credits (Income)</option>
              </select>
            </div>

            {/* Date Range Start */}
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                From Date
              </label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  setPage(1);
                }}
                className="h-9 text-xs"
              />
            </div>

            {/* Date Range End */}
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                To Date
              </label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value);
                  setPage(1);
                }}
                className="h-9 text-xs"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-slate-50">
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Min Amount (₹)
              </label>
              <Input
                type="number"
                placeholder="Min ₹"
                value={minAmount}
                onChange={(e) => {
                  setMinAmount(e.target.value);
                  setPage(1);
                }}
                className="h-9 text-xs"
              />
            </div>

            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Max Amount (₹)
              </label>
              <Input
                type="number"
                placeholder="Max ₹"
                value={maxAmount}
                onChange={(e) => {
                  setMaxAmount(e.target.value);
                  setPage(1);
                }}
                className="h-9 text-xs"
              />
            </div>
          </div>
        </Card>

        {/* Error Alert */}
        {txError && (
          <Alert
            type="error"
            title="Failed to load transactions"
            message={(txError as any)?.message || "Unknown error occurred"}
          />
        )}

        {/* Transactions Table / Cards */}
        <Card className="bg-white border-slate-200 overflow-hidden shadow-sm">
          {/* Loading Skeletons */}
          {isTxLoading && (
            <div className="p-6 space-y-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="animate-pulse flex items-center justify-between py-3 border-b border-slate-100 last:border-0">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-slate-200" />
                    <div className="space-y-2">
                      <div className="w-36 h-4 bg-slate-200 rounded" />
                      <div className="w-24 h-3 bg-slate-100 rounded" />
                    </div>
                  </div>
                  <div className="w-20 h-4 bg-slate-200 rounded" />
                </div>
              ))}
            </div>
          )}

          {/* Empty State */}
          {!isTxLoading && txData && txData.items.length === 0 && (
            <div className="text-center py-16 px-4">
              <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4 border border-blue-100">
                <Receipt className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-1">
                No transactions found
              </h3>
              <p className="text-sm text-slate-500 max-w-sm mx-auto mb-6">
                {search || categoryId || direction || startDate || endDate || minAmount || maxAmount
                  ? "No transactions match your active filters. Try clearing some criteria."
                  : "You haven't imported or recorded any transactions yet. Import your first bank statement to begin."}
              </p>
              <div className="flex items-center justify-center gap-3">
                {search || categoryId || direction || startDate || endDate || minAmount || maxAmount ? (
                  <Button variant="outline" size="sm" onClick={handleResetFilters}>
                    Clear Filters
                  </Button>
                ) : (
                  <Link href="/import">
                    <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white font-medium">
                      <FileSpreadsheet className="w-4 h-4 mr-1.5" />
                      Import Statement
                    </Button>
                  </Link>
                )}
              </div>
            </div>
          )}

          {/* Desktop Table View */}
          {!isTxLoading && txData && txData.items.length > 0 && (
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    <th className="py-3.5 px-4">Date</th>
                    <th className="py-3.5 px-4">Merchant</th>
                    <th className="py-3.5 px-4">Category</th>
                    <th className="py-3.5 px-4">Amount</th>
                    <th className="py-3.5 px-4">Source</th>
                    <th className="py-3.5 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {txData.items.map((txn) => {
                    const isDebit = txn.direction === "debit";
                    return (
                      <tr
                        key={txn.id}
                        onClick={() => handleRowClick(txn.id)}
                        className="hover:bg-blue-50/40 transition-colors cursor-pointer group"
                      >
                        <td className="py-3.5 px-4 text-xs font-medium text-slate-500 whitespace-nowrap">
                          {formatDate(txn.txn_date)}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors block">
                            {txn.merchant}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <div className="flex flex-col sm:flex-row sm:items-center gap-1.5">
                            {txn.category ? (
                              <span
                                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"
                                style={{
                                  backgroundColor: `${txn.category.color || "#3b82f6"}15`,
                                  color: txn.category.color || "#3b82f6",
                                  border: `1px solid ${txn.category.color || "#3b82f6"}30`,
                                }}
                              >
                                <Tag className="w-3 h-3 mr-1" />
                                {txn.category.name}
                              </span>
                            ) : (
                              <span className="text-xs text-slate-400 italic">Uncategorized</span>
                            )}
                            {renderCategorySourceBadge(
                              txn.category_source,
                              txn.category_confidence,
                              txn.needs_review
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <span
                            className={`font-mono font-bold ${
                              isDebit ? "text-rose-600" : "text-emerald-600"
                            }`}
                          >
                            {isDebit ? "-" : "+"} {formatCurrency(txn.amount_minor, txn.currency)}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          {getSourceBadge(txn.source)}
                        </td>
                        <td className="py-3.5 px-4 text-right whitespace-nowrap">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRowClick(txn.id);
                            }}
                            className="p-1 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                            title="Inspect structured record"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Mobile Stacked Cards View */}
          {!isTxLoading && txData && txData.items.length > 0 && (
            <div className="md:hidden divide-y divide-slate-100">
              {txData.items.map((txn) => {
                const isDebit = txn.direction === "debit";
                return (
                  <div
                    key={txn.id}
                    onClick={() => handleRowClick(txn.id)}
                    className="p-4 hover:bg-slate-50 transition-colors cursor-pointer space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-bold text-slate-900 text-sm">{txn.merchant}</p>
                        <p className="text-xs text-slate-400">{formatDate(txn.txn_date)}</p>
                      </div>
                      <span
                        className={`font-mono font-bold text-sm ${
                          isDebit ? "text-rose-600" : "text-emerald-600"
                        }`}
                      >
                        {isDebit ? "-" : "+"} {formatCurrency(txn.amount_minor, txn.currency)}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {txn.category ? (
                          <span
                            className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold"
                            style={{
                              backgroundColor: `${txn.category.color || "#3b82f6"}15`,
                              color: txn.category.color || "#3b82f6",
                            }}
                          >
                            <Tag className="w-2.5 h-2.5 mr-1" />
                            {txn.category.name}
                          </span>
                        ) : (
                          <span className="text-[11px] text-slate-400 italic">Uncategorized</span>
                        )}
                        {renderCategorySourceBadge(
                          txn.category_source,
                          txn.category_confidence,
                          txn.needs_review
                        )}
                      </div>
                      <div>{getSourceBadge(txn.source)}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination Controls */}
          {!isTxLoading && txData && txData.total > 0 && (
            <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 font-medium">
              <div>
                Showing {(txData.page - 1) * txData.limit + 1} to{" "}
                {Math.min(txData.page * txData.limit, txData.total)} of {txData.total} transactions
              </div>

              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-xs">Rows:</span>
                <select
                  value={limit}
                  onChange={(e) => {
                    setLimit(parseInt(e.target.value));
                    setPage(1);
                  }}
                  className="h-8 rounded border border-slate-200 bg-white px-2 text-xs text-slate-700"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>

                <Button
                  variant="outline"
                  size="sm"
                  disabled={txData.page <= 1}
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  className="h-8 px-2 text-xs"
                >
                  <ChevronLeft className="w-3.5 h-3.5 mr-1" /> Prev
                </Button>

                <span className="px-2 font-semibold text-slate-800">
                  Page {txData.page} of {txData.total_pages || 1}
                </span>

                <Button
                  variant="outline"
                  size="sm"
                  disabled={txData.page >= txData.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                  className="h-8 px-2 text-xs"
                >
                  Next <ChevronRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </Card>

        {/* Transaction Detail Modal */}
        <Modal
          isOpen={isDetailOpen}
          onClose={() => {
            setIsDetailOpen(false);
            setSelectedTxnId(null);
            setEditSuccessMessage(null);
          }}
          title="Structured Transaction Record"
          description="Direct inspection of user-isolated transaction schema and cryptographic properties."
          maxWidth="lg"
        >
          {isDetailLoading || !txnDetail ? (
            <div className="py-12 text-center">
              <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">
                Loading decrypted record...
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {editSuccessMessage && (
                <Alert
                  type="success"
                  message={editSuccessMessage}
                />
              )}

              {txnDetail.needs_review && (
                <Alert
                  type="warning"
                  title="Category Review Needed"
                  message="Our categorizer had low confidence (<60%) for this merchant. Please verify or update the category below."
                />
              )}

              {/* 6 Structured Concept Fields Demonstration */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200/90 text-xs">
                {/* 1. Transaction ID */}
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">
                    1. Transaction ID (UUID PK)
                  </span>
                  <span className="font-mono text-slate-900 font-semibold break-all">
                    {txnDetail.id}
                  </span>
                </div>

                {/* 2. User ID */}
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">
                    2. User ID (Owner FK)
                  </span>
                  <span className="font-mono text-slate-900 font-semibold break-all">
                    {txnDetail.user_id}
                  </span>
                </div>

                {/* 3. Merchant info */}
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">
                    3. Merchant Info
                  </span>
                  <p className="font-semibold text-slate-900">{txnDetail.merchant}</p>
                  {txnDetail.merchant_raw && (
                    <p className="text-[11px] text-slate-500 font-mono mt-0.5 truncate">
                      Raw: {txnDetail.merchant_raw}
                    </p>
                  )}
                </div>

                {/* 4. Date of transaction */}
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">
                    4. Transaction Date & Time
                  </span>
                  <p className="font-semibold text-slate-900">{formatDateTime(txnDetail.txn_date)}</p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    UTC: {txnDetail.txn_date}
                  </p>
                </div>

                {/* 5. Category of expense */}
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">
                    5. Category & Attribution
                  </span>
                  <div className="mt-1 flex items-center gap-2 flex-wrap">
                    {txnDetail.category ? (
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold"
                        style={{
                          backgroundColor: `${txnDetail.category.color || "#3b82f6"}15`,
                          color: txnDetail.category.color || "#3b82f6",
                        }}
                      >
                        <Tag className="w-3 h-3 mr-1" />
                        {txnDetail.category.name}
                      </span>
                    ) : (
                      <span className="text-slate-400 italic">Uncategorized</span>
                    )}
                    {renderCategorySourceBadge(
                      txnDetail.category_source,
                      txnDetail.category_confidence,
                      txnDetail.needs_review
                    )}
                  </div>
                </div>

                {/* 6. Money sent */}
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">
                    6. Amount & Direction
                  </span>
                  <p
                    className={`font-mono font-bold text-sm ${
                      txnDetail.direction === "debit" ? "text-rose-600" : "text-emerald-600"
                    }`}
                  >
                    {txnDetail.direction === "debit" ? "Debit (-)" : "Credit (+)"}{" "}
                    {formatCurrency(txnDetail.amount_minor, txnDetail.currency)}
                  </p>
                  <p className="text-[10px] text-slate-400 font-mono">
                    Integer Minor Units: {txnDetail.amount_minor} paise
                  </p>
                </div>
              </div>

              {/* Extra Account & Source Details */}
              <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-600 p-3 bg-white rounded-lg border border-slate-200">
                <div className="flex items-center gap-2">
                  <CreditCard className="w-4 h-4 text-slate-400" />
                  <span>
                    Account: <strong>{txnDetail.account?.name || "General"}</strong>{" "}
                    {txnDetail.account?.last4 ? `(••• ${txnDetail.account.last4})` : ""}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span>Import Source:</span>
                  {getSourceBadge(txnDetail.source)}
                </div>
              </div>

              {/* Change Category Form */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/90 space-y-3">
                <label className="text-xs font-bold text-slate-700 block">
                  Change / Reassign Category:
                </label>
                <div className="flex items-center gap-2">
                  <select
                    defaultValue={txnDetail.category?.id || ""}
                    onChange={(e) => setNewCategoryId(e.target.value)}
                    className="flex-1 h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  >
                    <option value="">No Category (Uncategorized)</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <Button
                    size="sm"
                    disabled={updateCategoryMutation.isPending}
                    onClick={() => {
                      updateCategoryMutation.mutate({
                        txnId: txnDetail.id,
                        catId: newCategoryId !== "" ? newCategoryId : (txnDetail.category?.id || ""),
                        createRule: createRuleForMerchant,
                      });
                    }}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-medium"
                  >
                    {updateCategoryMutation.isPending ? "Updating..." : "Save Category"}
                  </Button>
                </div>

                <div className="flex items-center gap-2 pt-1 border-t border-slate-200/60">
                  <input
                    type="checkbox"
                    id="create-rule-checkbox"
                    checked={createRuleForMerchant}
                    onChange={(e) => setCreateRuleForMerchant(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                  <label
                    htmlFor="create-rule-checkbox"
                    className="text-xs text-slate-700 font-medium cursor-pointer select-none"
                  >
                    Always use this category for <strong>{txnDetail.merchant}</strong> (creates your personal Merchant Rule)
                  </label>
                </div>
              </div>

              {/* Modal Footer with Actions */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsDeleteConfirmOpen(true)}
                  className="text-rose-600 border-rose-200 hover:bg-rose-50 hover:text-rose-700 text-xs"
                >
                  <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                  Delete Transaction
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setIsDetailOpen(false);
                    setSelectedTxnId(null);
                  }}
                  className="text-xs"
                >
                  Close
                </Button>
              </div>
            </div>
          )}
        </Modal>

        {/* Delete Confirmation Modal */}
        <Modal
          isOpen={isDeleteConfirmOpen}
          onClose={() => setIsDeleteConfirmOpen(false)}
          title="Confirm Transaction Deletion"
          description="Are you sure you want to delete this transaction record?"
          maxWidth="sm"
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-600 leading-relaxed">
              This action will soft-delete the transaction from your account and exclude it from future monthly forecasts and analytics calculations.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDeleteConfirmOpen(false)}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={() => {
                  if (selectedTxnId) {
                    deleteMutation.mutate(selectedTxnId);
                  }
                }}
                className="bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs"
              >
                {deleteMutation.isPending ? "Deleting..." : "Confirm Delete"}
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </AppLayout>
  );
}
