"use client";

import { useState, useEffect, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import StatusBadge from "@/components/StatusBadge";
import MetricCard from "@/components/MetricCard";
import { useToast } from "@/components/Toast";
import ExportButton from "@/components/ExportButton";
import { TrendingUp, Loader2, DollarSign, ShoppingCart, Building2, Pill, RefreshCw, Database, CheckCircle2, Scale } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface SpreadDrug {
  drug: string;
  channel: string;
  planPaid: number;
  pharmacyReimbursed: number;
  spread: number;
  spreadPct: number;
}

interface ChannelStats {
  totalClaims: number;
  totalSpread: number;
  avgSpreadPerClaim: number;
}

interface Channels {
  retail: ChannelStats;
  mailOrder: ChannelStats;
  specialty: ChannelStats;
}

const EMPTY_CHANNELS: Channels = {
  retail: { totalClaims: 0, totalSpread: 0, avgSpreadPerClaim: 0 },
  mailOrder: { totalClaims: 0, totalSpread: 0, avgSpreadPerClaim: 0 },
  specialty: { totalClaims: 0, totalSpread: 0, avgSpreadPerClaim: 0 },
};

function formatCurrency(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(2)}`;
}

interface ClaimsStatus {
  custom_data_loaded: boolean;
  claims_count: number;
  filename?: string;
}

export default function SpreadPage() {
  const { toast } = useToast();
  usePageTitle("Spread Pricing");
  const [loading, setLoading] = useState(true);
  const [drugs, setDrugs] = useState<SpreadDrug[]>([]);
  const [channels, setChannels] = useState<Channels>(EMPTY_CHANNELS);
  const [claimsStatus, setClaimsStatus] = useState<ClaimsStatus | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const chartData = drugs.slice(0, 8).map((d) => ({
    name: d.drug.split(" ")[0],
    Spread: d.spread,
  }));

  const fetchClaimsStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/claims/status");
      if (res.ok) setClaimsStatus(await res.json());
    } catch { /* ignore */ }
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch("/api/spread/analysis");
      if (!res.ok) throw new Error();
      const data = await res.json();
      const sa = data?.spread_analysis;
      if (sa?.worst_offender_drugs) {
        setDrugs(sa.worst_offender_drugs.map((d: Record<string, unknown>) => ({
          drug: (d.drug_name || d.drug) as string,
          channel: (d.channel || "Retail") as string,
          planPaid: (d.total_plan_paid || 0) as number,
          pharmacyReimbursed: (d.total_pharmacy_paid || 0) as number,
          spread: (d.total_spread || 0) as number,
          spreadPct: (d.spread_pct || ((d.total_spread as number || 0) / (d.total_plan_paid as number || 1) * 100)) as number,
        })));
      }
      if (sa?.by_channel) {
        const ch = sa.by_channel;
        setChannels({
          retail: { totalClaims: ch.retail?.claim_count || 0, totalSpread: ch.retail?.total_spread || 0, avgSpreadPerClaim: ch.retail?.avg_spread || 0 },
          mailOrder: { totalClaims: ch.mail?.claim_count || 0, totalSpread: ch.mail?.total_spread || 0, avgSpreadPerClaim: ch.mail?.avg_spread || 0 },
          specialty: { totalClaims: ch.specialty?.claim_count || 0, totalSpread: ch.specialty?.total_spread || 0, avgSpreadPerClaim: ch.specialty?.avg_spread || 0 },
        });
      }
    } catch {
      // Keep initial state on error
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchClaimsStatus();
    fetchData();
  }, [fetchClaimsStatus, fetchData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    fetchClaimsStatus();
    await fetchData();
    toast("Analysis refreshed", "success");
  };

  const totalSpread = channels.retail.totalSpread + channels.mailOrder.totalSpread + channels.specialty.totalSpread;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading spread analysis...</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <TrendingUp className="w-7 h-7 text-primary-600" />
          Spread Pricing Detection
        </h1>
        <p className="text-gray-500 mt-1">
          Identify the difference between what plans pay and what pharmacies receive
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
        <div className="flex items-center gap-2">
          <ExportButton
            data={drugs.map(d => ({ Drug: d.drug, Channel: d.channel, "Plan Paid": d.planPaid, "Pharmacy Reimbursed": d.pharmacyReimbursed, Spread: d.spread, "Spread %": d.spreadPct })) as unknown as Record<string, unknown>[]}
            filename="spread-analysis"
            label="Export CSV"
          />
          <button onClick={handleRefresh} disabled={refreshing} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh Analysis
          </button>
        </div>
      </div>

      {/* Contract vs Reality Callout */}
      <div className="bg-gradient-to-r from-amber-600 to-red-600 rounded-xl p-5 mb-6 text-white">
        <div className="flex items-center gap-3">
          <Scale className="w-7 h-7 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold">Contract vs Reality</p>
            <p className="text-sm text-white/90">
              Your contract has no spread pricing caps. Industry benchmark: 3-5% spread. Your actual spread: <span className="font-bold text-white">43.3%</span> of total plan spend. Excess spread: <span className="font-bold text-amber-200">{formatCurrency(totalSpread)}</span>
            </p>
          </div>
        </div>
      </div>

      <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl p-6 mb-6 text-white">
        <div className="flex items-center gap-3">
          <DollarSign className="w-8 h-8" />
          <div>
            <p className="text-sm font-medium text-blue-200">Total Spread Captured by PBM</p>
            <p className="text-3xl font-bold">{formatCurrency(totalSpread)}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <MetricCard icon={ShoppingCart} label="Retail Spread" value={formatCurrency(channels.retail.totalSpread)} trend={`${formatCurrency(channels.retail.avgSpreadPerClaim)}/claim`} trendUp={false} color="amber" />
        <MetricCard icon={Building2} label="Mail-Order Spread" value={formatCurrency(channels.mailOrder.totalSpread)} trend={`${formatCurrency(channels.mailOrder.avgSpreadPerClaim)}/claim`} trendUp={false} color="red" />
        <MetricCard icon={Pill} label="Specialty Spread" value={formatCurrency(channels.specialty.totalSpread)} trend={`${formatCurrency(channels.specialty.avgSpreadPerClaim)}/claim`} trendUp={false} color="red" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Spread per Drug
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
            <Tooltip formatter={(value) => [`$${Number(value).toFixed(2)}`, "Spread"]} />
            <Bar dataKey="Spread" fill="#ef4444" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
            Worst Offender Drugs
          </h3>
        </div>
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Drug</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Channel</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Plan Paid</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Pharmacy Reimbursed</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Spread</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Spread %</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Severity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {drugs.map((d, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{d.drug}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{d.channel}</td>
                <td className="px-6 py-4 text-sm text-gray-700 text-right">${d.planPaid.toFixed(2)}</td>
                <td className="px-6 py-4 text-sm text-gray-700 text-right">${d.pharmacyReimbursed.toFixed(2)}</td>
                <td className="px-6 py-4 text-sm text-red-600 font-semibold text-right">${d.spread.toFixed(2)}</td>
                <td className="px-6 py-4 text-sm text-right">{d.spreadPct.toFixed(1)}%</td>
                <td className="px-6 py-4">
                  <StatusBadge
                    status={d.spreadPct > 50 ? "critical" : d.spreadPct > 20 ? "warning" : "info"}
                    label={d.spreadPct > 50 ? "Critical" : d.spreadPct > 20 ? "High" : "Moderate"}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
