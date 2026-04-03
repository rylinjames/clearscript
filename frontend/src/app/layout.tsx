import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { ToastProvider } from "@/components/Toast";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "ClearScript — PBM Audit, Simplified",
  description:
    "AI-powered PBM contract analysis, disclosure auditing, and compliance tracking for self-insured employers.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={inter.variable}>
      <body className="bg-[#fafafa] text-gray-900 antialiased font-sans">
        <ClerkProvider>
          <ToastProvider>
            {children}
          </ToastProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
