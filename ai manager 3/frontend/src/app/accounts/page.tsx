"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { apiRequest, ApiException } from "@/lib/api";
import { formatCurrency, parseToMinorUnits } from "@/lib/formatters";
import { useAuth } from "@/context/AuthContext";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Alert } from "@/components/ui/Alert";
import {
  CreditCard,
  Plus,
  Pencil,
  Trash2,
  Wallet,
  Building,
  Coins,
  Loader2,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";

interface Account {
  id: string;
  user_id: string;
  name: string;
  type: "savings" | "current" | "credit_card" | "wallet" | "cash";
  last4?: string | null;
  opening_balance_minor: number;
  current_balance_minor?: number;
  created_at: string;
}

const accountSchema = z.object({
  name: z.string().min(1, "Account name is required").max(100),
  type: z.enum(["savings", "current", "credit_card", "wallet", "cash"]),
  last4: z
    .string()
    .optional()
    .refine((val) => !val || /^\d{4}$/.test(val), "Must be exactly 4 numeric digits"),
  opening_balance_rupees: z.string().default("0"),
});

type AccountFormData = z.infer<typeof accountSchema>;

export default function AccountsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [deletingAccount, setDeletingAccount] = useState<Account | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Fetch Accounts
  const {
    data: accounts = [],
    isLoading,
    isError,
    error,
  } = useQuery<Account[]>({
    queryKey: ["accounts"],
    queryFn: () => apiRequest<Account[]>("/accounts"),
  });

  // Create Account Mutation
  const createMutation = useMutation({
    mutationFn: (data: AccountFormData) => {
      const payload = {
        name: data.name,
        type: data.type,
        last4: data.last4 && data.last4.trim() ? data.last4.trim() : null,
        opening_balance_minor: parseToMinorUnits(data.opening_balance_rupees || "0"),
      };
      return apiRequest<Account>("/accounts", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setIsAddOpen(false);
      reset();
    },
    onError: (err: any) => {
      setFormError(err.message || "Failed to create account");
    },
  });

  // Update Account Mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AccountFormData> }) => {
      const payload: any = {};
      if (data.name) payload.name = data.name;
      if (data.type) payload.type = data.type;
      if (data.last4 !== undefined) {
        payload.last4 = data.last4 && data.last4.trim() ? data.last4.trim() : null;
      }
      if (data.opening_balance_rupees !== undefined) {
        payload.opening_balance_minor = parseToMinorUnits(data.opening_balance_rupees);
      }
      return apiRequest<Account>(`/accounts/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setEditingAccount(null);
    },
    onError: (err: any) => {
      setFormError(err.message || "Failed to update account");
    },
  });

  // Delete Account Mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/accounts/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setDeletingAccount(null);
    },
  });

  // Form handling
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AccountFormData>({
    resolver: zodResolver(accountSchema),
    defaultValues: {
      type: "savings",
      opening_balance_rupees: "0",
    },
  });

  const onSubmitCreate = async (data: AccountFormData) => {
    setFormError(null);
    setIsCreating(true);
    try {
      const payload = {
        name: data.name,
        type: data.type,
        last4: data.last4 && data.last4.trim() ? data.last4.trim() : null,
        opening_balance_minor: parseToMinorUnits(data.opening_balance_rupees || "0"),
      };
      await apiRequest<Account>("/accounts", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setIsAddOpen(false);
      reset();
    } catch (err: any) {
      setFormError(err.message || "Failed to create account");
    } finally {
      setIsCreating(false);
    }
  };

  const getAccountIcon = (type: string) => {
    switch (type) {
      case "savings":
      case "current":
        return <Building className="w-5 h-5 text-blue-600" />;
      case "credit_card":
        return <CreditCard className="w-5 h-5 text-purple-600" />;
      case "wallet":
        return <Wallet className="w-5 h-5 text-emerald-600" />;
      default:
        return <Coins className="w-5 h-5 text-amber-600" />;
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Financial Accounts
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Manage your bank accounts, credit cards, cash, and digital wallets.
            </p>
          </div>
          <Button
            variant="primary"
            size="md"
            onClick={() => {
              setFormError(null);
              reset();
              setIsAddOpen(true);
            }}
          >
            <Plus className="w-4 h-4 mr-1.5" />
            Add Account
          </Button>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse h-40 bg-slate-100 border-0" />
            ))}
          </div>
        )}

        {/* Error state */}
        {isError && (
          <Alert
            type="error"
            title="Unable to load accounts"
            message={(error as any)?.message || "Failed to fetch accounts from backend API."}
          />
        )}

        {/* Empty state */}
        {!isLoading && !isError && accounts.length === 0 && (
          <Card className="text-center py-16 px-4 border-dashed border-2 border-slate-200">
            <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4">
              <CreditCard className="w-7 h-7" />
            </div>
            <h3 className="text-lg font-bold text-slate-800">No accounts registered yet</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto mt-1 mb-6">
              Create an account like HDFC Salary, SBI Savings, or ICICI Credit Card to start categorizing statements and calculating balances.
            </p>
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                setFormError(null);
                reset();
                setIsAddOpen(true);
              }}
            >
              <Plus className="w-4 h-4 mr-1.5" />
              Add Your First Account
            </Button>
          </Card>
        )}

        {/* Accounts Grid */}
        {!isLoading && !isError && accounts.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {accounts.map((acc) => {
              const liveBalance = acc.current_balance_minor ?? acc.opening_balance_minor;
              return (
                <Card
                  key={acc.id}
                  className="flex flex-col justify-between hover:shadow-md transition-all group border-slate-200"
                >
                  <div>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center">
                          {getAccountIcon(acc.type)}
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-900 text-sm">{acc.name}</h4>
                          <span className="text-xs text-slate-400 font-mono">
                            {acc.last4 ? `•••• ${acc.last4}` : "No card/account digits"}
                          </span>
                        </div>
                      </div>
                      <Badge variant="default" className="capitalize text-[10px]">
                        {acc.type.replace("_", " ")}
                      </Badge>
                    </div>

                    <div className="mt-5 space-y-1.5">
                      <div className="flex items-baseline justify-between">
                        <span className="text-xs text-slate-500 font-medium">Current Balance</span>
                        <span className="text-lg font-black text-slate-900">
                          {formatCurrency(liveBalance, user?.currency)}
                        </span>
                      </div>
                      <div className="flex items-baseline justify-between text-[11px] text-slate-400">
                        <span>Opening balance</span>
                        <span>{formatCurrency(acc.opening_balance_minor, user?.currency)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-slate-500 hover:text-slate-800"
                      onClick={() => {
                        setFormError(null);
                        setEditingAccount(acc);
                      }}
                    >
                      <Pencil className="w-3.5 h-3.5 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-slate-500 hover:text-rose-600 hover:bg-rose-50"
                      onClick={() => setDeletingAccount(acc)}
                    >
                      <Trash2 className="w-3.5 h-3.5 mr-1" />
                      Delete
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* Modal: Add Account */}
        <Modal
          isOpen={isAddOpen}
          onClose={() => {
            setIsAddOpen(false);
            setFormError(null);
          }}
          title="Add New Account"
          description="Track balances with exact paise precision."
        >
          {formError && (
            <Alert type="error" title="Notice" message={formError} className="mb-4" />
          )}

          <form onSubmit={handleSubmit(onSubmitCreate)} className="space-y-4">
            <Input
              label="Account / Bank Name"
              placeholder="e.g. HDFC Salary, ICICI Coral Card"
              error={errors.name?.message}
              {...register("name")}
            />

            <Select
              label="Account Type"
              options={[
                { value: "savings", label: "Savings Account" },
                { value: "current", label: "Current / Business Account" },
                { value: "credit_card", label: "Credit Card" },
                { value: "wallet", label: "Digital Wallet (Paytm, etc.)" },
                { value: "cash", label: "Cash / Physical Vault" },
              ]}
              error={errors.type?.message}
              {...register("type")}
            />

            <Input
              label="Last 4 Digits (Optional)"
              placeholder="e.g. 4589"
              maxLength={4}
              error={errors.last4?.message}
              helperText="Helps match automated bank SMS and statements"
              {...register("last4")}
            />

            <Input
              label="Opening Balance (₹ Rupees)"
              type="number"
              step="0.01"
              placeholder="0.00"
              error={errors.opening_balance_rupees?.message}
              helperText="Stored safely in database as integer paise (minor units)"
              {...register("opening_balance_rupees")}
            />

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setIsAddOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                isLoading={isCreating}
              >
                Add Account
              </Button>
            </div>
          </form>
        </Modal>

        {/* Modal: Edit Account */}
        {editingAccount && (
          <Modal
            isOpen={!!editingAccount}
            onClose={() => setEditingAccount(null)}
            title={`Edit ${editingAccount.name}`}
            description="Update account details or opening balance."
          >
            {formError && (
              <Alert type="error" title="Update Error" message={formError} className="mb-4" />
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const form = e.target as HTMLFormElement;
                const name = (form.elements.namedItem("edit_name") as HTMLInputElement).value;
                const type = (form.elements.namedItem("edit_type") as HTMLSelectElement).value as any;
                const last4 = (form.elements.namedItem("edit_last4") as HTMLInputElement).value;
                const rupees = (form.elements.namedItem("edit_balance") as HTMLInputElement).value;

                updateMutation.mutate({
                  id: editingAccount.id,
                  data: {
                    name,
                    type,
                    last4,
                    opening_balance_rupees: rupees,
                  },
                });
              }}
              className="space-y-4"
            >
              <Input
                label="Account Name"
                name="edit_name"
                defaultValue={editingAccount.name}
                required
              />

              <Select
                label="Account Type"
                name="edit_type"
                defaultValue={editingAccount.type}
                options={[
                  { value: "savings", label: "Savings Account" },
                  { value: "current", label: "Current / Business Account" },
                  { value: "credit_card", label: "Credit Card" },
                  { value: "wallet", label: "Digital Wallet" },
                  { value: "cash", label: "Cash" },
                ]}
              />

              <Input
                label="Last 4 Digits"
                name="edit_last4"
                defaultValue={editingAccount.last4 || ""}
                maxLength={4}
              />

              <Input
                label="Opening Balance (₹ Rupees)"
                name="edit_balance"
                type="number"
                step="0.01"
                defaultValue={(editingAccount.opening_balance_minor / 100).toFixed(2)}
                required
              />

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setEditingAccount(null)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={updateMutation.isPending}
                >
                  Save Changes
                </Button>
              </div>
            </form>
          </Modal>
        )}

        {/* Modal: Delete Confirmation */}
        {deletingAccount && (
          <Modal
            isOpen={!!deletingAccount}
            onClose={() => setDeletingAccount(null)}
            title="Delete Account?"
            maxWidth="sm"
          >
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 bg-rose-50 border border-rose-100 rounded-xl text-rose-800 text-xs">
                <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
                <span>
                  Deleting <strong>{deletingAccount.name}</strong> will remove all its balance records. This action cannot be undone.
                </span>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <Button
                  variant="ghost"
                  onClick={() => setDeletingAccount(null)}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  isLoading={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(deletingAccount.id)}
                >
                  Confirm Delete
                </Button>
              </div>
            </div>
          </Modal>
        )}
      </div>
    </AppLayout>
  );
}

