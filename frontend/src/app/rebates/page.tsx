"use client";

import { useState, useEffect } from "react";
import StatusBadge from "@/components/StatusBadge";
import { DollarSign, Loader2, AlertTriangle } from "lucide-react";

interface RebateDrug {
  drug: string;
  manufacturer: string;
  totalRebate: number;
  passedThrough: number;
  retained: number;
  retainedPct: number;
}

const demoData = {
  totalRebates: 42300000,
  totalPassedThrough: 37224000,
  totalRetained: 5076000,
  leakagePct: 12.0,
  drugs: [
    { drug: "Humira", manufacturer: "AbbVie", totalRebate: 8200000, passedThrough: 6970000, retained: 1230000, retainedPct: 15.0 },
    { drug: "Eliquis", manufacturer: "BMS/Pfizer", totalRebate: 5400000, passedThrough: 4860000, retained: 540000, retainedPct: 10.0 },
    { drug: "Ozempic", manufacturer: "Novo Nordisk", totalRebate: 6100000, passedThrough: 5124000, retained: 976000, retainedPct: 16.0 },
    { drug: "Keytruda", manufacturer: "Merck", totalRebate: 4800000, passedThrough: 4320000, retained: 480000, retainedPct: 10.0 },
    { drug: "Stelara", manufacturer: "J&J", totalRebate: 3900000, passedThrough: 3276000, retained: 624000, retainedPct: 16.0 },
    { drug: "Dupixent", manufacturer: "Regeneron/Sanofi", totalRebate: 3200000, passedThrough: 2816000, retained: 384000, retainedPct: 12.0 },
    { drug: "Jardiance", manufacturer: "Boehringer", totalRebate: 2800000, passedThrough: 2520000, retained: 280000, retainedPct: 10.0 },
    { drug: "Trulicity", manufacturer: "Eli Lilly", totalRebate: 3100000, passedThrough: 2604000, retained: 496000, retainedPct: 16.0 },
    { drug: "Xarelto", manufacturer: "J&J/Bayer", totalRebate: 2400000, passedThrough: 2208000, retained: 192000, retainedPct: 8.0 },
    { drug: "Skyrizi", manufacturer: "AbbVie", totalRebate: 2400000, passedThrough: 1526000, retained: 874000, retainedPct: 36.4 },
  ] as RebateDrug[],
};

function formatCurrency(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function FlowBar({ label, total, passed, retained }: { label: string; total: number; passed: number; retained: number }) {
  const passedPct = (passed / total) * 100;
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span>{formatCurrency(total)}</span>
      </div>
      <div className="h-6 bg-gray-100 rounded-full overflow-hidden flex">
        <div className="bg-emerald-500 h-full flex items-center justify-center text-[10px] text-white font-semibold" style={{ width: `${passedPct}%` }}>
          {passedPct.toFixed(0)}% passed
        </div>
        <div className="bg-red-400 h-full flex items-center justify-center text-[10px] text-white font-semibold" style={{ width: `${100 - passedPct}%` }}>
          {(100 - passedPct).toFixed(0)}% retained
        </div>
      </div>
    </div>
  );
}

export default function RebatesPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(demoData);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("/api/rebates/analysis");
        if (!res.ok) throw new Error();
        const json = await res.json();
        const ra = json?.rebate_analysis;
        if (ra) {
          const manufacturers: Record<string, string> = {
            "Trulicity": "Eli Lilly", "Ozempic": "Novo Nordisk", "Humira": "AbbVie",
            "Insulin Glargine": "Sanofi", "Stelara": "J&J", "Eliquis": "BMS/Pfizer",
            "Jardiance": "Boehringer", "Keytruda": "Merck", "Dupixent": "Regeneron/Sanofi",
            "Skyrizi": "AbbVie", "Xarelto": "J&J/Bayer",
          };
          setData({
            totalRebates: ra.total_rebates_earned,
            totalPassedThrough: ra.rebates_passed_to_plan,
            totalRetained: ra.rebates_retained_by_pbm,
            leakagePct: ra.leakage_pct,
            drugs: (ra.top_leakage_drugs || []).map((d: Record<string, unknown>) => {
              const name = (d.drug_name as string) || "";
              const baseName = name.split(" ")[0];
              return {
                drug: name,
                manufacturer: manufacturers[baseName] || "Pharmaceutical Co.",
                totalRebate: (d.total_rebate as number) || 0,
                passedThrough: (d.amount_passed as number) || 0,
                retained: (d.amount_retained_by_pbm as number) || 0,
                retainedPct: d.passthrough_rate ? 100 - (d.passthrough_rate as number) : 0,
              };
            }),
          });
        } else {
          setData(demoData);
        }
      } catch {
        setData(demoData);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-[#1e3a5f] animate-spin" />
        <p className="text-sm text-gray-500">Loading rebate analysis...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <DollarSign className="w-7 h-7 text-[#1e3a5f]" />
          Rebate Passthrough Tracker
        </h1>
        <p className="text-gray-500 mt-1">
          Track manufacturer rebate flow from PBM to plan sponsor
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
          <p className="text-sm text-gray-500">Total Rebates Received</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{formatCurrency(data.totalRebates)}</p>
        </div>
        <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-6 text-center">
          <p className="text-sm text-emerald-600">Passed Through to Plan</p>
          <p className="text-2xl font-bold text-emerald-700 mt-1">{formatCurrency(data.totalPassedThrough)}</p>
        </div>
        <div className="bg-red-50 rounded-xl border border-red-200 p-6 text-center">
          <p className="text-sm text-red-600">Retained by PBM</p>
          <p className="text-2xl font-bold text-red-700 mt-1">{formatCurrency(data.totalRetained)}</p>
        </div>
      </div>

      <div className="bg-gradient-to-r from-amber-500 to-red-500 rounded-xl p-6 mb-6 text-white flex items-center gap-4">
        <AlertTriangle className="w-10 h-10 flex-shrink-0" />
        <div>
          <p className="text-lg font-bold">Leakage Rate: {data.leakagePct}%</p>
          <p className="text-sm text-white/90">
            {formatCurrency(data.totalRetained)} in rebates retained by PBM instead of being passed through to the plan
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Rebate Flow: Manufacturer &rarr; PBM &rarr; Plan
        </h3>
        {data.drugs.slice(0, 5).map((drug) => (
          <FlowBar
            key={drug.drug}
            label={`${drug.drug} (${drug.manufacturer})`}
            total={drug.totalRebate}
            passed={drug.passedThrough}
            retained={drug.retained}
          />
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Drug</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Manufacturer</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Total Rebate</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Passed Through</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Retained</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">% Retained</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.drugs.map((drug, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{drug.drug}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{drug.manufacturer}</td>
                <td className="px-6 py-4 text-sm text-gray-700 text-right">{formatCurrency(drug.totalRebate)}</td>
                <td className="px-6 py-4 text-sm text-emerald-600 text-right">{formatCurrency(drug.passedThrough)}</td>
                <td className="px-6 py-4 text-sm text-red-600 font-semibold text-right">{formatCurrency(drug.retained)}</td>
                <td className="px-6 py-4 text-sm text-right font-semibold">{drug.retainedPct.toFixed(1)}%</td>
                <td className="px-6 py-4">
                  <StatusBadge
                    status={drug.retainedPct > 15 ? "critical" : drug.retainedPct > 10 ? "warning" : "good"}
                    label={drug.retainedPct > 15 ? "High" : drug.retainedPct > 10 ? "Medium" : "Low"}
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
