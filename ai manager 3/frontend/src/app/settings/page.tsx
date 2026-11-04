"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest, ApiException } from "@/lib/api";
import { AppLayout } from "@/components/AppLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import {
  ShieldCheck,
  ShieldAlert,
  Download,
  Trash2,
  CheckCircle,
  XCircle,
  FileSpreadsheet,
  MessageSquareText,
  Lock,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Mail,
  Phone,
  Bell,
  KeyRound,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

interface ConsentRecord {
  id: string;
  consent_type: string;
  granted: boolean;
  granted_at: string;
  revoked_at?: string | null;
  policy_version: string;
}

interface SecurityProfile {
  email: string;
  email_verified: boolean;
  phone?: string | null;
  phone_verified: boolean;
  alert_preferences: Record<string, boolean>;
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [alertState, setAlertState] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null);

  const [phoneInput, setPhoneInput] = useState<string>("");
  const [alertPrefs, setAlertPrefs] = useState<Record<string, boolean>>({
    new_login: true,
    account_added: true,
    account_removed: true,
    security_settings_updated: true,
    consent_changed: true,
  });

  // Fetch security settings
  const { data: securityProfile, isLoading: securityLoading } = useQuery<SecurityProfile>({
    queryKey: ["security_profile"],
    queryFn: async () => {
      const data = await apiRequest<SecurityProfile>("/auth/security");
      if (data) {
        setPhoneInput(data.phone || "");
        if (data.alert_preferences) {
          setAlertPrefs((prev) => ({ ...prev, ...data.alert_preferences }));
        }
      }
      return data;
    },
  });

  // Update security settings mutation
  const updateSecurityMutation = useMutation({
    mutationFn: (payload: { phone?: string; alert_preferences?: Record<string, boolean> }) =>
      apiRequest("/auth/security", {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["security_profile"] });
      setAlertState({
        type: "success",
        message: "Security preferences updated successfully. An email alert has been sent to confirm this change.",
      });
    },
    onError: (err: any) => {
      setAlertState({ type: "error", message: err.message || "Failed to update security preferences." });
    },
  });

  // Revoke Modal State
  const [revokeModalOpen, setRevokeModalOpen] = useState(false);
  const [targetConsentType, setTargetConsentType] = useState<string>("");
  const [deleteImportedData, setDeleteImportedData] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);

  // Delete All Data Modal State
  const [deleteDataModalOpen, setDeleteDataModalOpen] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isDeletingData, setIsDeletingData] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Fetch active user consents
  const { data: consents = [], isLoading: consentsLoading } = useQuery<ConsentRecord[]>({
    queryKey: ["consents"],
    queryFn: () => apiRequest<ConsentRecord[]>("/consents"),
  });

  const getConsent = (type: string) => {
    return consents.find((c) => c.consent_type === type);
  };

  const smsConsent = getConsent("sms_import");
  const statementConsent = getConsent("statement_upload");
  const bankShareConsent = getConsent("share_with_bank");
  const aiConsent = getConsent("ai_processing");

  // Grant Consent
  const grantMutation = useMutation({
    mutationFn: (consent_type: string) =>
      apiRequest("/consents", {
        method: "POST",
        body: JSON.stringify({ consent_type, policy_version: "1.0" }),
      }),
    onSuccess: (data, type) => {
      queryClient.invalidateQueries({ queryKey: ["consents"] });
      const label =
        type === "sms_import"
          ? "SMS Ingestion"
          : type === "statement_upload"
          ? "Statement Uploads"
          : type === "share_with_bank"
          ? "Bank Staff Sharing"
          : "AI Insights & Processing";
      setAlertState({
        type: "success",
        message: `Consent for ${label} granted successfully.`,
      });
    },
    onError: (err: any) => {
      setAlertState({ type: "error", message: err.message || "Failed to grant consent." });
    },
  });

  // Handle Revoke Consent
  const handleOpenRevokeModal = (type: string) => {
    setTargetConsentType(type);
    setDeleteImportedData(false);
    setRevokeModalOpen(true);
  };

  const handleConfirmRevoke = async () => {
    setIsRevoking(true);
    try {
      const res = await apiRequest("/consents/revoke", {
        method: "POST",
        body: JSON.stringify({
          consent_type: targetConsentType,
          delete_data: deleteImportedData,
        }),
      });

      queryClient.invalidateQueries({ queryKey: ["consents"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });

      setAlertState({
        type: "info",
        message: `Consent revoked successfully.${
          res.deleted_transactions > 0
            ? ` ${res.deleted_transactions} previously imported transactions were permanently removed.`
            : ""
        }`,
      });
      setRevokeModalOpen(false);
    } catch (err: any) {
      setAlertState({ type: "error", message: err.message || "Failed to revoke consent." });
    } finally {
      setIsRevoking(false);
    }
  };

  // Export Data as JSON
  const handleExportData = async () => {
    setIsExporting(true);
    setAlertState(null);
    try {
      const data = await apiRequest("/users/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `financial_data_export_${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setAlertState({
        type: "success",
        message: "Your complete financial dataset was exported successfully as JSON.",
      });
    } catch (err: any) {
      setAlertState({ type: "error", message: err.message || "Failed to export data." });
    } finally {
      setIsExporting(false);
    }
  };

  // Delete All Financial Data
  const handleConfirmDeleteAllData = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!confirmPassword) return;

    setIsDeletingData(true);
    try {
      await apiRequest("/users/me/data", {
        method: "DELETE",
        body: JSON.stringify({ password: confirmPassword }),
      });

      queryClient.invalidateQueries();
      setDeleteDataModalOpen(false);
      setConfirmPassword("");
      setAlertState({
        type: "success",
        message: "All your financial accounts, transactions, statements, and analytics have been permanently deleted.",
      });
    } catch (err: any) {
      setAlertState({
        type: "error",
        message: err.message || "Failed to wipe data. Please verify your password.",
      });
    } finally {
      setIsDeletingData(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-8 max-w-4xl mx-auto pb-12">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="info" className="text-[10px] tracking-wider uppercase font-bold">
              Account Governance
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Privacy Settings & Data Control
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage your granular permissions, view active consents, export portable records, or purge financial history.
          </p>
        </div>

        {alertState && (
          <Alert
            type={alertState.type}
            title={
              alertState.type === "success"
                ? "Operation Succeeded"
                : alertState.type === "error"
                ? "Error"
                : "Notice"
            }
            message={alertState.message}
            onClose={() => setAlertState(null)}
          />
        )}

        {/* Section 1: Granular Consents */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Active Data Consents (Promise 1)</CardTitle>
                <CardDescription>
                  Permissions granted by you for financial message and statement ingestion.
                </CardDescription>
              </div>
              <Link href="/privacy" className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1">
                <span>View 6 Promises</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </CardHeader>

          <CardContent className="space-y-4 pt-0">
            {/* SMS Consent Card */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
                  <MessageSquareText className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-sm text-slate-900">SMS Ingestion Consent</h4>
                    {smsConsent?.granted && !smsConsent?.revoked_at ? (
                      <Badge variant="success">Active</Badge>
                    ) : (
                      <Badge variant="default">Not Granted / Revoked</Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Permission to parse pasted bank SMS transaction alerts (HDFC, SBI, ICICI, UPI, etc.).
                  </p>
                  {smsConsent?.granted && (
                    <p className="text-[11px] text-slate-400 mt-1">
                      Granted on {new Date(smsConsent.granted_at).toLocaleDateString()} (Policy v{smsConsent.policy_version})
                    </p>
                  )}
                </div>
              </div>

              <div>
                {smsConsent?.granted && !smsConsent?.revoked_at ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenRevokeModal("sms_import")}
                    className="text-slate-600 hover:text-rose-600 hover:border-rose-300"
                  >
                    Revoke Permission
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => grantMutation.mutate("sms_import")}
                    isLoading={grantMutation.isPending && grantMutation.variables === "sms_import"}
                  >
                    Grant Permission
                  </Button>
                )}
              </div>
            </div>

            {/* Statement Upload Consent Card */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-sm text-slate-900">Statement Upload Consent</h4>
                    {statementConsent?.granted && !statementConsent?.revoked_at ? (
                      <Badge variant="success">Active</Badge>
                    ) : (
                      <Badge variant="default">Not Granted / Revoked</Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Permission to parse uploaded CSV and text-based PDF bank statements in memory.
                  </p>
                  {statementConsent?.granted && (
                    <p className="text-[11px] text-slate-400 mt-1">
                      Granted on {new Date(statementConsent.granted_at).toLocaleDateString()} (Policy v{statementConsent.policy_version})
                    </p>
                  )}
                </div>
              </div>

              <div>
                {statementConsent?.granted && !statementConsent?.revoked_at ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenRevokeModal("statement_upload")}
                    className="text-slate-600 hover:text-rose-600 hover:border-rose-300"
                  >
                    Revoke Permission
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => grantMutation.mutate("statement_upload")}
                    isLoading={grantMutation.isPending && grantMutation.variables === "statement_upload"}
                  >
                    Grant Permission
                  </Button>
                )}
              </div>
            </div>

            {/* Share With Bank Staff Consent Card */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-sm text-slate-900">Share with Bank Staff / Advisor</h4>
                    {bankShareConsent?.granted && !bankShareConsent?.revoked_at ? (
                      <Badge variant="success">Active (Visible)</Badge>
                    ) : (
                      <Badge variant="default">Private (Invisible to Bank)</Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Permits authorized bank staff to view read-only masked account summaries and spending predictions for financial advice.
                  </p>
                  {bankShareConsent?.granted && (
                    <p className="text-[11px] text-slate-400 mt-1">
                      Granted on {new Date(bankShareConsent.granted_at).toLocaleDateString()} (Policy v{bankShareConsent.policy_version})
                    </p>
                  )}
                </div>
              </div>

              <div>
                {bankShareConsent?.granted && !bankShareConsent?.revoked_at ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenRevokeModal("share_with_bank")}
                    className="text-slate-600 hover:text-rose-600 hover:border-rose-300"
                  >
                    Revoke Access
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => grantMutation.mutate("share_with_bank")}
                    isLoading={grantMutation.isPending && grantMutation.variables === "share_with_bank"}
                  >
                    Grant Access
                  </Button>
                )}
              </div>
            </div>

            {/* AI Processing & Smart Categorization Consent Card */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-xl bg-purple-50 text-purple-600 border border-purple-100">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-sm text-slate-900">AI Model Insights & Categorization</h4>
                    {aiConsent?.granted && !aiConsent?.revoked_at ? (
                      <Badge variant="success">Active (AI Enabled)</Badge>
                    ) : (
                      <Badge variant="default">Disabled / Offline Only</Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Permits the AI model to analyze non-PII transaction categories, generate 24h spending insights, and power the financial assistant chat.
                  </p>
                  {aiConsent?.granted && (
                    <p className="text-[11px] text-slate-400 mt-1">
                      Granted on {new Date(aiConsent.granted_at).toLocaleDateString()} (Policy v{aiConsent.policy_version})
                    </p>
                  )}
                </div>
              </div>

              <div>
                {aiConsent?.granted && !aiConsent?.revoked_at ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenRevokeModal("ai_processing")}
                    className="text-slate-600 hover:text-rose-600 hover:border-rose-300"
                  >
                    Revoke Consent
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => grantMutation.mutate("ai_processing")}
                    isLoading={grantMutation.isPending && grantMutation.variables === "ai_processing"}
                  >
                    Enable AI Features
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section: Multi-Channel Authentication & Security Alerts */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-blue-600" />
              <CardTitle>Security & Notification Alerts</CardTitle>
            </div>
            <CardDescription>
              Manage your verified contact methods and security notification preferences.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-0">
            {/* Contact Status */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Email Status */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100/70 text-blue-700 rounded-lg">
                    <Mail className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 font-medium block">Email Address</span>
                    <span className="text-sm font-semibold text-slate-800">{securityProfile?.email || "—"}</span>
                  </div>
                </div>
                {securityProfile?.email_verified ? (
                  <Badge variant="success">Verified</Badge>
                ) : (
                  <Badge variant="warning">Unverified</Badge>
                )}
              </div>

              {/* Phone Status */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-100/70 text-indigo-700 rounded-lg">
                    <Phone className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 font-medium block">Mobile Phone</span>
                    <span className="text-sm font-semibold text-slate-800">
                      {securityProfile?.phone || "Not configured"}
                    </span>
                  </div>
                </div>
                <Badge variant={securityProfile?.phone ? "success" : "default"}>
                  {securityProfile?.phone ? "Configured" : "None"}
                </Badge>
              </div>
            </div>

            {/* Alert Preferences */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Bell className="w-4 h-4 text-slate-600" />
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                  Email Security Alert Preferences
                </label>
              </div>
              <p className="text-xs text-slate-500 mb-3">
                Informational notifications dispatched to your email for account security. No passwords or sensitive transaction numbers are ever included.
              </p>

              <div className="space-y-2.5">
                {[
                  { key: "new_login", label: "New sign-in from a new device or IP address" },
                  { key: "account_added", label: "Bank account or card linked to your profile" },
                  { key: "account_removed", label: "Bank account or card unlinked from your profile" },
                  { key: "security_settings_updated", label: "Security preferences or password updated" },
                  { key: "consent_changed", label: "Data privacy consent granted or revoked" },
                ].map(({ key, label }) => (
                  <label
                    key={key}
                    className="flex items-center justify-between p-3 rounded-lg border border-slate-100 hover:bg-slate-50/60 transition-colors cursor-pointer"
                  >
                    <span className="text-xs font-medium text-slate-700">{label}</span>
                    <input
                      type="checkbox"
                      checked={alertPrefs[key] ?? true}
                      onChange={(e) =>
                        setAlertPrefs((prev) => ({ ...prev, [key]: e.target.checked }))
                      }
                      className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                    />
                  </label>
                ))}
              </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end pt-2">
              <Button
                variant="primary"
                onClick={() =>
                  updateSecurityMutation.mutate({
                    phone: phoneInput || undefined,
                    alert_preferences: alertPrefs,
                  })
                }
                isLoading={updateSecurityMutation.isPending}
              >
                Save Security Preferences
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Section 2: Data Portability (Export) */}
        <Card>
          <CardHeader>
            <CardTitle>Data Portability & Export (Promise 4)</CardTitle>
            <CardDescription>
              Download a complete machine-readable copy of your financial data, accounts, categories, and consents.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-0">
            <div className="space-y-1">
              <p className="text-xs font-semibold text-slate-700">JSON Archive Download</p>
              <p className="text-xs text-slate-500">
                Exports all your records formatted with integer paise precision and UTC timestamps.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportData}
              isLoading={isExporting}
            >
              <Download className="w-4 h-4 mr-2 text-blue-600" />
              Export My Data (JSON)
            </Button>
          </CardContent>
        </Card>

        {/* Section 3: Data Deletion (Danger Zone) */}
        <Card className="border-rose-200 bg-rose-50/20">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-rose-600" />
              <CardTitle className="text-rose-900">Danger Zone: Financial Data Erasure</CardTitle>
            </div>
            <CardDescription className="text-rose-700/80">
              Permanently purge all linked bank accounts, transactions, statement files, and analytics.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-0">
            <div className="space-y-1">
              <p className="text-xs font-semibold text-slate-700">Irreversible Deletion</p>
              <p className="text-xs text-slate-500">
                Requires password confirmation. Your user profile will remain active, but all financial data will be erased.
              </p>
            </div>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setDeleteDataModalOpen(true)}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete All Financial Data
            </Button>
          </CardContent>
        </Card>

        {/* Revoke Consent Modal */}
        <Modal
          isOpen={revokeModalOpen}
          onClose={() => setRevokeModalOpen(false)}
          title={`Revoke ${targetConsentType === "sms_import" ? "SMS Ingestion" : "Statement Upload"} Permission`}
          description="Are you sure you want to revoke this consent?"
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-600 leading-relaxed">
              Future imports from this source will be blocked immediately until you grant consent again.
            </p>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={deleteImportedData}
                  onChange={(e) => setDeleteImportedData(e.target.checked)}
                  className="mt-0.5 rounded border-slate-300 text-rose-600 focus:ring-rose-500"
                />
                <div className="text-xs">
                  <span className="font-bold text-slate-800 block">
                    Delete previously imported data from this source
                  </span>
                  <span className="text-slate-500 block mt-0.5">
                    If checked, transactions previously parsed via this source ({targetConsentType === "sms_import" ? "SMS" : "CSV/PDF"}) will be permanently removed.
                  </span>
                </div>
              </label>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <Button variant="ghost" size="sm" onClick={() => setRevokeModalOpen(false)}>
                Cancel
              </Button>
              <Button
                variant={deleteImportedData ? "danger" : "primary"}
                size="sm"
                onClick={handleConfirmRevoke}
                isLoading={isRevoking}
              >
                Confirm Revocation
              </Button>
            </div>
          </div>
        </Modal>

        {/* Delete All Data Confirmation Modal */}
        <Modal
          isOpen={deleteDataModalOpen}
          onClose={() => setDeleteDataModalOpen(false)}
          title="Confirm Permanent Financial Data Deletion"
          description="This action cannot be undone."
        >
          <form onSubmit={handleConfirmDeleteAllData} className="space-y-4">
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>
                All your linked accounts, credit cards, statement imports, expense transactions, budgets, and predictive savings suggestions will be completely deleted from the database.
              </span>
            </div>

            <Input
              label="Confirm Your Password"
              type="password"
              placeholder="Enter your account password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <Button variant="ghost" size="sm" onClick={() => setDeleteDataModalOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="danger"
                size="sm"
                isLoading={isDeletingData}
                disabled={!confirmPassword}
              >
                Permanently Delete My Data
              </Button>
            </div>
          </form>
        </Modal>
      </div>
    </AppLayout>
  );
}
