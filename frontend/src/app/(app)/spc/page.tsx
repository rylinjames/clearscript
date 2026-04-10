"use client";

import { useState, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import { useToast } from "@/components/Toast";
import FileUpload from "@/components/FileUpload";
import {
  Loader2,
  FileText,
  DollarSign,
  Heart,
  Pill,
  ShieldCheck,
} from "lucide-react";
import AIAnalysisProgress from "@/components/AIAnalysisProgress";

// The AI returns this shape from parse_spc via spc_service.py.
// The previous frontend expected a completely different shape
// (planName, deductibleIndividual, rxTiers[]) that didn't match
// the backend, causing "Cannot read properties of undefined" crashes.
interface ParsedPlanDoc {
  plan_info?: {
    plan_name?: string | null;
    carrier?: string | null;
    effective_date?: string | null;
    plan_type?: string | null;
  };
  deductible?: Record<string, string | null>;
  out_of_pocket_maximum?: Record<string, string | null>;
  copays?: Record<string, string | null>;
  coinsurance?: Record<string, string | null>;
  prescription_drugs?: Record<string, string | null>;
  hospital_services?: Record<string, string | null>;
  exclusions_and_limits?: string[];
  other_benefits?: Record<string, string | null>;
  confidence_score?: number;
}

export default function SPCPage() {
  const { toast } = useToast();
  usePageTitle("SBC/SPD Parser");
  const [parsing, setParsing] = useState(false);
  const [data, setData] = useState<ParsedPlanDoc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);

  const handleFileUpload = useCallback(
    async (file: File) => {
      setParsing(true);
      setData(null);
      setError(null);
      setFilename(file.name);
      const formData = new FormData();
      formData.append("file", file);
      try {
        const res = await fetch("/api/spc/parse", { method: "POST", body: formData });
        if (!res.ok) {
          let detail = `Parsing failed with status ${res.status}`;
          try {
            const errJson = await res.json();
            if (errJson?.detail) detail = String(errJson.detail);
          } catch { /* not JSON */ }
          throw new Error(detail);
        }
        const result = await res.json();
        // The API returns { status, source, text_length, benefits }
        // where benefits is the AI-parsed plan document.
        setData(result.benefits || result);
        toast("Plan document parsed successfully", "success");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to parse plan document");
        toast("Failed to parse plan document", "error");
      }
      setParsing(false);
    },
    [toast]
  );

  // Render a key-value section from the AI's output. Skips null/empty
  // values and formats keys from snake_case to Title Case.
  const renderSection = (title: string, icon: React.ReactNode, obj: Record<string, string | null> | undefined) => {
    if (!obj) return null;
    const entries = Object.entries(obj).filter(
      ([k, v]) => v && k !== "notes" && k !== "_generated_by"
    );
    if (entries.length === 0) return null;
    return (
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-4">
        <div className="px-5 py-3 border-b border-gray-200 flex items-center gap-2">
          {icon}
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">{title}</h3>
        </div>
        <div className="divide-y divide-gray-100">
          {entries.map(([key, value]) => (
            <div key={key} className="px-5 py-2.5 flex items-start justify-between gap-4">
              <p className="text-sm text-gray-600">
                {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </p>
              <p className="text-sm font-medium text-gray-900 text-right">{value}</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

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
        <FileUpload onFileSelect={handleFileUpload} label="Upload SBC, SPD, or EOC document (PDF or TXT)" />
      </div>

      {parsing && (
        <div className="mt-6">
          <AIAnalysisProgress variant="plan_doc" estimatedSeconds={32} />
        </div>
      )}

      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-sm text-amber-700">{error}</p>
        </div>
      )}

      {data && !parsing && (
        <>
          {/* Header metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {data.plan_info?.plan_name && (
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-4">
                <div className="flex items-center gap-2 mb-1">
                  <ShieldCheck className="w-4 h-4 text-blue-600" />
                  <p className="text-[11px] font-semibold text-gray-500 uppercase">Plan</p>
                </div>
                <p className="text-sm font-bold text-gray-900 truncate">{data.plan_info.plan_name}</p>
                {data.plan_info.plan_type && (
                  <p className="text-xs text-gray-500 mt-0.5">{data.plan_info.plan_type}</p>
                )}
              </div>
            )}
            {data.deductible?.individual_in_network && (
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-4">
                <div className="flex items-center gap-2 mb-1">
                  <DollarSign className="w-4 h-4 text-amber-600" />
                  <p className="text-[11px] font-semibold text-gray-500 uppercase">Deductible (Ind)</p>
                </div>
                <p className="text-lg font-bold text-gray-900">{data.deductible.individual_in_network}</p>
              </div>
            )}
            {data.out_of_pocket_maximum?.individual_in_network && (
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-4">
                <div className="flex items-center gap-2 mb-1">
                  <DollarSign className="w-4 h-4 text-red-600" />
                  <p className="text-[11px] font-semibold text-gray-500 uppercase">OOP Max (Ind)</p>
                </div>
                <p className="text-lg font-bold text-gray-900">{data.out_of_pocket_maximum.individual_in_network}</p>
              </div>
            )}
            {data.confidence_score != null && (
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Heart className="w-4 h-4 text-emerald-600" />
                  <p className="text-[11px] font-semibold text-gray-500 uppercase">Confidence</p>
                </div>
                <p className="text-lg font-bold text-gray-900">{data.confidence_score}%</p>
                {filename && <p className="text-xs text-gray-500 mt-0.5 truncate">{filename}</p>}
              </div>
            )}
          </div>

          {/* Sections */}
          {renderSection("Deductible", <DollarSign className="w-4 h-4 text-primary-600" />, data.deductible)}
          {renderSection("Out-of-Pocket Maximum", <DollarSign className="w-4 h-4 text-primary-600" />, data.out_of_pocket_maximum)}
          {renderSection("Copays", <Heart className="w-4 h-4 text-primary-600" />, data.copays)}
          {renderSection("Coinsurance", <ShieldCheck className="w-4 h-4 text-primary-600" />, data.coinsurance)}
          {renderSection("Prescription Drugs", <Pill className="w-4 h-4 text-primary-600" />, data.prescription_drugs)}
          {renderSection("Hospital Services", <Heart className="w-4 h-4 text-primary-600" />, data.hospital_services)}
          {renderSection("Other Benefits", <ShieldCheck className="w-4 h-4 text-primary-600" />, data.other_benefits)}

          {/* Exclusions */}
          {data.exclusions_and_limits && data.exclusions_and_limits.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-4">
              <div className="px-5 py-3 border-b border-gray-200 flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary-600" />
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Exclusions & Limitations</h3>
              </div>
              <ul className="divide-y divide-gray-100">
                {data.exclusions_and_limits.map((item, i) => (
                  <li key={i} className="px-5 py-2.5 text-sm text-gray-700">{item}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Plan info details */}
          {data.plan_info && (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 mb-6">
              <div className="flex flex-wrap gap-4 text-xs text-gray-600">
                {data.plan_info.carrier && <span><strong>Carrier:</strong> {data.plan_info.carrier}</span>}
                {data.plan_info.effective_date && <span><strong>Effective:</strong> {data.plan_info.effective_date}</span>}
                {data.plan_info.plan_type && <span><strong>Type:</strong> {data.plan_info.plan_type}</span>}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
