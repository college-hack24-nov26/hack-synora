"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAuth } from "@/context/AuthContext";
import { ApiException } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Alert } from "@/components/ui/Alert";
import { Sparkles, ShieldCheck } from "lucide-react";

const registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  phone: z.string().optional().or(z.literal("")),
  password: z.string().min(8, "Password must be at least 8 characters long"),
  currency: z.string().default("INR"),
  timezone: z.string().default("Asia/Kolkata"),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      currency: "INR",
      timezone: "Asia/Kolkata",
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      await registerUser({
        name: data.name,
        email: data.email,
        phone: data.phone || undefined,
        password: data.password,
        currency: data.currency,
        timezone: data.timezone,
      });
    } catch (err: any) {
      if (err instanceof ApiException) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to register. Please check your information.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/40 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 items-center justify-center text-white shadow-lg shadow-blue-500/30 mb-4">
          <Sparkles className="w-6 h-6" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Create your account
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Automated Indian banking analytics & smart budgeting
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-xl shadow-slate-200/50 rounded-3xl border border-slate-100">
          {errorMsg && (
            <Alert
              type="error"
              title="Registration Notice"
              message={errorMsg}
              className="mb-6"
            />
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Full Name"
              type="text"
              placeholder="Arjun Sharma"
              error={errors.name?.message}
              {...register("name")}
            />

            <Input
              label="Email Address"
              type="email"
              placeholder="arjun@example.com"
              error={errors.email?.message}
              {...register("email")}
            />

            <Input
              label="Mobile Phone (Optional)"
              type="tel"
              placeholder="+919876543210"
              error={errors.phone?.message}
              {...register("phone")}
            />

            <Input
              label="Password (min 8 chars)"
              type="password"
              placeholder="••••••••"
              error={errors.password?.message}
              {...register("password")}
            />

            <div className="grid grid-cols-2 gap-3">
              <Select
                label="Base Currency"
                options={[
                  { value: "INR", label: "INR (₹) - Indian Rupee" },
                  { value: "USD", label: "USD ($) - US Dollar" },
                  { value: "EUR", label: "EUR (€) - Euro" },
                  { value: "GBP", label: "GBP (£) - British Pound" },
                ]}
                {...register("currency")}
              />

              <Select
                label="Timezone"
                options={[
                  { value: "Asia/Kolkata", label: "Asia/Kolkata (IST)" },
                  { value: "UTC", label: "UTC" },
                  { value: "America/New_York", label: "America/New_York (EST)" },
                  { value: "Europe/London", label: "Europe/London (GMT)" },
                  { value: "Asia/Singapore", label: "Asia/Singapore (SGT)" },
                ]}
                {...register("timezone")}
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-4"
              isLoading={isSubmitting}
            >
              Create Account
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-500">
              Already have an account?{" "}
              <Link
                href="/login"
                className="font-bold text-blue-600 hover:text-blue-700 ml-1"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>

        <div className="mt-6 flex flex-col items-center justify-center gap-1.5 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Bank-grade encryption & privacy</span>
          </div>
          <Link href="/privacy" className="text-blue-600 hover:text-blue-700 font-medium underline text-[11px]">
            Read our Privacy & Trust Promises
          </Link>
        </div>
      </div>
    </div>
  );
}
