"use client";

import { useState } from "react";
import { usePageTitle } from "@/components/PageTitle";
import FileUpload from "@/components/FileUpload";
import StatusBadge from "@/components/StatusBadge";
import DataSourceBanner from "@/components/DataSourceBanner";
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
  };
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

const demoTerms: ExtractedTerm[] = [
  { clause: "Rebate Passthrough Guarantee", value: "100% passthrough", status: "good", note: "Industry best practice" },
  { clause: "Spread Pricing Allowance", value: "Not prohibited", status: "critical", note: "No spread pricing ban -- PBM may retain spread" },
  { clause: "Audit Rights", value: "Annual, 60-day notice", status: "warning", note: "Industry standard is 30-day notice" },
  { clause: "Mail-Order Mandate", value: "Mandatory after 2 fills", status: "warning", note: "May limit member choice" },
  { clause: "Formulary Change Notice", value: "60 days", status: "good", note: "Meets minimum requirement" },
  { clause: "MAC List Transparency", value: "Not disclosed", status: "critical", note: "No visibility into MAC pricing" },
  { clause: "Performance Guarantees", value: "Generic fill rate >88%", status: "good", note: "Reasonable target" },
  { clause: "Specialty Drug Carve-Out", value: "None specified", status: "critical", note: "Specialty drugs under PBM control" },
  { clause: "Contract Term", value: "3 years, auto-renew", status: "warning", note: "Auto-renewal may limit negotiation leverage" },
  { clause: "Termination Clause", value: "180-day notice", status: "warning", note: "Long notice period favors PBM" },
];

const demoAuditChecklist: AuditChecklistItem[] = [
  { item: "Annual audit right", found: true, details: "One audit per contract year permitted" },
  { item: "30-day notice period or less", found: false, details: "60-day notice required -- exceeds best practice" },
  { item: "Unrestricted scope (claims, rebates, pricing)", found: false, details: "Scope limited to pricing and rebate terms only" },
  { item: "Access to pharmacy network agreements", found: false, details: "Explicitly excluded from audit scope" },
  { item: "Access to manufacturer contracts", found: false, details: "Explicitly excluded from audit scope" },
  { item: "Right to use independent auditor", found: true, details: "Plan sponsor may designate auditor" },
  { item: "Plan sponsor bears audit costs only if compliant", found: false, details: "All costs borne by plan sponsor regardless" },
  { item: "Electronic data access", found: true, details: "Data extracts in electronic format required" },
  { item: "Statistical extrapolation allowed", found: false, details: "No mention of extrapolation rights" },
  { item: "Audit lookback period >= 2 years", found: false, details: "Limited to current contract year" },
  { item: "Remediation timeline specified", found: false, details: "No requirement for PBM to remediate findings" },
];

const demoRebateDefinition: EligibleRebateDefinition = {
  narrow_definition_flag: true,
  excludes_admin_fees: true,
  excludes_volume_bonuses: true,
  excludes_price_protection: true,
  details: "Rebates defined narrowly as only payments 'specifically designated as rebates' by manufacturers. Admin fees, service fees, data fees, market share incentives, and price protection payments excluded.",
};

const demoDisputeResolution: DisputeResolution = {
  mechanism: "litigation",
  details: "Governed by Delaware law. No mediation or arbitration clause specified.",
  risk_level: "medium",
};

const demoStatisticalExtrapolation = {
  found: false,
  details: "No statistical extrapolation clause found. Audit findings cannot be projected to full population.",
};

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
    rebate_passthrough: "Rebate Passthrough",
    spread_pricing: "Spread Pricing",
    formulary_clauses: "Formulary Management",
    audit_rights: "Audit Rights",
    mac_pricing: "MAC Pricing",
    termination_provisions: "Termination Provisions",
    gag_clauses: "Gag Clauses",
    specialty_channel: "Specialty Channel Control",
  };
  const terms: ExtractedTerm[] = [];
  for (const [key, val] of Object.entries(a)) {
    if (!val || typeof val !== "object" || key === "compliance_flags" || key === "overall_risk_score" || key === "summary" || key === "audit_rights" || key === "eligible_rebate_definition" || key === "dispute_resolution" || key === "statistical_extrapolation" || key === "statistical_extrapolation_rights" || key === "linked_findings" || key === "economic_linkages" || key === "specialty_channel") continue;
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
      clause: labels[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      value: extractedValue,
      status,
      note: (val.details as string) || "",
    });
  }
  return terms.length > 0 ? terms : [];
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

  const loadDemoExtras = () => {
    setAuditChecklist(demoAuditChecklist);
    setRebateDefinition(demoRebateDefinition);
    setDisputeResolution(demoDisputeResolution);
    setStatisticalExtrapolation(demoStatisticalExtrapolation);
  };

  const processResponse = (data: Record<string, unknown>) => {
    const a = data?.analysis as AnalysisExtras | undefined;
    if (a && a.rebate_passthrough) {
      setTerms(mapApiToTerms(a as Record<string, Record<string, unknown>>));
      loadExtras(a);
      setRawContractAnalysis(a as Record<string, unknown>);
    } else {
      setTerms((data.terms as ExtractedTerm[]) || demoTerms);
      loadDemoExtras();
      setRawContractAnalysis(null);
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
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      setPlanBenefits(data.benefits as PlanBenefits);
      setPlanDocType(data.document_type);

      // Auto-trigger cross-reference if we have both contract and plan data
      if (rawContractAnalysis && data.benefits) {
        runCrossReference(rawContractAnalysis, data.benefits);
      }
    } catch {
      setPlanBenefits(null);
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
      if (!res.ok) throw new Error("Cross-reference failed");
      const data = await res.json();
      setCrossRef(data.cross_reference as CrossRefResult);
    } catch {
      setCrossRef(null);
    } finally {
      setCrossRefLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (!rawContractAnalysis) return;
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
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ClearScript_Report_${contractFilename.replace(/\.[^.]+$/, "")}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF export failed:", err);
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
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      processResponse(data);
    } catch {
      setTerms(demoTerms);
      loadDemoExtras();
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
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      processResponse(data);
    } catch {
      setTerms(demoTerms);
      loadDemoExtras();
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
  const benchmarkObservations = ((rawContractAnalysis?.benchmark_observations as BenchmarkObservation[] | undefined) || []).slice(0, 4);
  const immediateActions = ((rawContractAnalysis?.immediate_actions as string[] | undefined) || []).slice(0, 3);
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
        <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
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
                {(immediateActions.length > 0) && (
                  <div className="mt-5 pt-4 border-t border-gray-100">
                    <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">Negotiation Sequence</p>
                    <div className="space-y-2">
                      {immediateActions.map((action, i) => (
                        <div key={`${action}-${i}`} className="flex gap-3">
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary-50 text-primary-700 text-[11px] font-bold flex-shrink-0">{i + 1}</span>
                          <p className="text-sm text-gray-700">{action}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {financialExposure && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Supporting Leakage Estimates</h3>
                {financialExposure.summary && <p className="text-sm text-gray-500 mt-1">{financialExposure.summary}</p>}
                {financialExposure.mode === "claims_backed" && financialExposure.claims_context?.claims_count && (
                  <p className="text-xs text-emerald-700 mt-2">
                    Based on {financialExposure.claims_context.claims_count.toLocaleString()} uploaded claims
                    {financialExposure.claims_context.claims_filename ? ` from ${financialExposure.claims_context.claims_filename}` : ""}
                    {financialExposure.claims_context.date_range_start && financialExposure.claims_context.date_range_end ? ` (${financialExposure.claims_context.date_range_start} to ${financialExposure.claims_context.date_range_end})` : ""}.
                  </p>
                )}
              </div>
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
                    <p className="text-lg font-bold text-gray-900">{item.estimate}</p>
                    <p className="text-sm text-gray-600 mt-2">{item.driver}</p>
                  </div>
                ) : null)}
              </div>
            </div>
          )}

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
                      <p className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider mb-1">Suggested Language (Add)</p>
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
            <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center gap-3 mb-6">
              <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
              <p className="text-sm text-gray-500">Extracting plan document benefits...</p>
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
