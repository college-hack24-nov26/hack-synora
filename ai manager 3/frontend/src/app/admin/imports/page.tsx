"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { formatDate } from "@/lib/formatters";
import { AdminLayout } from "@/components/AdminLayout";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  FileSpreadsheet,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronLeft,
  ChevronRight,
  Eye,
} from "lucide-react";

interface AdminImportItem {
  id: string;
  customer_id: string;
  customer_name: string;
  masked_email: string;
  source_type: string;
  status: string;
  total_rows: number;
  parsed_rows: number;
  failed_rows: number;
  error_summary?: string;
  created_at: string;
}

interface ImportResponse {
  items: AdminImportItem[];
  total: number;
  page: number;
  limit: number;
}

export default function AdminImportsPage() {
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);

  const queryParams = new URLSearchParams({
    page: page.toString(),
    limit: "15",
    ...(statusFilter !== "all" ? { status: statusFilter } : {}),
  });

  const { data, isLoading } = useQuery<ImportResponse>({
    queryKey: ["admin_imports", page, statusFilter],
    queryFn: () => apiRequest<ImportResponse>(`/admin/imports?${queryParams.toString()}`),
  });

  const totalPages = Math.ceil((data?.total || 0) / 15) || 1;

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-md bg-indigo-950/80 border border-indigo-800 text-indigo-300 text-xs font-semibold mb-2">
              <FileSpreadsheet className="w-3.5 h-3.5 text-indigo-400" />
              <span>Statement Processing Pipeline</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Customer Statement Ingestion Monitoring
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Real-time monitoring of SMS and digital statement ingestion jobs without raw file exposure.
            </p>
          </div>

          <div>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Ingestion Statuses</option>
              <option value="done">Completed Only</option>
              <option value="failed">Failed Jobs Only</option>
              <option value="processing">Processing</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
          {isLoading ? (
            <div className="p-16 text-center text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-indigo-500 mb-3" />
              <p className="text-sm">Loading ingestion jobs...</p>
            </div>
          ) : data?.items && data.items.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] uppercase font-bold text-slate-400">
                    <tr>
                      <th className="px-5 py-3.5">Customer</th>
                      <th className="px-4 py-3.5">Source Format</th>
                      <th className="px-4 py-3.5">Status</th>
                      <th className="px-4 py-3.5">Parsed / Total</th>
                      <th className="px-4 py-3.5">Failed Rows</th>
                      <th className="px-4 py-3.5">Timestamp</th>
                      <th className="px-4 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 font-medium">
                    {data.items.map((job) => (
                      <tr key={job.id} className="hover:bg-slate-850/60">
                        <td className="px-5 py-3.5">
                          <div className="font-bold text-white text-sm">{job.customer_name}</div>
                          <div className="text-slate-400 font-mono text-[11px]">{job.masked_email}</div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="text-[10px] uppercase font-bold text-slate-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                            {job.source_type}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          <Badge
                            variant={job.status === "done" ? "success" : job.status === "failed" ? "danger" : "warning"}
                            className="text-[10px] uppercase"
                          >
                            {job.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3.5 font-bold text-slate-200">
                          {job.parsed_rows} / {job.total_rows}
                        </td>
                        <td className="px-4 py-3.5">
                          {job.failed_rows > 0 ? (
                            <span className="text-rose-400 font-bold">{job.failed_rows}</span>
                          ) : (
                            <span className="text-slate-500">0</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-slate-400">{formatDate(job.created_at)}</td>
                        <td className="px-4 py-3.5 text-right">
                          <Link href={`/admin/customers/${job.customer_id}`}>
                            <Button size="sm" variant="outline" className="border-slate-800 text-xs py-1 h-8">
                              <Eye className="w-3.5 h-3.5 mr-1" />
                              View Client
                            </Button>
                          </Link>
                        </td>
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
              No statement ingestion records found.
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}

