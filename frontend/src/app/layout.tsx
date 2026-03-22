import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "ClearScript — PBM Disclosure Audit Engine",
  description:
    "Enterprise PBM contract audit, disclosure analysis, and compliance tracking.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-gray-50 text-gray-900 antialiased">
        <Sidebar />
        <main className="ml-64 min-h-screen">
          <div className="max-w-7xl mx-auto px-8 py-8">{children}</div>
        </main>
      </body>
    </html>
  );
}
