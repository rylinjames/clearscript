"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  FileText,
  Search,
  ClipboardList,
  DollarSign,
  TrendingUp,
  Mail,
  MapPin,
  Pill,
  BarChart3,
  CalendarClock,
  ShieldCheck,
  Database,
  CheckCircle2,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/claims", label: "Upload Claims", icon: Upload },
  { href: "/contracts", label: "Contract Intake", icon: FileText },
  { href: "/disclosure", label: "Disclosure Analyzer", icon: Search },
  { href: "/reports", label: "Report Auditor", icon: ClipboardList },
  { href: "/rebates", label: "Rebate Tracker", icon: DollarSign },
  { href: "/spread", label: "Spread Pricing", icon: TrendingUp },
  { href: "/audit", label: "Audit Generator", icon: Mail },
  { href: "/network", label: "Network Adequacy", icon: MapPin },
  { href: "/formulary", label: "Formulary Detector", icon: Pill },
  { href: "/benchmarks", label: "Benchmarks", icon: BarChart3 },
  { href: "/compliance", label: "Compliance Tracker", icon: CalendarClock },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [dataSource, setDataSource] = useState<{ custom_data_loaded: boolean; claims_count: number } | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/claims/status");
        if (res.ok) setDataSource(await res.json());
      } catch { /* ignore */ }
    };
    fetchStatus();
  }, []);

  return (
    <aside className="w-64 bg-[#1e3a5f] text-white flex flex-col min-h-screen fixed left-0 top-0 z-40">
      <div className="p-6 border-b border-white/10">
        <Link href="/" className="flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-emerald-400" />
          <div>
            <h1 className="text-xl font-bold tracking-tight">ClearScript</h1>
            <p className="text-xs text-blue-200 mt-0.5">PBM Disclosure Audit Engine</p>
          </div>
        </Link>
      </div>

      <nav className="flex-1 py-4 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-6 py-3 text-sm transition-colors ${
                isActive
                  ? "bg-white/15 text-white border-r-3 border-emerald-400 font-semibold"
                  : "text-blue-100 hover:bg-white/8 hover:text-white"
              }`}
            >
              <Icon className="w-4.5 h-4.5 flex-shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Data Source Badge */}
      {dataSource && (
        <div className="px-4 py-3 border-t border-white/10">
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium ${
            dataSource.custom_data_loaded
              ? "bg-emerald-500/20 text-emerald-300"
              : "bg-blue-500/20 text-blue-300"
          }`}>
            {dataSource.custom_data_loaded ? (
              <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
            ) : (
              <Database className="w-3.5 h-3.5 flex-shrink-0" />
            )}
            <span>{dataSource.custom_data_loaded ? "Custom Data" : "Sample Data"}</span>
          </div>
        </div>
      )}

      <div className="p-4 border-t border-white/10 text-xs text-blue-200">
        <p>&copy; 2026 ClearScript</p>
        <p className="mt-0.5">v1.0.0 &middot; Enterprise</p>
      </div>
    </aside>
  );
}
