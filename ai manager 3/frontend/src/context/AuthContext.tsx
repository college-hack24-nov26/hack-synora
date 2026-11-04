"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiRequest, setAuthToken, getAuthToken, ApiException } from "@/lib/api";

export interface User {
  id: string;
  email: string;
  name: string;
  currency: string;
  timezone: string;
  phone?: string;
  phone_verified?: boolean;
  email_verified?: boolean;
  preferred_otp_channel?: "email" | "sms" | "both";
  alert_preferences?: Record<string, boolean>;
  role?: "customer" | "admin";
  is_active?: boolean;
  is_demo?: boolean;
  segment?: string;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    name: string;
    phone?: string;
    currency?: string;
    timezone?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  const fetchCurrentUser = async () => {
    try {
      const userData = await apiRequest<User>("/auth/me");
      setUser(userData);
      return userData;
    } catch (err) {
      setUser(null);
      setAuthToken(null);
      return null;
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const existingToken = getAuthToken();
      if (existingToken) {
        await fetchCurrentUser();
      } else {
        // Try refresh token via cookie
        try {
          const res = await apiRequest<{ access_token: string }>("/auth/refresh", {
            method: "POST",
            skipAuthRefresh: true,
          });
          if (res?.access_token) {
            setAuthToken(res.access_token);
            await fetchCurrentUser();
          }
        } catch {
          // No active session
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await apiRequest<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (res?.access_token) {
      setAuthToken(res.access_token);
      const currentUser = await fetchCurrentUser();
      if (currentUser?.role === "admin") {
        router.push("/admin");
      } else {
        router.push("/dashboard");
      }
    }
  };

  const register = async (payload: {
    email: string;
    password: string;
    name: string;
    phone?: string;
    currency?: string;
    timezone?: string;
  }) => {
    await apiRequest<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    // Automatically log in after registration
    await login(payload.email, payload.password);
  };

  const logout = async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } catch (e) {
      // Continue client cleanup regardless
    } finally {
      setUser(null);
      setAuthToken(null);
      router.push("/login");
    }
  };

  const refreshUser = async () => {
    await fetchCurrentUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        isAdmin: user?.role === "admin",
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

