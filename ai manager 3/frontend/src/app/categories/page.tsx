"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { apiRequest } from "@/lib/api";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Alert } from "@/components/ui/Alert";
import {
  Tags,
  Plus,
  Trash2,
  Lock,
  Sparkles,
  ArrowDownLeft,
  ArrowUpRight,
  FolderPlus,
} from "lucide-react";

interface Category {
  id: string;
  user_id: string | null; // null = system default
  name: string;
  icon?: string;
  color?: string;
  is_income: boolean;
  created_at: string;
}

const categorySchema = z.object({
  name: z.string().min(1, "Category name is required").max(100),
  color: z.string().default("#3b82f6"),
  icon: z.string().default("tag"),
  is_income: z.boolean().default(false),
});

type CategoryFormData = z.infer<typeof categorySchema>;

const COLOR_PRESETS = [
  "#3b82f6", // Blue
  "#10b981", // Emerald
  "#f97316", // Orange
  "#8b5cf6", // Purple
  "#ec4899", // Pink
  "#ef4444", // Red
  "#eab308", // Yellow
  "#06b6d4", // Cyan
  "#64748b", // Slate
];

export default function CategoriesPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"all" | "system" | "custom">("all");
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Fetch Categories
  const {
    data: categories = [],
    isLoading,
    isError,
    error,
  } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => apiRequest<Category[]>("/categories"),
  });

  // Create Category Mutation
  const createMutation = useMutation({
    mutationFn: (data: CategoryFormData) =>
      apiRequest<Category>("/categories", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setIsAddOpen(false);
      reset();
    },
    onError: (err: any) => {
      setFormError(err.message || "Failed to create category");
    },
  });

  // Delete Category Mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiRequest(`/categories/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<CategoryFormData>({
    resolver: zodResolver(categorySchema),
    defaultValues: {
      color: "#3b82f6",
      icon: "tag",
      is_income: false,
    },
  });

  const selectedColor = watch("color");
  const isIncome = watch("is_income");

  const filteredCategories = categories.filter((cat) => {
    if (activeTab === "system") return cat.user_id === null;
    if (activeTab === "custom") return cat.user_id !== null;
    return true;
  });

  const onSubmit = (data: CategoryFormData) => {
    setFormError(null);
    createMutation.mutate(data);
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Transaction Categories
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Explore 20 Indian default categories or define your custom tags for AI categorization.
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
            Add Custom Category
          </Button>
        </div>

        {/* Tab Filters */}
        <div className="flex border-b border-slate-200 gap-6 text-sm font-semibold">
          <button
            onClick={() => setActiveTab("all")}
            className={`pb-3 border-b-2 transition-colors ${
              activeTab === "all"
                ? "border-blue-600 text-blue-600 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-900"
            }`}
          >
            All Categories ({categories.length})
          </button>
          <button
            onClick={() => setActiveTab("system")}
            className={`pb-3 border-b-2 transition-colors ${
              activeTab === "system"
                ? "border-blue-600 text-blue-600 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-900"
            }`}
          >
            System Default (Protected)
          </button>
          <button
            onClick={() => setActiveTab("custom")}
            className={`pb-3 border-b-2 transition-colors ${
              activeTab === "custom"
                ? "border-blue-600 text-blue-600 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-900"
            }`}
          >
            Custom User Categories
          </button>
        </div>

        {/* Error state */}
        {isError && (
          <Alert
            type="error"
            title="Failed to load categories"
            message={(error as any)?.message || "Could not retrieve category taxonomy."}
          />
        )}

        {/* Categories Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <Card key={i} className="animate-pulse h-24 bg-slate-100 border-0" />
            ))}
          </div>
        ) : filteredCategories.length === 0 ? (
          <Card className="text-center py-12 px-4 border-dashed border-2 border-slate-200">
            <FolderPlus className="w-10 h-10 text-slate-400 mx-auto mb-2" />
            <h4 className="font-bold text-slate-800">No custom categories found</h4>
            <p className="text-xs text-slate-500 mt-1 mb-4">
              Create custom categories to organize personal hobby spends, freelance contracts, or special funds.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setFormError(null);
                reset();
                setIsAddOpen(true);
              }}
            >
              <Plus className="w-4 h-4 mr-1.5" />
              Create Custom Category
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredCategories.map((cat) => {
              const isSystem = cat.user_id === null;
              return (
                <Card
                  key={cat.id}
                  className="flex items-center justify-between p-4 hover:border-slate-300 transition-all group"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-xs shadow-sm"
                      style={{ backgroundColor: cat.color || "#6b7280" }}
                    >
                      {cat.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm leading-snug">
                        {cat.name}
                      </h4>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        {cat.is_income ? (
                          <span className="text-[10px] font-semibold text-emerald-600 flex items-center gap-0.5">
                            <ArrowDownLeft className="w-3 h-3" /> Income
                          </span>
                        ) : (
                          <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-0.5">
                            <ArrowUpRight className="w-3 h-3" /> Expense
                          </span>
                        )}
                        <span className="text-slate-300">•</span>
                        {isSystem ? (
                          <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                            <Lock className="w-2.5 h-2.5 text-slate-400" /> Default
                          </span>
                        ) : (
                          <span className="text-[10px] text-blue-600 font-semibold">Custom</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {!isSystem && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-slate-400 hover:text-rose-600 hover:bg-rose-50 p-2"
                      title="Delete category"
                      onClick={() => deleteMutation.mutate(cat.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </Card>
              );
            })}
          </div>
        )}

        {/* Modal: Add Custom Category */}
        <Modal
          isOpen={isAddOpen}
          onClose={() => setIsAddOpen(false)}
          title="Create Custom Category"
          description="Teach the classifier your personal category preference."
        >
          {formError && (
            <Alert type="error" title="Creation Error" message={formError} className="mb-4" />
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Category Name"
              placeholder="e.g. Badminton Club, Side Hustle"
              error={errors.name?.message}
              {...register("name")}
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 tracking-wide uppercase mb-2">
                Color Badge
              </label>
              <div className="flex items-center gap-2 flex-wrap">
                {COLOR_PRESETS.map((color) => (
                  <button
                    key={color}
                    type="button"
                    onClick={() => setValue("color", color)}
                    className={`w-7 h-7 rounded-full transition-transform ${
                      selectedColor === color
                        ? "scale-125 ring-2 ring-offset-2 ring-slate-800"
                        : "hover:scale-110"
                    }`}
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
            </div>

            <div className="pt-2">
              <label className="block text-xs font-semibold text-slate-700 tracking-wide uppercase mb-2">
                Type
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setValue("is_income", false)}
                  className={`py-2 px-3 rounded-xl border text-xs font-bold transition-all ${
                    !isIncome
                      ? "bg-slate-900 text-white border-slate-900"
                      : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  Expense / Debit
                </button>
                <button
                  type="button"
                  onClick={() => setValue("is_income", true)}
                  className={`py-2 px-3 rounded-xl border text-xs font-bold transition-all ${
                    isIncome
                      ? "bg-emerald-600 text-white border-emerald-600"
                      : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  Income / Credit
                </button>
              </div>
            </div>

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
                isLoading={createMutation.isPending}
              >
                Create Category
              </Button>
            </div>
          </form>
        </Modal>
      </div>
    </AppLayout>
  );
}

