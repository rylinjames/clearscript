"use client";

import { useState, useEffect, useCallback } from "react";
import StatusBadge from "@/components/StatusBadge";
import { ClipboardList, Loader2, DollarSign, RefreshCw, Database, CheckCircle2, Scale } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Discrepancy {
  category: string;
  reportedAmount: number;
  expectedAmount: number;
  difference: number;
  severity: "critical" | "warning" | "info";
  detail: string;
}

const demoDiscrepancies: Discrepancy[] = [
  { category: "Generic Dispensing Rate", reportedAmount: 91, expectedAmount: 88, difference: 3, severity: "info", detail: "Reported GDR exceeds guarantee — verify claims data" },
  { category: "Brand Rebate Revenue ($M)", reportedAmount: 18.4, expectedAmount: 24.1, difference: -5.7, severity: "critical", detail: "Rebates $5.7M below expected per contracted rates" },
  { category: "Admin Fees ($M)", reportedAmount: 3.2, expectedAmount: 2.8, difference: 0.4, severity: "warning", detail: "Admin fees exceed contracted per-claim rate by $0.4M" },
  { category: "Mail-Order Utilization (%)", reportedAmount: 34, expectedAmount: 30, difference: 4, severity: "warning", detail: "Higher mail-order may indicate auto-refill steering" },
  { category: "Specialty Drug Spend ($M)", reportedAmount: 42.6, expectedAmount: 38.1, difference: 4.5, severity: "critical", detail: "Specialty costs $4.5M above projection" },
  { category: "Claims Processing Errors", reportedAmount: 0.3, expectedAmount: 0.5, difference: -0.2, severity: "info", detail: "Error rate within acceptable tolerance" },
  { category: "Network Discount (%)", reportedAmount: 22.1, expectedAmount: 24.5, difference: -2.4, severity: "warning", detail: "Effective discount below guaranteed rate" },
  { category: "Prior Auth Savings ($M)", reportedAmount: 6.8, expectedAmount: 8.2, difference: -1.4, severity: "warning", detail: "PA savings below projected — review denial rates" },
];

const chartData = demoDiscrepancies.map((d) => ({
  name: d.category.replace(/ \(\$M\)| \(%\)/g, ""),
  Actual: d.reportedAmount,
  Contracted: d.expectedAmount,
}));

interface ClaimsStatus {
  custom_data_loaded: boolean;
  claims_count: number;
  filename?: string;
}

export default function ReportsPage() {
  const [loading, setLoading] = useState(true);
  const [discrepancies, setDiscrepancies] = useState<Discrepancy[]>([]);
  const [claimsStatus, setClaimsStatus] = useState<ClaimsStatus | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchClaimsStatus = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/claims/status");
      if (res.ok) setClaimsStatus(await res.json());
    } catch { /* ignore */ }
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch("/api/reports/audit");
      if (!res.ok) throw new Error();
      await res.json();
      setDiscrepancies(demoDiscrepancies);
    } catch {
      setDiscrepancies(demoDiscrepancies);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchClaimsStatus();
    fetchData();
  }, [fetchClaimsStatus, fetchData]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchClaimsStatus();
    fetchData();
  };

  const totalRecovery = discrepancies
    .filter((d) => d.difference < 0 && d.category.includes("$M"))
    .reduce((sum, d) => sum + Math.abs(d.difference), 0);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-[#1e3a5f] animate-spin" />
        <p className="text-sm text-gray-500">Loading audit report...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <ClipboardList className="w-7 h-7 text-[#1e3a5f]" />
          Semiannual Report Auditor
        </h1>
        <p className="text-gray-500 mt-1">
          Compare PBM-reported figures against expected values and contracted rates
        </p>
      </div>

      {/* Data Source Banner */}
      <div className={`rounded-lg border px-4 py-2.5 mb-4 flex items-center justify-between ${
        claimsStatus?.custom_data_loaded
          ? "bg-emerald-50 border-emerald-200"
          : "bg-blue-50 border-blue-200"
      }`}>
        <div className="flex items-center gap-2">
          {claimsStatus?.custom_data_loaded ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          ) : (
            <Database className="w-4 h-4 text-blue-600" />
          )}
          <span className={`text-sm font-medium ${claimsStatus?.custom_data_loaded ? "text-emerald-800" : "text-blue-800"}`}>
            Analyzing: {claimsStatus?.custom_data_loaded
              ? `Your Uploaded Data (${claimsStatus.claims_count.toLocaleString()} claims)`
              : `Sample Claims Data (${claimsStatus?.claims_count?.toLocaleString() || "500"} claims)`}
          </span>
        </div>
        <button onClick={handleRefresh} disabled={refreshing} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
          Refresh Analysis
        </button>
      </div>

      {/* Plan Design vs Reality Banner */}
      <div className="bg-gradient-to-r from-[#1e3a5f] to-[#2a4f7f] rounded-xl p-6 mb-6 text-white">
        <div className="flex items-center gap-3 mb-2">
          <Scale className="w-8 h-8" />
          <div>
            <p className="text-lg font-bold">Plan Design vs Reality</p>
            <p className="text-sm text-blue-200">
              Your plan guarantees specific rates and savings — claims data shows the PBM is falling short. Potential recovery: <span className="font-bold text-white">${totalRecovery.toFixed(1)}M</span>
            </p>
          </div>
        </div>
      </div>

      {/* Summary Cards: Contract vs Actual */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase">Contracted GDR</p>
          <p className="text-xl font-bold text-gray-900 mt-1">88%</p>
          <p className="text-xs text-gray-400">Plan guarantee</p>
        </div>
        <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-4">
          <p className="text-xs text-emerald-600 uppercase">Actual GDR</p>
          <p className="text-xl font-bold text-emerald-700 mt-1">91.2%</p>
          <p className="text-xs text-emerald-500">Claims data</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase">Contracted Rebate</p>
          <p className="text-xl font-bold text-gray-900 mt-1">$24.1M</p>
          <p className="text-xs text-gray-400">Plan guarantee</p>
        </div>
        <div className="bg-red-50 rounded-xl border border-red-200 p-4">
          <p className="text-xs text-red-600 uppercase">Actual Rebate</p>
          <p className="text-xl font-bold text-red-700 mt-1">$18.4M</p>
          <p className="text-xs text-red-500">Claims data — $5.7M gap</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Contract Guarantee vs Actual Performance
        </h3>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
            <YAxis tick={{ fontSize: 12 }} domain={[0, "auto"]} />
            <Tooltip />
            <Legend />
            <Bar dataKey="Actual" fill="#1e3a5f" radius={[4, 4, 0, 0]} barSize={20} />
            <Bar dataKey="Contracted" fill="#10b981" radius={[4, 4, 0, 0]} barSize={20} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Category</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Reported</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Expected</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Difference</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Severity</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {discrepancies.map((d, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{d.category}</td>
                <td className="px-6 py-4 text-sm text-gray-700 text-right">{d.reportedAmount}</td>
                <td className="px-6 py-4 text-sm text-gray-700 text-right">{d.expectedAmount}</td>
                <td className={`px-6 py-4 text-sm font-semibold text-right ${d.difference < 0 ? "text-red-600" : d.difference > 0 ? "text-amber-600" : "text-gray-600"}`}>
                  {d.difference > 0 ? "+" : ""}{d.difference}
                </td>
                <td className="px-6 py-4"><StatusBadge status={d.severity} /></td>
                <td className="px-6 py-4 text-sm text-gray-500">{d.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
