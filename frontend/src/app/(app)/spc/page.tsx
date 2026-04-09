"use client";

import { useState, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import MetricCard from "@/components/MetricCard";
import StatusBadge from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import FileUpload from "@/components/FileUpload";
import {
  Loader2,
  FileText,
  DollarSign,
  Heart,
  Pill,
  GitCompare,
  ShieldCheck,
} from "lucide-react";
import AIAnalysisProgress from "@/components/AIAnalysisProgress";

interface BenefitDetail {
  label: string;
  inNetwork: string;
  outOfNetwork: string;
}

interface RxTier {
  tier: string;
  copay: string;
  coinsurance: string;
}

interface SPCData {
  planName: string;
  deductibleIndividual: string;
  deductibleFamily: string;
  oopMaxIndividual: string;
  oopMaxFamily: string;
  benefits: BenefitDetail[];
  rxTiers: RxTier[];
}

interface ComparisonResult {
  field: string;
  plan1: string;
  plan2: string;
  status: string;
}

export default function SPCPage() {
  const { toast } = useToast();
  usePageTitle("SBC/SPD Parser");
  const [parsing, setParsing] = useState(false);
  const [data, setData] = useState<SPCData | null>(null);
  const [comparing, setComparing] = useState(false);
  const [comparison, setComparison] = useState<ComparisonResult[] | null>(null);

  const handleFileUpload = useCallback(
    async (file: File) => {
      setParsing(true);
      setData(null);
      setComparison(null);
      const formData = new FormData();
      formData.append("file", file);
      try {
        const res = await fetch("/api/spc/parse", { method: "POST", body: formData });
        if (res.ok) {
          setData(await res.json());
          toast("Plan document parsed successfully", "success");
        } else {
          toast("Failed to parse plan document document", "error");
        }
      } catch {
        toast("Failed to parse plan document document", "error");
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
        const res = await fetch("/api/spc/compare", { method: "POST", body: formData });
        if (res.ok) {
          setComparison(await res.json());
          toast("Comparison complete", "success");
        } else {
          toast("Failed to compare documents", "error");
        }
      } catch {
        toast("Failed to compare documents", "error");
      }
      setComparing(false);
    },
    [toast]
  );

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <FileText className="w-7 h-7 text-primary-600" />
          Plan Document Parser
        </h1>
        <p className="text-gray-500 mt-1">
          Upload a Summary of Benefits and Coverage to extract and structure plan details
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Upload SBC/SPD Document
        </h3>
        <FileUpload onFileSelect={handleFileUpload} accept=".pdf" label="Upload SBC, SPD, or EOC document" />
      </div>

      {parsing && (
        <div className="mt-6">
          <AIAnalysisProgress variant="plan_doc" estimatedSeconds={32} />
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <MetricCard icon={ShieldCheck} label="Plan Name" value={data.planName} color="blue" />
            <MetricCard icon={DollarSign} label="Deductible (Ind)" value={data.deductibleIndividual} color="amber" />
            <MetricCard icon={DollarSign} label="OOP Max (Ind)" value={data.oopMaxIndividual} color="red" />
            <MetricCard icon={Heart} label="Rx Tiers" value={String(data.rxTiers.length)} color="green" />
          </div>

          {/* Benefits Table */}
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                Extracted Benefits
              </h3>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Benefit</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">In-Network</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Out-of-Network</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.benefits.map((b, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-medium text-gray-900">{b.label}</td>
                    <td className="px-6 py-3 text-gray-700">{b.inNetwork}</td>
                    <td className="px-6 py-3 text-gray-700">{b.outOfNetwork}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Rx Tiers */}
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
              <Pill className="w-4 h-4 text-primary-600" />
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                Prescription Drug Tiers
              </h3>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Tier</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Copay</th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Coinsurance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.rxTiers.map((rx, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-medium text-gray-900">{rx.tier}</td>
                    <td className="px-6 py-3 text-gray-700">{rx.copay}</td>
                    <td className="px-6 py-3 text-gray-700">{rx.coinsurance}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Compare Section */}
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider flex items-center gap-2">
              <GitCompare className="w-4 h-4 text-primary-600" />
              Compare with Another SPC
            </h3>
            <FileUpload onFileSelect={handleCompareUpload} accept=".pdf" label="Upload second SBC/SPD for comparison" />
          </div>

          {comparing && (
            <div className="mt-6">
              <AIAnalysisProgress variant="cross_reference" estimatedSeconds={38} />
            </div>
          )}

          {comparison && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                  Comparison Results
                </h3>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Field</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Plan 1</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Plan 2</th>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {comparison.map((c, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-gray-900">{c.field}</td>
                      <td className="px-6 py-3 text-gray-700">{c.plan1}</td>
                      <td className="px-6 py-3 text-gray-700">{c.plan2}</td>
                      <td className="px-6 py-3"><StatusBadge status={c.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
