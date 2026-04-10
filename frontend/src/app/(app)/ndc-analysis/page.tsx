"use client";

import { useState, useEffect, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import StatusBadge from "@/components/StatusBadge";
import MetricCard from "@/components/MetricCard";
import ScoreCircle from "@/components/ScoreCircle";
import { useToast } from "@/components/Toast";
import ExportButton from "@/components/ExportButton";
import { Loader2, AlertTriangle, DollarSign, Activity, MapPin, ArrowRight, RefreshCw, Layers } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

function fmt(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

interface JCodeCrosswalk {
  jcode: string;
  description: string;
  therapy_class: string;
  ndc_count: number;
  drugs: string[];
  max_rebate_pct: number;
  claims_count: number;
  claims_without_ndc: number;
  spend: number;
  potential_annual_rebate_recovery: number;
}

interface FailureChainStep {
  party: string;
  role: string;
  issue: string;
  fix: string;
}

export default function NdcAnalysisPage() {
  const { toast } = useToast();
  usePageTitle("NDC vs J-Code");
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const res = await fetch("/api/ndc-analysis/analysis");
      if (res.ok) {
        const json = await res.json();
        setData(json.ndc_analysis);
      } else {
        setError("Failed to load NDC analysis. Check if backend is running.");
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
        <p className="text-sm text-gray-500">Analyzing NDC vs J-code billing gap...</p>
      </div>
    );
  }

  const summary = (data?.summary || {}) as Record<string, number>;
  const failureChain = (data?.failure_chain || []) as FailureChainStep[];
  const crosswalk = (data?.jcode_crosswalk || []) as JCodeCrosswalk[];
  const recommendations = (data?.recommendations || []) as string[];
  const stateBenchmarks = (data?.state_benchmarks || {}) as Record<string, Record<string, unknown>>;

  const chartData = crosswalk.filter(j => j.spend > 0).map(j => ({
    name: j.jcode,
    Spend: Math.round(j.spend),
    Recovery: Math.round(j.potential_annual_rebate_recovery),
  }));

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Layers className="w-7 h-7 text-primary-600" />
          NDC vs J-Code Rebate Gap Analysis
        </h1>
        <p className="text-gray-500 mt-1">
          Detect claims where J-code billing masks rebate-eligible NDCs — based on Segal consulting intel
        </p>
      </div>


      {/* Risk Banner */}
      <div className="bg-gradient-to-r from-red-600 to-amber-600 rounded-xl p-5 mb-6 text-white">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-7 h-7 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold">NDC Billing Gap Detected</p>
            <p className="text-sm text-white/90">
              {summary.pct_spend_in_jcode_zone || 0}% of total Rx spend is in the J-code zone. Only {((summary.ndc_capture_rate || 0) * 100).toFixed(0)}% of physician-administered claims have proper NDC crosswalk. Alabama benchmark: 98%.
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <ScoreCircle score={summary.risk_score as number || 0} label="NDC Gap Risk" size="lg" />
        <div className="ml-auto flex items-center gap-2">
          <ExportButton
            data={crosswalk.map(j => ({ "J-Code": j.jcode, Description: j.description, "Therapy Class": j.therapy_class, "NDC Count": j.ndc_count, Drugs: j.drugs.join("; "), "Max Rebate %": (j.max_rebate_pct * 100).toFixed(0) + "%", "Claims": j.claims_count, "Claims Without NDC": j.claims_without_ndc, Spend: j.spend, "Potential Recovery": j.potential_annual_rebate_recovery })) as unknown as Record<string, unknown>[]}
            filename="ndc-jcode-crosswalk"
            label="Export CSV"
          />
          <button onClick={() => { setRefreshing(true); fetchData(); }} disabled={refreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <MetricCard icon={Activity} label="Physician-Admin Claims" value={String(summary.physician_admin_claims || 0)} color="blue" />
        <MetricCard icon={DollarSign} label="Spend Without NDC" value={fmt(summary.spend_without_ndc || 0)} color="red" />
        <MetricCard icon={DollarSign} label="Current Rebate (5% floor)" value={fmt(summary.current_rebate_at_5pct_floor || 0)} color="amber" />
        <MetricCard icon={DollarSign} label="Potential Rebate (with NDC)" value={fmt(summary.potential_rebate_with_ndc || 0)} trend={fmt(summary.annual_rebate_gap || 0) + "/yr recoverable"} trendUp={true} color="green" />
      </div>

      {/* Failure Chain */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">NDC Billing Failure Chain</h3>
        <div className="flex items-stretch gap-2">
          {failureChain.map((step, i) => (
            <div key={i} className="flex items-center gap-2 flex-1">
              <div className={`rounded-lg border p-4 flex-1 ${i === 0 ? "border-red-200 bg-red-50" : i === 1 ? "border-amber-200 bg-amber-50" : "border-blue-200 bg-blue-50"}`}>
                <p className="text-xs font-bold text-gray-900 mb-1">{step.party}</p>
                <p className="text-xs text-gray-500 mb-2">{step.role}</p>
                <p className="text-xs text-red-700 mb-2">{step.issue}</p>
                <p className="text-xs text-emerald-700 font-medium">{step.fix}</p>
              </div>
              {i < failureChain.length - 1 && <ArrowRight className="w-5 h-5 text-gray-400 flex-shrink-0" />}
            </div>
          ))}
        </div>
      </div>

      {/* J-Code Crosswalk Chart */}
      {chartData.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">J-Code Spend vs Recoverable Rebates</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => fmt(v)} />
              <Tooltip formatter={(value) => [fmt(Number(value)), ""]} />
              <Bar dataKey="Spend" fill="#ef4444" radius={[4, 4, 0, 0]} name="Current Spend" />
              <Bar dataKey="Recovery" fill="#10b981" radius={[4, 4, 0, 0]} name="Potential Recovery" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* J-Code Crosswalk Table */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">J-Code to NDC Crosswalk Details</h3>
        </div>
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">J-Code</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Description</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">NDCs</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Max Rebate</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Missing NDC</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Annual Recovery</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {crosswalk.map((j, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-mono font-bold text-primary-600">{j.jcode}</td>
                <td className="px-6 py-4 text-sm text-gray-700">{j.description}</td>
                <td className="px-6 py-4">
                  <div className="flex flex-col gap-0.5">
                    {j.drugs.map((d, di) => <span key={di} className="text-xs text-gray-600">{d}</span>)}
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-right font-semibold text-emerald-700">{(j.max_rebate_pct * 100).toFixed(0)}%</td>
                <td className="px-6 py-4 text-sm text-right">
                  <StatusBadge status={j.claims_without_ndc > 0 ? "critical" : "success"} label={`${j.claims_without_ndc}/${j.claims_count}`} />
                </td>
                <td className="px-6 py-4 text-sm text-right font-semibold text-emerald-700">{fmt(j.potential_annual_rebate_recovery)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* State Benchmarks Table */}
      {Object.keys(stateBenchmarks).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider flex items-center gap-2">
              <MapPin className="w-4 h-4" /> State NDC Compliance Benchmarks
            </h3>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">State</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">NDC Capture Rate</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Rebate Passthrough Rate</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Enforcer</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {Object.entries(stateBenchmarks).map(([state, bm]) => {
                const b = bm as Record<string, unknown>;
                const captureRate = (b.ndc_capture_rate as number || 0) * 100;
                const passthroughRate = (b.rebate_passthrough_rate as number || 0) * 100;
                return (
                  <tr key={state} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-sm font-medium text-gray-900">{state}</td>
                    <td className="px-6 py-3 text-sm text-right">
                      <span className={`font-semibold ${captureRate >= 90 ? "text-emerald-700" : captureRate >= 60 ? "text-amber-700" : "text-red-700"}`}>
                        {captureRate.toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-6 py-3 text-sm text-right">
                      <span className={`font-semibold ${passthroughRate >= 90 ? "text-emerald-700" : passthroughRate >= 60 ? "text-amber-700" : "text-red-700"}`}>
                        {passthroughRate > 0 ? `${passthroughRate.toFixed(0)}%` : "--"}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-sm text-gray-600">{(b.enforcer as string) || "--"}</td>
                    <td className="px-6 py-3 text-sm text-gray-500">{(b.notes as string) || ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

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
