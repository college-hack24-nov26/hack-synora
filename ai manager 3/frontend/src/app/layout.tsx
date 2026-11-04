import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { QueryProvider } from "@/providers/QueryProvider";

export const metadata: Metadata = {
  title: "AI Personal Finance Manager",
  description: "Automated statement ingestion, AI categorization, and predictive spending analytics for Indian & global banking.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased bg-slate-50 text-slate-900">
        <QueryProvider>
          <AuthProvider>{children}</AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}

