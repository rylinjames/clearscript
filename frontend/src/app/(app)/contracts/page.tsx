"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { usePageTitle } from "@/components/PageTitle";
import FileUpload from "@/components/FileUpload";
import StatusBadge from "@/components/StatusBadge";
import AIAnalysisProgress from "@/components/AIAnalysisProgress";
import {
  FileText,
  Loader2,
  DollarSign,
  BarChart3,
  BookOpen,
  ShieldCheck,
  Tag,
  XCircle,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle2,
  XCircle as XCircleIcon,
  Download,
  Mail,
  Copy,
  Check,
  Share2,
  History,
  Clock,
} from "lucide-react";
import type {
  ExtractedTerm,
  AuditChecklistItem,
  EligibleRebateDefinition,
  AnalysisExtras,
  PlanBenefits,
  CrossRefFinding,
  CrossRefResult,
  WeightedAssessment,
  TopRisk,
  ContractIdentification,
  FinancialExposureEntry,
  FinancialExposure,
  ControlMapItem,
  ControlPosture,
  StructuralRiskOverride,
  PastContract,
  BenchmarkObservation,
} from "@/types/contract";
import {
  formatUsdShort,
  formatLongDate,
  formatRelativeDays,
  riskLevelStyles,
  riskBadgeStyles,
  observationKindStyles,
  formatRiskLevel,
  mapApiToTerms,
  CLAUSE_LABELS,
} from "@/lib/contract-utils";
import ContractIdentificationCard from "@/components/contract/ContractIdentificationCard";
import RecentAnalysesPicker from "@/components/contract/RecentAnalysesPicker";

const analyzeCategories = [
  { icon: DollarSign, label: "Rebate Terms", description: "Passthrough guarantees, retention percentages" },
  { icon: BarChart3, label: "Spread Pricing", description: "Ingredient cost vs. plan charge provisions" },
  { icon: BookOpen, label: "Formulary Clauses", description: "Change notice periods, exclusion rights" },
  { icon: ShieldCheck, label: "Audit Rights", description: "Frequency, notice requirements, scope" },
  { icon: Tag, label: "MAC Pricing", description: "List transparency, update frequency, appeals" },
  { icon: XCircle, label: "Termination Provisions", description: "Notice periods, auto-renewal, exit fees" },
];

// Wrapped so the inner component can use useSearchParams. Next.js
// App Router requires useSearchParams to be inside a Suspense boundary
// or it bails out of static rendering for the whole page.
export default function ContractsPage() {
  return (
    <Suspense fallback={<div className="animate-fade-in p-8"><div className="h-6 w-48 bg-gray-100 rounded animate-pulse" /></div>}>
      <ContractsPageInner />
    </Suspense>
  );
}

function ContractsPageInner() {
  usePageTitle("Contract Intake");
  const searchParams = useSearchParams();
  // Deep link: /contracts?contract_id=N loads that persisted analysis
  // on mount instead of forcing the user to re-upload. Used by the
  // "Back to Plan Intelligence" link on the audit page so users can
  // return to the analysis they came from without rescanning.
  const deepLinkContractId = (() => {
    const raw = searchParams.get("contract_id");
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : null;
  })();
  const [loading, setLoading] = useState(false);
  const [terms, setTerms] = useState<ExtractedTerm[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // New analysis extras state
  const [auditChecklist, setAuditChecklist] = useState<AuditChecklistItem[] | null>(null);
  const [rebateDefinition, setRebateDefinition] = useState<EligibleRebateDefinition | null>(null);

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
  // Per-session dismissal of the sticky "upload claims" CTA banner.
  // Once dismissed, we don't re-render it for the rest of this page
  // session. Reset on every fresh upload (handled in handleFileUpload).
  const [stickyClaimsDismissed, setStickyClaimsDismissed] = useState(false);

  // Recent uploaded contracts list — populates the "Recent Analyses"
  // picker so users can revisit prior scans without re-uploading. The
  // backend persists every analysis to the contracts table, so this
  // is just a thin client of /api/contracts/list.
  const [pastContracts, setPastContracts] = useState<PastContract[]>([]);
  const [pastContractsLoading, setPastContractsLoading] = useState(true);
  const [loadingPastId, setLoadingPastId] = useState<number | null>(null);
  // Set when the current analysis on screen was loaded from the DB
  // rather than from a fresh upload. Used to show a "Loaded from
  // history" badge so the user knows they're looking at a prior scan.
  const [loadedFromHistoryId, setLoadedFromHistoryId] = useState<number | null>(null);

  // Claims-per-contract state: tracks whether the current contract has
  // associated claims and handles the inline claims upload flow.
  const [contractClaimsStatus, setContractClaimsStatus] = useState<{
    has_claims: boolean;
    claims_count: number;
    filename: string | null;
  } | null>(null);
  const [claimsUploading, setClaimsUploading] = useState(false);
  const [claimsUploadError, setClaimsUploadError] = useState<string | null>(null);
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

  // Build a forwarding-friendly email summary of the contract analysis
  // and open the user's mail client with subject + body pre-populated.
  // This is the "share with my colleague" workflow Brad asked about —
  // most ClearScript output gets forwarded between consultants and
  // benefits leaders by email, not by file. Mailto keeps the share
  // surface ephemeral (no link, no upload, no third-party hosting)
  // while still letting the recipient see the headline numbers without
  // having to log into ClearScript.
  const handleShare = () => {
    if (!rawContractAnalysis) return;

    const wa = rawContractAnalysis.weighted_assessment as { deal_score?: number; risk_level?: string } | undefined;
    const cid = rawContractAnalysis.contract_identification as { plan_sponsor_name?: string | null; pbm_name?: string | null } | undefined;
    const fe = rawContractAnalysis.financial_exposure as FinancialExposure | undefined;
    const tr = (rawContractAnalysis.top_risks as TopRisk[] | undefined) || [];
    const diagnosis = rawContractAnalysis.deal_diagnosis as string | undefined;

    const dealScore = wa?.deal_score ?? Math.max(0, 100 - (rawContractAnalysis.overall_risk_score as number || 0));
    const partiesLine = (cid?.pbm_name && cid?.plan_sponsor_name)
      ? `${cid.pbm_name} × ${cid.plan_sponsor_name}`
      : (cid?.pbm_name || cid?.plan_sponsor_name || contractFilename);

    // Total annual leakage from the three exposure buckets.
    const buckets: FinancialExposureEntry[] = fe ? [fe.rebate_leakage, fe.spread_exposure, fe.specialty_control].filter((e): e is FinancialExposureEntry => !!e) : [];
    const totalLow = buckets.reduce((s, e) => s + (e.dollar_estimate_low ?? 0), 0);
    const totalHigh = buckets.reduce((s, e) => s + (e.dollar_estimate_high ?? 0), 0);
    const leakageLine = (totalLow > 0 || totalHigh > 0)
      ? `Estimated annual leakage: ${formatUsdShort(totalLow)}–${formatUsdShort(totalHigh)}/yr`
      : null;

    const subject = `ClearScript analysis: ${partiesLine} (Deal Score ${dealScore}/100)`;

    const lines: string[] = [];
    lines.push(`PBM Contract Analysis — ${partiesLine}`);
    lines.push("");
    lines.push(`Deal Score: ${dealScore}/100${wa?.risk_level ? ` (${wa.risk_level} risk)` : ""}`);
    if (leakageLine) lines.push(leakageLine);
    lines.push("");
    if (diagnosis) {
      lines.push("Diagnosis:");
      lines.push(diagnosis);
      lines.push("");
    }
    if (tr.length > 0) {
      lines.push("Top risks:");
      tr.slice(0, 3).forEach((risk, i) => {
        lines.push(`  ${i + 1}. ${risk.title}${risk.severity ? ` (${risk.severity})` : ""}`);
      });
      lines.push("");
    }
    lines.push("This summary was generated by ClearScript Plan Intelligence.");
    lines.push("Full analysis, recommended redlines, and audit interpretation are available in the platform.");

    const body = lines.join("\n");
    const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailto;
  };

  const loadExtras = (a: AnalysisExtras) => {
    if (a.audit_rights?.checklist) {
      setAuditChecklist(a.audit_rights.checklist);
    }
    if (a.eligible_rebate_definition) {
      setRebateDefinition(a.eligible_rebate_definition);
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

  // Fetch the recent-contracts list once on mount. Refreshed after
  // every successful upload so newly-analyzed contracts appear in the
  // picker without a page reload.
  const refreshPastContracts = async () => {
    setPastContractsLoading(true);
    try {
      const res = await fetch("/api/contracts/list");
      if (!res.ok) return;
      const data = await res.json();
      const list = Array.isArray(data?.contracts) ? data.contracts : [];
      setPastContracts(list);
    } catch {
      /* picker is optional — silently leave the list empty */
    } finally {
      setPastContractsLoading(false);
    }
  };

  // Load a previously-analyzed contract from the DB and populate the
  // page state as if it had just been uploaded. Drives both the
  // "Recent Analyses" picker click handler AND the ?contract_id=N
  // deep link from the audit page's "Back to Plan Intelligence" link.
  const loadContractFromHistory = async (id: number) => {
    setLoadingPastId(id);
    setError(null);
    try {
      const res = await fetch(`/api/contracts/${id}`);
      if (!res.ok) {
        let detail = `Could not load contract id=${id}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      const data = await res.json();
      const contract = data?.contract;
      if (!contract || !contract.analysis) {
        throw new Error("This contract has no saved analysis to load.");
      }
      // Reset everything as if it were a new upload, then populate
      // from the persisted analysis. processResponse expects the same
      // shape /api/contracts/upload returns: { id, filename, analysis }.
      setTerms(null);
      setAuditChecklist(null);
      setRebateDefinition(null);
      setPlanBenefits(null);
      setPlanDocType(null);
      setCrossRef(null);
      setStickyClaimsDismissed(false);
      setContractFilename(contract.filename || "contract");
      processResponse({
        id: contract.id,
        filename: contract.filename,
        analysis: contract.analysis,
      });
      setLoadedFromHistoryId(contract.id);

      // Restore persisted plan doc + cross-reference if they exist
      // for this contract. This is what makes "click a past contract
      // and see everything" work — claims are restored via the
      // useEffect on contractRowId, and plan doc + cross-ref are
      // restored here from the GET response.
      if (contract.has_plan_doc && contract.plan_doc_benefits) {
        setPlanBenefits(contract.plan_doc_benefits as PlanBenefits);
        setPlanDocType(contract.plan_doc_type || null);
      }
      if (contract.has_cross_reference && contract.cross_reference) {
        setCrossRef(contract.cross_reference as CrossRefResult);
      }
      // Scroll to the top of the analysis so the user sees the
      // Deal Diagnosis hero immediately.
      if (typeof window !== "undefined") {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this contract from history");
    } finally {
      setLoadingPastId(null);
    }
  };

  // Mount-time effects: load the recent-contracts list, and if the URL
  // has a ?contract_id=N parameter, immediately deep-link to that
  // contract instead of showing the empty state.
  useEffect(() => {
    refreshPastContracts();
  }, []);

  useEffect(() => {
    if (deepLinkContractId !== null) {
      loadContractFromHistory(deepLinkContractId);
    }
    // We deliberately do NOT depend on loadContractFromHistory here —
    // it would re-fetch on every state change. The deep link is a
    // one-shot on mount when the URL parameter is present.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deepLinkContractId]);

  // Upload claims CSV for the current contract and re-enrich the
  // analysis so dollar-denominated leakage estimates appear.
  const handleClaimsUpload = async (file: File) => {
    if (!contractRowId) return;
    setClaimsUploading(true);
    setClaimsUploadError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`/api/claims/upload?contract_id=${contractRowId}`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        let detail = `Claims upload failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      const uploadData = await res.json();
      // Re-enrich the contract analysis with the new claims data
      const enrichRes = await fetch(`/api/contracts/${contractRowId}/re-enrich`, {
        method: "POST",
      });
      if (enrichRes.ok) {
        const enrichData = await enrichRes.json();
        if (enrichData.analysis) {
          // Re-populate the page with the enriched analysis
          processResponse({
            id: contractRowId,
            filename: contractFilename,
            analysis: enrichData.analysis,
          });
        }
      }
      setContractClaimsStatus({
        has_claims: true,
        claims_count: uploadData.summary?.total_claims || 0,
        filename: file.name,
      });
      setStickyClaimsDismissed(true); // Hide the "upload claims" CTA
    } catch (e) {
      setClaimsUploadError(e instanceof Error ? e.message : "Claims upload failed");
    } finally {
      setClaimsUploading(false);
    }
  };

  // Fetch claims status when a contract is loaded (from upload or history)
  useEffect(() => {
    if (!contractRowId) {
      setContractClaimsStatus(null);
      return;
    }
    const fetchClaimsStatus = async () => {
      try {
        const res = await fetch(`/api/claims/for-contract/${contractRowId}`);
        if (res.ok) {
          const data = await res.json();
          setContractClaimsStatus({
            has_claims: data.has_claims,
            claims_count: data.claims_count || 0,
            filename: data.filename || null,
          });
        }
      } catch {
        // Non-critical — claims status is optional
      }
    };
    fetchClaimsStatus();
  }, [contractRowId]);

  const handlePlanDocUpload = async (file: File) => {
    setPlanLoading(true);
    setPlanBenefits(null);
    setPlanDocType(null);
    setCrossRef(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const url = contractRowId
        ? `/api/contracts/upload-plan-document?contract_id=${contractRowId}`
        : "/api/contracts/upload-plan-document";
      const res = await fetch(url, {
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
          contract_id: contractRowId,
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
    setStickyClaimsDismissed(false);
    setLoadedFromHistoryId(null);

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
      // Refresh the recent-contracts picker so the new upload appears.
      refreshPastContracts();
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
  const contractIdentification = (rawContractAnalysis?.contract_identification as ContractIdentification | undefined) || undefined;
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
  const linkedFindings = ((rawContractAnalysis?.linked_findings as Array<Record<string, string>> | undefined) || []).slice(0, 3);
  const dealDiagnosis = (rawContractAnalysis?.deal_diagnosis as string | undefined) || (rawContractAnalysis?.summary as string | undefined) || null;
  const auditImplication = (rawContractAnalysis?.audit_implication as string | undefined) || null;

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


      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-primary-600" />
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">PBM / TPA Contract</h2>
        </div>
        <FileUpload
          onFileSelect={handleFileUpload}
          label="Upload a PBM contract (PDF, DOC, or TXT)"
        />
      </div>

      <RecentAnalysesPicker
        pastContracts={pastContracts}
        pastContractsLoading={pastContractsLoading}
        loadedFromHistoryId={loadedFromHistoryId}
        loadingPastId={loadingPastId}
        uploadInProgress={loading}
        onSelect={loadContractFromHistory}
      />

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
                <div className="flex items-center gap-2 mb-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-600">Deal Diagnosis</p>
                  {loadedFromHistoryId !== null && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                      <History className="w-2.5 h-2.5" />
                      Loaded from history
                    </span>
                  )}
                </div>
                <h2 className="text-2xl font-bold text-gray-900 leading-tight">
                  {dealDiagnosis || "PBM contract analysis complete"}
                </h2>
              </div>
              <div className="flex flex-col sm:flex-row gap-2">
                <button
                  onClick={handleShare}
                  disabled={!rawContractAnalysis}
                  className="inline-flex items-center justify-center gap-2 px-5 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Open your mail client with a pre-populated summary"
                >
                  <Share2 className="w-4 h-4" />
                  Share
                </button>
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

          <ContractIdentificationCard contractIdentification={contractIdentification} />

          {/* ═══ Cross-reference promotion banner ═══
              The Step 2 plan-document upload is the most differentiated
              feature in the product (contract-vs-SBC alignment) but it
              previously lived 18 sections below the fold where most users
              never saw it. This banner sits right under Critical Dates so
              it's visible above the metric cards and points users at the
              upload they would otherwise miss. Hidden once a plan document
              has actually been uploaded so it doesn't nag.
          */}
          {!planBenefits && (
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl px-5 py-4 mb-6 flex items-center gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-blue-700" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-blue-900">Want a deeper analysis?</p>
                <p className="text-xs text-blue-800 mt-0.5 leading-relaxed">
                  Upload your SBC, SPD, or EOC below to cross-reference the plan benefits against this contract and surface gaps the contract-only analysis can&apos;t catch.
                </p>
              </div>
              <a
                href="#plan-document-upload"
                className="flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
              >
                Upload plan doc
                <ChevronDown className="w-3 h-3" />
              </a>
            </div>
          )}

          {/* ═══ Score collapse: Deal Score hero + supporting indicators strip ═══
              Customer critique flagged five competing "scores" all saying
              "this contract is bad" in slightly different vocabulary. We
              keep all the information but rebuild the hierarchy: Deal
              Score becomes a single full-width hero card with the giant
              number, peer anchor, and risk structure. Control Posture,
              Structural Risk, and Clause Balance demote to a smaller
              3-up "Supporting Indicators" strip with smaller numbers and
              tighter copy. Customer now sees ONE number first, with
              everything else as supporting evidence.
          */}
          {(() => {
            const dealScore = weightedAssessment?.deal_score ?? Math.max(0, 100 - (rawContractAnalysis?.overall_risk_score as number || 0));
            return (
              <div className={`rounded-xl border-2 p-6 mb-4 ${riskLevelStyles(weightedAssessment?.risk_level)}`}>
                <div className="flex items-start gap-6 flex-wrap">
                  <div className="flex-shrink-0">
                    <p className="text-xs font-semibold uppercase tracking-wider opacity-80 mb-2">PBM Deal Score</p>
                    <p className="text-6xl font-bold leading-none">
                      {dealScore}
                      <span className="text-2xl font-normal opacity-60 ml-1">/ 100</span>
                    </p>
                  </div>
                  <div className="flex-1 min-w-0 pt-1">
                    <p className="text-base font-semibold">{formatRiskLevel(weightedAssessment?.risk_level)} risk structure</p>
                    <p className="text-sm opacity-90 mt-1 leading-relaxed">
                      {dealScore >= 70
                        ? "This contract's core economic and governance terms are closer to employer-favorable benchmarks."
                        : dealScore >= 40
                        ? "This contract has a mix of employer-favorable and PBM-favorable terms. Focus renegotiation on the Tier 1 economics."
                        : "This contract's rebate, pricing, specialty, and audit terms are heavily PBM-favorable. The redlines below are the priority."}
                    </p>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Supporting indicators strip — three smaller cards beneath
              the hero. Each provides a different lens on the same "bad
              contract" finding (control, structural override, clause
              mix), but none competes with the headline Deal Score.
              The grid auto-equalizes card heights so the row stays
              tidy even when one card's description is longer than the
              others. No line-clamp — the full text needs to be readable
              for the indicators to be useful. */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
            <div className={`rounded-lg border p-3 ${riskLevelStyles(controlPosture?.level)}`}>
              <p className="text-[10px] font-semibold uppercase tracking-wider opacity-80 mb-1">Control Posture</p>
              <p className="text-sm font-bold leading-tight">{controlPosture?.label || "Pending analysis"}</p>
              <p className="text-[11px] mt-1 leading-snug opacity-90">{controlPosture?.summary || "Who controls pricing, rebates, specialty, and audit rights."}</p>
            </div>
            <div className={`rounded-lg border p-3 ${riskLevelStyles(structuralRiskOverride?.triggered ? structuralRiskOverride?.level : "low")}`}>
              <p className="text-[10px] font-semibold uppercase tracking-wider opacity-80 mb-1">Structural Risk</p>
              <p className="text-sm font-bold leading-tight">
                {structuralRiskOverride?.triggered ? "Override triggered" : "Weighted only"}
              </p>
              <p className="text-[11px] mt-1 leading-snug opacity-90">
                {structuralRiskOverride?.rationale || "No structural override was required."}
              </p>
            </div>
            <div className={`rounded-lg border p-3 ${
              complianceCount!.good === 0 && complianceCount!.critical > 0
                ? "bg-red-50 border-red-200 text-red-700"
                : complianceCount!.good > complianceCount!.critical
                ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                : "bg-amber-50 border-amber-200 text-amber-700"
            }`}>
              <p className="text-[10px] font-semibold uppercase tracking-wider opacity-80 mb-1">Clause Balance</p>
              <p className="text-sm font-bold leading-tight">
                {complianceCount!.good} of {complianceCount!.good + complianceCount!.warning + complianceCount!.critical} employer-favorable
              </p>
              <p className="text-[11px] mt-1 leading-snug opacity-90">
                {complianceCount!.warning} balanced; {complianceCount!.critical} PBM-favorable.
              </p>
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

          {/* Audit Interpretation promoted to full-width callout above
              the Observations section. Used to live in a sidebar next
              to a Weighted Tier Scores progress bar (which was internal
              methodology bleeding into the customer view). The progress
              bars are gone; this single sentence is one of the strongest
              pieces of analytical content the platform produces, so it
              gets its own row right above the evidence cards. */}
          {auditImplication && (
            <div className="bg-blue-50 rounded-xl border border-blue-200 p-5 mb-6">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-700 mb-2">Audit Interpretation</p>
              <p className="text-sm text-blue-900 leading-relaxed">{auditImplication}</p>
            </div>
          )}

          <div className="mb-6">
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
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

          </div>

          {financialExposure && (() => {
            // Compute total annual leakage = sum of the three category
            // dollar ranges. Only renders dollars when the user has
            // uploaded real claims; otherwise we fall back to the
            // percentage ranges from the AI's estimate strings rather
            // than fabricating dollar denominators from a synthetic
            // benchmark plan. The platform should never display a fake
            // number, even with a disclaimer.
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
                      Estimates below are expressed as percentages of plan spend.{" "}
                      <a href="#claims-upload" className="underline font-semibold hover:text-amber-900">Upload your claims data</a>
                      {" "}to convert these into your specific dollar figures.
                    </p>
                  )}
                </div>
                {hasTotal ? (
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
                ) : entries.length > 0 && (
                  <div className="px-6 py-5 bg-gradient-to-r from-red-50 to-amber-50 border-b border-gray-200">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-red-700 mb-1">Estimated Annual Leakage</p>
                    <div className="space-y-1.5">
                      {entries.map((e, i) => (
                        e.estimate ? (
                          <p key={i} className="text-sm text-gray-900">
                            <span className="font-semibold">
                              {i === 0 ? "Rebate leakage" : i === 1 ? "Spread exposure" : "Specialty control"}:
                            </span>
                            {" "}
                            {e.estimate}
                          </p>
                        ) : null
                      ))}
                    </div>
                    <p className="text-xs text-gray-600 mt-2">
                      <a href="#claims-upload" className="underline font-semibold text-primary-600 hover:text-primary-800">Upload your claims data</a>
                      {" "}to convert these percentage ranges into specific dollar figures for your plan.
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

          {/* Clause counts moved up to the metric cards row above as
              the "Clause Balance" card. The redundant 3-card breakdown
              that used to live here was buried below the fold and
              showed the same info as the new top-of-page summary. */}

          {/* Compact extracted-terms strip. The previous version was a
              4-column 7-row table that duplicated information already
              shown in the Recommended Contract Redlines section below
              and the Clause Balance card above. As a customer scanning
              the page, those rows added no new analytical value — every
              PBM-favorable row was just a slower, less actionable version
              of the same finding rendered as a redline. We keep a one-line
              chip-strip here so users can still see the lever names and
              their favorability at a glance, but the wall-of-table is
              gone. The full clause text + suggested language lives in
              the Redlines section. */}
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Clauses Extracted</h3>
              <span className="text-xs text-gray-500">{terms.length} {terms.length === 1 ? "clause" : "clauses"} analyzed</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {terms.map((term, i) => (
                <span
                  key={i}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${
                    term.status === "good"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                      : term.status === "warning"
                      ? "bg-amber-50 text-amber-700 border-amber-200"
                      : "bg-red-50 text-red-700 border-red-200"
                  }`}
                  title={term.note || term.value}
                >
                  {term.clause}
                  <span className="opacity-60">·</span>
                  <span className="font-normal">
                    {term.status === "good" ? "Employer" : term.status === "warning" ? "Balanced" : "PBM"}
                  </span>
                </span>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-3 leading-relaxed">
              Each PBM-favorable clause is paired with a specific suggested redline below — see Recommended Contract Redlines for the exact language to propose during renegotiation.
            </p>
          </div>

          {/* ═══ AUDIT-RELATED FINDINGS GROUP ═══
              Previously the Audit Rights Checklist, Statistical Extrapolation,
              and Dispute Resolution rendered as three independent sections
              floating between the leakage banner and the redlines. As a
              customer reading the page they felt orphaned — Statistical
              Extrapolation in particular looks like trivia until you see
              it next to the audit checklist and realize it's part of the
              same "can the plan sponsor actually verify what they paid
              for" question. Grouping them under a single header makes the
              audit story coherent. */}
          {auditChecklist && auditChecklist.length > 0 ? (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-primary-600" />
                Audit & Enforcement Rights
              </h3>
              <p className="text-xs text-gray-500 mb-4 max-w-3xl">
                Whether the plan sponsor can actually verify what they paid for, project errors across the full claims population, and force the PBM to fix problems found during an audit.
              </p>

              {/* Audit Rights Checklist */}
              {auditChecklist && auditChecklist.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-4">
                  <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-gray-900">
                      Audit Rights Checklist
                    </h4>
                    <span className="ml-auto text-xs text-gray-500">
                      {auditChecklist.filter(c => c.found).length}/{auditChecklist.length} provisions found
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

            </div>
          ) : null}

          {/* ═══ REDLINE SUGGESTIONS ═══ */}
          {rawContractAnalysis && (rawContractAnalysis as Record<string, unknown>).redline_suggestions && Array.isArray((rawContractAnalysis as Record<string, unknown>).redline_suggestions) && ((rawContractAnalysis as Record<string, unknown>).redline_suggestions as Array<Record<string, unknown>>).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200 bg-primary-600">
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Recommended Contract Redlines
                </h3>
                <p className="text-xs text-primary-200 mt-0.5">Take these to your next PBM negotiation — each has the exact clause to change, the replacement language, the source authority, and the estimated dollar recovery</p>
              </div>
              <div className="divide-y divide-gray-100">
                {((rawContractAnalysis as Record<string, unknown>).redline_suggestions as Array<Record<string, unknown>>).map((redlineRaw, i) => {
                  const redline = redlineRaw as {
                    section?: string;
                    current_language?: string;
                    suggested_language?: string;
                    rationale?: string;
                    source?: string;
                    impact?: string;
                    savings_low?: number;
                    savings_high?: number;
                    savings_category?: string;
                  };
                  const hasSavings = typeof redline.savings_low === "number" && typeof redline.savings_high === "number" && (redline.savings_low > 0 || redline.savings_high > 0);
                  return (
                  <div key={i} className="px-6 py-5">
                    <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
                      <h4 className="text-sm font-semibold text-gray-900 flex-1 min-w-0">{redline.section}</h4>
                      <div className="flex items-center gap-2 flex-wrap">
                        {hasSavings && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border bg-emerald-50 text-emerald-700 border-emerald-200">
                            +{formatUsdShort(redline.savings_low)}–{formatUsdShort(redline.savings_high)}/yr
                          </span>
                        )}
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
                    </div>
                    {redline.source && (
                      <div className="mb-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium border bg-blue-50 text-blue-700 border-blue-200">
                          <BookOpen className="w-3 h-3 mr-1" />
                          {redline.source}
                        </span>
                      </div>
                    )}

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
                          onClick={() => copyRedline(i, redline.suggested_language || "")}
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

                    {/* Rationale — source is rendered as a chip above
                        the language blocks now, so this row only shows the
                        why-it-matters text. */}
                    {redline.rationale && (
                      <div className="text-xs text-gray-500">
                        <span className="font-semibold text-gray-700">Why: </span>{redline.rationale}
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
              {/* Reconciliation footer: rolls up the per-redline savings
                  chips so a customer can see "if I take all of these
                  asks to the table, I recover $X of $Y total leakage."
                  Without this, a skeptical reader notices that the
                  redline chips don't add up to the leakage banner and
                  loses trust. Showing the math explicitly closes the
                  loop. Only renders when both the redlines have savings
                  AND the leakage banner has dollar totals. */}
              {(() => {
                const redlines = ((rawContractAnalysis as Record<string, unknown>).redline_suggestions as Array<Record<string, unknown>>) || [];
                const recoveredLow = redlines.reduce((sum, r) => sum + (typeof (r as { savings_low?: number }).savings_low === "number" ? (r as { savings_low?: number }).savings_low! : 0), 0);
                const recoveredHigh = redlines.reduce((sum, r) => sum + (typeof (r as { savings_high?: number }).savings_high === "number" ? (r as { savings_high?: number }).savings_high! : 0), 0);
                const exposureEntries: FinancialExposureEntry[] = financialExposure ? [
                  financialExposure.rebate_leakage,
                  financialExposure.spread_exposure,
                  financialExposure.specialty_control,
                ].filter((e): e is FinancialExposureEntry => !!e) : [];
                const totalLeakageLow = exposureEntries.reduce((s, e) => s + (e.dollar_estimate_low ?? 0), 0);
                const totalLeakageHigh = exposureEntries.reduce((s, e) => s + (e.dollar_estimate_high ?? 0), 0);
                if (recoveredLow <= 0 && recoveredHigh <= 0) return null;
                if (totalLeakageLow <= 0 && totalLeakageHigh <= 0) return null;
                const pctLow = totalLeakageHigh > 0 ? Math.round((recoveredLow / totalLeakageHigh) * 100) : 0;
                const pctHigh = totalLeakageLow > 0 ? Math.round((recoveredHigh / totalLeakageLow) * 100) : 0;
                return (
                  <div className="px-6 py-4 bg-gradient-to-r from-emerald-50 to-blue-50 border-t border-gray-200">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700 mb-1">If you accept all redlines</p>
                    <p className="text-base font-bold text-gray-900">
                      Recover {formatUsdShort(recoveredLow)}–{formatUsdShort(recoveredHigh)}/yr
                      <span className="text-sm font-normal text-gray-600"> of {formatUsdShort(totalLeakageLow)}–{formatUsdShort(totalLeakageHigh)} total annual leakage</span>
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      Approximately {pctLow}–{pctHigh}% of total leakage is directly recoverable through these clause changes. The remaining gap reflects structural issues (e.g. specialty channel lock-in) that require vendor changes or carve-outs rather than redline language.
                    </p>
                  </div>
                );
              })()}
            </div>
          )}

          {/* ═══ UPLOAD CLAIMS FOR THIS CONTRACT ═══
              Inline claims upload tied to the current contract. When
              the user uploads a claims CSV here, it gets associated
              with this contract's row in the database and the analysis
              is re-enriched so dollar-denominated leakage figures
              replace the percentage ranges. This is the flow that
              was missing — previously claims upload was an orphaned
              page in the sidebar with no connection to any contract.
          */}
          {contractRowId !== null && (
            <div id="claims-upload" className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6 scroll-mt-20">
              <div className="flex items-center gap-2 mb-4">
                <DollarSign className="w-5 h-5 text-primary-600" />
                <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Claims Data</h2>
                {contractClaimsStatus?.has_claims && (
                  <span className="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3" />
                    {contractClaimsStatus.claims_count.toLocaleString()} claims loaded
                    {contractClaimsStatus.filename && ` from ${contractClaimsStatus.filename}`}
                  </span>
                )}
              </div>
              {contractClaimsStatus?.has_claims ? (
                <p className="text-sm text-emerald-700">
                  Claims data is loaded for this contract. The leakage estimates above reflect your plan&apos;s actual spend.
                  Upload a new CSV to replace the existing claims.
                </p>
              ) : (
                <p className="text-sm text-gray-500 mb-4">
                  Upload your pharmacy claims CSV to convert the percentage-based leakage estimates above into dollar figures based on your plan&apos;s actual spend.
                </p>
              )}
              <div className="mt-3">
                <FileUpload
                  onFileSelect={handleClaimsUpload}
                  label="Upload pharmacy claims CSV"
                />
              </div>
              {claimsUploading && (
                <div className="mt-3 flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading claims and re-computing leakage estimates...
                </div>
              )}
              {claimsUploadError && (
                <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-700">{claimsUploadError}</p>
                </div>
              )}
            </div>
          )}

          {/* ═══ STEP 2: Plan Document Upload ═══ */}
          <div id="plan-document-upload" className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className="w-5 h-5 text-primary-600" />
              <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Plan Document (SBC / SPD / EOC)</h2>
              {planBenefits && (
                <span className="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3" />
                  {planDocType || "Plan doc"} loaded
                </span>
              )}
            </div>
            {planBenefits ? (
              <p className="text-sm text-emerald-700 mb-4">
                Plan document is loaded for this contract. The cross-reference analysis below reflects your plan&apos;s benefits. Upload a new document to replace.
              </p>
            ) : (
              <p className="text-sm text-gray-500 mb-4">
                Upload the associated plan document to extract benefit structure and cross-reference against the contract.
              </p>
            )}
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
                    <BarChart3 className="w-5 h-5 text-primary-600" />
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

      {/* ═══ Sticky upload-claims CTA ═══
          Renders when a contract has been analyzed but no real claims
          have been uploaded — meaning the leakage section is showing
          percentage ranges rather than dollar figures. The banner
          sticks to the bottom of the viewport so the user is reminded
          to upload their claims to unlock dollar-denominated estimates
          for their specific plan. Dismissable for the session.
      */}
      {terms && !loading && financialExposure && !financialExposure.claims_context?.custom_data_loaded && !stickyClaimsDismissed && (
        <div className="fixed bottom-4 left-4 right-4 lg:left-72 lg:right-8 z-30">
          <div className="max-w-5xl mx-auto bg-amber-50 border border-amber-300 rounded-xl shadow-lg px-4 py-3 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <p className="text-sm text-amber-900 flex-1 leading-snug">
              <span className="font-semibold">Leakage shown as percentages.</span>{" "}
              <a href="#claims-upload" className="underline font-semibold text-amber-900 hover:text-amber-700">
                Upload your claims data
              </a>
              {" "}to convert these into specific dollar figures for your plan.
            </p>
            <button
              type="button"
              onClick={() => setStickyClaimsDismissed(true)}
              className="flex-shrink-0 p-1 text-amber-700 hover:text-amber-900 hover:bg-amber-100 rounded transition-colors"
              aria-label="Dismiss"
            >
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
