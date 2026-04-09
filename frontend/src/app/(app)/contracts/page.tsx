"use client";

import { useState } from "react";
import Link from "next/link";
import { usePageTitle } from "@/components/PageTitle";
import FileUpload from "@/components/FileUpload";
import StatusBadge from "@/components/StatusBadge";
import DataSourceBanner from "@/components/DataSourceBanner";
import AIAnalysisProgress from "@/components/AIAnalysisProgress";
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
  AlertTriangle,
  Scale,
  CheckCircle2,
  XCircle as XCircleIcon,
  Download,
  Mail,
  Copy,
  Check,
} from "lucide-react";

interface ExtractedTerm {
  clause: string;
  value: string;
  status: "good" | "warning" | "critical";
  note: string;
}

interface AuditChecklistItem {
  item: string;
  found: boolean;
  details?: string;
}

interface EligibleRebateDefinition {
  narrow_definition_flag: boolean;
  excludes_admin_fees?: boolean;
  excludes_volume_bonuses?: boolean;
  excludes_price_protection?: boolean;
  details?: string;
}

interface DisputeResolution {
  mechanism: string;
  details?: string;
  risk_level?: string;
}

interface AnalysisExtras {
  audit_rights?: {
    checklist?: AuditChecklistItem[];
    [key: string]: unknown;
  };
  eligible_rebate_definition?: EligibleRebateDefinition;
  dispute_resolution?: DisputeResolution;
  statistical_extrapolation_rights?: {
    found: boolean;
    details?: string;
  };
  statistical_extrapolation?: {
    found: boolean;
    details?: string;
  };
  [key: string]: unknown;
}

interface PlanBenefits {
  plan_info?: { plan_name?: string; carrier?: string; plan_type?: string; effective_date?: string; coverage_period?: string };
  deductible?: Record<string, string | null>;
  out_of_pocket_maximum?: Record<string, string | null>;
  copays?: Record<string, string | null>;
  coinsurance?: Record<string, string | null>;
  prescription_drugs?: Record<string, unknown>;
  hospital_services?: Record<string, string | null>;
  exclusions_and_limits?: string[];
  other_benefits?: Record<string, string | null>;
  confidence_score?: number;
  _generated_by?: string;
}

interface CrossRefFinding {
  category: string;
  finding: string;
  severity: "high" | "medium" | "low";
  contract_says: string;
  plan_doc_says: string;
  recommendation: string;
}

interface CrossRefResult {
  summary: string;
  overall_alignment_score: number;
  findings: CrossRefFinding[];
  action_items?: { priority: string; action: string; reason: string }[];
  missing_from_contract?: string[];
  missing_from_plan_doc?: string[];
  _generated_by?: string;
}

interface WeightedAssessment {
  deal_score?: number;
  weighted_risk_score?: number;
  risk_level?: string;
  methodology?: string;
  tier_scores?: { tier: string; score: number; weight: number }[];
}

interface TopRisk {
  title: string;
  tier: number;
  severity: "high" | "medium" | "low";
  why_it_matters: string;
  recommendation: string;
}

interface FinancialExposureEntry {
  level: string;
  estimate: string;
  driver: string;
  // Dollar-denominated estimates added by the backend's
  // _attach_dollar_exposure helper. Present whenever the backend has
  // either real uploaded claims or the synthetic sample dataset to
  // multiply the percentage range against.
  dollar_estimate_low?: number;
  dollar_estimate_high?: number;
  dollar_denominator?: number;
  dollar_denominator_label?: string;
  dollar_estimate_basis?: "uploaded_claims" | "synthetic_sample";
}

interface FinancialExposure {
  mode?: string;
  summary?: string;
  rebate_leakage?: FinancialExposureEntry;
  spread_exposure?: FinancialExposureEntry;
  specialty_control?: FinancialExposureEntry;
  claims_context?: {
    claims_count?: number;
    claims_filename?: string;
    date_range_start?: string;
    date_range_end?: string;
    custom_data_loaded?: boolean;
    total_plan_paid?: number;
    brand_spend?: number;
    specialty_spend?: number;
  };
}

// Format a dollar amount as "$420k" for >$1k or "$420" for less.
// Used by the dollar-denominated leakage display.
function formatUsdShort(n: number | undefined | null): string {
  if (n == null || !isFinite(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${Math.round(n / 1_000)}k`;
  return `$${Math.round(n)}`;
}

interface ControlMapItem {
  lever: string;
  controller: string;
  assessment: string;
  implication: string;
}

interface ControlPosture {
  label: string;
  level: string;
  headline: string;
  summary: string;
  pbm_controlled_levers?: number;
  shared_levers?: number;
}

interface StructuralRiskOverride {
  triggered: boolean;
  level: string;
  minimum_weighted_risk_score?: number;
  drivers?: string[];
  headline: string;
  rationale: string;
}

interface BenchmarkObservation {
  kind: "strength" | "consideration";
  title: string;
  category: string;
  tier: number;
  severity: "high" | "medium" | "low";
  benchmark_label: string;
  benchmark: string;
  benchmark_source: string;
  observation: string;
  implication: string;
  recommendation: string;
  supporting_detail?: string | null;
}

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

// Allow-list of contract clause keys that get rendered as rows in the
// extracted terms table. Anything not in this list is treated as
// post-processing metadata (control_map, top_risks, immediate_actions,
// benchmark_observations, weighted_assessment, redline_suggestions,
// financial_exposure, structural_risk_override, control_posture, etc.)
// and rendered by its own dedicated section elsewhere on the page.
//
// audit_rights is intentionally excluded — it has the eleven-point
// dedicated audit-rights scorecard rendered below (auditChecklist).
//
// IMPORTANT: this list must be a whitelist, not a blacklist. The
// previous implementation looped over every key in the analysis JSON
// and skipped a hardcoded blacklist; every time enrich_contract_analysis
// or the AI prompt added a new top-level field, that field would show
// up as a phantom "Not found" row in the table. Whitelist iteration
// is future-proof against that whole class of bug.
const CLAUSE_LABELS: Record<string, string> = {
  rebate_passthrough: "Rebate Passthrough",
  spread_pricing: "Spread Pricing",
  formulary_clauses: "Formulary Management",
  mac_pricing: "MAC Pricing",
  termination_provisions: "Termination Provisions",
  gag_clauses: "Gag Clauses",
  specialty_channel: "Specialty Channel Control",
};

function mapApiToTerms(a: Record<string, Record<string, unknown>>): ExtractedTerm[] {
  const terms: ExtractedTerm[] = [];
  // Iterate the whitelist, not the analysis object — guarantees we
  // only ever try to render real contract clauses.
  for (const key of Object.keys(CLAUSE_LABELS)) {
    const val = a[key];
    if (!val || typeof val !== "object") continue;
    // Use favorability from AI if available, fall back to heuristic
    const favorability = (val.favorability as string) || "";
    let status: "good" | "warning" | "critical";
    if (favorability === "employer_favorable") {
      status = "good";
    } else if (favorability === "neutral") {
      status = "warning";
    } else if (favorability === "pbm_favorable") {
      status = "critical";
    } else {
      // Fallback heuristic
      const details = ((val.details as string) || "").toLowerCase();
      const hasIssue = details.includes("no ") || details.includes("not ") || details.includes("concern") || details.includes("narrow") || details.includes("limit") || details.includes("restrict") || details.includes("retain");
      status = hasIssue ? "critical" : "good";
    }
    const extractedValue = (val.percentage || val.effective_passthrough || val.caps || (val.change_notification_days ? val.change_notification_days + " days" : null) || val.scope || val.notice_period || (val.notice_days ? val.notice_days + " days" : null) || val.mechanism || (val.found ? "Found" : "Not found")) as string;
    terms.push({
      clause: CLAUSE_LABELS[key],
      value: extractedValue,
      status,
      note: (val.details as string) || "",
    });
  }
  return terms;
}

function riskLevelStyles(level?: string) {
  if (level === "high") return "bg-red-50 border-red-200 text-red-700";
  if (level === "low") return "bg-emerald-50 border-emerald-200 text-emerald-700";
  return "bg-amber-50 border-amber-200 text-amber-700";
}

function riskBadgeStyles(level?: string) {
  if (level === "high") return "bg-red-100 text-red-800";
  if (level === "low") return "bg-emerald-100 text-emerald-800";
  return "bg-amber-100 text-amber-800";
}

function observationKindStyles(kind?: string) {
  if (kind === "strength") return "bg-emerald-100 text-emerald-800";
  return "bg-amber-100 text-amber-800";
}

function formatRiskLevel(level?: string) {
  return (level || "moderate").replace(/^\w/, (c) => c.toUpperCase());
}

export default function ContractsPage() {
  usePageTitle("Contract Intake");
  const [loading, setLoading] = useState(false);
  const [terms, setTerms] = useState<ExtractedTerm[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSource, setShowSource] = useState(false);
  const [sourceText, setSourceText] = useState<string | null>(null);

  // New analysis extras state
  const [auditChecklist, setAuditChecklist] = useState<AuditChecklistItem[] | null>(null);
  const [rebateDefinition, setRebateDefinition] = useState<EligibleRebateDefinition | null>(null);
  const [disputeResolution, setDisputeResolution] = useState<DisputeResolution | null>(null);
  const [statisticalExtrapolation, setStatisticalExtrapolation] = useState<{ found: boolean; details?: string } | null>(null);

  // Step 2: Plan document state
  const [planBenefits, setPlanBenefits] = useState<PlanBenefits | null>(null);
  const [planDocType, setPlanDocType] = useState<string | null>(null);
  const [planLoading, setPlanLoading] = useState(false);

  // Step 3: Cross-reference state
  const [crossRef, setCrossRef] = useState<CrossRefResult | null>(null);
  const [crossRefLoading, setCrossRefLoading] = useState(false);

  // Store raw contract analysis for cross-reference
  const [rawContractAnalysis, setRawContractAnalysis] = useState<Record<string, unknown> | null>(null);

  // PDF export state
  const [exporting, setExporting] = useState(false);
  const [contractFilename, setContractFilename] = useState<string>("contract");
  // SQLite/Postgres primary key for the most recently uploaded contract,
  // returned by /api/contracts/upload. Used to deep-link the audit-letter
  // generator at /audit?contract_id={id} so the user can draft a letter
  // against this exact contract instead of re-picking it from a dropdown.
  const [contractRowId, setContractRowId] = useState<number | null>(null);
  // Index of the redline whose suggested language was just copied to the
  // clipboard, so we can show a "Copied" success state for ~1.5 seconds.
  // null means nothing was copied recently.
  const [copiedRedline, setCopiedRedline] = useState<number | null>(null);

  const copyRedline = async (idx: number, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedRedline(idx);
      window.setTimeout(() => setCopiedRedline((prev) => (prev === idx ? null : prev)), 1500);
    } catch {
      // If clipboard write fails (rare — usually a permissions issue
      // in an iframe or insecure context), do nothing. The button just
      // doesn't show the success state.
    }
  };

  const loadExtras = (a: AnalysisExtras) => {
    if (a.audit_rights?.checklist) {
      setAuditChecklist(a.audit_rights.checklist);
    }
    if (a.eligible_rebate_definition) {
      setRebateDefinition(a.eligible_rebate_definition);
    }
    if (a.dispute_resolution) {
      setDisputeResolution(a.dispute_resolution);
    }
    if (a.statistical_extrapolation_rights) {
      setStatisticalExtrapolation(a.statistical_extrapolation_rights);
    } else if (a.statistical_extrapolation) {
      setStatisticalExtrapolation(a.statistical_extrapolation);
    }
  };

  const processResponse = (data: Record<string, unknown>) => {
    // Capture the contract row id (returned by /api/contracts/upload)
    // so the "Draft Audit Letter" button can deep-link to the audit
    // page with this specific contract preselected.
    if (typeof data?.id === "number") {
      setContractRowId(data.id as number);
    } else {
      setContractRowId(null);
    }
    const a = data?.analysis as AnalysisExtras | undefined;
    if (a && a.rebate_passthrough) {
      setTerms(mapApiToTerms(a as Record<string, Record<string, unknown>>));
      loadExtras(a);
      setRawContractAnalysis(a as Record<string, unknown>);
    } else {
      // The backend returned success but the analysis shape is missing
      // rebate_passthrough — this usually means the AI response was truncated
      // or malformed. Surface it rather than quietly showing a fake analysis.
      throw new Error(
        "Analysis response was incomplete. The AI engine returned a result " +
        "without the expected fields. Please retry — if it persists, the " +
        "AI service may be degraded."
      );
    }
  };

  const handlePlanDocUpload = async (file: File) => {
    setPlanLoading(true);
    setPlanBenefits(null);
    setPlanDocType(null);
    setCrossRef(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/contracts/upload-plan-document", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        let detail = `Plan document upload failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      const data = await res.json();
      setPlanBenefits(data.benefits as PlanBenefits);
      setPlanDocType(data.document_type);

      // Auto-trigger cross-reference if we have both contract and plan data
      if (rawContractAnalysis && data.benefits) {
        runCrossReference(rawContractAnalysis, data.benefits);
      }
    } catch (e) {
      setPlanBenefits(null);
      setError(e instanceof Error ? e.message : "Plan document upload failed");
    } finally {
      setPlanLoading(false);
    }
  };

  const runCrossReference = async (contractData: Record<string, unknown>, planData: unknown) => {
    setCrossRefLoading(true);
    try {
      const res = await fetch("/api/contracts/cross-reference", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contract_analysis: contractData,
          plan_benefits: planData,
        }),
      });
      if (!res.ok) {
        let detail = `Cross-reference failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      const data = await res.json();
      setCrossRef(data.cross_reference as CrossRefResult);
    } catch (e) {
      setCrossRef(null);
      setError(e instanceof Error ? e.message : "Cross-reference failed");
    } finally {
      setCrossRefLoading(false);
    }
  };

  const handleExportPDF = async () => {
    setError(null);
    if (!rawContractAnalysis) {
      // Used to silently `return` here, which made the export button feel
      // broken when clicked before an upload had completed. Surface it.
      setError(
        "There is no analysis to export yet. Upload a PBM contract first, " +
        "wait for the analysis to finish, then click Export PDF Report."
      );
      return;
    }
    setExporting(true);
    try {
      const res = await fetch("/api/contracts/export-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: contractFilename,
          analysis: rawContractAnalysis,
          audit_rights_benchmark: auditChecklist ? { provisions: auditChecklist.map(c => ({ item: c.item, present: c.found, details: c.details })), score: auditChecklist.filter(c => c.found).length * 9, grade: auditChecklist.filter(c => c.found).length >= 8 ? "A" : auditChecklist.filter(c => c.found).length >= 6 ? "B" : "C", assessment: `${auditChecklist.filter(c => c.found).length} of ${auditChecklist.length} audit rights found` } : undefined,
          plan_benefits: planBenefits || undefined,
          cross_reference: crossRef || undefined,
        }),
      });
      if (!res.ok) {
        // Pull the real FastAPI detail out of the body so the user sees
        // why the export failed instead of a generic "Export failed".
        let detail = `PDF export failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON — body was probably the PDF or empty */ }
        throw new Error(detail);
      }
      const blob = await res.blob();
      if (blob.size === 0) {
        throw new Error("PDF export returned an empty file. The backend may have failed to render the report.");
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ClearScript_Report_${(contractFilename || "PBM_Contract").replace(/\.[^.]+$/, "")}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF export failed:", err);
      setError(err instanceof Error ? err.message : "PDF export failed");
    } finally {
      setExporting(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    setLoading(true);
    setError(null);
    setTerms(null);
    setAuditChecklist(null);
    setRebateDefinition(null);
    setContractFilename(file.name);
    setDisputeResolution(null);
    setStatisticalExtrapolation(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/contracts/upload", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        // Try to pull the real error detail out of the FastAPI response body
        // so the user sees "AI contract analysis is currently unavailable: ..."
        // instead of a generic "Upload failed".
        let detail = `Upload failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      const data = await res.json();
      processResponse(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSampleContract = async () => {
    setLoading(true);
    setError(null);
    setTerms(null);
    setSourceText(SAMPLE_CONTRACT_TEXT);
    setAuditChecklist(null);
    setRebateDefinition(null);
    setDisputeResolution(null);
    setStatisticalExtrapolation(null);

    const blob = new Blob([SAMPLE_CONTRACT_TEXT], { type: "text/plain" });
    const file = new File([blob], "sample-pbm-contract.txt", { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/contracts/upload", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        let detail = `Upload failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      const data = await res.json();
      processResponse(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
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

  const weightedAssessment = (rawContractAnalysis?.weighted_assessment as WeightedAssessment | undefined) || undefined;
  const topRisks = ((rawContractAnalysis?.top_risks as TopRisk[] | undefined) || []).slice(0, 3);
  const financialExposure = (rawContractAnalysis?.financial_exposure as FinancialExposure | undefined) || undefined;
  const controlMap = ((rawContractAnalysis?.control_map as ControlMapItem[] | undefined) || []).slice(0, 5);
  const controlPosture = (rawContractAnalysis?.control_posture as ControlPosture | undefined) || undefined;
  const structuralRiskOverride = (rawContractAnalysis?.structural_risk_override as StructuralRiskOverride | undefined) || undefined;
  // Show every benchmark observation the model produced, sorted by tier
  // (Tier 1 economics first) then severity (high before medium/low),
  // with a dedup pass that drops duplicate (category, tier) cards.
  // Even after the backend dedup in _derive_benchmark_observations, the
  // AI itself sometimes generates two cards for the same Tier 1 Rebates
  // slot with slightly different observation text but identical
  // recommendation. The frontend dedup is the belt-and-suspenders
  // backstop so the user never sees the same finding twice.
  const SEVERITY_RANK: Record<string, number> = { high: 0, medium: 1, low: 2 };
  const benchmarkObservations = (() => {
    const raw = (rawContractAnalysis?.benchmark_observations as BenchmarkObservation[] | undefined) || [];
    const sorted = raw.slice().sort((a, b) => {
      const tierDiff = (a.tier ?? 99) - (b.tier ?? 99);
      if (tierDiff !== 0) return tierDiff;
      return (SEVERITY_RANK[a.severity] ?? 9) - (SEVERITY_RANK[b.severity] ?? 9);
    });
    const seen = new Set<string>();
    const out: BenchmarkObservation[] = [];
    for (const obs of sorted) {
      // Dedup key: category + tier + first 5 words of recommendation.
      // Two cards saying "Tie passthrough guarantees..." and "Expand
      // the definition of eligible rebates..." for the same Tier 1
      // Rebates slot get coalesced into the highest-severity one.
      const recPrefix = (obs.recommendation || "").trim().split(/\s+/).slice(0, 5).join(" ").toLowerCase();
      const key = `${obs.category || ""}::${obs.tier ?? "?"}::${recPrefix}`;
      // For different recommendation prefixes within the same (category,
      // tier), still allow both — the user might genuinely have two
      // distinct issues in the same tier.
      const slotKey = `${obs.category || ""}::${obs.tier ?? "?"}`;
      if (seen.has(key) || seen.has(slotKey)) continue;
      seen.add(key);
      seen.add(slotKey);
      out.push(obs);
    }
    return out;
  })();
  // All immediate actions from the contract analysis. Used to be sliced to
  // 3 and tucked into a sidebar subhead — now rendered as a top-level panel
  // right under the deal-score metric cards so it's the second thing the
  // user sees, regardless of whether they uploaded a plan document.
  const immediateActions = (rawContractAnalysis?.immediate_actions as string[] | undefined) || [];
  const linkedFindings = ((rawContractAnalysis?.linked_findings as Array<Record<string, string>> | undefined) || []).slice(0, 3);
  const dealDiagnosis = (rawContractAnalysis?.deal_diagnosis as string | undefined) || (rawContractAnalysis?.summary as string | undefined) || null;
  const auditImplication = (rawContractAnalysis?.audit_implication as string | undefined) || null;

  const disputeRiskColor = (level?: string) => {
    if (level === "high") return "text-red-700 bg-red-50 border-red-200";
    if (level === "low") return "text-emerald-700 bg-emerald-50 border-emerald-200";
    return "text-amber-700 bg-amber-50 border-amber-200";
  };

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <FileText className="w-7 h-7 text-primary-600" />
          Plan Intelligence
        </h1>
        <p className="text-gray-500 mt-1">
          Upload your PBM contract and plan documents (SBC, SPD, EOC) to analyze terms, extract benefits, and cross-reference for gaps
        </p>
      </div>

      <DataSourceBanner />

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary-600 text-white text-xs font-bold">1</span>
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">PBM / TPA Contract</h2>
        </div>
        <FileUpload
          onFileSelect={handleFileUpload}
          label="Upload a PBM contract (PDF, DOC, or TXT)"
        />
        <div className="mt-4 text-center">
          <button
            onClick={handleSampleContract}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
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
              <FileText className="w-4 h-4 text-primary-600" />
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
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
            What We Analyze
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {analyzeCategories.map((cat) => (
              <div
                key={cat.label}
                className="flex items-start gap-3 p-4 rounded-lg bg-gray-50 border border-gray-100"
              >
                <cat.icon className="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5" />
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
        <AIAnalysisProgress
          variant="contract"
          filename={contractFilename}
          estimatedSeconds={30}
        />
      )}

      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-sm text-amber-700">{error}</p>
        </div>
      )}

      {terms && !loading && (
        <>
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-600 mb-2">Deal Diagnosis</p>
                <h2 className="text-2xl font-bold text-gray-900 leading-tight">
                  {dealDiagnosis || "PBM contract analysis complete"}
                </h2>
                <p className="text-sm text-gray-500 mt-2">
                  Lead with the economics and control terms first. Detailed clause extraction and audit support remain below as supporting evidence.
                </p>
              </div>
              <div className="flex flex-col sm:flex-row gap-2">
                {contractRowId !== null && (
                  <Link
                    href={`/audit?contract_id=${contractRowId}`}
                    className="inline-flex items-center justify-center gap-2 px-5 py-2.5 border border-primary-600 text-primary-600 rounded-lg text-sm font-medium hover:bg-primary-50 transition-colors"
                  >
                    <Mail className="w-4 h-4" />
                    Draft Audit Letter
                  </Link>
                )}
                <button
                  onClick={handleExportPDF}
                  disabled={exporting || !rawContractAnalysis}
                  className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {exporting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  {exporting ? "Generating PDF..." : "Export PDF Report"}
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            <div className={`rounded-xl border p-5 ${riskLevelStyles(weightedAssessment?.risk_level)}`}>
              <p className="text-xs font-semibold uppercase tracking-wider opacity-80 mb-2">PBM Deal Score</p>
              <p className="text-3xl font-bold">{weightedAssessment?.deal_score ?? Math.max(0, 100 - (rawContractAnalysis?.overall_risk_score as number || 0))}</p>
              <p className="text-sm mt-1">{formatRiskLevel(weightedAssessment?.risk_level)} risk structure</p>
            </div>
            <div className={`rounded-xl border p-5 ${riskLevelStyles(controlPosture?.level)}`}>
              <p className="text-xs font-semibold uppercase tracking-wider opacity-80 mb-2">Control Posture</p>
              <p className="text-lg font-bold">{controlPosture?.label || "Pending analysis"}</p>
              <p className="text-sm mt-1">{controlPosture?.summary || "Lead with who controls pricing, rebates, specialty, and audit rights."}</p>
            </div>
            <div className={`rounded-xl border p-5 ${riskLevelStyles(structuralRiskOverride?.triggered ? structuralRiskOverride?.level : "low")}`}>
              <p className="text-xs font-semibold uppercase tracking-wider opacity-80 mb-2">Structural Risk</p>
              <p className="text-lg font-bold">
                {structuralRiskOverride?.triggered ? "Override triggered" : "Weighted only"}
              </p>
              <p className="text-sm mt-1">
                {structuralRiskOverride?.rationale || "No structural override was required."}
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">Benchmark Observations</p>
              <p className="text-3xl font-bold text-gray-900">{benchmarkObservations.length || topRisks.length || complianceCount!.critical}</p>
              <p className="text-sm text-gray-600 mt-1">Observations tie contract language to a benchmark and recommendation.</p>
            </div>
          </div>

          {immediateActions.length > 0 && (
            <div className="bg-white rounded-xl border-2 border-primary-200 shadow-[var(--shadow-card)] overflow-hidden mb-6">
              <div className="px-6 py-4 bg-primary-50 border-b border-primary-100 flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-700">Action Items</p>
                  <h3 className="text-lg font-bold text-gray-900 mt-1">What to do next</h3>
                </div>
                <span className="inline-flex items-center px-3 py-1 rounded-full bg-white border border-primary-200 text-xs font-semibold text-primary-700">
                  {immediateActions.length} {immediateActions.length === 1 ? "action" : "actions"}
                </span>
              </div>
              <ol className="divide-y divide-gray-100">
                {immediateActions.map((action, i) => (
                  <li key={`action-${i}`} className="px-6 py-4 flex gap-4">
                    <span className="flex-shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary-600 text-white text-sm font-bold">
                      {i + 1}
                    </span>
                    <p className="text-sm text-gray-800 leading-relaxed pt-0.5">{action}</p>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {controlMap.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Control Map</h3>
                <p className="text-sm text-gray-500 mt-1">Who controls the key cost and governance levers in this contract.</p>
              </div>
              <div className="divide-y divide-gray-100">
                {controlMap.map((item, i) => (
                  <div key={`${item.lever}-${i}`} className="px-6 py-4 grid grid-cols-1 md:grid-cols-[1.1fr_0.9fr_1.4fr_1.6fr] gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Lever</p>
                      <p className="text-sm font-medium text-gray-900 mt-1">{item.lever}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Controller</p>
                      <p className="text-sm font-medium text-gray-900 mt-1">{item.controller}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Assessment</p>
                      <p className="text-sm text-gray-700 mt-1">{item.assessment}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Implication</p>
                      <p className="text-sm text-gray-700 mt-1">{item.implication}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
            <div className="xl:col-span-2 bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Observations & Recommendations</h3>
                  <p className="text-sm text-gray-500 mt-1">Client-style considerations tied to a benchmark, with the recommendation embedded directly in the observation.</p>
                </div>
                {weightedAssessment?.methodology && (
                  <span className="text-xs text-gray-500 text-right max-w-xs">{weightedAssessment.methodology}</span>
                )}
              </div>
              <div className="divide-y divide-gray-100">
                {benchmarkObservations.length > 0 ? benchmarkObservations.map((item, i) => (
                  <div key={`${item.title}-${i}`} className="px-6 py-5">
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${observationKindStyles(item.kind)}`}>
                        {item.kind === "strength" ? "STRENGTH" : "CONSIDERATION"}
                      </span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${riskBadgeStyles(item.severity)}`}>
                        {item.severity.toUpperCase()}
                      </span>
                      <span className="text-xs font-semibold uppercase tracking-wider text-primary-600">Tier {item.tier}</span>
                      <span className="text-xs text-gray-500">{item.category}</span>
                    </div>
                    <p className="text-base font-semibold text-gray-900">{item.title}</p>
                    <div className="mt-3 rounded-lg bg-gray-50 border border-gray-100 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Benchmark</p>
                      <p className="text-sm font-medium text-gray-900 mt-1">{item.benchmark_label}</p>
                      <p className="text-sm text-gray-600 mt-1">{item.benchmark}</p>
                      <p className="text-xs text-gray-500 mt-2">Source: {item.benchmark_source}</p>
                    </div>
                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Observation</p>
                        <p className="text-sm text-gray-700 mt-1">{item.observation}</p>
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Implication</p>
                        <p className="text-sm text-gray-700 mt-1">{item.implication}</p>
                      </div>
                    </div>
                    {item.supporting_detail && (
                      <p className="text-sm text-gray-600 mt-3">{item.supporting_detail}</p>
                    )}
                    <div className="mt-4 rounded-lg bg-primary-50 border border-primary-100 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-primary-700">Recommendation</p>
                      <p className="text-sm text-primary-700 font-medium mt-1">{item.recommendation}</p>
                    </div>
                  </div>
                )) : topRisks.length > 0 ? topRisks.map((risk, i) => (
                  <div key={`${risk.title}-${i}`} className="px-6 py-5">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${observationKindStyles("consideration")}`}>
                        CONSIDERATION
                      </span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${riskBadgeStyles(risk.severity)}`}>
                        {risk.severity.toUpperCase()}
                      </span>
                      <span className="text-xs font-semibold uppercase tracking-wider text-primary-600">Tier {risk.tier}</span>
                    </div>
                    <p className="text-base font-semibold text-gray-900 mt-2">{risk.title}</p>
                    <p className="text-sm text-gray-600 mt-1">{risk.why_it_matters}</p>
                    <div className="mt-4 rounded-lg bg-primary-50 border border-primary-100 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-primary-700">Recommendation</p>
                      <p className="text-sm text-primary-700 font-medium mt-1">{risk.recommendation}</p>
                    </div>
                  </div>
                )) : (
                  <div className="px-6 py-5 text-sm text-gray-500">Observations will appear here after contract analysis.</div>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">Risk Framing</h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Structural View</p>
                    <p className="text-sm text-gray-700 mt-1">{structuralRiskOverride?.rationale || "Weighted scoring is active without a structural override."}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Control View</p>
                    <p className="text-sm text-gray-700 mt-1">{controlPosture?.headline || "Control posture will appear after contract analysis."}</p>
                  </div>
                  {auditImplication && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Audit Interpretation</p>
                      <p className="text-sm text-gray-700 mt-1">{auditImplication}</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">Weighted Tier Scores</h3>
                <div className="space-y-3">
                  {(weightedAssessment?.tier_scores || []).map((tier) => (
                    <div key={tier.tier}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-medium text-gray-800">{tier.tier}</span>
                        <span className="text-gray-500">{tier.score}% risk</span>
                      </div>
                      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                        <div className={`h-full ${
                          tier.score >= 65 ? "bg-red-500" : tier.score >= 35 ? "bg-amber-500" : "bg-emerald-500"
                        }`} style={{ width: `${Math.min(tier.score, 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                {/* Action items moved to a prominent top-level panel above. */}
              </div>
            </div>
          </div>

          {financialExposure && (() => {
            // Compute total annual leakage = sum of the three category
            // dollar ranges. This is the single number a CFO actually
            // cares about — previously the user had to mentally add
            // three separate ranges to get it. Surface it as the
            // headline of the Supporting Leakage Estimates section.
            const entries: FinancialExposureEntry[] = [
              financialExposure.rebate_leakage,
              financialExposure.spread_exposure,
              financialExposure.specialty_control,
            ].filter((e): e is FinancialExposureEntry => !!e);
            const totalLow = entries.reduce((sum, e) => sum + (e.dollar_estimate_low ?? 0), 0);
            const totalHigh = entries.reduce((sum, e) => sum + (e.dollar_estimate_high ?? 0), 0);
            const hasTotal = totalLow > 0 || totalHigh > 0;
            const customLoaded = !!financialExposure.claims_context?.custom_data_loaded;
            return (
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Supporting Leakage Estimates</h3>
                  {financialExposure.summary && <p className="text-sm text-gray-500 mt-1">{financialExposure.summary}</p>}
                  {customLoaded && financialExposure.claims_context?.claims_count != null && (
                    <p className="text-xs text-emerald-700 mt-2">
                      Based on {financialExposure.claims_context.claims_count.toLocaleString()} uploaded claims
                      {financialExposure.claims_context.claims_filename ? ` from ${financialExposure.claims_context.claims_filename}` : ""}
                      {financialExposure.claims_context.date_range_start && financialExposure.claims_context.date_range_end ? ` (${financialExposure.claims_context.date_range_start} to ${financialExposure.claims_context.date_range_end})` : ""}.
                    </p>
                  )}
                  {!customLoaded && (
                    <p className="text-xs text-amber-700 mt-2">
                      Dollar figures below are illustrative — based on a representative 1,000-employee self-insured plan. Upload your real claims on the Claims page to recompute against your actual spend.
                    </p>
                  )}
                </div>
                {hasTotal && (
                  <div className="px-6 py-5 bg-gradient-to-r from-red-50 to-amber-50 border-b border-gray-200">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-red-700 mb-1">Total Estimated Annual Leakage</p>
                    <p className="text-3xl font-bold text-gray-900">
                      {formatUsdShort(totalLow)}
                      <span className="text-gray-400 mx-2">–</span>
                      {formatUsdShort(totalHigh)}
                      <span className="text-base font-normal text-gray-600 ml-1">/yr</span>
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      Sum of rebate leakage, spread exposure, and specialty channel control across all three categories below.
                    </p>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-100">
                  {[
                    { label: "Rebate Leakage", item: financialExposure.rebate_leakage },
                    { label: "Spread Exposure", item: financialExposure.spread_exposure },
                    { label: "Specialty Control", item: financialExposure.specialty_control },
                  ].map(({ label, item }) => item ? (
                    <div key={label} className="p-5">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-semibold text-gray-900">{label}</p>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${riskBadgeStyles(item.level)}`}>
                          {item.level.toUpperCase()}
                        </span>
                      </div>
                      {item.dollar_estimate_low != null && item.dollar_estimate_high != null ? (
                        <>
                          <p className="text-2xl font-bold text-gray-900">
                            {formatUsdShort(item.dollar_estimate_low)}
                            <span className="text-gray-400 mx-1">–</span>
                            {formatUsdShort(item.dollar_estimate_high)}
                            <span className="text-sm font-normal text-gray-500"> /yr</span>
                          </p>
                          <p className="text-xs text-gray-500 mt-1">{item.estimate}</p>
                        </>
                      ) : (
                        <p className="text-lg font-bold text-gray-900">{item.estimate}</p>
                      )}
                      <p className="text-sm text-gray-600 mt-2">{item.driver}</p>
                    </div>
                  ) : null)}
                </div>
              </div>
            );
          })()}

          {linkedFindings.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5 mb-6">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">Economic Linkages</h3>
              <div className="space-y-3">
                {linkedFindings.map((finding, i) => (
                  <div key={`${finding.title}-${i}`} className="rounded-lg bg-gray-50 border border-gray-100 p-4">
                    <p className="text-sm font-medium text-gray-900">{finding.title}</p>
                    {finding.explanation && <p className="text-sm text-gray-600 mt-1">{finding.explanation}</p>}
                    {finding.economic_impact && <p className="text-sm text-primary-600 mt-2">{finding.economic_impact}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-emerald-700">{complianceCount!.good}</p>
              <p className="text-sm text-emerald-600">Employer-Favorable Clauses</p>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-amber-700">{complianceCount!.warning}</p>
              <p className="text-sm text-amber-600">Neutral Clauses</p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-red-700">{complianceCount!.critical}</p>
              <p className="text-sm text-red-600">PBM-Favorable Clauses</p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
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
                            ? "Employer"
                            : term.status === "warning"
                            ? "Neutral"
                            : "PBM"
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

          {/* Audit Rights Checklist */}
          {auditChecklist && auditChecklist.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-primary-600" />
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                  Audit Rights Checklist
                </h3>
                <span className="ml-auto text-xs text-gray-500">
                  {auditChecklist.filter(c => c.found).length}/{auditChecklist.length} found
                </span>
              </div>
              <div className="divide-y divide-gray-100">
                {auditChecklist.map((item, i) => (
                  <div key={i} className="flex items-center gap-3 px-6 py-3 hover:bg-gray-50">
                    {item.found ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                    ) : (
                      <XCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{item.item}</p>
                      {item.details && (
                        <p className="text-xs text-gray-500 mt-0.5">{item.details}</p>
                      )}
                    </div>
                    <StatusBadge
                      status={item.found ? "good" : "critical"}
                      label={item.found ? "Found" : "Missing"}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Eligible Rebate Definition Alert */}
          {rebateDefinition && rebateDefinition.narrow_definition_flag && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-5 mb-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-bold text-red-800 mb-1">
                    Narrow Rebate Definition Detected
                  </h3>
                  {rebateDefinition.details && (
                    <p className="text-sm text-red-700 mb-3">{rebateDefinition.details}</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {rebateDefinition.excludes_admin_fees && (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        Excludes admin fees
                      </span>
                    )}
                    {rebateDefinition.excludes_volume_bonuses && (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        Excludes volume bonuses
                      </span>
                    )}
                    {rebateDefinition.excludes_price_protection && (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        Excludes price protection
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Dispute Resolution & Statistical Extrapolation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Dispute Resolution */}
            {disputeResolution && (
              <div className={`rounded-xl border p-5 ${disputeRiskColor(disputeResolution.risk_level)}`}>
                <div className="flex items-center gap-2 mb-2">
                  <Scale className="w-4 h-4" />
                  <h3 className="text-sm font-bold uppercase tracking-wider">
                    Dispute Resolution
                  </h3>
                </div>
                <p className="text-lg font-bold capitalize mb-1">
                  {disputeResolution.mechanism}
                </p>
                {disputeResolution.details && (
                  <p className="text-sm opacity-80">{disputeResolution.details}</p>
                )}
                {disputeResolution.risk_level && (
                  <div className="mt-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                      disputeResolution.risk_level === "high"
                        ? "bg-red-200 text-red-800"
                        : disputeResolution.risk_level === "low"
                        ? "bg-emerald-200 text-emerald-800"
                        : "bg-amber-200 text-amber-800"
                    }`}>
                      {disputeResolution.risk_level.toUpperCase()} RISK
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Statistical Extrapolation */}
            {statisticalExtrapolation && (
              <div className={`rounded-xl border p-5 ${
                statisticalExtrapolation.found
                  ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                  : "bg-red-50 border-red-200 text-red-700"
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  <BarChart3 className="w-4 h-4" />
                  <h3 className="text-sm font-bold uppercase tracking-wider">
                    Statistical Extrapolation
                  </h3>
                </div>
                <div className="flex items-center gap-2 mb-1">
                  {statisticalExtrapolation.found ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  ) : (
                    <XCircleIcon className="w-5 h-5 text-red-500" />
                  )}
                  <p className="text-lg font-bold">
                    {statisticalExtrapolation.found ? "Found" : "Not Found"}
                  </p>
                </div>
                {statisticalExtrapolation.details && (
                  <p className="text-sm opacity-80">{statisticalExtrapolation.details}</p>
                )}
              </div>
            )}
          </div>

          {/* ═══ REDLINE SUGGESTIONS ═══ */}
          {rawContractAnalysis && (rawContractAnalysis as Record<string, unknown>).redline_suggestions && Array.isArray((rawContractAnalysis as Record<string, unknown>).redline_suggestions) && ((rawContractAnalysis as Record<string, unknown>).redline_suggestions as Array<Record<string, string>>).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200 bg-primary-600">
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Recommended Contract Redlines
                </h3>
                <p className="text-xs text-primary-200 mt-0.5">Specific language to propose during renegotiation</p>
              </div>
              <div className="divide-y divide-gray-100">
                {((rawContractAnalysis as Record<string, unknown>).redline_suggestions as Array<Record<string, string>>).map((redline, i) => (
                  <div key={i} className="px-6 py-5">
                    <div className="flex items-start justify-between mb-3">
                      <h4 className="text-sm font-semibold text-gray-900">{redline.section}</h4>
                      {redline.impact && (
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium border ${
                          redline.impact === "high" ? "bg-red-50 text-red-600 border-red-100" :
                          redline.impact === "medium" ? "bg-amber-50 text-amber-600 border-amber-100" :
                          "bg-blue-50 text-blue-600 border-blue-100"
                        }`}>
                          {redline.impact.toUpperCase()} IMPACT
                        </span>
                      )}
                    </div>

                    {/* Current language */}
                    <div className="mb-3">
                      <p className="text-[11px] font-semibold text-red-500 uppercase tracking-wider mb-1">Current Language (Remove)</p>
                      <div className="bg-red-50 border border-red-100 rounded-lg px-4 py-3">
                        <p className="text-sm text-red-800 leading-relaxed line-through decoration-red-300">{redline.current_language}</p>
                      </div>
                    </div>

                    {/* Suggested language */}
                    <div className="mb-3">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider">Suggested Language (Add)</p>
                        <button
                          type="button"
                          onClick={() => copyRedline(i, redline.suggested_language)}
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 hover:text-emerald-900 px-2 py-0.5 rounded hover:bg-emerald-100 transition-colors"
                          aria-label="Copy suggested language to clipboard"
                        >
                          {copiedRedline === i ? (
                            <>
                              <Check className="w-3 h-3" />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              Copy
                            </>
                          )}
                        </button>
                      </div>
                      <div className="bg-emerald-50 border border-emerald-100 rounded-lg px-4 py-3">
                        <p className="text-sm text-emerald-800 leading-relaxed font-medium">{redline.suggested_language}</p>
                      </div>
                    </div>

                    {/* Rationale */}
                    <div className="flex items-start gap-4 text-xs text-gray-500">
                      <div className="flex-1">
                        <span className="font-semibold text-gray-700">Why: </span>{redline.rationale}
                      </div>
                      {redline.source && (
                        <div className="flex-shrink-0 text-right">
                          <span className="font-semibold text-gray-700">Source: </span>{redline.source}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ═══ STEP 2: Plan Document Upload ═══ */}
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary-600 text-white text-xs font-bold">2</span>
              <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Plan Document (SBC / SPD / EOC)</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Upload the associated plan document to extract benefit structure and cross-reference against the contract.
            </p>
            <FileUpload
              onFileSelect={handlePlanDocUpload}
              label="Upload SBC, SPD, EOC, or COC (PDF or TXT)"
            />
          </div>

          {planLoading && (
            <div className="mb-6">
              <AIAnalysisProgress variant="plan_doc" estimatedSeconds={32} />
            </div>
          )}

          {/* Plan Benefits Display */}
          {planBenefits && !planLoading && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-primary-600" />
                  <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                    Plan Document Benefits
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  {planDocType && (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {planDocType}
                    </span>
                  )}
                  {planBenefits.confidence_score && (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      {planBenefits.confidence_score}% confidence
                    </span>
                  )}
                </div>
              </div>

              {/* Plan Info */}
              {planBenefits.plan_info && (
                <div className="px-6 py-3 bg-gray-50 border-b border-gray-100 flex flex-wrap gap-4 text-sm">
                  {planBenefits.plan_info.plan_name && <span><strong>Plan:</strong> {planBenefits.plan_info.plan_name}</span>}
                  {planBenefits.plan_info.carrier && <span><strong>Carrier:</strong> {planBenefits.plan_info.carrier}</span>}
                  {planBenefits.plan_info.plan_type && <span><strong>Type:</strong> {planBenefits.plan_info.plan_type}</span>}
                  {planBenefits.plan_info.effective_date && <span><strong>Effective:</strong> {planBenefits.plan_info.effective_date}</span>}
                </div>
              )}

              {/* Key Benefits Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6">
                {planBenefits.deductible?.individual_in_network && (
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500 uppercase">Deductible (Ind)</p>
                    <p className="text-lg font-bold text-gray-900">{planBenefits.deductible.individual_in_network}</p>
                  </div>
                )}
                {planBenefits.out_of_pocket_maximum?.individual_in_network && (
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500 uppercase">OOP Max (Ind)</p>
                    <p className="text-lg font-bold text-gray-900">{planBenefits.out_of_pocket_maximum.individual_in_network}</p>
                  </div>
                )}
                {planBenefits.copays?.pcp_visit && (
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500 uppercase">PCP Copay</p>
                    <p className="text-lg font-bold text-gray-900">{planBenefits.copays.pcp_visit}</p>
                  </div>
                )}
                {planBenefits.copays?.specialist_visit && (
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500 uppercase">Specialist</p>
                    <p className="text-lg font-bold text-gray-900">{planBenefits.copays.specialist_visit}</p>
                  </div>
                )}
              </div>

              {/* Rx Coverage */}
              {planBenefits.prescription_drugs && (
                <div className="px-6 pb-6">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Prescription Drug Coverage</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {Object.entries(planBenefits.prescription_drugs).map(([key, val]) => {
                      if (typeof val === "object" && val && "copay" in (val as Record<string, unknown>)) {
                        const tier = val as { copay?: string; mail_order?: string };
                        return (
                          <div key={key} className="p-3 bg-blue-50 rounded-lg">
                            <p className="text-xs text-blue-600 font-medium">{key.replace(/_/g, " ").replace(/tier \d /i, (m) => m.toUpperCase())}</p>
                            <p className="text-sm font-bold text-gray-900">{tier.copay || "N/A"}</p>
                            {tier.mail_order && <p className="text-xs text-gray-500">Mail: {tier.mail_order}</p>}
                          </div>
                        );
                      }
                      return null;
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ═══ STEP 3: Cross-Reference Results ═══ */}
          {crossRefLoading && (
            <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center gap-3 mb-6">
              <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
              <p className="text-sm text-gray-500">Cross-referencing contract against plan document...</p>
            </div>
          )}

          {crossRef && !crossRefLoading && (
            <>
              <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary-600 text-white text-xs font-bold">3</span>
                    <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                      Cross-Reference Analysis
                    </h3>
                  </div>
                  <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold ${
                    crossRef.overall_alignment_score >= 80
                      ? "bg-emerald-100 text-emerald-800"
                      : crossRef.overall_alignment_score >= 60
                      ? "bg-amber-100 text-amber-800"
                      : "bg-red-100 text-red-800"
                  }`}>
                    {crossRef.overall_alignment_score}% Aligned
                  </div>
                </div>

                {crossRef.summary && (
                  <div className="px-6 py-4 bg-gray-50 border-b border-gray-100">
                    <p className="text-sm text-gray-700">{crossRef.summary}</p>
                  </div>
                )}

                {/* Findings */}
                <div className="divide-y divide-gray-100">
                  {crossRef.findings.map((f, i) => (
                    <div key={i} className="px-6 py-4">
                      <div className="flex items-start gap-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold mt-0.5 ${
                          f.severity === "high" ? "bg-red-100 text-red-800" :
                          f.severity === "medium" ? "bg-amber-100 text-amber-800" :
                          "bg-blue-100 text-blue-800"
                        }`}>
                          {f.severity.toUpperCase()}
                        </span>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900">{f.finding}</p>
                          <p className="text-xs text-gray-500 mt-0.5">{f.category}</p>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                            <div className="p-3 bg-gray-50 rounded-lg">
                              <p className="text-xs text-gray-500 font-medium uppercase">Contract Says</p>
                              <p className="text-sm text-gray-700 mt-1">{f.contract_says}</p>
                            </div>
                            <div className="p-3 bg-gray-50 rounded-lg">
                              <p className="text-xs text-gray-500 font-medium uppercase">Plan Document Says</p>
                              <p className="text-sm text-gray-700 mt-1">{f.plan_doc_says}</p>
                            </div>
                          </div>
                          <p className="text-sm text-primary-600 mt-2 font-medium">{f.recommendation}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Items */}
              {crossRef.action_items && crossRef.action_items.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Action Items</h3>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {crossRef.action_items.map((item, i) => (
                      <div key={i} className="px-6 py-4 flex items-start gap-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold mt-0.5 ${
                          item.priority === "high" ? "bg-red-100 text-red-800" :
                          item.priority === "medium" ? "bg-amber-100 text-amber-800" :
                          "bg-blue-100 text-blue-800"
                        }`}>
                          {item.priority.toUpperCase()}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{item.action}</p>
                          <p className="text-xs text-gray-500 mt-0.5">{item.reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Missing Items */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                {crossRef.missing_from_contract && crossRef.missing_from_contract.length > 0 && (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-5">
                    <h4 className="text-sm font-bold text-red-800 mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      Missing from PBM Contract
                    </h4>
                    <ul className="space-y-2">
                      {crossRef.missing_from_contract.map((item, i) => (
                        <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                          <XCircleIcon className="w-4 h-4 flex-shrink-0 mt-0.5" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {crossRef.missing_from_plan_doc && crossRef.missing_from_plan_doc.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
                    <h4 className="text-sm font-bold text-amber-800 mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      Missing from Plan Document
                    </h4>
                    <ul className="space-y-2">
                      {crossRef.missing_from_plan_doc.map((item, i) => (
                        <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                          <XCircleIcon className="w-4 h-4 flex-shrink-0 mt-0.5" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
