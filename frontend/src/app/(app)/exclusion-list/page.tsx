"use client";

import { useState, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import MetricCard from "@/components/MetricCard";
import StatusBadge from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import FileUpload from "@/components/FileUpload";
import {
  Loader2,
  ListX,
  Pill,
  ArrowLeftRight,
  TrendingUp,
  AlertTriangle,
  BarChart3,
} from "lucide-react";

interface Exclusion {
  drugClass: string;
  excludedMeds: string[];
  preferredAlternatives: string[];
}

interface ComparisonResult {
  newlyExcluded: string[];
  returnedToFormulary: string[];
  churnRate: number;
  totalCurrentExclusions: number;
  totalPriorExclusions: number;
}

interface ImpactData {
  affectedMembers: number;
  estimatedCostShift: number;
  disruptionScore: string;
}

export default function ExclusionListPage() {
  const { toast } = useToast();
  usePageTitle("Exclusion List Analyzer");
  const [parsing, setParsing] = useState(false);
  const [exclusions, setExclusions] = useState<Exclusion[] | null>(null);
  const [comparing, setComparing] = useState(false);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [estimating, setEstimating] = useState(false);
  const [impact, setImpact] = useState<ImpactData | null>(null);

  const handleFileUpload = useCallback(
    async (file: File) => {
      setParsing(true);
      setExclusions(null);
      setComparison(null);
      setImpact(null);
      const formData = new FormData();
      formData.append("file", file);
      try {
        const res = await fetch("/api/exclusion-list/parse", { method: "POST", body: formData });
        if (res.ok) {
          setExclusions(await res.json());
          toast("Exclusion list parsed successfully", "success");
        } else {
          toast("Failed to parse exclusion list", "error");
        }
      } catch {
        toast("Failed to parse exclusion list", "error");
      }
      setParsing(false);
    },
    [toast]
  );

  const handleCompareUpload = useCallback(
    async (file: File) => {
      setComparing(true);
      const formData = new FormData();
      formData.append("file", file);
      try {
        const res = await fetch("/api/exclusion-list/compare", { method: "POST", body: formData });
        if (res.ok) {
          setComparison(await res.json());
          toast("Year-over-year comparison complete", "success");
        } else {
          toast("Failed to compare exclusion lists", "error");
        }
      } catch {
        toast("Failed to compare exclusion lists", "error");
      }
      setComparing(false);
    },
    [toast]
  );

  const handleEstimateImpact = async () => {
    setEstimating(true);
    try {
      const res = await fetch("/api/exclusion-list/impact");
      if (res.ok) {
        setImpact(await res.json());
        toast("Impact estimate generated", "success");
      } else {
        toast("Failed to estimate impact", "error");
      }
    } catch {
      toast("Failed to estimate impact", "error");
    }
    setEstimating(false);
  };

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <ListX className="w-7 h-7 text-primary-600" />
          Exclusion List Analyzer
        </h1>
        <p className="text-gray-500 mt-1">
          Parse ESI exclusion lists and compare year-over-year formulary changes
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Upload Exclusion List PDF
        </h3>
        <FileUpload onFileSelect={handleFileUpload} accept=".pdf" label="Upload ESI exclusion list PDF" />
        {parsing && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
            <span className="text-sm text-gray-500">Parsing exclusion list...</span>
          </div>
        )}
      </div>

      {exclusions && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <MetricCard icon={Pill} label="Drug Classes" value={String(exclusions.length)} color="blue" />
            <MetricCard
              icon={ListX}
              label="Total Excluded Drugs"
              value={String(exclusions.reduce((s, e) => s + e.excludedMeds.length, 0))}
              color="red"
            />
            <MetricCard
              icon={ArrowLeftRight}
              label="Alternatives Listed"
              value={String(exclusions.reduce((s, e) => s + e.preferredAlternatives.length, 0))}
              color="green"
            />
          </div>

          {/* Exclusions Table */}
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                Parsed Exclusions
              </h3>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Drug Class</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Excluded Meds</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Preferred Alternatives</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {exclusions.map((ex, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-medium text-gray-900">{ex.drugClass}</td>
                    <td className="px-6 py-3 text-gray-700">
                      <div className="flex flex-wrap gap-1">
                        {ex.excludedMeds.map((m, j) => (
                          <span key={j} className="inline-block bg-red-50 text-red-700 text-xs px-2 py-0.5 rounded">{m}</span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-3 text-gray-700">
                      <div className="flex flex-wrap gap-1">
                        {ex.preferredAlternatives.map((a, j) => (
                          <span key={j} className="inline-block bg-emerald-50 text-emerald-700 text-xs px-2 py-0.5 rounded">{a}</span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Impact Button */}
          <div className="flex justify-end mb-6">
            <button
              onClick={handleEstimateImpact}
              disabled={estimating}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {estimating ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
              Estimate Impact
            </button>
          </div>

          {impact && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <MetricCard icon={TrendingUp} label="Affected Members" value={impact.affectedMembers.toLocaleString()} color="amber" />
              <MetricCard icon={TrendingUp} label="Estimated Cost Shift" value={`$${impact.estimatedCostShift.toLocaleString()}`} color="red" />
              <MetricCard icon={AlertTriangle} label="Disruption Score" value={impact.disruptionScore} color="amber" />
            </div>
          )}

          {/* Compare Section */}
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
              Year-over-Year Comparison
            </h3>
            <FileUpload onFileSelect={handleCompareUpload} accept=".pdf" label="Upload prior year exclusion list for comparison" />
            {comparing && (
              <div className="flex items-center justify-center gap-2 mt-4">
                <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
                <span className="text-sm text-gray-500">Comparing exclusion lists...</span>
              </div>
            )}
          </div>

          {comparison && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
                Comparison Results
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div className="bg-red-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-red-700">{comparison.newlyExcluded.length}</p>
                  <p className="text-xs text-red-600 mt-1">Newly Excluded</p>
                </div>
                <div className="bg-emerald-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-emerald-700">{comparison.returnedToFormulary.length}</p>
                  <p className="text-xs text-emerald-600 mt-1">Returned to Formulary</p>
                </div>
                <div className="bg-amber-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-amber-700">{comparison.churnRate}%</p>
                  <p className="text-xs text-amber-600 mt-1">Churn Rate</p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-semibold text-red-700 mb-2 uppercase">Newly Excluded</p>
                  <div className="flex flex-wrap gap-1">
                    {comparison.newlyExcluded.map((d, i) => (
                      <StatusBadge key={i} status="critical" label={d} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-semibold text-emerald-700 mb-2 uppercase">Returned to Formulary</p>
                  <div className="flex flex-wrap gap-1">
                    {comparison.returnedToFormulary.map((d, i) => (
                      <StatusBadge key={i} status="good" label={d} />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
