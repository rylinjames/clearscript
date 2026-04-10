"use client";

import { useState, useEffect } from "react";
import { usePageTitle } from "@/components/PageTitle";
import FileUpload from "@/components/FileUpload";
import ScoreCircle from "@/components/ScoreCircle";
import { Search, Loader2, Sparkles, Check, X, ChevronDown, ChevronUp, FileText, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import AIAnalysisProgress from "@/components/AIAnalysisProgress";

interface ChecklistItem {
  item: string;
  found: boolean;
  detail: string;
}

interface GapItem {
  missing_item: string;
  why_required: string;
  recommendation: string;
  impact: string;
}

interface ContractListItem {
  id: number;
  filename: string;
  analysis_date: string | null;
  deal_score: number | null;
  risk_level: string | null;
}

interface Discrepancy {
  category: string;
  severity: string;
  contract_says: string;
  disclosure_says: string;
  gap: string;
  recommendation: string;
}

interface Confirmation {
  category: string;
  contract_says: string;
  disclosure_confirms: string;
}

interface CrossRefResult {
  discrepancies: Discrepancy[];
  confirmations: Confirmation[];
  overall_alignment_score: number;
  summary: string;
}

const SAMPLE_DISCLOSURE_TEXT = `PBM INITIAL DISCLOSURE REPORT
Prepared for: Heartland Employers Health Coalition
Reporting Period: January 1, 2025 — June 30, 2025
Prepared by: MegaCare PBM, Inc.

SECTION 1: REBATE REVENUE DISCLOSURE

During the reporting period, MegaCare PBM negotiated and received manufacturer rebates on behalf of the Plan Sponsor. Total rebate revenue attributable to Plan Sponsor claims: $42,317,892.45.

Rebate categories:
- Brand formulary rebates: $31,208,441.00
- Market share incentives: $6,892,103.22
- Admin/data fees from manufacturers: $4,217,348.23

100% of designated "rebates" ($31,208,441.00) were passed through to Plan Sponsor per contract terms.

Note: Market share incentives and admin/data fees are retained by PBM per Section 4.4 of the Agreement.

SECTION 2: ADMINISTRATIVE FEE BREAKDOWN

Per-member per-month (PMPM) administrative fee: $4.25
Total members enrolled (average): 28,400
Total administrative fees collected: $1,447,800.00

Per-claim processing fees: $0.00 (included in PMPM)
Specialty coordination fees: $312,000.00
Clinical program management fees: $186,500.00

SECTION 3: FORMULARY MANAGEMENT

The Pharmacy and Therapeutics Committee met quarterly during the reporting period. Formulary changes during the period:
- 14 new additions
- 8 tier changes
- 3 removals

All changes communicated to Plan Sponsor with 60 days advance notice per contractual terms.

SECTION 4: MAIL-ORDER PHARMACY UTILIZATION

Mail-order utilization rate: 34.2%
Total mail-order claims: 186,443
Mail-order revenue (dispensing margin): $8,234,112.00
Mail-order dispensing fees: $0.00

Maintenance medication conversion program enrolled 12,800 members in auto-refill.

SECTION 5: CLINICAL PROGRAM OUTCOMES

Prior Authorization Program:
- Total PA requests: 42,318
- Approved: 36,122 (85.4%)
- Denied: 6,196 (14.6%)
- Estimated savings: $4,200,000

Step Therapy Program:
- Members enrolled: 8,400
- Estimated savings: $2,600,000

Total clinical program savings: $6,800,000

SECTION 6: PERFORMANCE GUARANTEE REPORTING

Generic Dispensing Rate (GDR):
- Guaranteed minimum: 88.0%
- Actual achieved: 91.2%
- Status: GUARANTEE MET

Brand Effective Rate (BER):
- Guaranteed minimum: AWP-17%
- Actual achieved: AWP-18.1%
- Status: GUARANTEE MET

Generic Effective Rate (GER):
- Guaranteed minimum: AWP-80%
- Actual achieved: AWP-82.3%
- Status: GUARANTEE MET

Claims Processing Accuracy:
- Guaranteed minimum: 99.0%
- Actual achieved: 99.2%
- Status: GUARANTEE MET

SECTION 7: NETWORK SUMMARY

Total network pharmacies: 67,200
Retail pharmacies: 64,100
Specialty pharmacies: 1,800
Mail-order facilities: 3

Network adequacy meets CMS standards in all required zip codes.

END OF DISCLOSURE REPORT

Note: This disclosure does not include information regarding spread pricing differentials, MAC list composition, specialty pharmacy margins, manufacturer administrative fees, or subcontractor relationships, as these items are considered proprietary and confidential under the terms of the Agreement.`;

export default function DisclosurePage() {
  usePageTitle("Disclosure Analyzer");
  const [loading, setLoading] = useState(false);
  const [checklist, setChecklist] = useState<ChecklistItem[] | null>(null);
  const [gaps, setGaps] = useState<GapItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showSource, setShowSource] = useState(false);
  const [sourceText, setSourceText] = useState<string | null>(null);

  // Cross-reference state
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);
  const [crossRefLoading, setCrossRefLoading] = useState(false);
  const [crossRef, setCrossRef] = useState<CrossRefResult | null>(null);
  const [crossRefContractName, setCrossRefContractName] = useState<string | null>(null);
  // Store the last uploaded file so we can re-send it for cross-reference
  const [lastUploadedFile, setLastUploadedFile] = useState<File | null>(null);

  // Fetch contract list on mount for the cross-reference picker
  useEffect(() => {
    const fetchContracts = async () => {
      try {
        const res = await fetch("/api/contracts/list");
        if (!res.ok) return;
        const data = await res.json();
        setContracts(Array.isArray(data?.contracts) ? data.contracts : []);
      } catch { /* optional */ }
    };
    fetchContracts();
  }, []);

  const runAnalysis = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/api/disclosure/analyze", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      let detail = `Disclosure analysis failed with status ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson?.detail) detail = String(errJson.detail);
      } catch { /* not JSON */ }
      throw new Error(detail);
    }

    const data = await res.json();
    const a = data?.analysis;
    if (!a?.items_checked) {
      throw new Error("Disclosure response missing `items_checked` — the AI engine returned an incomplete result.");
    }

    setChecklist(
      a.items_checked.map((ic: Record<string, unknown>) => ({
        item: ic.item as string,
        found: ic.found as boolean,
        detail: (ic.details || ic.detail) as string,
      }))
    );

    const gr = a.gap_report;
    if (gr) {
      const parseGap = (g: unknown, impact: string): GapItem => {
        if (typeof g === "object" && g !== null) {
          const obj = g as Record<string, string>;
          return {
            missing_item: obj.missing_item || obj.gap || "",
            why_required: obj.why_required || "",
            recommendation: obj.recommendation || "",
            impact,
          };
        }
        // Legacy: plain string from old prompt
        return { missing_item: String(g), why_required: "", recommendation: String(g), impact };
      };
      const allGaps = [
        ...(gr.critical_gaps || []).map((g: unknown) => parseGap(g, "Critical")),
        ...(gr.moderate_gaps || []).map((g: unknown) => parseGap(g, "High")),
        ...(gr.minor_gaps || []).map((g: unknown) => parseGap(g, "Medium")),
      ];
      setGaps(allGaps);
    } else {
      setGaps([]);
    }
  };

  const handleFileUpload = async (file: File) => {
    setLoading(true);
    setError(null);
    setChecklist(null);
    setGaps([]);
    setCrossRef(null);
    setLastUploadedFile(file);
    try {
      await runAnalysis(file);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Disclosure analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSampleDisclosure = async () => {
    setLoading(true);
    setError(null);
    setChecklist(null);
    setSourceText(SAMPLE_DISCLOSURE_TEXT);
    setGaps([]);
    setCrossRef(null);

    const blob = new Blob([SAMPLE_DISCLOSURE_TEXT], { type: "text/plain" });
    const file = new File([blob], "sample-pbm-disclosure.txt", { type: "text/plain" });
    setLastUploadedFile(file);
    try {
      await runAnalysis(file);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Disclosure analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const score = checklist
    ? Math.round(
        (checklist.filter((c) => c.found).length / checklist.length) * 100
      )
    : 0;

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Search className="w-7 h-7 text-primary-600" />
          Disclosure Analyzer
        </h1>
        <p className="text-gray-500 mt-1">
          Evaluate PBM disclosure completeness against regulatory requirements
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <FileUpload
          onFileSelect={handleFileUpload}
          label="Upload a PBM disclosure document"
        />
        <div className="mt-4 text-center">
          <button
            onClick={handleSampleDisclosure}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            Analyze Sample Disclosure
          </button>
        </div>
      </div>

      {sourceText && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 mb-6 overflow-hidden">
          <button
            onClick={() => setShowSource(!showSource)}
            className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
              <FileText className="w-4 h-4 text-primary-600" />
              Source Document Being Analyzed
            </div>
            {showSource ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
          </button>
          {showSource && (
            <div className="border-t border-gray-200 p-4 bg-gray-50 max-h-80 overflow-y-auto">
              <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono leading-relaxed">{sourceText}</pre>
            </div>
          )}
        </div>
      )}

      {loading && (
        <AIAnalysisProgress
          variant="disclosure"
          estimatedSeconds={28}
        />
      )}

      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-sm text-amber-700">{error}</p>
        </div>
      )}

      {checklist && !loading && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 flex justify-center">
              <ScoreCircle score={score} label="Completeness Score" size={160} />
            </div>
            <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
                Disclosure Checklist
              </h3>
              <div className="space-y-2">
                {checklist.map((item, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-3 p-3 rounded-lg ${
                      item.found ? "bg-emerald-50" : "bg-red-50"
                    }`}
                  >
                    {item.found ? (
                      <Check className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                    ) : (
                      <X className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p
                        className={`text-sm font-medium ${
                          item.found ? "text-emerald-800" : "text-red-800"
                        }`}
                      >
                        {item.item}
                      </p>
                      <p
                        className={`text-xs mt-0.5 ${
                          item.found ? "text-emerald-600" : "text-red-600"
                        }`}
                      >
                        {item.detail}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {gaps.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
                Gap Report
              </h3>
              <div className="space-y-3">
                {gaps.map((gap, i) => (
                  <div key={i} className={`rounded-lg border p-4 ${
                    gap.impact === "Critical" ? "bg-red-50 border-red-200" : gap.impact === "High" ? "bg-amber-50 border-amber-200" : "bg-blue-50 border-blue-200"
                  }`}>
                    <div className="flex items-start gap-3 mb-2">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold flex-shrink-0 ${
                        gap.impact === "Critical"
                          ? "bg-red-100 text-red-700"
                          : gap.impact === "High"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-blue-100 text-blue-700"
                      }`}>
                        {gap.impact}
                      </span>
                      <p className={`text-sm font-semibold ${
                        gap.impact === "Critical" ? "text-red-900" : gap.impact === "High" ? "text-amber-900" : "text-blue-900"
                      }`}>
                        {gap.missing_item}
                      </p>
                    </div>
                    {gap.why_required && (
                      <p className="text-xs text-gray-600 mb-1.5 ml-8">
                        <span className="font-semibold">Required by:</span> {gap.why_required}
                      </p>
                    )}
                    {gap.recommendation && gap.recommendation !== gap.missing_item && (
                      <p className="text-xs text-gray-700 ml-8">
                        <span className="font-semibold">Action:</span> {gap.recommendation}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ═══ Cross-Reference Against Contract ═══ */}
          {contracts.length > 0 && lastUploadedFile && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">
                Cross-Reference Against a Contract
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Compare this disclosure against a previously analyzed PBM contract to find discrepancies between what the contract promises and what the disclosure reports.
              </p>
              <div className="flex items-end gap-3 flex-wrap">
                <div className="flex-1 min-w-[200px]">
                  <label className="block text-xs font-medium text-gray-700 mb-1">Select contract</label>
                  <select
                    value={selectedContractId ?? ""}
                    onChange={(e) => setSelectedContractId(e.target.value ? Number(e.target.value) : null)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none bg-white"
                  >
                    <option value="">Choose a contract...</option>
                    {contracts.map((c) => {
                      const dateStr = c.analysis_date ? c.analysis_date.split(" ")[0] : "";
                      return (
                        <option key={c.id} value={c.id}>
                          {c.filename} ({dateStr}{c.deal_score !== null ? ` · score ${c.deal_score}` : ""})
                        </option>
                      );
                    })}
                  </select>
                </div>
                <button
                  onClick={async () => {
                    if (!selectedContractId || !lastUploadedFile) return;
                    setCrossRefLoading(true);
                    setCrossRef(null);
                    try {
                      const formData = new FormData();
                      formData.append("file", lastUploadedFile);
                      const res = await fetch(`/api/disclosure/cross-reference?contract_id=${selectedContractId}`, {
                        method: "POST",
                        body: formData,
                      });
                      if (!res.ok) {
                        let detail = `Cross-reference failed with status ${res.status}`;
                        try { const e = await res.json(); if (e?.detail) detail = String(e.detail); } catch {}
                        throw new Error(detail);
                      }
                      const data = await res.json();
                      setCrossRef(data.cross_reference || null);
                      setCrossRefContractName(data.contract_filename || null);
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Cross-reference failed");
                    } finally {
                      setCrossRefLoading(false);
                    }
                  }}
                  disabled={!selectedContractId || crossRefLoading}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
                >
                  {crossRefLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  {crossRefLoading ? "Comparing..." : "Compare"}
                </button>
              </div>
            </div>
          )}

          {crossRefLoading && (
            <AIAnalysisProgress variant="disclosure" estimatedSeconds={30} />
          )}

          {/* Cross-reference results */}
          {crossRef && !crossRefLoading && (
            <div className="space-y-6 mb-6">
              {/* Alignment score */}
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                      Disclosure vs Contract
                    </h3>
                    {crossRefContractName && (
                      <p className="text-xs text-gray-500 mt-0.5">Compared against {crossRefContractName}</p>
                    )}
                  </div>
                  <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${
                    crossRef.overall_alignment_score >= 80
                      ? "bg-emerald-100 text-emerald-800"
                      : crossRef.overall_alignment_score >= 50
                      ? "bg-amber-100 text-amber-800"
                      : "bg-red-100 text-red-800"
                  }`}>
                    {crossRef.overall_alignment_score}% Aligned
                  </div>
                </div>
                {crossRef.summary && (
                  <p className="text-sm text-gray-700">{crossRef.summary}</p>
                )}
              </div>

              {/* Discrepancies */}
              {crossRef.discrepancies && crossRef.discrepancies.length > 0 && (
                <div className="bg-white rounded-xl border-2 border-red-200 shadow-[var(--shadow-card)] overflow-hidden">
                  <div className="px-5 py-3 bg-red-50 border-b border-red-100 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                    <h3 className="text-sm font-bold text-red-900 uppercase tracking-wider">
                      Discrepancies Found ({crossRef.discrepancies.length})
                    </h3>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {crossRef.discrepancies.map((d, i) => (
                      <div key={i} className="px-5 py-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                            d.severity === "high" ? "bg-red-100 text-red-700" : d.severity === "medium" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                          }`}>
                            {d.severity.toUpperCase()}
                          </span>
                          <span className="text-xs text-gray-500">{d.category}</span>
                        </div>
                        <p className="text-sm font-semibold text-gray-900 mb-2">{d.gap}</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-2">
                          <div className="p-3 bg-blue-50 rounded-lg">
                            <p className="text-[11px] font-semibold text-blue-700 uppercase mb-1">Contract says</p>
                            <p className="text-xs text-blue-900">{d.contract_says}</p>
                          </div>
                          <div className="p-3 bg-amber-50 rounded-lg">
                            <p className="text-[11px] font-semibold text-amber-700 uppercase mb-1">Disclosure says</p>
                            <p className="text-xs text-amber-900">{d.disclosure_says}</p>
                          </div>
                        </div>
                        {d.recommendation && (
                          <p className="text-xs text-gray-600">
                            <span className="font-semibold">Action:</span> {d.recommendation}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Confirmations */}
              {crossRef.confirmations && crossRef.confirmations.length > 0 && (
                <div className="bg-white rounded-xl border border-emerald-200 shadow-[var(--shadow-card)] overflow-hidden">
                  <div className="px-5 py-3 bg-emerald-50 border-b border-emerald-100 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <h3 className="text-sm font-bold text-emerald-900 uppercase tracking-wider">
                      Confirmed ({crossRef.confirmations.length})
                    </h3>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {crossRef.confirmations.map((c, i) => (
                      <div key={i} className="px-5 py-3 flex items-start gap-3">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm text-gray-900">{c.contract_says}</p>
                          <p className="text-xs text-emerald-700 mt-0.5">{c.disclosure_confirms}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
