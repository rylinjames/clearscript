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
      if (statsRes.ok) setPartD(await statsRes.json());
      if (iraRes.ok) setIraDrugs(await iraRes.json());
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
          setCompareResults(await res.json());
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
