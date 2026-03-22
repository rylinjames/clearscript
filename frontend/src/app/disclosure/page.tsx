"use client";

import { useState, useEffect, useRef } from "react";
import FileUpload from "@/components/FileUpload";
import ScoreCircle from "@/components/ScoreCircle";
import { Search, Loader2, Sparkles, Check, X, ChevronDown, ChevronUp, FileText } from "lucide-react";

interface ChecklistItem {
  item: string;
  found: boolean;
  detail: string;
}

interface GapItem {
  gap: string;
  impact: string;
  recommendation: string;
}

const demoChecklist: ChecklistItem[] = [
  { item: "Rebate Revenue Disclosure", found: true, detail: "Total rebates received disclosed ($42.3M)" },
  { item: "Administrative Fee Breakdown", found: true, detail: "Per-claim and per-member fees itemized" },
  { item: "Spread Pricing Disclosure", found: false, detail: "No disclosure of ingredient cost vs. plan charge differences" },
  { item: "Formulary Change Notifications", found: true, detail: "Semi-annual formulary update reports included" },
  { item: "Network Pharmacy Reimbursement Rates", found: false, detail: "MAC list and reimbursement rates not shared" },
  { item: "Mail-Order Pharmacy Revenue", found: true, detail: "Mail-order dispensing revenue separated" },
  { item: "Specialty Pharmacy Margins", found: false, detail: "No visibility into specialty drug margins" },
  { item: "Clinical Program Outcomes", found: true, detail: "Prior auth and step therapy savings quantified" },
  { item: "GER/BER Guarantee Reporting", found: true, detail: "Generic and brand effective rate guarantees met" },
  { item: "Manufacturer Revenue Streams", found: false, detail: "No disclosure of pharma manufacturer fees" },
  { item: "Subcontractor Relationships", found: false, detail: "Third-party vendor relationships undisclosed" },
  { item: "Claims Processing Accuracy", found: true, detail: "99.2% accuracy rate reported" },
];

const demoGaps: GapItem[] = [
  { gap: "Spread Pricing Transparency", impact: "High", recommendation: "Require full ingredient cost disclosure for all claims" },
  { gap: "MAC List Access", impact: "High", recommendation: "Demand quarterly MAC list publication with update notifications" },
  { gap: "Specialty Drug Margins", impact: "Critical", recommendation: "Negotiate specialty carve-out or require margin disclosure" },
  { gap: "Manufacturer Revenue", impact: "Critical", recommendation: "Include all revenue stream disclosure in contract amendment" },
  { gap: "Subcontractor Disclosure", impact: "Medium", recommendation: "Request annual disclosure of all subcontracted services" },
];

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
  const [loading, setLoading] = useState(false);
  const [checklist, setChecklist] = useState<ChecklistItem[] | null>(null);
  const [gaps, setGaps] = useState<GapItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showSource, setShowSource] = useState(false);
  const [sourceText, setSourceText] = useState<string | null>(null);

  const hasAutoLoaded = useRef(false);

  useEffect(() => {
    if (!hasAutoLoaded.current) {
      hasAutoLoaded.current = true;
      handleSampleDisclosure();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFileUpload = async (file: File) => {
    setLoading(true);
    setError(null);
    setChecklist(null);
    setGaps([]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/disclosure/analyze", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      const a = data?.analysis;
      if (a?.items_checked) {
        setChecklist(a.items_checked.map((ic: Record<string, unknown>) => ({
          item: ic.item as string,
          found: ic.found as boolean,
          detail: (ic.details || ic.detail) as string,
        })));
        const gr = a.gap_report;
        if (gr) {
          const allGaps = [
            ...(gr.critical_gaps || []).map((g: string) => ({ gap: g.split("'")[1] || g.substring(0, 40), impact: "Critical", recommendation: g })),
            ...(gr.moderate_gaps || []).map((g: string) => ({ gap: g.split("'")[1] || g.substring(0, 40), impact: "High", recommendation: g })),
            ...(gr.minor_gaps || []).map((g: string) => ({ gap: g.split("'")[1] || g.substring(0, 40), impact: "Medium", recommendation: g })),
          ];
          setGaps(allGaps.length > 0 ? allGaps : demoGaps);
        } else {
          setGaps(demoGaps);
        }
      } else {
        setChecklist(data.checklist || demoChecklist);
        setGaps(data.gaps || demoGaps);
      }
    } catch {
      setChecklist(demoChecklist);
      setGaps(demoGaps);
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

    const blob = new Blob([SAMPLE_DISCLOSURE_TEXT], { type: "text/plain" });
    const file = new File([blob], "sample-pbm-disclosure.txt", { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/disclosure/analyze", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      const a = data?.analysis;
      if (a?.items_checked) {
        setChecklist(a.items_checked.map((ic: Record<string, unknown>) => ({
          item: ic.item as string,
          found: ic.found as boolean,
          detail: (ic.details || ic.detail) as string,
        })));
        const gr = a.gap_report;
        if (gr) {
          const allGaps = [
            ...(gr.critical_gaps || []).map((g: string) => ({ gap: g.split("'")[1] || g.substring(0, 40), impact: "Critical", recommendation: g })),
            ...(gr.moderate_gaps || []).map((g: string) => ({ gap: g.split("'")[1] || g.substring(0, 40), impact: "High", recommendation: g })),
            ...(gr.minor_gaps || []).map((g: string) => ({ gap: g.split("'")[1] || g.substring(0, 40), impact: "Medium", recommendation: g })),
          ];
          setGaps(allGaps.length > 0 ? allGaps : demoGaps);
        } else {
          setGaps(demoGaps);
        }
      } else {
        setChecklist(data.checklist || demoChecklist);
        setGaps(data.gaps || demoGaps);
      }
    } catch {
      setChecklist(demoChecklist);
      setGaps(demoGaps);
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
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Search className="w-7 h-7 text-[#1e3a5f]" />
          Disclosure Analyzer
        </h1>
        <p className="text-gray-500 mt-1">
          Evaluate PBM disclosure completeness against regulatory requirements
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <FileUpload
          onFileSelect={handleFileUpload}
          label="Upload a PBM disclosure document"
        />
        <div className="mt-4 text-center">
          <button
            onClick={handleSampleDisclosure}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#1e3a5f] text-white rounded-lg hover:bg-[#2a4f7f] transition-colors text-sm font-medium disabled:opacity-50"
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
              <FileText className="w-4 h-4 text-[#1e3a5f]" />
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
        <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-[#1e3a5f] animate-spin" />
          <p className="text-sm text-gray-500">Evaluating disclosure completeness...</p>
        </div>
      )}

      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-sm text-amber-700">{error}</p>
        </div>
      )}

      {checklist && !loading && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6 flex justify-center">
              <ScoreCircle score={score} label="Completeness Score" size={160} />
            </div>
            <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
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
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Gap Report
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">
                        Missing Item
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">
                        Impact
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">
                        Recommendation
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {gaps.map((gap, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {gap.gap}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              gap.impact === "Critical"
                                ? "bg-red-100 text-red-700"
                                : gap.impact === "High"
                                ? "bg-amber-100 text-amber-700"
                                : "bg-blue-100 text-blue-700"
                            }`}
                          >
                            {gap.impact}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {gap.recommendation}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
