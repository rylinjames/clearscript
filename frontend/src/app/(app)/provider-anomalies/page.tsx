"use client";

import { useState, useEffect, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import StatusBadge from "@/components/StatusBadge";
import MetricCard from "@/components/MetricCard";
import DataSourceBanner from "@/components/DataSourceBanner";
import { useToast } from "@/components/Toast";
import { Loader2, Users, AlertTriangle, DollarSign, Activity, RefreshCw, ExternalLink } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";

function fmt(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

interface ProviderMetric {
  npi: string;
  name: string;
  specialty: string;
  city: string;
  state: string;
  beneficiaries: number;
  total_charges: number;
  avg_cost_per_beneficiary: number;
  benchmark_avg_cost: number;
  avg_services_per_beneficiary: number;
  benchmark_avg_services: number;
  z_score: number;
  flag: string;
  severity: string;
  anomalies: string[];
  is_outlier: boolean;
}

export default function ProviderAnomalyPage() {
  const { toast } = useToast();
  usePageTitle("Provider Anomalies");
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const res = await fetch("/api/provider-anomalies/analysis");
      if (res.ok) {
        const json = await res.json();
        setData(json.provider_analysis);
      } else {
        setError("Failed to load provider analysis. Check if backend is running.");
      }
    } catch {
      setError("Cannot connect to server. Start the backend and refresh.");
    }
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Analyzing provider billing patterns...</p>
      </div>
    );
  }

  const summary = (data?.summary || {}) as Record<string, number>;
  const providers = (data?.providers || []) as ProviderMetric[];
  const outliers = (data?.outlier_details || []) as ProviderMetric[];
  const recommendations = (data?.recommendations || []) as string[];
  const cmsSource = (data?.cms_data_source || {}) as Record<string, unknown>;

  const displayProviders = showAll ? providers : outliers;

  const chartData = providers.map(p => ({
    name: p.name.split(" ").slice(-1)[0],
    cost: Math.round(p.avg_cost_per_beneficiary),
    benchmark: Math.round(p.benchmark_avg_cost),
    outlier: p.is_outlier,
  })).sort((a, b) => b.cost - a.cost);

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Users className="w-7 h-7 text-primary-600" />
          Provider Billing Anomaly Detection
        </h1>
        <p className="text-gray-500 mt-1">
          Detect outlier billing patterns using CMS Medicare utilization benchmarks
        </p>
      </div>

      <DataSourceBanner onRefresh={() => { setRefreshing(true); fetchData(); }} refreshing={refreshing} error={error} />

      {outliers.length > 0 && (
        <div className="bg-gradient-to-r from-red-600 to-amber-600 rounded-xl p-5 mb-6 text-white">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-7 h-7 flex-shrink-0" />
            <div>
              <p className="text-sm font-bold">{outliers.length} Provider Billing Anomalies Detected</p>
              <p className="text-sm text-white/90">
                Estimated excess charges: {fmt(summary.total_excess_charges || 0)}. Potential annual savings: {fmt(summary.annualized_savings_potential || 0)}.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => { setRefreshing(true); fetchData(); }} disabled={refreshing}
          className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <MetricCard icon={Users} label="Providers Analyzed" value={String(summary.providers_analyzed || 0)} color="blue" />
        <MetricCard icon={AlertTriangle} label="Outliers Detected" value={String(summary.outliers_detected || 0)} color="red" />
        <MetricCard icon={DollarSign} label="Excess Charges" value={fmt(summary.total_excess_charges || 0)} color="red" />
        <MetricCard icon={DollarSign} label="Savings Potential (40%)" value={fmt(summary.annualized_savings_potential || 0)} color="green" />
      </div>

      {/* Cost per Beneficiary Chart */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">Cost per Beneficiary vs Specialty Benchmark</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => fmt(v)} />
            <Tooltip formatter={(value) => [fmt(Number(value)), ""]} />
            <Bar dataKey="cost" radius={[4, 4, 0, 0]} name="Actual Cost/Bene">
              {chartData.map((entry, i) => (
                <rect key={i} fill={entry.outlier ? "#ef4444" : "#3b82f6"} />
              ))}
            </Bar>
            <Bar dataKey="benchmark" fill="#94a3b8" radius={[4, 4, 0, 0]} name="Benchmark" opacity={0.4} />
          </BarChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-3 justify-center">
          <span className="flex items-center gap-1 text-xs text-gray-500"><span className="w-3 h-3 rounded bg-red-500" /> Outlier</span>
          <span className="flex items-center gap-1 text-xs text-gray-500"><span className="w-3 h-3 rounded bg-blue-500" /> Normal</span>
          <span className="flex items-center gap-1 text-xs text-gray-500"><span className="w-3 h-3 rounded bg-gray-400" /> Benchmark</span>
        </div>
      </div>

      {/* Toggle */}
      <div className="flex gap-2 mb-4">
        <button onClick={() => setShowAll(false)}
          className={`px-4 py-2 text-sm font-medium rounded-lg border ${!showAll ? "bg-primary-600 text-white border-primary-600" : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"}`}>
          Outliers Only ({outliers.length})
        </button>
        <button onClick={() => setShowAll(true)}
          className={`px-4 py-2 text-sm font-medium rounded-lg border ${showAll ? "bg-primary-600 text-white border-primary-600" : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"}`}>
          All Providers ({providers.length})
        </button>
      </div>

      {/* Providers Table */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Provider</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Specialty</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Cost/Bene</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Benchmark</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Z-Score</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Anomalies</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {displayProviders.map((p, i) => (
              <tr key={i} className={`hover:bg-gray-50 ${p.is_outlier ? "bg-red-50/50" : ""}`}>
                <td className="px-6 py-4">
                  <p className="text-sm font-medium text-gray-900">{p.name}</p>
                  <p className="text-xs text-gray-500">{p.city}, {p.state} | NPI: {p.npi}</p>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">{p.specialty}</td>
                <td className="px-6 py-4 text-sm text-right font-semibold">{fmt(p.avg_cost_per_beneficiary)}</td>
                <td className="px-6 py-4 text-sm text-right text-gray-500">{fmt(p.benchmark_avg_cost)}</td>
                <td className="px-6 py-4 text-right">
                  <span className={`text-sm font-bold ${p.z_score > 2 ? "text-red-600" : p.z_score > 1 ? "text-amber-600" : "text-gray-600"}`}>
                    {p.z_score > 0 ? "+" : ""}{p.z_score.toFixed(1)}σ
                  </span>
                </td>
                <td className="px-6 py-4">
                  <StatusBadge
                    status={p.severity === "critical" ? "critical" : p.severity === "warning" ? "warning" : "success"}
                    label={p.severity === "critical" ? "Critical" : p.severity === "warning" ? "Warning" : "Normal"}
                  />
                </td>
                <td className="px-6 py-4">
                  {p.anomalies.length > 0 ? (
                    <ul className="text-xs text-red-700 space-y-0.5">
                      {p.anomalies.map((a, ai) => <li key={ai}>{a}</li>)}
                    </ul>
                  ) : (
                    <span className="text-xs text-gray-400">None</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* CMS Data Source */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-6">
        <h3 className="text-sm font-semibold text-blue-900 mb-2 flex items-center gap-2">
          <Activity className="w-4 h-4" /> Data Source: CMS Medicare Provider Utilization
        </h3>
        <p className="text-sm text-blue-800 mb-2">{cmsSource.description as string}</p>
        <p className="text-xs text-blue-600">
          <a href={cmsSource.url as string} target="_blank" rel="noopener noreferrer" className="underline flex items-center gap-1">
            {cmsSource.url as string} <ExternalLink className="w-3 h-3" />
          </a>
        </p>
        <p className="text-xs text-blue-700 mt-2">
          API Status: {cmsSource.cms_api_available ? "Available" : "Unavailable (using benchmark data)"}
        </p>
      </div>

      {/* Recommendations */}
      <div className="bg-primary-600 rounded-xl p-6 text-white">
        <h3 className="text-sm font-semibold uppercase tracking-wider mb-3">Recommendations</h3>
        <ul className="space-y-2">
          {recommendations.map((r, i) => (
            <li key={i} className="text-sm text-blue-100 flex items-start gap-2">
              <span className="text-emerald-400 mt-0.5">&#10003;</span> {r}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
