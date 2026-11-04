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
import { Alert } from "@/components/ui/Alert";
import { Sparkles, ShieldCheck } from "lucide-react";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login } = useAuth();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const fillCredentials = (email: string, pass: string) => {
    setValue("email", email, { shouldValidate: true });
    setValue("password", pass, { shouldValidate: true });
  };

  const onSubmit = async (data: LoginFormData) => {
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      await login(data.email, data.password);
    } catch (err: any) {
      if (err instanceof ApiException) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to sign in. Please verify your credentials.");
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
          Welcome back
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Sign in to your AI Personal Finance Manager
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-xl shadow-slate-200/50 rounded-3xl border border-slate-100">
          {errorMsg && (
            <Alert
              type="error"
              title="Authentication Notice"
              message={errorMsg}
              className="mb-6"
            />
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <Input
              label="Email Address"
              type="email"
              placeholder="arjun@example.com"
              error={errors.email?.message}
              {...register("email")}
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              error={errors.password?.message}
              {...register("password")}
            />

            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                Protected session
              </span>
              <span className="text-slate-400">Encrypted in transit</span>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              isLoading={isSubmitting}
            >
              Sign In
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-500">
              Don&apos;t have an account yet?{" "}
              <Link
                href="/register"
                className="font-bold text-blue-600 hover:text-blue-700 ml-1"
              >
                Create one now
              </Link>
            </p>
          </div>

          {/* Quick Demo Logins Helper */}
          <div className="mt-6 pt-6 border-t border-dashed border-slate-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Quick Demo Logins
              </span>
              <span className="text-[10px] text-indigo-600 font-semibold bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-100">
                1-Click Autofill
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => fillCredentials("admin@demo.com", "AdminDemo@123!")}
                className="p-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 font-semibold text-left transition-colors flex flex-col"
              >
                <span>🏦 Bank Staff Admin</span>
                <span className="text-[10px] text-indigo-500 font-mono font-normal">admin@demo.com</span>
              </button>

              <button
                type="button"
                onClick={() => fillCredentials("student@demo.com", "Customer@123!")}
                className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold text-left transition-colors flex flex-col"
              >
                <span>🎓 Student</span>
                <span className="text-[10px] text-slate-400 font-mono font-normal">student@demo.com</span>
              </button>

              <button
                type="button"
                onClick={() => fillCredentials("professional@demo.com", "Customer@123!")}
                className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold text-left transition-colors flex flex-col"
              >
                <span>💼 Professional</span>
                <span className="text-[10px] text-slate-400 font-mono font-normal">professional@demo.com</span>
              </button>

              <button
                type="button"
                onClick={() => fillCredentials("business@demo.com", "Customer@123!")}
                className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold text-left transition-colors flex flex-col"
              >
                <span>🏪 Business</span>
                <span className="text-[10px] text-slate-400 font-mono font-normal">business@demo.com</span>
              </button>

              <button
                type="button"
                onClick={() => fillCredentials("freelancer@demo.com", "Customer@123!")}
                className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold text-left transition-colors flex flex-col"
              >
                <span>💻 Freelancer</span>
                <span className="text-[10px] text-slate-400 font-mono font-normal">freelancer@demo.com</span>
              </button>

              <button
                type="button"
                onClick={() => fillCredentials("family@demo.com", "Customer@123!")}
                className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold text-left transition-colors flex flex-col"
              >
                <span>🏡 Family Household</span>
                <span className="text-[10px] text-slate-400 font-mono font-normal">family@demo.com</span>
              </button>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-col items-center justify-center gap-1.5 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Encrypted at rest and in transit</span>
          </div>
          <Link href="/privacy" className="text-blue-600 hover:text-blue-700 font-medium underline text-[11px]">
            Read our Privacy & Trust Promises
          </Link>
        </div>
      </div>
    </div>
  );
}
