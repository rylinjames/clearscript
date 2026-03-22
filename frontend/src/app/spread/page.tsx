"use client";

import { useState, useEffect } from "react";
import StatusBadge from "@/components/StatusBadge";
import MetricCard from "@/components/MetricCard";
import { TrendingUp, Loader2, DollarSign, ShoppingCart, Building2, Pill } from "lucide-react";
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

const demoChannels = {
  retail: { totalClaims: 142000, totalSpread: 1840000, avgSpreadPerClaim: 12.96 },
  mailOrder: { totalClaims: 48000, totalSpread: 2160000, avgSpreadPerClaim: 45.0 },
  specialty: { totalClaims: 8200, totalSpread: 3400000, avgSpreadPerClaim: 414.63 },
};

const demoDrugs: SpreadDrug[] = [
  { drug: "Atorvastatin 40mg", channel: "Retail", planPaid: 28.50, pharmacyReimbursed: 8.20, spread: 20.30, spreadPct: 71.2 },
  { drug: "Lisinopril 20mg", channel: "Retail", planPaid: 22.00, pharmacyReimbursed: 4.10, spread: 17.90, spreadPct: 81.4 },
  { drug: "Metformin 1000mg", channel: "Retail", planPaid: 18.75, pharmacyReimbursed: 3.50, spread: 15.25, spreadPct: 81.3 },
  { drug: "Humira (pen)", channel: "Specialty", planPaid: 6800.00, pharmacyReimbursed: 5200.00, spread: 1600.00, spreadPct: 23.5 },
  { drug: "Ozempic 1mg", channel: "Mail-Order", planPaid: 892.00, pharmacyReimbursed: 680.00, spread: 212.00, spreadPct: 23.8 },
  { drug: "Eliquis 5mg", channel: "Mail-Order", planPaid: 520.00, pharmacyReimbursed: 380.00, spread: 140.00, spreadPct: 26.9 },
  { drug: "Stelara 90mg", channel: "Specialty", planPaid: 13200.00, pharmacyReimbursed: 11400.00, spread: 1800.00, spreadPct: 13.6 },
  { drug: "Amlodipine 10mg", channel: "Retail", planPaid: 15.00, pharmacyReimbursed: 2.80, spread: 12.20, spreadPct: 81.3 },
  { drug: "Jardiance 25mg", channel: "Mail-Order", planPaid: 540.00, pharmacyReimbursed: 410.00, spread: 130.00, spreadPct: 24.1 },
  { drug: "Dupixent 300mg", channel: "Specialty", planPaid: 3800.00, pharmacyReimbursed: 2900.00, spread: 900.00, spreadPct: 23.7 },
];

const chartData = demoDrugs.slice(0, 8).map((d) => ({
  name: d.drug.split(" ")[0],
  Spread: d.spread,
}));

function formatCurrency(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(2)}`;
}

export default function SpreadPage() {
  const [loading, setLoading] = useState(true);
  const [drugs, setDrugs] = useState<SpreadDrug[]>([]);
  const [channels, setChannels] = useState(demoChannels);

  useEffect(() => {
    const fetchData = async () => {
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
        } else {
          setDrugs(demoDrugs);
        }
        if (sa?.by_channel) {
          const ch = sa.by_channel;
          setChannels({
            retail: { totalClaims: ch.retail?.claim_count || 0, totalSpread: ch.retail?.total_spread || 0, avgSpreadPerClaim: ch.retail?.avg_spread || 0 },
            mailOrder: { totalClaims: ch.mail?.claim_count || 0, totalSpread: ch.mail?.total_spread || 0, avgSpreadPerClaim: ch.mail?.avg_spread || 0 },
            specialty: { totalClaims: ch.specialty?.claim_count || 0, totalSpread: ch.specialty?.total_spread || 0, avgSpreadPerClaim: ch.specialty?.avg_spread || 0 },
          });
        } else {
          setChannels(demoChannels);
        }
      } catch {
        setDrugs(demoDrugs);
        setChannels(demoChannels);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const totalSpread = channels.retail.totalSpread + channels.mailOrder.totalSpread + channels.specialty.totalSpread;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-[#1e3a5f] animate-spin" />
        <p className="text-sm text-gray-500">Loading spread analysis...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <TrendingUp className="w-7 h-7 text-[#1e3a5f]" />
          Spread Pricing Detection
        </h1>
        <p className="text-gray-500 mt-1">
          Identify the difference between what plans pay and what pharmacies receive
        </p>
      </div>

      <div className="bg-gradient-to-r from-[#1e3a5f] to-[#2a4f7f] rounded-xl p-6 mb-6 text-white">
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

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
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

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
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
