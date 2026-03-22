"use client";

import { useState, useEffect, useRef } from "react";
import FileUpload from "@/components/FileUpload";
import StatusBadge from "@/components/StatusBadge";
import {
  FileText,
  Loader2,
  Sparkles,
  DollarSign,
  BarChart3,
  BookOpen,
  ShieldCheck,
  Tag,
  XCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface ExtractedTerm {
  clause: string;
  value: string;
  status: "good" | "warning" | "critical";
  note: string;
}

const demoTerms: ExtractedTerm[] = [
  { clause: "Rebate Passthrough Guarantee", value: "100% passthrough", status: "good", note: "Industry best practice" },
  { clause: "Spread Pricing Allowance", value: "Not prohibited", status: "critical", note: "No spread pricing ban — PBM may retain spread" },
  { clause: "Audit Rights", value: "Annual, 60-day notice", status: "warning", note: "Industry standard is 30-day notice" },
  { clause: "Mail-Order Mandate", value: "Mandatory after 2 fills", status: "warning", note: "May limit member choice" },
  { clause: "Formulary Change Notice", value: "60 days", status: "good", note: "Meets minimum requirement" },
  { clause: "MAC List Transparency", value: "Not disclosed", status: "critical", note: "No visibility into MAC pricing" },
  { clause: "Performance Guarantees", value: "Generic fill rate >88%", status: "good", note: "Reasonable target" },
  { clause: "Specialty Drug Carve-Out", value: "None specified", status: "critical", note: "Specialty drugs under PBM control" },
  { clause: "Contract Term", value: "3 years, auto-renew", status: "warning", note: "Auto-renewal may limit negotiation leverage" },
  { clause: "Termination Clause", value: "180-day notice", status: "warning", note: "Long notice period favors PBM" },
];

const analyzeCategories = [
  { icon: DollarSign, label: "Rebate Terms", description: "Passthrough guarantees, retention percentages" },
  { icon: BarChart3, label: "Spread Pricing", description: "Ingredient cost vs. plan charge provisions" },
  { icon: BookOpen, label: "Formulary Clauses", description: "Change notice periods, exclusion rights" },
  { icon: ShieldCheck, label: "Audit Rights", description: "Frequency, notice requirements, scope" },
  { icon: Tag, label: "MAC Pricing", description: "List transparency, update frequency, appeals" },
  { icon: XCircle, label: "Termination Provisions", description: "Notice periods, auto-renewal, exit fees" },
];

const SAMPLE_CONTRACT_TEXT = `PHARMACY BENEFIT MANAGEMENT SERVICES AGREEMENT

This Pharmacy Benefit Management Services Agreement ("Agreement") is entered into as of January 1, 2025 ("Effective Date"), by and between MegaCare PBM, Inc., a Delaware corporation ("PBM"), and Heartland Employers Health Coalition ("Plan Sponsor").

ARTICLE 1 — DEFINITIONS

1.1 "Average Wholesale Price" or "AWP" means the average wholesale price of a pharmaceutical product as published by Medi-Span or First Databank.

1.2 "Brand Drug" means a pharmaceutical product marketed under a proprietary, trademark-protected name.

1.3 "Claims" means requests for reimbursement for Covered Drugs dispensed to Members.

1.4 "Covered Drugs" means those pharmaceutical products included in the Formulary and covered under the Plan.

1.5 "Effective Rate" means the aggregate discount from AWP achieved across all Claims within a measurement period.

1.6 "Formulary" means the list of preferred pharmaceutical products established and maintained by PBM's Pharmacy and Therapeutics Committee.

1.7 "Generic Drug" means a pharmaceutical product that is therapeutically equivalent to a Brand Drug and is marketed under its chemical or non-proprietary name.

1.8 "MAC" or "Maximum Allowable Cost" means the maximum amount the PBM will reimburse a pharmacy for a multi-source generic drug.

1.9 "Member" means an individual eligible for benefits under the Plan Sponsor's pharmacy benefit plan.

1.10 "Network Pharmacy" means a pharmacy that has entered into an agreement with PBM to provide pharmaceutical services.

ARTICLE 2 — SERVICES

2.1 Claims Processing. PBM shall process pharmacy Claims electronically through its proprietary claims adjudication system. PBM guarantees a claims processing accuracy rate of not less than 99.0%.

2.2 Formulary Management. PBM shall establish and maintain a Formulary. PBM reserves the right to modify the Formulary at its sole discretion upon sixty (60) days' prior written notice to Plan Sponsor. PBM's Pharmacy and Therapeutics Committee shall meet no less than quarterly to review formulary composition.

2.3 Network Management. PBM shall maintain a national network of retail pharmacies. The network shall include no fewer than 65,000 retail pharmacy locations nationwide.

2.4 Mail-Order Services. PBM shall provide mail-order pharmacy services through its wholly-owned mail service pharmacy. Members shall be required to use mail-order pharmacy for maintenance medications after the second retail fill of any maintenance medication.

2.5 Specialty Pharmacy Services. All specialty medications shall be dispensed exclusively through PBM's specialty pharmacy division. No carve-out provisions shall apply to specialty medications.

ARTICLE 3 — PRICING AND FINANCIAL TERMS

3.1 Brand Drug Pricing. Brand Drug Claims shall be priced at AWP minus fifteen percent (AWP-15%) for retail pharmacy claims and AWP minus eighteen percent (AWP-18%) for mail-order claims, plus a dispensing fee of $1.50 per claim.

3.2 Generic Drug Pricing. Generic Drug Claims shall be priced at the lower of (a) MAC or (b) AWP minus seventy-five percent (AWP-75%) for retail claims, and AWP minus eighty percent (AWP-80%) for mail-order claims.

3.3 MAC List. PBM shall maintain and administer a Maximum Allowable Cost list. The MAC list shall not be disclosed to Plan Sponsor. PBM shall update the MAC list at its sole discretion. Plan Sponsor shall have no right to review, audit, or challenge individual MAC prices.

3.4 Spread Pricing. PBM shall retain any difference between the amount charged to Plan Sponsor and the amount reimbursed to Network Pharmacies as compensation for services. This spread shall not be subject to disclosure, audit, or reconciliation.

3.5 Dispensing Fees. Retail dispensing fees shall not exceed $1.50 per claim. Mail-order dispensing fees shall not exceed $0.00 per claim.

3.6 Administrative Fees. Plan Sponsor shall pay PBM an administrative fee of $4.25 per member per month (PMPM).

ARTICLE 4 — REBATES

4.1 Manufacturer Rebates. PBM shall use commercially reasonable efforts to negotiate manufacturer rebates on behalf of Plan Sponsor.

4.2 Rebate Passthrough. PBM guarantees to pass through one hundred percent (100%) of all manufacturer rebates received by PBM that are attributable to Plan Sponsor's Claims.

4.3 Rebate Timing. Rebates shall be reported and remitted to Plan Sponsor within ninety (90) days following the end of each calendar quarter.

4.4 Rebate Definition. For purposes of this Agreement, "rebates" shall mean only those payments specifically designated as "rebates" by pharmaceutical manufacturers. Administrative fees, service fees, data fees, market share incentives, price protection payments, and other manufacturer payments shall not be considered rebates and shall be retained by PBM.

ARTICLE 5 — PERFORMANCE GUARANTEES

5.1 Generic Dispensing Rate. PBM guarantees a Generic Dispensing Rate of not less than eighty-eight percent (88%) measured on a calendar year basis.

5.2 Brand Effective Rate. PBM guarantees a Brand Effective Rate discount of not less than AWP minus seventeen percent (AWP-17%) measured on a calendar year basis across all retail brand claims.

5.3 Generic Effective Rate. PBM guarantees a Generic Effective Rate discount of not less than AWP minus eighty percent (AWP-80%) measured on a calendar year basis across all retail generic claims.

5.4 Measurement and Reconciliation. Performance guarantees shall be measured annually. Any shortfall shall be credited to Plan Sponsor within sixty (60) days of the measurement period. Specialty drug claims shall be excluded from all guarantee calculations.

ARTICLE 6 — AUDIT RIGHTS

6.1 Audit Frequency. Plan Sponsor shall have the right to conduct one (1) audit per contract year.

6.2 Audit Notice. Plan Sponsor shall provide PBM with no less than sixty (60) days' prior written notice of its intent to conduct an audit.

6.3 Audit Scope. Audits shall be limited to verification of pricing and rebate terms. Audits shall not include review of PBM's contracts with pharmaceutical manufacturers, pharmacy network agreements, or internal cost structures.

6.4 Audit Costs. All costs associated with any audit shall be borne solely by Plan Sponsor.

ARTICLE 7 — TERM AND TERMINATION

7.1 Initial Term. This Agreement shall have an initial term of three (3) years commencing on the Effective Date.

7.2 Renewal. This Agreement shall automatically renew for successive one (1) year periods unless either party provides written notice of non-renewal at least one hundred eighty (180) days prior to the expiration of the then-current term.

7.3 Termination for Cause. Either party may terminate this Agreement upon ninety (90) days' written notice if the other party materially breaches any provision and fails to cure within sixty (60) days of receipt of written notice.

7.4 Termination Fee. In the event Plan Sponsor terminates this Agreement prior to the expiration of the initial term for any reason other than PBM's uncured material breach, Plan Sponsor shall pay PBM a termination fee equal to twelve (12) months of administrative fees.

7.5 Transition Assistance. Upon termination or expiration, PBM shall provide transition assistance for a period of ninety (90) days. PBM shall charge Plan Sponsor its standard hourly consulting rate for transition assistance services.

ARTICLE 8 — CONFIDENTIALITY

8.1 All terms of this Agreement, including pricing, rebate guarantees, and performance metrics, shall be considered Confidential Information and shall not be disclosed by either party without the prior written consent of the other party.

ARTICLE 9 — LIMITATION OF LIABILITY

9.1 IN NO EVENT SHALL PBM'S AGGREGATE LIABILITY UNDER THIS AGREEMENT EXCEED THE TOTAL ADMINISTRATIVE FEES PAID BY PLAN SPONSOR DURING THE TWELVE (12) MONTH PERIOD PRECEDING THE EVENT GIVING RISE TO LIABILITY.

ARTICLE 10 — GOVERNING LAW

10.1 This Agreement shall be governed by the laws of the State of Delaware without regard to conflicts of law principles.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date.

MegaCare PBM, Inc.
By: ___________________________
Name: James R. Harrison
Title: Chief Executive Officer

Heartland Employers Health Coalition
By: ___________________________
Name: Sarah M. Chen
Title: Executive Director`;

function mapApiToTerms(a: Record<string, Record<string, unknown>>): ExtractedTerm[] {
  const labels: Record<string, string> = {
    rebate_passthrough: "Rebate Passthrough Guarantee",
    spread_pricing: "Spread Pricing Allowance",
    audit_rights: "Audit Rights",
    formulary_clauses: "Formulary Management",
    mac_pricing: "MAC List Transparency",
    termination_provisions: "Termination Provisions",
    gag_clauses: "Gag Clause Provisions",
  };
  const terms: ExtractedTerm[] = [];
  for (const [key, val] of Object.entries(a)) {
    if (!val || typeof val !== "object" || key === "compliance_flags" || key === "overall_risk_score" || key === "summary") continue;
    const details = ((val.details as string) || "").toLowerCase();
    const hasIssue = details.includes("no ") || details.includes("not ") || details.includes("concern") || details.includes("narrow") || details.includes("limit") || details.includes("restrict") || details.includes("proprietary") || details.includes("retain");
    const isCritical = details.includes("significant") || details.includes("narrow") || details.includes("proprietary") || details.includes("no transparency") || details.includes("no requirement");
    const extractedValue = (val.percentage || val.caps || (val.change_notification_days ? val.change_notification_days + " days" : null) || val.scope || val.notice_period || (val.found ? "Found" : "Not found")) as string;
    terms.push({
      clause: labels[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      value: extractedValue,
      status: isCritical ? "critical" : hasIssue ? "warning" : "good",
      note: (val.details as string) || "",
    });
  }
  return terms.length > 0 ? terms : [];
}

export default function ContractsPage() {
  const [loading, setLoading] = useState(false);
  const [terms, setTerms] = useState<ExtractedTerm[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSource, setShowSource] = useState(false);
  const [sourceText, setSourceText] = useState<string | null>(null);
  const hasAutoLoaded = useRef(false);

  const processResponse = (data: Record<string, unknown>) => {
    const a = data?.analysis as Record<string, Record<string, unknown>> | undefined;
    if (a && a.rebate_passthrough) {
      setTerms(mapApiToTerms(a));
    } else {
      setTerms((data.terms as ExtractedTerm[]) || demoTerms);
    }
  };

  const handleFileUpload = async (file: File) => {
    setLoading(true);
    setError(null);
    setTerms(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/contracts/upload", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      processResponse(data);
    } catch {
      setTerms(demoTerms);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!hasAutoLoaded.current) {
      hasAutoLoaded.current = true;
      handleSampleContract();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSampleContract = async () => {
    setLoading(true);
    setError(null);
    setTerms(null);
    setSourceText(SAMPLE_CONTRACT_TEXT);

    const blob = new Blob([SAMPLE_CONTRACT_TEXT], { type: "text/plain" });
    const file = new File([blob], "sample-pbm-contract.txt", { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/contracts/upload", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      processResponse(data);
    } catch {
      setTerms(demoTerms);
    } finally {
      setLoading(false);
    }
  };

  const complianceCount = terms
    ? {
        good: terms.filter((t) => t.status === "good").length,
        warning: terms.filter((t) => t.status === "warning").length,
        critical: terms.filter((t) => t.status === "critical").length,
      }
    : null;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <FileText className="w-7 h-7 text-[#1e3a5f]" />
          Contract Intake &amp; Parsing
        </h1>
        <p className="text-gray-500 mt-1">
          Upload a PBM contract to extract and analyze key terms
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <FileUpload
          onFileSelect={handleFileUpload}
          label="Upload a PBM contract (PDF, DOC, or TXT)"
        />
        <div className="mt-4 text-center">
          <button
            onClick={handleSampleContract}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#1e3a5f] text-white rounded-lg hover:bg-[#2a4f7f] transition-colors text-sm font-medium disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            Analyze Sample Contract
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
              Source Contract Being Analyzed
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

      {!terms && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
            What We Analyze
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {analyzeCategories.map((cat) => (
              <div
                key={cat.label}
                className="flex items-start gap-3 p-4 rounded-lg bg-gray-50 border border-gray-100"
              >
                <cat.icon className="w-5 h-5 text-[#1e3a5f] flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-gray-900">{cat.label}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{cat.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-[#1e3a5f] animate-spin" />
          <p className="text-sm text-gray-500">Analyzing contract terms...</p>
        </div>
      )}

      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-sm text-amber-700">{error}</p>
        </div>
      )}

      {terms && !loading && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-emerald-700">
                {complianceCount!.good}
              </p>
              <p className="text-sm text-emerald-600">Compliant</p>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-amber-700">
                {complianceCount!.warning}
              </p>
              <p className="text-sm text-amber-600">Review Needed</p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-red-700">
                {complianceCount!.critical}
              </p>
              <p className="text-sm text-red-600">Non-Compliant</p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Contract Clause
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Extracted Value
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Note
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {terms.map((term, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {term.clause}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {term.value}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge
                        status={term.status}
                        label={
                          term.status === "good"
                            ? "Compliant"
                            : term.status === "warning"
                            ? "Review"
                            : "Non-Compliant"
                        }
                      />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {term.note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
