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
  Sparkles,
} from "lucide-react";
import AIAnalysisProgress from "@/components/AIAnalysisProgress";

// Abbreviations that should stay uppercase when formatting snake_case
// keys into display labels. Without this, "pbm_name" becomes "Pbm Name"
// instead of "PBM Name".
const ABBREVIATIONS: Record<string, string> = {
  pbm: "PBM",
  pcp: "PCP",
  oop: "OOP",
  hmo: "HMO",
  ppo: "PPO",
  sbc: "SBC",
  spd: "SPD",
  eoc: "EOC",
  coc: "COC",
  cobra: "COBRA",
  hdhp: "HDHP",
  pos: "POS",
  er: "ER",
  dme: "DME",
  cms: "CMS",
  aca: "ACA",
};

function formatLabel(snakeKey: string): string {
  return snakeKey
    .replace(/_/g, " ")
    .split(" ")
    .map((word) => ABBREVIATIONS[word.toLowerCase()] || (word.charAt(0).toUpperCase() + word.slice(1)))
    .join(" ");
}

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
  key_exclusions?: string[];
  confidence_score?: number;
  // The AI may also return fields not in the schema — render them
  // generically via the catch-all logic below.
  [key: string]: unknown;
}

const SAMPLE_PLAN_DOC_TEXT = `SUMMARY OF BENEFITS AND COVERAGE (SBC)
Heartland Employers Health Coalition
PBM: MegaCare PBM, Inc.
Plan Type: Self-Insured PPO
Effective Date: January 1, 2025
Coverage Period: January 1, 2025 — December 31, 2025

DEDUCTIBLE
Individual In-Network: $1,500
Individual Out-of-Network: $3,000
Family In-Network: $3,000
Family Out-of-Network: $6,000

OUT-OF-POCKET MAXIMUM
Individual In-Network: $6,500
Individual Out-of-Network: $13,000
Family In-Network: $13,000
Family Out-of-Network: $26,000

COPAYMENTS AND COINSURANCE
Primary Care Visit: $25 copay (in-network) / 40% coinsurance (out-of-network)
Specialist Visit: $50 copay (in-network) / 40% coinsurance (out-of-network)
Urgent Care: $75 copay
Emergency Room: $250 copay (waived if admitted)
Preventive Care: $0 (in-network only)
Mental Health (outpatient): $25 copay (in-network) / 40% coinsurance (out-of-network)
Telehealth Visit: $10 copay

PRESCRIPTION DRUG COVERAGE
Pharmacy Benefit Manager: MegaCare PBM, Inc.
Formulary: MegaCare National Formulary (closed formulary)
Mandatory Mail-Order: Required for maintenance medications after second retail fill
Specialty Pharmacy: MegaCare Specialty Pharmacy (exclusive)

Tier 1 — Generic Drugs: Retail $10 copay / Mail Order $25 copay
Tier 2 — Preferred Brand: Retail $35 copay / Mail Order $90 copay
Tier 3 — Non-Preferred Brand: Retail $60 copay / Mail Order $150 copay
Tier 4 — Specialty: 20% coinsurance up to $250 per fill

Prior Authorization: Required for all Tier 3 and Tier 4 medications.
Step Therapy: Required for select Tier 2 and Tier 3 medications.

HOSPITAL SERVICES
Inpatient (in-network): 20% coinsurance after deductible
Inpatient (out-of-network): 40% coinsurance after deductible
Outpatient Surgery: $150 copay + 20% coinsurance (in-network)

EXCLUSIONS AND LIMITATIONS
- Cosmetic surgery or procedures
- Experimental or investigational treatments
- Weight loss surgery (unless medically necessary with prior authorization)
- Dental services (covered under separate dental plan)
- Vision services beyond annual eye exam
- Long-term care or custodial care
- Over-the-counter medications
- Infertility treatments beyond initial diagnostic evaluation

OTHER BENEFITS
Chiropractic Care: $40 copay, limited to 20 visits per year
Physical Therapy: $40 copay, limited to 30 visits per year
Durable Medical Equipment: 20% coinsurance after deductible
Ambulance: $250 copay + 20% coinsurance`;

export default function SPCPage() {
  const { toast } = useToast();
  usePageTitle("SBC/SPD Parser");
  const [parsing, setParsing] = useState(false);
  const [data, setData] = useState<ParsedPlanDoc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);

  const handleSampleUpload = async () => {
    const blob = new Blob([SAMPLE_PLAN_DOC_TEXT], { type: "text/plain" });
    const file = new File([blob], "sample-plan-document.txt", { type: "text/plain" });
    await handleFileUpload(file);
  };

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
                {formatLabel(key)}
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
        <div className="mt-4 text-center">
          <button
            onClick={handleSampleUpload}
            disabled={parsing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            Analyze Sample Plan Document
          </button>
        </div>
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

          {/* Key Exclusions — Rx-relevant only */}
          {data.key_exclusions && data.key_exclusions.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-4">
              <div className="px-5 py-3 border-b border-gray-200 flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary-600" />
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Key Rx Exclusions</h3>
              </div>
              <ul className="divide-y divide-gray-100">
                {data.key_exclusions.map((item, i) => (
                  <li key={i} className="px-5 py-2.5 text-sm text-gray-700">{item}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Catch-all: render any extra sections the AI returned that
              we don't have explicit rendering for. This prevents data
              from being silently dropped if the AI adds new fields. */}
          {(() => {
            const knownKeys = new Set([
              "plan_info", "deductible", "out_of_pocket_maximum", "copays",
              "coinsurance", "prescription_drugs", "key_exclusions",
              "confidence_score", "_generated_by", "status", "source",
              "text_length", "benefits",
            ]);
            const extraSections = Object.entries(data)
              .filter(([key, val]) => !knownKeys.has(key) && val && typeof val === "object" && !Array.isArray(val))
              .map(([key, val]) => ({ key, val: val as Record<string, string | null> }));
            return extraSections.map(({ key, val }) =>
              renderSection(formatLabel(key), <ShieldCheck className="w-4 h-4 text-primary-600" />, val)
            );
          })()}

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
