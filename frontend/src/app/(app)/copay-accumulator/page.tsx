"use client";

import { useState, useEffect, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import MetricCard from "@/components/MetricCard";
import StatusBadge from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import {
  Loader2,
  Wallet,
  Users,
  DollarSign,
  Pill,
  TrendingUp,
  ShieldCheck,
  Scale,
  Lightbulb,
} from "lucide-react";

interface AnalysisSummary {
  affectedMembers: number;
  totalCapturedValue: number;
  perMemberImpact: number;
  avgDeductibleGap: number;
  pctMembersHitOOP: number;
}

interface DrugImpact {
  drugName: string;
  drugClass: string;
  annualCopayCardValue: number;
  annualDrugCost: number;
  copayAsPctOfCost: number;
}

interface Recommendation {
  strategy: string;
  description: string;
  pros: string[];
  cons: string[];
  estimatedSavings: string;
  status: string;
}

export default function CopayAccumulatorPage() {
  const { toast } = useToast();
  usePageTitle("Copay Accumulator");
  const [loading, setLoading] = useState(true);
  const [analysis, setAnalysis] = useState<AnalysisSummary | null>(null);
  const [drugs, setDrugs] = useState<DrugImpact[]>([]);

  const recommendations: Recommendation[] = [
    {
      strategy: "Accumulator",
      description: "Copay assistance does NOT count toward deductible or OOP max. Member pays full cost after copay card exhausted.",
      pros: ["Maximizes plan savings", "Reduces overall plan spend", "Simple to implement"],
      cons: ["Member disruption risk", "Compliance concerns", "State law restrictions"],
      estimatedSavings: "High",
      status: "warning",
    },
    {
      strategy: "Maximizer",
      description: "Copay assistance applied to highest-cost drugs to maximize manufacturer funding. Extends copay card duration.",
      pros: ["Less member disruption", "Optimizes copay card value", "Better member satisfaction"],
      cons: ["Complex administration", "Lower savings than accumulator", "Requires vendor partnership"],
      estimatedSavings: "Medium-High",
      status: "good",
    },
    {
      strategy: "Hybrid",
      description: "Accumulator for specialty drugs above threshold, standard accumulation for others. Balances savings and member experience.",
      pros: ["Balanced approach", "Targets highest-cost drugs", "Regulatory flexibility"],
      cons: ["Complex to communicate", "Requires tier-level rules", "Moderate implementation effort"],
      estimatedSavings: "Medium",
      status: "info",
    },
  ];

  const fetchData = useCallback(async () => {
    try {
      const [analysisRes, drugsRes] = await Promise.all([
        fetch("/api/copay-accumulator/analysis"),
        fetch("/api/copay-accumulator/drug-list"),
      ]);
      if (analysisRes.ok) setAnalysis(await analysisRes.json());
      if (drugsRes.ok) setDrugs(await drugsRes.json());
    } catch {
      /* silent */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading copay accumulator analysis...</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Wallet className="w-7 h-7 text-primary-600" />
          Copay Accumulator Analysis
        </h1>
        <p className="text-gray-500 mt-1">
          Analyze copay accumulator program impact on members and evaluate program strategies
        </p>
      </div>

      {/* Impact Summary */}
      {analysis && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <MetricCard icon={Users} label="Affected Members" value={analysis.affectedMembers.toLocaleString()} color="amber" />
          <MetricCard icon={DollarSign} label="Total Captured Value" value={`$${analysis.totalCapturedValue.toLocaleString()}`} color="red" />
          <MetricCard icon={TrendingUp} label="Per-Member Impact" value={`$${analysis.perMemberImpact.toLocaleString()}`} color="amber" />
          <MetricCard icon={ShieldCheck} label="Hit OOP Max" value={`${analysis.pctMembersHitOOP}%`} color="red" />
        </div>
      )}

      {/* Drug List Table */}
      {drugs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
            <Pill className="w-4 h-4 text-primary-600" />
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
              Drug Impact Details
            </h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Drug Name</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Class</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Annual Copay Card Value</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Annual Drug Cost</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Copay as % of Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {drugs.map((drug, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium text-gray-900">{drug.drugName}</td>
                  <td className="px-6 py-3 text-gray-700">{drug.drugClass}</td>
                  <td className="px-6 py-3 text-right text-emerald-700 font-medium">${drug.annualCopayCardValue.toLocaleString()}</td>
                  <td className="px-6 py-3 text-right text-gray-700">${drug.annualDrugCost.toLocaleString()}</td>
                  <td className="px-6 py-3 text-right">
                    <StatusBadge
                      status={drug.copayAsPctOfCost > 50 ? "good" : drug.copayAsPctOfCost > 20 ? "warning" : "info"}
                      label={`${drug.copayAsPctOfCost}%`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Recommendations */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-6 uppercase tracking-wider flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-500" />
          Strategy Recommendations
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {recommendations.map((rec, i) => (
            <div key={i} className="rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Scale className="w-4 h-4 text-primary-600" />
                  <h4 className="text-sm font-bold text-gray-900">{rec.strategy}</h4>
                </div>
                <StatusBadge status={rec.status} label={rec.estimatedSavings} />
              </div>
              <p className="text-xs text-gray-600 mb-3">{rec.description}</p>
              <div className="mb-2">
                <p className="text-xs font-semibold text-emerald-700 mb-1">Pros</p>
                <ul className="text-xs text-gray-600 list-disc list-inside space-y-0.5">
                  {rec.pros.map((p, j) => <li key={j}>{p}</li>)}
                </ul>
              </div>
              <div>
                <p className="text-xs font-semibold text-red-700 mb-1">Cons</p>
                <ul className="text-xs text-gray-600 list-disc list-inside space-y-0.5">
                  {rec.cons.map((c, j) => <li key={j}>{c}</li>)}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
