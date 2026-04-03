"use client";

import { useState, useEffect, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import StatusBadge from "@/components/StatusBadge";
import MetricCard from "@/components/MetricCard";
import DataSourceBanner from "@/components/DataSourceBanner";
import { useToast } from "@/components/Toast";
import { Loader2, ShieldCheck, AlertTriangle, CheckCircle2, Edit3, Trash2, RefreshCw, Clock, DollarSign, Award } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

function fmt(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

interface PARule {
  drug: string;
  drug_class: string;
  pa_type: string;
  approval_rate: number;
  avg_review_days: number;
  annual_pa_volume: number;
  admin_cost_per_pa: number;
  clinical_rationale: string;
  specialty: boolean;
  recommendation: string;
  rationale: string;
  annual_admin_waste: number;
  gold_card_eligible: boolean;
}

const REC_COLORS: Record<string, string> = {
  REMOVE: "#ef4444",
  MODIFY: "#f59e0b",
  KEEP: "#10b981",
  "N/A": "#94a3b8",
};

const REC_ICONS: Record<string, typeof Trash2> = {
  REMOVE: Trash2,
  MODIFY: Edit3,
  KEEP: CheckCircle2,
};

export default function PriorAuthPage() {
  const { toast } = useToast();
  usePageTitle("PA Value Detector");
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("ALL");

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const res = await fetch("/api/prior-auth/analysis");
      if (res.ok) {
        const json = await res.json();
        setData(json.pa_analysis);
      } else {
        setError("Failed to load PA analysis. Check if backend is running.");
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
        <p className="text-sm text-gray-500">Analyzing prior authorization value...</p>
      </div>
    );
  }

  const summary = (data?.summary || {}) as Record<string, number>;
  const rules = (data?.rules || []) as PARule[];
  const goldContext = (data?.gold_carding_context || {}) as Record<string, unknown>;
  const recommendations = (data?.recommendations || []) as string[];

  const paRules = rules.filter(r => r.pa_type !== "None");
  const filtered = filter === "ALL" ? paRules : paRules.filter(r => r.recommendation === filter);

  const chartData = paRules.map(r => ({
    name: r.drug.split(" ")[0],
    rate: Math.round(r.approval_rate * 100),
    rec: r.recommendation,
  }));

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <ShieldCheck className="w-7 h-7 text-primary-600" />
          Prior Authorization Value Detector
        </h1>
        <p className="text-gray-500 mt-1">
          Evaluate PA rules: Keep, Remove, or Modify — based on population-level effectiveness
        </p>
      </div>

      <DataSourceBanner onRefresh={() => { setRefreshing(true); fetchData(); }} refreshing={refreshing} error={error} />

      {/* Summary Banner */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl p-6 mb-6 text-white">
        <div className="grid grid-cols-4 gap-6">
          <div className="text-center">
            <p className="text-3xl font-bold text-red-300">{summary.remove || 0}</p>
            <p className="text-sm text-blue-200">Remove</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-amber-300">{summary.modify || 0}</p>
            <p className="text-sm text-blue-200">Modify</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-emerald-300">{summary.keep || 0}</p>
            <p className="text-sm text-blue-200">Keep</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-white">{fmt(summary.total_annual_admin_waste_removable || 0)}</p>
            <p className="text-sm text-blue-200">Recoverable Admin Cost</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1">
          <MetricCard icon={Clock} label="Avg Approval Rate" value={`${((summary.avg_approval_rate || 0) * 100).toFixed(0)}%`} color="blue" />
          <MetricCard icon={Award} label="Gold Card Eligible" value={`${summary.gold_card_eligible_providers || 0} drugs`} color="green" />
          <MetricCard icon={DollarSign} label="Admin Waste (Removable)" value={fmt(summary.total_annual_admin_waste_removable || 0)} color="red" />
        </div>
        <button onClick={() => { setRefreshing(true); fetchData(); }} disabled={refreshing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 self-start">
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {/* Approval Rate Chart */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">PA Approval Rates by Drug</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
            <Tooltip formatter={(value) => [`${value}%`, "Approval Rate"]} />
            <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={REC_COLORS[entry.rec] || "#94a3b8"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-3 justify-center">
          <span className="flex items-center gap-1 text-xs text-gray-500"><span className="w-3 h-3 rounded bg-red-500" /> Remove (&gt;90%)</span>
          <span className="flex items-center gap-1 text-xs text-gray-500"><span className="w-3 h-3 rounded bg-amber-500" /> Modify (80-90%)</span>
          <span className="flex items-center gap-1 text-xs text-gray-500"><span className="w-3 h-3 rounded bg-emerald-500" /> Keep (&lt;80%)</span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-4">
        {["ALL", "REMOVE", "MODIFY", "KEEP"].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${filter === f ? "bg-primary-600 text-white border-primary-600" : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"}`}>
            {f === "ALL" ? `All (${paRules.length})` : `${f} (${paRules.filter(r => r.recommendation === f).length})`}
          </button>
        ))}
      </div>

      {/* PA Rules Table */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Drug</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">PA Type</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Approval Rate</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Annual Volume</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Admin Waste</th>
              <th className="text-center px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Recommendation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map((r, i) => {
              const Icon = REC_ICONS[r.recommendation] || CheckCircle2;
              return (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <p className="text-sm font-medium text-gray-900">{r.drug}</p>
                    <p className="text-xs text-gray-500">{r.drug_class}</p>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{r.pa_type}</td>
                  <td className="px-6 py-4 text-right">
                    <span className={`text-sm font-bold ${r.approval_rate >= 0.9 ? "text-red-600" : r.approval_rate >= 0.8 ? "text-amber-600" : "text-emerald-600"}`}>
                      {(r.approval_rate * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700 text-right">{r.annual_pa_volume.toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm text-red-600 text-right font-medium">{fmt(r.annual_admin_waste)}</td>
                  <td className="px-6 py-4 text-center">
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold text-white" style={{ backgroundColor: REC_COLORS[r.recommendation] }}>
                      <Icon className="w-3.5 h-3.5" />
                      {r.recommendation}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Gold Carding Context */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-6">
        <h3 className="text-sm font-semibold text-amber-900 mb-3 flex items-center gap-2">
          <Award className="w-5 h-5" /> Gold Carding Context
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-amber-800">
          <div><span className="font-semibold">Highmark benchmark:</span> {goldContext.highmark_benchmark as string}</div>
          <div><span className="font-semibold">Texas reality:</span> {goldContext.texas_reality as string}</div>
          <div><span className="font-semibold">MUSC savings:</span> {goldContext.musc_savings as string}</div>
          <div><span className="font-semibold">CMS 2026 rule:</span> {goldContext.cms_2026_rule as string}</div>
          <div><span className="font-semibold">States with laws:</span> {(goldContext.states_with_laws as string[] || []).join(", ")}</div>
        </div>
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
