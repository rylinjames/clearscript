"use client";

import { useState, useEffect } from "react";
import StatusBadge from "@/components/StatusBadge";
import { Pill, Loader2, AlertTriangle, ArrowRight } from "lucide-react";

interface FormularySwap {
  date: string;
  oldDrug: string;
  newDrug: string;
  oldCost: number;
  newCost: number;
  priceChange: number;
  rebateImpact: string;
  severity: "critical" | "warning" | "info";
  reason: string;
}

interface TimelineEvent {
  date: string;
  description: string;
  type: "addition" | "removal" | "tier_change" | "swap";
}

const demoSwaps: FormularySwap[] = [
  { date: "2025-11-01", oldDrug: "Humira (adalimumab)", newDrug: "Hadlima (biosimilar)", oldCost: 6800, newCost: 5100, priceChange: -25, rebateImpact: "Rebate loss: $1.2M/yr", severity: "critical", reason: "Biosimilar swap eliminates brand rebate — net cost may increase" },
  { date: "2025-10-15", oldDrug: "Lantus (insulin glargine)", newDrug: "Semglee (biosimilar)", oldCost: 340, newCost: 180, priceChange: -47, rebateImpact: "Rebate loss: $800K/yr", severity: "warning", reason: "Biosimilar swap with significant rebate reduction" },
  { date: "2025-09-01", oldDrug: "Lipitor (atorvastatin 20mg)", newDrug: "Rosuvastatin 10mg", oldCost: 15, newCost: 22, priceChange: 47, rebateImpact: "New rebate: +$200K/yr", severity: "critical", reason: "Therapeutic swap to more expensive statin — rebate-driven?" },
  { date: "2025-08-15", oldDrug: "Protonix (pantoprazole)", newDrug: "Omeprazole", oldCost: 28, newCost: 8, priceChange: -71, rebateImpact: "Minimal impact", severity: "info", reason: "Generic substitution — appropriate cost reduction" },
  { date: "2025-07-01", oldDrug: "Celebrex (celecoxib)", newDrug: "Meloxicam", oldCost: 45, newCost: 12, priceChange: -73, rebateImpact: "Rebate loss: $150K/yr", severity: "info", reason: "Therapeutic alternative — clinically reasonable" },
  { date: "2025-06-01", oldDrug: "Crestor (rosuvastatin 20mg)", newDrug: "Livalo (pitavastatin)", oldCost: 18, newCost: 350, priceChange: 1844, rebateImpact: "New rebate: +$1.8M/yr", severity: "critical", reason: "Brand swap with massive price increase — likely rebate-motivated" },
  { date: "2025-05-15", oldDrug: "Nexium (esomeprazole)", newDrug: "Dexilant (dexlansoprazole)", oldCost: 22, newCost: 380, priceChange: 1627, rebateImpact: "New rebate: +$900K/yr", severity: "critical", reason: "Brand-to-brand swap with extreme price increase" },
  { date: "2025-04-01", oldDrug: "Metformin ER 500mg", newDrug: "Metformin ER 750mg", oldCost: 8, newCost: 12, priceChange: 50, rebateImpact: "No impact", severity: "warning", reason: "Dose form change — may affect member convenience" },
];

const demoTimeline: TimelineEvent[] = [
  { date: "2025-11-01", description: "4 drugs removed, 3 biosimilars added, 1 tier change", type: "swap" },
  { date: "2025-10-15", description: "Insulin formulary restructured — 2 products swapped", type: "swap" },
  { date: "2025-09-01", description: "Statin preferred list changed — rosuvastatin now preferred", type: "tier_change" },
  { date: "2025-08-15", description: "2 generics added to preferred tier", type: "addition" },
  { date: "2025-07-01", description: "NSAID formulary updated — 1 removal, 1 addition", type: "swap" },
  { date: "2025-06-01", description: "Major statin swap — Crestor replaced by Livalo", type: "swap" },
  { date: "2025-05-15", description: "PPI formulary change — brand-to-brand swap flagged", type: "swap" },
  { date: "2025-04-01", description: "Metformin formulation change", type: "tier_change" },
];

export default function FormularyPage() {
  const [loading, setLoading] = useState(true);
  const [swaps, setSwaps] = useState<FormularySwap[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("/api/formulary/analysis");
        if (!res.ok) throw new Error();
        const data = await res.json();
        const fa = data?.formulary_analysis;
        if (fa?.manipulation_flags) {
          setSwaps(fa.manipulation_flags.map((f: Record<string, unknown>) => ({
            oldDrug: f.old_drug || "Unknown",
            newDrug: f.new_drug || "Unknown",
            oldPrice: f.old_cost || 0,
            newPrice: f.new_cost || 0,
            priceChange: f.cost_increase_pct || 0,
            rebateImpact: f.rebate_impact || "Unknown",
            severity: (f.severity as string) || "warning",
            date: (f.date as string) || "2025-06-01",
          })));
        } else {
          setSwaps(demoSwaps);
        }
        setTimeline(data?.timeline || demoTimeline);
      } catch {
        setSwaps(demoSwaps);
        setTimeline(demoTimeline);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const criticalCount = swaps.filter((s) => s.severity === "critical").length;
  const totalCostImpact = swaps.reduce((sum, s) => sum + (s.newCost - s.oldCost), 0);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-[#1e3a5f] animate-spin" />
        <p className="text-sm text-gray-500">Loading formulary analysis...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Pill className="w-7 h-7 text-[#1e3a5f]" />
          Formulary Manipulation Detector
        </h1>
        <p className="text-gray-500 mt-1">
          Identify suspicious drug swaps that may be rebate-motivated rather than clinically driven
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-red-50 rounded-xl border border-red-200 p-6 text-center">
          <p className="text-3xl font-bold text-red-700">{criticalCount}</p>
          <p className="text-sm text-red-600 mt-1">Suspicious Swaps</p>
        </div>
        <div className="bg-amber-50 rounded-xl border border-amber-200 p-6 text-center">
          <p className="text-3xl font-bold text-amber-700">{swaps.length}</p>
          <p className="text-sm text-amber-600 mt-1">Total Formulary Changes</p>
        </div>
        <div className={`rounded-xl border p-6 text-center ${totalCostImpact > 0 ? "bg-red-50 border-red-200" : "bg-emerald-50 border-emerald-200"}`}>
          <p className={`text-3xl font-bold ${totalCostImpact > 0 ? "text-red-700" : "text-emerald-700"}`}>
            {totalCostImpact > 0 ? "+" : ""}${Math.abs(totalCostImpact).toLocaleString()}
          </p>
          <p className={`text-sm mt-1 ${totalCostImpact > 0 ? "text-red-600" : "text-emerald-600"}`}>Net Per-Rx Cost Impact</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Formulary Change Timeline
        </h3>
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />
          <div className="space-y-4">
            {timeline.map((event, i) => (
              <div key={i} className="relative pl-10">
                <div className={`absolute left-2.5 top-1.5 w-3 h-3 rounded-full border-2 border-white ${
                  event.type === "swap" ? "bg-red-500" : event.type === "removal" ? "bg-amber-500" : event.type === "addition" ? "bg-emerald-500" : "bg-blue-500"
                }`} />
                <div className="flex items-baseline gap-3">
                  <span className="text-xs text-gray-400 font-mono w-24 flex-shrink-0">{event.date}</span>
                  <p className="text-sm text-gray-700">{event.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
            Suspicious Drug Swaps
          </h3>
        </div>
        <div className="divide-y divide-gray-100">
          {swaps.map((swap, i) => (
            <div key={i} className="p-6 hover:bg-gray-50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 font-mono">{swap.date}</span>
                  <StatusBadge status={swap.severity} />
                </div>
                <span className={`text-sm font-semibold ${swap.priceChange > 0 ? "text-red-600" : "text-emerald-600"}`}>
                  {swap.priceChange > 0 ? "+" : ""}{swap.priceChange}% price change
                </span>
              </div>
              <div className="flex items-center gap-3 mb-2">
                <span className="text-sm font-medium text-gray-900 bg-red-50 px-2 py-1 rounded">{swap.oldDrug}</span>
                <ArrowRight className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-900 bg-emerald-50 px-2 py-1 rounded">{swap.newDrug}</span>
                <span className="text-xs text-gray-500 ml-2">
                  ${swap.oldCost} &rarr; ${swap.newCost}
                </span>
              </div>
              <p className="text-xs text-gray-500">{swap.reason}</p>
              <p className="text-xs text-amber-600 mt-1 font-medium">{swap.rebateImpact}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
