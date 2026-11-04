"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { AppLayout } from "@/components/AppLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { ConsentModal } from "@/components/ConsentModal";
import {
  MessageSquareText,
  FileSpreadsheet,
  FileText,
  PlusCircle,
  Upload,
  CheckCircle,
  ShieldCheck,
  ShieldAlert,
  Info,
  Sparkles,
  Lock,
  ArrowRight,
  Loader2,
  FileCheck2,
  AlertCircle,
  Trash2,
  HelpCircle,
} from "lucide-react";

interface Account {
  id: string;
  name: string;
  type: string;
  last4?: string;
}

interface ConsentRecord {
  id: string;
  consent_type: string;
  granted: boolean;
  granted_at: string;
  revoked_at?: string | null;
  policy_version: string;
}

interface ImportSummary {
  import_id?: string;
  source: string;
  total: number;
  inserted: number;
  duplicates: number;
  failed: number;
}

export default function ImportPage() {
  const queryClient = useQueryClient();
  const [activeMethod, setActiveMethod] = useState<"sms" | "csv" | "pdf" | "manual">("sms");
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [smsText, setSmsText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [resultMessage, setResultMessage] = useState<{ type: "success" | "info" | "warning"; text: string } | null>(null);
  const [importSummary, setImportSummary] = useState<ImportSummary | null>(null);

  // File Upload State
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [pdfFile, setPdfFile] = useState<File | null>(null);

  // Manual Transaction State
  const [manualPayee, setManualPayee] = useState("");
  const [manualAmount, setManualAmount] = useState("");
  const [manualDirection, setManualDirection] = useState("debit");
  const [manualDate, setManualDate] = useState(new Date().toISOString().split("T")[0]);
  const [manualDesc, setManualDesc] = useState("");

  // Consent Modal State
  const [consentModalOpen, setConsentModalOpen] = useState(false);
  const [consentModalType, setConsentModalType] = useState<"sms_import" | "statement_upload" | null>(null);
  const [isGrantingConsent, setIsGrantingConsent] = useState(false);

  // Fetch Accounts to bind the import to
  const { data: accounts = [], isLoading: accountsLoading } = useQuery<Account[]>({
    queryKey: ["accounts"],
    queryFn: () => apiRequest<Account[]>("/accounts"),
  });

  // Fetch User Consents (Promise 1)
  const { data: consents = [], refetch: refetchConsents } = useQuery<ConsentRecord[]>({
    queryKey: ["consents"],
    queryFn: () => apiRequest<ConsentRecord[]>("/consents"),
  });

  const hasSmsConsent = consents.some(
    (c) => c.consent_type === "sms_import" && c.granted && !c.revoked_at
  );
  const hasStatementConsent = consents.some(
    (c) => c.consent_type === "statement_upload" && c.granted && !c.revoked_at
  );

  const SAMPLE_SMS = `HDFC Bank: Rs 849.00 debited from a/c **4589 on 03-Nov-26 to SWIGGY. Avl bal: Rs 42,150.00.
Dear SBI User, your A/C 9901 debited by Rs 1500.00 on 02-Nov-26 by UPI/3310029/UBER.
ICICI Bank: Acct XX1204 debited with INR 2,499.00 on 01-Nov-26 towards AMAZON PAY.`;

  const handleSimulateSms = () => {
    setSmsText(SAMPLE_SMS);
  };

  const handleOpenConsentModal = (type: "sms_import" | "statement_upload") => {
    setConsentModalType(type);
    setConsentModalOpen(true);
  };

  const handleGrantConsent = async () => {
    if (!consentModalType) return;
    setIsGrantingConsent(true);
    try {
      await apiRequest("/consents", {
        method: "POST",
        body: JSON.stringify({
          consent_type: consentModalType,
          policy_version: "1.0",
        }),
      });
      await refetchConsents();
      setConsentModalOpen(false);
      setResultMessage({
        type: "success",
        text: `Consent for ${consentModalType === "sms_import" ? "SMS ingestion" : "statement uploads"} has been granted. You can proceed with your import.`,
      });
    } catch (err: any) {
      setResultMessage({
        type: "warning",
        text: err.message || "Failed to record consent.",
      });
    } finally {
      setIsGrantingConsent(false);
    }
  };

  // Process SMS Import
  const handleProcessSmsImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAccountId) {
      setResultMessage({
        type: "warning",
        text: "Please select a target account to attribute these transactions to.",
      });
      return;
    }

    if (!hasSmsConsent) {
      handleOpenConsentModal("sms_import");
      return;
    }

    setIsProcessing(true);
    setResultMessage(null);
    setImportSummary(null);

    try {
      const response = await apiRequest("/imports/sms", {
        method: "POST",
        body: JSON.stringify({
          account_id: selectedAccountId,
          raw_text: smsText,
        }),
      });

      setImportSummary({
        import_id: response.import_id,
        source: "sms",
        total: response.total_messages,
        inserted: response.inserted_transactions,
        duplicates: response.duplicates_skipped,
        failed: response.unparsed_count,
      });

      setResultMessage({
        type: "success",
        text: `Successfully parsed and categorized ${response.inserted_transactions} transactions (${response.duplicates_skipped} duplicates skipped).`,
      });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-current-month"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-history"] });
    } catch (err: any) {
      if (err.status === 403) {
        handleOpenConsentModal("sms_import");
      }
      setResultMessage({
        type: "warning",
        text: err.message || "Failed to process SMS import.",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Process CSV Upload
  const handleProcessCsvUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAccountId) {
      setResultMessage({
        type: "warning",
        text: "Please select a target account to attribute these transactions to.",
      });
      return;
    }

    if (!hasStatementConsent) {
      handleOpenConsentModal("statement_upload");
      return;
    }

    if (!csvFile) {
      setResultMessage({
        type: "warning",
        text: "Please select a CSV statement file to upload.",
      });
      return;
    }

    setIsProcessing(true);
    setResultMessage(null);
    setImportSummary(null);

    const formData = new FormData();
    formData.append("account_id", selectedAccountId);
    formData.append("file", csvFile);

    try {
      const response = await apiRequest("/imports/csv", {
        method: "POST",
        body: formData,
      });

      setImportSummary({
        import_id: response.import_id,
        source: "csv",
        total: response.total_rows,
        inserted: response.inserted_transactions,
        duplicates: response.duplicates_skipped,
        failed: response.failed_rows,
      });

      setResultMessage({
        type: "success",
        text: `CSV statement parsed successfully! ${response.inserted_transactions} new transactions recorded.`,
      });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-current-month"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-history"] });
      setCsvFile(null);
    } catch (err: any) {
      if (err.status === 403) {
        handleOpenConsentModal("statement_upload");
      }
      setResultMessage({
        type: "warning",
        text: err.message || "Failed to process CSV statement.",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Process PDF Upload
  const handleProcessPdfUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAccountId) {
      setResultMessage({
        type: "warning",
        text: "Please select a target account to attribute these transactions to.",
      });
      return;
    }

    if (!hasStatementConsent) {
      handleOpenConsentModal("statement_upload");
      return;
    }

    if (!pdfFile) {
      setResultMessage({
        type: "warning",
        text: "Please select a PDF bank statement file to upload.",
      });
      return;
    }

    setIsProcessing(true);
    setResultMessage(null);
    setImportSummary(null);

    const formData = new FormData();
    formData.append("account_id", selectedAccountId);
    formData.append("file", pdfFile);

    try {
      const response = await apiRequest("/imports/pdf", {
        method: "POST",
        body: formData,
      });

      setImportSummary({
        import_id: response.import_id,
        source: "pdf",
        total: response.total_rows,
        inserted: response.inserted_transactions,
        duplicates: response.duplicates_skipped,
        failed: response.failed_rows,
      });

      setResultMessage({
        type: "success",
        text: `PDF statement parsed successfully in memory! ${response.inserted_transactions} new transactions recorded.`,
      });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-current-month"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-history"] });
      setPdfFile(null);
    } catch (err: any) {
      if (err.status === 403) {
        handleOpenConsentModal("statement_upload");
      }
      setResultMessage({
        type: "warning",
        text: err.message || "Failed to process PDF statement.",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Process Manual Transaction
  const handleProcessManualTxn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAccountId) {
      setResultMessage({
        type: "warning",
        text: "Please select a target account.",
      });
      return;
    }

    const amtFloat = parseFloat(manualAmount);
    if (isNaN(amtFloat) || amtFloat <= 0) {
      setResultMessage({
        type: "warning",
        text: "Please enter a valid positive amount.",
      });
      return;
    }

    setIsProcessing(true);
    setResultMessage(null);

    try {
      await apiRequest("/transactions", {
        method: "POST",
        body: JSON.stringify({
          account_id: selectedAccountId,
          amount_minor: Math.round(amtFloat * 100),
          direction: manualDirection,
          merchant: manualPayee,
          txn_date: new Date(manualDate).toISOString(),
          description: manualDesc || `Manual: ${manualPayee}`,
        }),
      });

      setResultMessage({
        type: "success",
        text: `Manual transaction for ₹${amtFloat.toFixed(2)} recorded successfully!`,
      });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-current-month"] });
      queryClient.invalidateQueries({ queryKey: ["prediction-history"] });
      setManualPayee("");
      setManualAmount("");
      setManualDesc("");
    } catch (err: any) {
      setResultMessage({
        type: "warning",
        text: err.message || "Failed to save transaction.",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6 max-w-5xl mx-auto pb-12">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="info" className="text-[10px] tracking-wider uppercase font-bold">
              Multi-Source Ingestion Engine
            </Badge>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Import Bank Statements & Spends
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Choose your preferred method below. SMS reading is completely optional; you can upload CSV or PDF statements instead.
          </p>
        </div>

        {/* Input Methods Switcher */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <button
            type="button"
            onClick={() => {
              setActiveMethod("sms");
              setResultMessage(null);
              if (!hasSmsConsent) {
                handleOpenConsentModal("sms_import");
              }
            }}
            className={`p-4 rounded-2xl border text-left transition-all ${activeMethod === "sms"
                ? "bg-blue-50/70 border-blue-600 ring-2 ring-blue-600/20 shadow-sm"
                : "bg-white border-slate-200 hover:border-slate-300"
              }`}
          >
            <div className="flex items-center justify-between mb-2">
              <MessageSquareText
                className={`w-6 h-6 ${activeMethod === "sms" ? "text-blue-600" : "text-slate-400"
                  }`}
              />
              <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                Optional
              </span>
            </div>
            <h4 className="font-bold text-sm text-slate-900">Paste SMS</h4>
            <p className="text-xs text-slate-500 mt-0.5">UPI, Cards & Alerts</p>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveMethod("csv");
              setResultMessage(null);
              if (!hasStatementConsent) {
                handleOpenConsentModal("statement_upload");
              }
            }}
            className={`p-4 rounded-2xl border text-left transition-all ${activeMethod === "csv"
                ? "bg-blue-50/70 border-blue-600 ring-2 ring-blue-600/20 shadow-sm"
                : "bg-white border-slate-200 hover:border-slate-300"
              }`}
          >
            <FileSpreadsheet
              className={`w-6 h-6 mb-2 ${activeMethod === "csv" ? "text-blue-600" : "text-slate-400"
                }`}
            />
            <h4 className="font-bold text-sm text-slate-900">CSV Statement</h4>
            <p className="text-xs text-slate-500 mt-0.5">Auto column detection</p>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveMethod("pdf");
              setResultMessage(null);
              if (!hasStatementConsent) {
                handleOpenConsentModal("statement_upload");
              }
            }}
            className={`p-4 rounded-2xl border text-left transition-all ${activeMethod === "pdf"
                ? "bg-blue-50/70 border-blue-600 ring-2 ring-blue-600/20 shadow-sm"
                : "bg-white border-slate-200 hover:border-slate-300"
              }`}
          >
            <FileText
              className={`w-6 h-6 mb-2 ${activeMethod === "pdf" ? "text-blue-600" : "text-slate-400"
                }`}
            />
            <h4 className="font-bold text-sm text-slate-900">PDF Statement</h4>
            <p className="text-xs text-slate-500 mt-0.5">Text-based e-statements</p>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveMethod("manual");
              setResultMessage(null);
            }}
            className={`p-4 rounded-2xl border text-left transition-all ${activeMethod === "manual"
                ? "bg-blue-50/70 border-blue-600 ring-2 ring-blue-600/20 shadow-sm"
                : "bg-white border-slate-200 hover:border-slate-300"
              }`}
          >
            <PlusCircle
              className={`w-6 h-6 mb-2 ${activeMethod === "manual" ? "text-blue-600" : "text-slate-400"
                }`}
            />
            <h4 className="font-bold text-sm text-slate-900">Manual Entry</h4>
            <p className="text-xs text-slate-500 mt-0.5">Single spend or cash</p>
          </button>
        </div>

        {/* Destination Account Selector */}
        <Card>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-0.5">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Target Bank Account
              </label>
              <p className="text-xs text-slate-500">
                Transactions will be deduplicated against this account using SHA-256 hash.
              </p>
            </div>
            <div className="w-full sm:w-72">
              <select
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
              >
                <option value="">Select an account...</option>
                {accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} {acc.last4 ? `(•• ${acc.last4})` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </Card>

        {/* Trust & Privacy Badge (Promise 3, 4, 5) */}
        <div className="flex items-center justify-between flex-wrap gap-2 px-4 py-3 rounded-2xl bg-gradient-to-r from-emerald-50 via-teal-50 to-blue-50 border border-emerald-200/60 text-xs text-slate-700 shadow-sm">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold text-slate-800">
              Encrypted at Rest · Only You Can Access This · Zero Funds Movement
            </span>
          </div>
          <Link href="/privacy" className="text-blue-600 hover:text-blue-700 font-bold underline text-[11px]">
            Read our 6 Trust Promises
          </Link>
        </div>

        {/* Feedback message */}
        {resultMessage && (
          <Alert
            type={resultMessage.type}
            title={
              resultMessage.type === "success"
                ? "Import Completed"
                : resultMessage.type === "info"
                  ? "Ingestion Pipeline Status"
                  : "Import Notice"
            }
            message={resultMessage.text}
            onClose={() => setResultMessage(null)}
          />
        )}

        {/* Summary Card for Import */}
        {importSummary && (
          <div className="p-4 rounded-2xl border border-emerald-200 bg-emerald-50/50 flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 text-emerald-700 rounded-xl">
                <FileCheck2 className="w-5 h-5" />
              </div>
              <div>
                <p className="font-bold text-slate-800 text-sm">
                  Batch Ingestion Summary ({importSummary.source.toUpperCase()})
                </p>
                <p className="text-slate-500">
                  {importSummary.total} total lines processed
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <span className="block font-bold text-emerald-700 text-sm">{importSummary.inserted}</span>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Saved</span>
              </div>
              <div className="text-center">
                <span className="block font-bold text-slate-600 text-sm">{importSummary.duplicates}</span>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Duplicates</span>
              </div>
              {importSummary.failed > 0 && (
                <div className="text-center">
                  <span className="block font-bold text-amber-600 text-sm">{importSummary.failed}</span>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Skipped</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Mode 1: SMS Raw Text */}
        {activeMethod === "sms" && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle>Paste Bank SMS Messages</CardTitle>
                  <Badge variant="default">Optional</Badge>
                </div>
                <CardDescription>
                  Supports HDFC, SBI, ICICI, Axis, Kotak, PhonePe, Google Pay & Paytm alerts.
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={handleSimulateSms}>
                <Sparkles className="w-3.5 h-3.5 mr-1 text-blue-600" />
                Load Sample SMS
              </Button>
            </CardHeader>

            {/* Consent Notice if missing */}
            {!hasSmsConsent && (
              <div className="mx-6 mb-4 p-4 rounded-xl border border-amber-200 bg-amber-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-amber-900">
                <div className="flex items-start gap-2.5">
                  <ShieldAlert className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                  <div>
                    <span className="font-bold block">Explicit Permission Required (Promise 1)</span>
                    <span className="text-amber-800">
                      We require your permission before parsing bank SMS text. You can revoke it anytime in Privacy Settings.
                    </span>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => handleOpenConsentModal("sms_import")}
                  className="bg-amber-600 hover:bg-amber-700 text-white shrink-0"
                >
                  Grant SMS Permission
                </Button>
              </div>
            )}

            <form onSubmit={handleProcessSmsImport} className="space-y-4">
              <textarea
                value={smsText}
                onChange={(e) => setSmsText(e.target.value)}
                rows={7}
                placeholder="Paste one or multiple SMS alerts here. Example:&#10;HDFC Bank: Rs 550.00 debited from a/c **4589 on 03-Nov-26 to ZOMATO..."
                className="w-full p-4 text-sm font-mono bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all resize-y"
                required
              />

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 pt-2 border-t border-slate-100">
                <div className="flex items-center gap-1.5 text-slate-500">
                  <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>OTPs, balances, and promotional texts are automatically filtered out.</span>
                </div>
                <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setActiveMethod("manual")}
                  >
                    Skip, I'll add manually
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    isLoading={isProcessing}
                    disabled={!hasSmsConsent || !smsText.trim()}
                    title={!hasSmsConsent ? "Grant SMS permission to enable parsing" : ""}
                  >
                    Parse & Categorize Spends
                  </Button>
                </div>
              </div>
            </form>
          </Card>
        )}

        {/* Mode 2: CSV / Excel Upload */}
        {activeMethod === "csv" && (
          <Card>
            <CardHeader>
              <CardTitle>Upload CSV / Excel Bank Statement</CardTitle>
              <CardDescription>
                Flexible column detection for date, description, debit/credit, or single amount columns.
              </CardDescription>
            </CardHeader>

            {/* Consent Notice if missing */}
            {!hasStatementConsent && (
              <div className="mx-6 mb-4 p-4 rounded-xl border border-amber-200 bg-amber-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-amber-900">
                <div className="flex items-start gap-2.5">
                  <ShieldAlert className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                  <div>
                    <span className="font-bold block">Explicit Statement Upload Consent Required (Promise 1)</span>
                    <span className="text-amber-800">
                      We require your permission before uploading statements. Files are processed in memory and never stored on disk.
                    </span>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => handleOpenConsentModal("statement_upload")}
                  className="bg-amber-600 hover:bg-amber-700 text-white shrink-0"
                >
                  Grant Statement Permission
                </Button>
              </div>
            )}

            <form onSubmit={handleProcessCsvUpload} className="space-y-4">
              <div
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${csvFile
                  ? "border-emerald-400 bg-emerald-50/30"
                  : "border-slate-200 bg-slate-50/50 hover:border-slate-300"
                  }`}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    setCsvFile(e.dataTransfer.files[0]);
                  }
                }}
              >
                {csvFile ? (
                  <div className="space-y-2">
                    <FileCheck2 className="w-10 h-10 text-emerald-600 mx-auto mb-2" />
                    <h4 className="text-sm font-bold text-slate-800">{csvFile.name}</h4>
                    <p className="text-xs text-slate-500">
                      {(csvFile.size / 1024).toFixed(1)} KB · Ready to parse
                    </p>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setCsvFile(null)}
                      className="text-slate-400 hover:text-rose-600"
                    >
                      <Trash2 className="w-4 h-4 mr-1" /> Remove
                    </Button>
                  </div>
                ) : (
                  <div>
                    <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                    <h4 className="text-sm font-bold text-slate-800">
                      Drag and drop your statement file here
                    </h4>
                    <p className="text-xs text-slate-500 mt-1 mb-4">
                      Supported formats: .csv, .tsv, .txt (up to 10 MB)
                    </p>
                    <input
                      type="file"
                      id="csv-file-input"
                      className="hidden"
                      accept=".csv, .tsv, .txt"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setCsvFile(e.target.files[0]);
                        }
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => document.getElementById("csv-file-input")?.click()}
                    >
                      Browse Files
                    </Button>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <span className="text-xs text-slate-400">
                  Processed in memory · Raw file is never saved to disk
                </span>
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={isProcessing}
                  disabled={!hasStatementConsent || !csvFile}
                >
                  Upload & Ingest CSV
                </Button>
              </div>
            </form>
          </Card>
        )}

        {/* Mode 3: PDF Statement */}
        {activeMethod === "pdf" && (
          <Card>
            <CardHeader>
              <CardTitle>Upload PDF e-Statement</CardTitle>
              <CardDescription>
                Direct digital statements from net banking parsed in memory via pdfplumber.
              </CardDescription>
            </CardHeader>

            {/* Consent Notice if missing */}
            {!hasStatementConsent && (
              <div className="mx-6 mb-4 p-4 rounded-xl border border-amber-200 bg-amber-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-amber-900">
                <div className="flex items-start gap-2.5">
                  <ShieldAlert className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                  <div>
                    <span className="font-bold block">Explicit Statement Upload Consent Required (Promise 1)</span>
                    <span className="text-amber-800">
                      We require your permission before uploading statements. Processed in memory only.
                    </span>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => handleOpenConsentModal("statement_upload")}
                  className="bg-amber-600 hover:bg-amber-700 text-white shrink-0"
                >
                  Grant Statement Permission
                </Button>
              </div>
            )}

            <form onSubmit={handleProcessPdfUpload} className="space-y-4">
              <div
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${pdfFile
                  ? "border-emerald-400 bg-emerald-50/30"
                  : "border-slate-200 bg-slate-50/50 hover:border-slate-300"
                  }`}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    setPdfFile(e.dataTransfer.files[0]);
                  }
                }}
              >
                {pdfFile ? (
                  <div className="space-y-2">
                    <FileCheck2 className="w-10 h-10 text-emerald-600 mx-auto mb-2" />
                    <h4 className="text-sm font-bold text-slate-800">{pdfFile.name}</h4>
                    <p className="text-xs text-slate-500">
                      {(pdfFile.size / (1024 * 1024)).toFixed(2)} MB · Ready to parse
                    </p>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setPdfFile(null)}
                      className="text-slate-400 hover:text-rose-600"
                    >
                      <Trash2 className="w-4 h-4 mr-1" /> Remove
                    </Button>
                  </div>
                ) : (
                  <div>
                    <FileText className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                    <h4 className="text-sm font-bold text-slate-800">
                      Upload your digital PDF bank statement
                    </h4>
                    <p className="text-xs text-slate-500 mt-1 mb-4">
                      Note: Text-based PDFs only. Scanned image/photo PDFs will return a warning.
                    </p>
                    <input
                      type="file"
                      id="pdf-file-input"
                      className="hidden"
                      accept=".pdf"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setPdfFile(e.target.files[0]);
                        }
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => document.getElementById("pdf-file-input")?.click()}
                    >
                      Browse PDF
                    </Button>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <span className="text-xs text-slate-400">
                  Processed in memory · Raw PDF is never saved to disk
                </span>
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={isProcessing}
                  disabled={!hasStatementConsent || !pdfFile}
                >
                  Upload & Parse PDF
                </Button>
              </div>
            </form>
          </Card>
        )}

        {/* Mode 4: Manual Entry */}
        {activeMethod === "manual" && (
          <Card>
            <CardHeader>
              <CardTitle>Add Transaction Manually</CardTitle>
              <CardDescription>
                For cash expenses or offline purchases not captured via SMS or digital statements.
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleProcessManualTxn} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Payee / Merchant"
                  placeholder="e.g. Swiggy, Chai Point, Auto Rickshaw"
                  value={manualPayee}
                  onChange={(e) => setManualPayee(e.target.value)}
                  required
                />
                <Input
                  label="Amount (₹ Rupees)"
                  type="number"
                  step="0.01"
                  placeholder="150.00"
                  value={manualAmount}
                  onChange={(e) => setManualAmount(e.target.value)}
                  required
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select
                  label="Transaction Direction"
                  value={manualDirection}
                  onChange={(e) => setManualDirection(e.target.value)}
                  options={[
                    { value: "debit", label: "Debit (Expense)" },
                    { value: "credit", label: "Credit (Income)" },
                  ]}
                />
                <Input
                  label="Date"
                  type="date"
                  value={manualDate}
                  onChange={(e) => setManualDate(e.target.value)}
                  required
                />
              </div>
              <Input
                label="Description / Notes"
                placeholder="Optional notes about this transaction"
                value={manualDesc}
                onChange={(e) => setManualDesc(e.target.value)}
              />
              <div className="flex justify-end pt-3 border-t border-slate-100">
                <Button type="submit" variant="primary" isLoading={isProcessing}>
                  Save Transaction
                </Button>
              </div>
            </form>
          </Card>
        )}

        {/* Standard Google-style Security Consent Modal */}
        {consentModalType && (
          <ConsentModal
            isOpen={consentModalOpen}
            onClose={() => setConsentModalOpen(false)}
            onAllow={handleGrantConsent}
            consentType={consentModalType}
            isLoading={isGrantingConsent}
          />
        )}
      </div>
    </AppLayout>
  );
}
