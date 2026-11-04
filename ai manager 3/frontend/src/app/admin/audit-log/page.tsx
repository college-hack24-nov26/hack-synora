"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { formatDate } from "@/lib/formatters";
import { AdminLayout } from "@/components/AdminLayout";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  ShieldCheck,
  Lock,
  Loader2,
  ChevronLeft,
  ChevronRight,
  UserCheck,
  Eye,
  FileSpreadsheet,
} from "lucide-react";

interface AuditLogItem {
  id: string;
  admin_id: string;
  admin_email: string;
  action: string;
  customer_id?: string;
  customer_name?: string;
  timestamp: string;
  ip_address?: string;
  details?: Record<string, any>;
}

interface AuditLogResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  limit: number;
}

export default function AdminAuditLogPage() {
  const [actionFilter, setActionFilter] = useState("all");
  const [page, setPage] = useState(1);

  const queryParams = new URLSearchParams({
    page: page.toString(),
    limit: "15",
    ...(actionFilter !== "all" ? { action: actionFilter } : {}),
  });

  const { data, isLoading } = useQuery<AuditLogResponse>({
    queryKey: ["admin_audit_log", page, actionFilter],
    queryFn: () => apiRequest<AuditLogResponse>(`/admin/audit-log?${queryParams.toString()}`),
  });

  const totalPages = Math.ceil((data?.total || 0) / 15) || 1;

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-md bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs font-semibold mb-2">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Compliance & Security Verification</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Administrative Access Audit Trail
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Immutable log of every bank staff lookup, Customer 360 view, CSV export, and status modification.
            </p>
          </div>

          <div>
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Administrative Actions</option>
              <option value="ADMIN_VIEW_CUSTOMER">Customer 360 Views</option>
              <option value="ADMIN_LIST_CUSTOMERS">Customer Directory Lookups</option>
              <option value="ADMIN_EXPORT_CUSTOMERS">CSV Data Exports</option>
              <option value="ADMIN_UPDATE_CUSTOMER_STATUS">Status Updates</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
          {isLoading ? (
            <div className="p-16 text-center text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-indigo-500 mb-3" />
              <p className="text-sm">Retrieving administrative audit trail...</p>
            </div>
          ) : data?.items && data.items.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] uppercase font-bold text-slate-400">
                    <tr>
                      <th className="px-5 py-3.5">Action Executed</th>
                      <th className="px-4 py-3.5">Staff Admin</th>
                      <th className="px-4 py-3.5">Target Customer</th>
                      <th className="px-4 py-3.5">Client IP</th>
                      <th className="px-4 py-3.5">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 font-medium">
                    {data.items.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-850/60">
                        <td className="px-5 py-3.5">
                          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-indigo-300 font-semibold">
                            {log.action}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 font-mono text-slate-300">
                          {log.admin_email}
                        </td>
                        <td className="px-4 py-3.5">
                          {log.customer_name ? (
                            <div>
                              <span className="font-semibold text-white">{log.customer_name}</span>
                              <span className="text-[10px] text-slate-500 block font-mono">{log.customer_id}</span>
                            </div>
                          ) : (
                            <span className="text-slate-500 text-[11px]">System Directory</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-slate-400">
                          {log.ip_address || "127.0.0.1"}
                        </td>
                        <td className="px-4 py-3.5 text-slate-400">{formatDate(log.timestamp)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="p-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                <span>Page {page} of {totalPages}</span>
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
            <div className="p-16 text-center text-slate-500 text-xs">
              No audit logs matching this action filter.
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}

