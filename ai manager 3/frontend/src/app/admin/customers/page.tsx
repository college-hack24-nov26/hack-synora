"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/formatters";
import { AdminLayout } from "@/components/AdminLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import {
  Users,
  Search,
  Filter,
  Eye,
  UserX,
  UserCheck,
  AlertTriangle,
  Loader2,
  Download,
  ShieldCheck,
  Building2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface CustomerItem {
  id: string;
  name: string;
  masked_email: string;
  segment?: string;
  accounts_count: number;
  this_month_spend_minor: number;
  predicted_month_end_spend_minor: number;
  last_activity?: string;
  is_active: boolean;
  is_demo: boolean;
  consent_type?: string;
  risk_flags: string[];
}

interface CustomerListResponse {
  items: CustomerItem[];
  total: number;
  page: number;
  limit: number;
}

export default function AdminCustomersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [segment, setSegment] = useState("all");
  const [status, setStatus] = useState("all");
  const [riskFlag, setRiskFlag] = useState("all");
  const [page, setPage] = useState(1);

  // Status Change Modal State
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerItem | null>(null);

  const queryParams = new URLSearchParams({
    page: page.toString(),
    limit: "10",
    ...(search ? { q: search } : {}),
    ...(segment !== "all" ? { segment } : {}),
    ...(status !== "all" ? { status } : {}),
    ...(riskFlag !== "all" ? { risk_flag: riskFlag } : {}),
  });

  const { data, isLoading, refetch } = useQuery<CustomerListResponse>({
    queryKey: ["admin_customers", page, search, segment, status, riskFlag],
    queryFn: () => apiRequest<CustomerListResponse>(`/admin/customers?${queryParams.toString()}`),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      apiRequest(`/admin/customers/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin_customers"] });
      queryClient.invalidateQueries({ queryKey: ["admin_overview"] });
      setStatusModalOpen(false);
      setSelectedCustomer(null);
    },
    onError: (err: any) => {
      alert(err.message || "Failed to update customer status.");
    },
  });

  const handleOpenStatusModal = (cust: CustomerItem) => {
    setSelectedCustomer(cust);
    setStatusModalOpen(true);
  };

  const handleConfirmStatusChange = () => {
    if (!selectedCustomer) return;
    statusMutation.mutate({
      id: selectedCustomer.id,
      is_active: !selectedCustomer.is_active,
    });
  };

  const totalPages = Math.ceil((data?.total || 0) / 10) || 1;

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-md bg-indigo-950/80 border border-indigo-800 text-indigo-300 text-xs font-semibold mb-2">
              <Users className="w-3.5 h-3.5 text-indigo-400" />
              <span>Customer Registry</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Customer Accounts & Visibility
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Protected directory. Only demo personas and users with active "share_with_bank" consent appear here.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">
              Total Visible: <strong className="text-white">{data?.total ?? 0}</strong>
            </span>
          </div>
        </div>

        {/* Filter Controls Bar */}
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
            {/* Segment */}
            <select
              value={segment}
              onChange={(e) => {
                setSegment(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Segments</option>
              <option value="student">Student</option>
              <option value="professional">Working Professional</option>
              <option value="business">Business Owner</option>
              <option value="freelancer">Freelancer</option>
              <option value="family">Family Household</option>
            </select>

            {/* Status */}
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active Only</option>
              <option value="inactive">Deactivated Only</option>
            </select>

            {/* Risk */}
            <select
              value={riskFlag}
              onChange={(e) => {
                setRiskFlag(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Risk Levels</option>
              <option value="flagged">Flagged Anomalies</option>
              <option value="clean">Clean (No Flags)</option>
            </select>
          </div>
        </div>

        {/* Table / Cards */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
          {isLoading ? (
            <div className="p-12 text-center text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-indigo-500 mb-3" />
              <p className="text-sm">Loading customer directory...</p>
            </div>
          ) : data?.items && data.items.length > 0 ? (
            <>
              {/* Desktop Table View */}
              <div className="hidden lg:block overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] uppercase font-bold text-slate-400">
                    <tr>
                      <th className="px-5 py-3.5">Customer Name & Email</th>
                      <th className="px-4 py-3.5">Segment</th>
                      <th className="px-4 py-3.5">Accounts</th>
                      <th className="px-4 py-3.5">This Month Spend</th>
                      <th className="px-4 py-3.5">Predicted Total</th>
                      <th className="px-4 py-3.5">Status</th>
                      <th className="px-4 py-3.5">Risk Flags</th>
                      <th className="px-5 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 font-medium">
                    {data.items.map((cust) => (
                      <tr key={cust.id} className="hover:bg-slate-850/60 transition-colors">
                        <td className="px-5 py-4">
                          <div className="font-bold text-white text-sm">{cust.name}</div>
                          <div className="text-slate-400 font-mono text-[11px] mt-0.5">
                            {cust.masked_email}
                          </div>
                          <div className="flex items-center gap-1.5 mt-1">
                            {cust.is_demo ? (
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                                Demo Persona
                              </span>
                            ) : (
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                                Consented Client
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <span className="capitalize text-slate-200">
                            {cust.segment || "General"}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <span className="text-slate-200">{cust.accounts_count} linked</span>
                        </td>
                        <td className="px-4 py-4 font-bold text-slate-100">
                          {formatCurrency(cust.this_month_spend_minor)}
                        </td>
                        <td className="px-4 py-4 text-slate-300">
                          {formatCurrency(cust.predicted_month_end_spend_minor)}
                        </td>
                        <td className="px-4 py-4">
                          {cust.is_active ? (
                            <Badge variant="success" className="text-[10px]">
                              Active
                            </Badge>
                          ) : (
                            <Badge variant="danger" className="text-[10px]">
                              Deactivated
                            </Badge>
                          )}
                        </td>
                        <td className="px-4 py-4">
                          {cust.risk_flags && cust.risk_flags.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {cust.risk_flags.map((flag, idx) => (
                                <Badge key={idx} variant="warning" className="text-[9px] uppercase font-bold">
                                  {flag.replace(/_/g, " ")}
                                </Badge>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-500 text-[11px]">Normal</span>
                          )}
                        </td>
                        <td className="px-5 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link href={`/admin/customers/${cust.id}`}>
                              <Button
                                size="sm"
                                variant="outline"
                                className="border-indigo-800 text-indigo-300 hover:bg-indigo-950/80 bg-slate-900 text-xs py-1 h-8"
                              >
                                <Eye className="w-3.5 h-3.5 mr-1" />
                                360 View
                              </Button>
                            </Link>

                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleOpenStatusModal(cust)}
                              className={`text-xs py-1 h-8 ${
                                cust.is_active
                                  ? "border-rose-900/60 text-rose-400 hover:bg-rose-950/60"
                                  : "border-emerald-900/60 text-emerald-400 hover:bg-emerald-950/60"
                              } bg-slate-900`}
                            >
                              {cust.is_active ? (
                                <>
                                  <UserX className="w-3.5 h-3.5 mr-1" />
                                  Deactivate
                                </>
                              ) : (
                                <>
                                  <UserCheck className="w-3.5 h-3.5 mr-1" />
                                  Reactivate
                                </>
                              )}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile Card View */}
              <div className="lg:hidden divide-y divide-slate-800 p-3 space-y-3">
                {data.items.map((cust) => (
                  <div key={cust.id} className="pt-3 first:pt-0 space-y-2.5">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-bold text-white text-sm">{cust.name}</div>
                        <div className="text-slate-400 text-xs font-mono">{cust.masked_email}</div>
                      </div>
                      <Badge variant={cust.is_active ? "success" : "danger"} className="text-[10px]">
                        {cust.is_active ? "Active" : "Deactivated"}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs py-1.5 bg-slate-950/50 p-2.5 rounded-xl border border-slate-800/60">
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase">This Month</span>
                        <span className="font-bold text-slate-200">
                          {formatCurrency(cust.this_month_spend_minor)}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase">Predicted</span>
                        <span className="font-bold text-slate-300">
                          {formatCurrency(cust.predicted_month_end_spend_minor)}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <Link href={`/admin/customers/${cust.id}`}>
                        <Button size="sm" variant="outline" className="border-indigo-800 text-indigo-300 text-xs">
                          <Eye className="w-3.5 h-3.5 mr-1" />
                          View 360
                        </Button>
                      </Link>

                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleOpenStatusModal(cust)}
                        className={`text-xs ${
                          cust.is_active ? "text-rose-400 border-rose-900" : "text-emerald-400 border-emerald-900"
                        }`}
                      >
                        {cust.is_active ? "Deactivate" : "Reactivate"}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination Controls */}
              <div className="p-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                <span>
                  Showing Page <strong className="text-white">{page}</strong> of{" "}
                  <strong className="text-white">{totalPages}</strong>
                </span>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="border-slate-800 bg-slate-900 text-slate-300 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    className="border-slate-800 bg-slate-900 text-slate-300 disabled:opacity-40"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-slate-500 text-xs">
              No matching visible customers found for this query.
            </div>
          )}
        </div>

        {/* Deactivate / Reactivate Modal */}
        <Modal
          isOpen={statusModalOpen}
          onClose={() => setStatusModalOpen(false)}
          title={selectedCustomer?.is_active ? "Deactivate Customer Account" : "Reactivate Customer Account"}
        >
          <div className="space-y-4 text-slate-300 text-xs">
            <p>
              Are you sure you want to {selectedCustomer?.is_active ? "deactivate" : "reactivate"} the account for{" "}
              <strong className="text-white">{selectedCustomer?.name}</strong> (
              <span className="font-mono">{selectedCustomer?.masked_email}</span>)?
            </p>

            {selectedCustomer?.is_active ? (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/50 text-rose-300">
                <strong>Warning:</strong> Deactivated customers are immediately blocked from logging in to the portal.
                Existing session tokens will be rejected.
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-emerald-300">
                The customer will immediately regain access to log in and access their financial dashboard.
              </div>
            )}

            <p className="text-slate-400 text-[11px]">
              This operational administrative action will be recorded in the security AuditLog with your staff ID and timestamp.
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
                onClick={handleConfirmStatusChange}
                disabled={statusMutation.isPending}
                className={
                  selectedCustomer?.is_active
                    ? "bg-rose-600 hover:bg-rose-500 text-white"
                    : "bg-emerald-600 hover:bg-emerald-500 text-white"
                }
              >
                {statusMutation.isPending ? "Updating..." : selectedCustomer?.is_active ? "Confirm Deactivation" : "Confirm Reactivation"}
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </AdminLayout>
  );
}

