"use client";

import { useState, useEffect, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import MetricCard from "@/components/MetricCard";
import StatusBadge from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import FileUpload from "@/components/FileUpload";
import {
  Loader2,
  Building2,
  Layers,
  BarChart3,
  Pill,
  DollarSign,
  TrendingDown,
  Upload,
} from "lucide-react";

interface PartDStats {
  planCount: number;
  avgFormularySize: number;
  tierDistribution: { tier: string; percentage: number }[];
  paRate: number;
  qlRate: number;
  stRate: number;
}

interface IRADrug {
  drugName: string;
  manufacturer: string;
  condition: string;
  listPrice: number;
  negotiatedPrice: number;
  savingsPercent: number;
}

interface CompareResult {
  metric: string;
  yourPlan: string;
  partDBenchmark: string;
  status: string;
}

function normalizePartDStats(payload: unknown): PartDStats | null {
  const source = payload && typeof payload === "object" && "partd_benchmarks" in payload
    ? (payload as { partd_benchmarks?: Record<string, unknown> }).partd_benchmarks
    : payload;

  if (!source || typeof source !== "object") {
    return null;
  }

  const stats = source as Record<string, unknown>;
  const tierDistributionRaw = stats.tier_distribution_pct as Record<string, unknown> | undefined;
  const utilizationRaw = stats.utilization_management_rates as Record<string, unknown> | undefined;

  return {
    planCount: Number(stats.total_plans || 0),
    avgFormularySize: Number(stats.average_formulary_size_ndcs || 0),
    tierDistribution: tierDistributionRaw
      ? Object.entries(tierDistributionRaw).map(([tier, percentage]) => ({
          tier: tier.replace(/_/g, " "),
          percentage: Number(percentage || 0),
        }))
      : [],
    paRate: Number((utilizationRaw?.prior_authorization as { mean_pct?: number } | undefined)?.mean_pct || 0),
    qlRate: Number((utilizationRaw?.quantity_limit as { mean_pct?: number } | undefined)?.mean_pct || 0),
    stRate: Number((utilizationRaw?.step_therapy as { mean_pct?: number } | undefined)?.mean_pct || 0),
  };
}

function normalizeIRADrugs(payload: unknown): IRADrug[] {
  const source = payload && typeof payload === "object" && "ira_selected_drugs" in payload
    ? (payload as { ira_selected_drugs?: unknown[] }).ira_selected_drugs
    : payload;

  if (!Array.isArray(source)) {
    return [];
  }

  return source.map((item) => {
    const drug = item as Record<string, unknown>;
    return {
      drugName: String(drug.drug_name || ""),
      manufacturer: String(drug.manufacturer || ""),
      condition: String(drug.condition || ""),
      listPrice: Number(drug.current_list_price_30day || 0),
      negotiatedPrice: Number(drug.negotiated_max_fair_price_30day || 0),
      savingsPercent: Math.round(Number(drug.savings_pct || 0) * 100),
    };
  });
}

function normalizeCompareResults(payload: unknown): CompareResult[] {
  const source = payload && typeof payload === "object" && "comparison" in payload
    ? (payload as { comparison?: Record<string, unknown> }).comparison
    : payload;

  if (!source || typeof source !== "object") {
    return [];
  }

  const comparison = source as Record<string, unknown>;
  const tierDistribution = comparison.tier_distribution as Record<string, unknown> | undefined;
  const utilization = comparison.utilization_management as Record<string, unknown> | undefined;
  const employerTier = (tierDistribution?.employer || {}) as Record<string, unknown>;
  const benchmarkTier = (tierDistribution?.partd_average || {}) as Record<string, unknown>;
  const employerUM = (utilization?.employer || {}) as Record<string, unknown>;
  const benchmarkUM = (utilization?.partd_average || {}) as Record<string, unknown>;

  return [
    {
      metric: "Formulary size",
      yourPlan: String(comparison.formulary_size || 0),
      partDBenchmark: String(comparison.partd_avg_formulary_size || 0),
      status: Number(comparison.formulary_size || 0) >= Number(comparison.partd_avg_formulary_size || 0) ? "good" : "warning",
    },
    {
      metric: "Coverage gaps",
      yourPlan: String(comparison.coverage_gaps_count || 0),
      partDBenchmark: "0",
      status: Number(comparison.coverage_gaps_count || 0) === 0 ? "good" : "warning",
    },
    {
      metric: "Tier mismatches",
      yourPlan: String(comparison.tier_mismatches_count || 0),
      partDBenchmark: "0",
      status: Number(comparison.tier_mismatches_count || 0) === 0 ? "good" : "warning",
    },
    {
      metric: "PA rate",
      yourPlan: `${Number(employerUM.pa_pct || 0)}%`,
      partDBenchmark: `${Number(((benchmarkUM.prior_authorization || {}) as { mean_pct?: number }).mean_pct || 0)}%`,
      status: Number(employerUM.pa_pct || 0) <= Number(((benchmarkUM.prior_authorization || {}) as { mean_pct?: number }).mean_pct || 0) ? "good" : "warning",
    },
    {
      metric: "Tier 5 specialty share",
      yourPlan: `${Number(employerTier.tier_5_specialty_pct || 0)}%`,
      partDBenchmark: `${Number(benchmarkTier.tier_5_specialty_pct || 0)}%`,
      status: "info",
    },
  ];
}

export default function CMSBenchmarkPage() {
  const { toast } = useToast();
  usePageTitle("CMS Benchmark");
  const [loading, setLoading] = useState(true);
  const [partD, setPartD] = useState<PartDStats | null>(null);
  const [iraDrugs, setIraDrugs] = useState<IRADrug[]>([]);
  const [uploading, setUploading] = useState(false);
  const [compareResults, setCompareResults] = useState<CompareResult[] | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, iraRes] = await Promise.all([
        fetch("/api/cms-benchmark/partd-stats"),
        fetch("/api/cms-benchmark/ira-drugs"),
      ]);
      if (statsRes.ok) setPartD(normalizePartDStats(await statsRes.json()));
      if (iraRes.ok) setIraDrugs(normalizeIRADrugs(await iraRes.json()));
    } catch {
      /* silent */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCompareUpload = useCallback(
    async (file: File) => {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", file);
      try {
        const res = await fetch("/api/cms-benchmark/compare", { method: "POST", body: formData });
        if (res.ok) {
          setCompareResults(normalizeCompareResults(await res.json()));
          toast("Formulary compared against Part D benchmarks", "success");
        } else {
          toast("Comparison failed", "error");
        }
      } catch {
        toast("Comparison failed", "error");
      }
      setUploading(false);
    },
    [toast]
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading CMS benchmarks...</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Building2 className="w-7 h-7 text-primary-600" />
          CMS Benchmark Data
        </h1>
        <p className="text-gray-500 mt-1">
          Compare your formulary against Medicare Part D benchmarks and IRA negotiated drug prices
        </p>
      </div>

      {/* Part D Stats */}
      {partD && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <MetricCard icon={Layers} label="Part D Plans" value={partD.planCount.toLocaleString()} color="blue" />
            <MetricCard icon={Pill} label="Avg Formulary Size" value={partD.avgFormularySize.toLocaleString()} color="blue" />
            <MetricCard icon={BarChart3} label="PA Rate" value={`${partD.paRate}%`} color="amber" />
            <MetricCard icon={BarChart3} label="Step Therapy Rate" value={`${partD.stRate}%`} color="amber" />
          </div>

          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
              Tier Distribution
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {partD.tierDistribution.map((t, i) => (
                <div key={i} className="bg-blue-50 rounded-lg p-4 text-center">
                  <p className="text-lg font-bold text-primary-600">{t.percentage}%</p>
                  <p className="text-xs text-gray-600 mt-1">{t.tier}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 flex gap-4">
              <div className="bg-gray-50 rounded-lg px-4 py-2">
                <span className="text-xs text-gray-500">QL Rate: </span>
                <span className="text-sm font-semibold text-gray-900">{partD.qlRate}%</span>
              </div>
            </div>
          </div>
        </>
      )}

      {/* IRA Selected Drugs */}
      {iraDrugs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-emerald-600" />
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
              IRA Selected Drugs &mdash; Negotiated Prices
            </h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Drug</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Manufacturer</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Condition</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">List Price</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Negotiated</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Savings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {iraDrugs.map((drug, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium text-gray-900">{drug.drugName}</td>
                  <td className="px-6 py-3 text-gray-700">{drug.manufacturer}</td>
                  <td className="px-6 py-3 text-gray-700">{drug.condition}</td>
                  <td className="px-6 py-3 text-right text-gray-700">${drug.listPrice.toLocaleString()}</td>
                  <td className="px-6 py-3 text-right font-semibold text-emerald-700">${drug.negotiatedPrice.toLocaleString()}</td>
                  <td className="px-6 py-3 text-right">
                    <StatusBadge status="good" label={`${drug.savingsPercent}%`} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Compare Formulary */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider flex items-center gap-2">
          <Upload className="w-4 h-4 text-primary-600" />
          Compare Your Formulary Against Part D
        </h3>
        <FileUpload onFileSelect={handleCompareUpload} accept=".pdf,.csv" label="Upload your formulary (PDF or CSV)" />
        {uploading && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
            <span className="text-sm text-gray-500">Comparing against benchmarks...</span>
          </div>
        )}
      </div>

      {compareResults && (
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
              Benchmark Comparison Results
            </h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Metric</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Your Plan</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Part D Benchmark</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {compareResults.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium text-gray-900">{r.metric}</td>
                  <td className="px-6 py-3 text-gray-700">{r.yourPlan}</td>
                  <td className="px-6 py-3 text-gray-700">{r.partDBenchmark}</td>
                  <td className="px-6 py-3"><StatusBadge status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
