"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { formatDate } from "@/lib/formatters";
import { AdminLayout } from "@/components/AdminLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Loader2,
  Filter,
  CheckCircle2,
  Eye,
} from "lucide-react";

interface RiskAlert {
  id: string;
  customer_id: string;
  customer_name: string;
  masked_email: string;
  segment?: string;
  alert_type: string;
  severity: "high" | "medium" | "low";
  reason: string;
  detected_at: string;
}

export default function AdminRiskAlertsPage() {
  const [severityFilter, setSeverityFilter] = useState("all");

  const { data: alerts = [], isLoading, refetch } = useQuery<RiskAlert[]>({
    queryKey: ["admin_risk_alerts"],
    queryFn: () => apiRequest<RiskAlert[]>("/admin/risk-alerts"),
  });

  const filteredAlerts = alerts.filter((a) => {
    if (severityFilter === "all") return true;
    return a.severity === severityFilter;
  });

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-md bg-amber-950/80 border border-amber-800/80 text-amber-300 text-xs font-semibold mb-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>Risk & Anomaly Engine</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Client Risk Alerts & Spikes
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Rule-based spending anomalies, category spikes, budget overshoots, and deficit cashflow flags.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Severities</option>
              <option value="high">High Severity Only</option>
              <option value="medium">Medium Severity</option>
              <option value="low">Low Severity</option>
            </select>
          </div>
        </div>

        {/* Alerts Grid */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="p-16 text-center text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-amber-400 mb-3" />
              <p className="text-sm">Scanning client profiles for spending anomalies...</p>
            </div>
          ) : filteredAlerts.length > 0 ? (
            filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700/80 transition-all shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-white text-base">{alert.customer_name}</span>
                    <span className="text-xs text-slate-400 font-mono">({alert.masked_email})</span>
                    <Badge
                      variant={alert.severity === "high" ? "danger" : "warning"}
                      className="text-[10px] uppercase font-bold"
                    >
                      {alert.severity} Severity
                    </Badge>
                    <Badge variant="outline" className="bg-slate-950 text-slate-400 border-slate-800 text-[10px] uppercase">
                      {alert.alert_type.replace(/_/g, " ")}
                    </Badge>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
                    {alert.reason}
                  </p>

                  <div className="text-[11px] text-slate-500">
                    Detected on {formatDate(alert.detected_at)} • Segment: <span className="capitalize text-slate-400">{alert.segment || "General"}</span>
                  </div>
                </div>

                <div className="shrink-0">
                  <Link href={`/admin/customers/${alert.customer_id}`}>
                    <Button size="sm" variant="outline" className="border-indigo-800 text-indigo-300 hover:bg-indigo-950 text-xs">
                      <Eye className="w-3.5 h-3.5 mr-1.5" />
                      Investigate Profile
                    </Button>
                  </Link>
                </div>
              </div>
            ))
          ) : (
            <div className="p-16 text-center rounded-2xl bg-slate-900 border border-slate-800 text-slate-400 text-xs">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
              <p className="font-semibold text-white text-sm">No Active Risk Flags</p>
              <p className="mt-1">All monitored customers are currently spending within baseline parameters.</p>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
