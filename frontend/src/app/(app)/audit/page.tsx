"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { usePageTitle } from "@/components/PageTitle";
import { useToast } from "@/components/Toast";
import { Mail, Loader2, Copy, Download, Check, ClipboardList, FileText, AlertTriangle, BookOpen, Scale, Send, ArrowLeft } from "lucide-react";
import AIAnalysisProgress from "@/components/AIAnalysisProgress";

const auditTypeDescriptions = {
  financial: "Verify numbers -- claims, rebates, spreads match contract terms",
  process: "Evaluate PBM administration -- formulary compliance, PA turnaround, claims accuracy",
};

interface AuditTypeInfo {
  audit_type: string;
  description: string;
  checklist: string[];
}

interface ContractListItem {
  id: number;
  filename: string;
  analysis_date: string | null;
  deal_score: number | null;
  risk_level: string | null;
}

// Subset of the full contract analysis the audit page needs to (1)
// auto-populate the form fields and (2) preview which findings will be
// cited in the generated letter. Fetched from /api/contracts/{id} when
// the user picks a contract from the dropdown.
interface ContractAnalysisDetail {
  id?: number;
  filename?: string;
  analysis_date?: string | null;
  analysis?: {
    contract_identification?: {
      plan_sponsor_name?: string | null;
      pbm_name?: string | null;
      effective_date?: string | null;
    };
    top_risks?: Array<{ title?: string; tier?: number; severity?: string }>;
    redline_suggestions?: Array<{ section?: string }>;
    audit_implication?: string;
  };
}

// Structured letter payload returned by the AI. Each section renders
// as its own card so the user can review/copy them independently.
// `letter_text` is the full assembled letter for one-shot copy/download.
interface SpecificDemand {
  demand: string;
  contract_section?: string | null;
  data_requested?: string;
}

interface LegalAuthority {
  citation: string;
  explanation: string;
}

interface LetterPayload {
  subject_line?: string;
  recipient_block?: string;
  opening_paragraph?: string;
  background_paragraph?: string;
  specific_demands?: SpecificDemand[];
  legal_authority?: LegalAuthority[];
  response_deadline_paragraph?: string;
  closing_paragraph?: string;
  signature_block?: string;
  deadline_iso?: string;
  letter_text?: string;
}

interface DataProvenance {
  has_analyzed_contract: boolean;
  has_real_claims_data: boolean;
  contract_filename?: string | null;
  contract_id?: number | null;
  contract_analysis_date?: string | null;
}

export default function AuditPage() {
  usePageTitle("Audit Generator");
  const { toast } = useToast();
  // The Plan Intelligence "Draft Audit Letter" button deep-links here
  // with ?contract_id={id} so the picker can be pre-pinned to that
  // exact uploaded contract instead of forcing the user to re-find it.
  const searchParams = useSearchParams();
  const deepLinkContractId = (() => {
    const raw = searchParams.get("contract_id");
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : null;
  })();

  const [form, setForm] = useState({
    employerName: "",
    pbmName: "",
    contractDate: "",
    concerns: "",
  });
  const [auditType, setAuditType] = useState<"financial" | "process">("financial");
  const [loading, setLoading] = useState(false);
  const [letter, setLetter] = useState<string | null>(null);
  const [letterPayload, setLetterPayload] = useState<LetterPayload | null>(null);
  const [provenance, setProvenance] = useState<DataProvenance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [auditTypeInfo, setAuditTypeInfo] = useState<AuditTypeInfo | null>(null);
  const [copied, setCopied] = useState(false);

  // Contract picker state — populated by /api/contracts/list on mount.
  // selectedContractId === null means "use the most recently uploaded
  // contract" (the backend default). Any other value pins the audit
  // letter to that specific persisted contract.
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [contractsLoading, setContractsLoading] = useState(true);
  const [selectedContractId, setSelectedContractId] = useState<number | null>(deepLinkContractId);

  // Full analysis for the picked contract — fetched on selection so we
  // can (1) auto-populate the form fields and (2) preview which findings
  // will be cited in the generated letter BEFORE the user hits Generate.
  // Without this preview the user is firing blind into a 28-second AI call.
  const [pickedContractDetail, setPickedContractDetail] = useState<ContractAnalysisDetail | null>(null);
  const [pickedDetailLoading, setPickedDetailLoading] = useState(false);

  // Track which form fields the user has manually edited so we don't
  // overwrite their typing when they pick a different contract.
  const [manuallyEdited, setManuallyEdited] = useState<{ employerName: boolean; pbmName: boolean; contractDate: boolean }>({
    employerName: false,
    pbmName: false,
    contractDate: false,
  });

  useEffect(() => {
    const fetchContracts = async () => {
      try {
        const res = await fetch("/api/contracts/list");
        if (!res.ok) return;
        const data = await res.json();
        const list: ContractListItem[] = Array.isArray(data?.contracts) ? data.contracts : [];
        setContracts(list);
        // If the URL deep-link contract id matches one in the picker,
        // honor it. If it doesn't (the contract was deleted or the
        // deep-link is stale), silently fall back to "most recent".
        if (deepLinkContractId !== null && list.some((c) => c.id === deepLinkContractId)) {
          setSelectedContractId(deepLinkContractId);
        }
      } catch {
        /* picker is optional — silently leave the list empty */
      } finally {
        setContractsLoading(false);
      }
    };
    fetchContracts();
  }, [deepLinkContractId]);

  // Fetch the full analysis for whichever contract is currently picked.
  // This drives both the auto-populate flow and the citation preview.
  // When selectedContractId is null we resolve "most recent" to the first
  // item in the contracts list (which is sorted most-recent-first by the
  // backend).
  const resolvedContractId =
    selectedContractId !== null ? selectedContractId : (contracts[0]?.id ?? null);

  useEffect(() => {
    if (resolvedContractId === null) {
      setPickedContractDetail(null);
      return;
    }
    let cancelled = false;
    const fetchDetail = async () => {
      setPickedDetailLoading(true);
      try {
        const res = await fetch(`/api/contracts/${resolvedContractId}`);
        if (!res.ok) {
          if (!cancelled) setPickedContractDetail(null);
          return;
        }
        const data = await res.json();
        if (!cancelled) {
          setPickedContractDetail(data?.contract || null);
        }
      } catch {
        if (!cancelled) setPickedContractDetail(null);
      } finally {
        if (!cancelled) setPickedDetailLoading(false);
      }
    };
    fetchDetail();
    return () => {
      cancelled = true;
    };
  }, [resolvedContractId]);

  // Auto-populate form fields from the picked contract's
  // contract_identification block. Skip any field the user has already
  // manually edited so we don't trample their typing. Re-runs whenever
  // the user picks a new contract.
  useEffect(() => {
    const cid = pickedContractDetail?.analysis?.contract_identification;
    if (!cid) return;
    setForm((prev) => ({
      employerName: manuallyEdited.employerName ? prev.employerName : (cid.plan_sponsor_name || prev.employerName),
      pbmName: manuallyEdited.pbmName ? prev.pbmName : (cid.pbm_name || prev.pbmName),
      contractDate: manuallyEdited.contractDate ? prev.contractDate : (cid.effective_date || prev.contractDate),
      concerns: prev.concerns,
    }));
  }, [pickedContractDetail, manuallyEdited]);

  const updateField = useCallback((field: "employerName" | "pbmName" | "contractDate", value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setManuallyEdited((prev) => ({ ...prev, [field]: true }));
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    setLetter(null);
    setLetterPayload(null);
    setProvenance(null);
    setAuditTypeInfo(null);
    setError(null);

    try {
      const res = await fetch("/api/audit/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          employer_name: form.employerName,
          pbm_name: form.pbmName,
          contract_date: form.contractDate,
          concerns: form.concerns,
          audit_type: auditType,
          // Pin the letter to a specific uploaded contract if the user
          // picked one, otherwise let the backend default to the most
          // recent upload.
          contract_id: selectedContractId,
        }),
      });
      if (!res.ok) {
        let detail = `Audit letter generation failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      const data = await res.json();
      const payload: LetterPayload | null = (data.letter_payload && typeof data.letter_payload === "object")
        ? data.letter_payload as LetterPayload
        : null;
      const resolvedLetter =
        typeof data.letter === "string"
          ? data.letter
          : payload?.letter_text || null;
      if (!resolvedLetter && !payload) {
        throw new Error("Audit letter response was empty. The AI engine returned no letter text — please retry.");
      }
      setLetter(resolvedLetter);
      setLetterPayload(payload);
      if (data.data_provenance && typeof data.data_provenance === "object") {
        setProvenance(data.data_provenance as DataProvenance);
      }
      if (data.audit_type_info) {
        setAuditTypeInfo({
          audit_type: data.audit_type_info.audit_type || auditType,
          description: data.audit_type_info.description || "",
          checklist: data.audit_type_info.checklist || data.audit_type_info.checks || [],
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Audit letter generation failed");
    } finally {
      setLoading(false);
    }
  };

  const copySection = async (text: string, label: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      toast(`${label} copied to clipboard`, "success");
    } catch {
      toast("Could not copy to clipboard", "error");
    }
  };

  const handleCopy = async () => {
    if (letter) {
      await navigator.clipboard.writeText(letter);
      setCopied(true);
      toast("Audit letter copied to clipboard", "success");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (!letter) return;
    const blob = new Blob([letter], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-request-${form.pbmName || "PBM"}-${new Date().toISOString().split("T")[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast("Audit letter downloaded", "success");
  };

  // Resolve the contract id to use for the "Back to Plan Intelligence"
  // link. Prefer the explicit user pick, fall back to the first
  // available contract (most recent), so the link still works in the
  // common deep-link-from-contracts-page flow.
  const backLinkContractId = selectedContractId !== null
    ? selectedContractId
    : (contracts[0]?.id ?? null);

  return (
    <div className="animate-fade-in">
      <div className="mb-8 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <Mail className="w-7 h-7 text-primary-600" />
            Audit Request Generator
          </h1>
          <p className="text-gray-500 mt-1">
            Generate a professional audit request letter based on your contract terms
          </p>
        </div>
        {backLinkContractId !== null && (
          <Link
            href={`/contracts?contract_id=${backLinkContractId}`}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors flex-shrink-0"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Plan Intelligence
          </Link>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
            Audit Details
          </h3>
          <div className="space-y-4">
            {/* Contract picker — choose which uploaded contract to audit */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Contract to audit
              </label>
              {contractsLoading ? (
                <div className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-sm text-gray-500">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Loading uploaded contracts...
                </div>
              ) : contracts.length === 0 ? (
                <div className="px-3 py-3 border border-amber-200 rounded-lg bg-amber-50">
                  <p className="text-sm text-amber-900 font-medium">No analyzed contracts yet</p>
                  <p className="text-xs text-amber-800 mt-1">
                    Upload a PBM contract on the Plan Intelligence page first. The audit
                    letter will reference findings from that specific contract instead of
                    making things up.
                  </p>
                </div>
              ) : (
                <>
                  <select
                    value={selectedContractId === null ? "__latest__" : String(selectedContractId)}
                    onChange={(e) =>
                      setSelectedContractId(
                        e.target.value === "__latest__" ? null : Number(e.target.value)
                      )
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none bg-white"
                  >
                    <option value="__latest__">Most recently uploaded contract</option>
                    {contracts.map((c) => {
                      const dateStr = c.analysis_date ? c.analysis_date.split(" ")[0] : "unknown date";
                      const score = c.deal_score !== null ? ` · score ${c.deal_score}/100` : "";
                      const risk = c.risk_level ? ` · ${c.risk_level}` : "";
                      return (
                        <option key={c.id} value={c.id}>
                          {c.filename} ({dateStr}{score}{risk})
                        </option>
                      );
                    })}
                  </select>
                  <p className="text-xs text-gray-500 mt-1.5 flex items-center gap-1.5">
                    <FileText className="w-3 h-3" />
                    {contracts.length} contract{contracts.length === 1 ? "" : "s"} available. The letter will cite findings from the contract you pick.
                  </p>
                </>
              )}
            </div>

            {/* Audit Type Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Audit Type
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setAuditType("financial")}
                  className={`relative rounded-lg border-2 p-4 text-left transition-all ${
                    auditType === "financial"
                      ? "border-primary-600 bg-blue-50 ring-1 ring-primary-600"
                      : "border-gray-200 hover:border-gray-300 bg-white"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                      auditType === "financial" ? "border-primary-600" : "border-gray-300"
                    }`}>
                      {auditType === "financial" && (
                        <div className="w-2 h-2 rounded-full bg-primary-600" />
                      )}
                    </div>
                    <span className="text-sm font-semibold text-gray-900">Financial Audit</span>
                  </div>
                  <p className="text-xs text-gray-500 ml-6">
                    {auditTypeDescriptions.financial}
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => setAuditType("process")}
                  className={`relative rounded-lg border-2 p-4 text-left transition-all ${
                    auditType === "process"
                      ? "border-primary-600 bg-blue-50 ring-1 ring-primary-600"
                      : "border-gray-200 hover:border-gray-300 bg-white"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                      auditType === "process" ? "border-primary-600" : "border-gray-300"
                    }`}>
                      {auditType === "process" && (
                        <div className="w-2 h-2 rounded-full bg-primary-600" />
                      )}
                    </div>
                    <span className="text-sm font-semibold text-gray-900">Process Audit</span>
                  </div>
                  <p className="text-xs text-gray-500 ml-6">
                    {auditTypeDescriptions.process}
                  </p>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Employer Name
              </label>
              <input
                type="text"
                value={form.employerName}
                onChange={(e) => updateField("employerName", e.target.value)}
                placeholder="Acme Corporation"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none"
              />
              {pickedContractDetail?.analysis?.contract_identification?.plan_sponsor_name && !manuallyEdited.employerName && (
                <p className="text-[11px] text-gray-500 mt-1">Auto-filled from {pickedContractDetail.filename}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                PBM Name
              </label>
              <input
                type="text"
                value={form.pbmName}
                onChange={(e) => updateField("pbmName", e.target.value)}
                placeholder="OptumRx"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contract Date
              </label>
              <input
                type="date"
                value={form.contractDate}
                onChange={(e) => updateField("contractDate", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Specific Concerns
              </label>
              <textarea
                value={form.concerns}
                onChange={(e) =>
                  setForm({ ...form, concerns: e.target.value })
                }
                placeholder="e.g., Suspected spread pricing on generics, rebate passthrough below contracted rate, mail-order steering..."
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none resize-none"
              />
            </div>
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Mail className="w-4 h-4" />
              )}
              Generate Audit Letter
            </button>
          </div>
        </div>

        <div className="space-y-6">
          {/* ═══ Citation preview ═══
              Shows the user EXACTLY which contract findings will be cited
              in the generated letter, BEFORE they spend 28 seconds on an
              AI call. The preview is built from the picked contract's
              top_risks, redline_suggestions section names, and
              audit_implication. Without this the user is firing blind.
          */}
          {pickedContractDetail && pickedContractDetail.analysis && !letter && !loading && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-600">Letter will reference</p>
                  <h3 className="text-sm font-bold text-gray-900 mt-0.5">Findings from this contract</h3>
                </div>
                {pickedDetailLoading && <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />}
              </div>
              {pickedContractDetail.analysis.contract_identification && (
                <p className="text-xs text-gray-500 mb-3 leading-relaxed">
                  {pickedContractDetail.analysis.contract_identification.pbm_name || "PBM"}
                  {" × "}
                  {pickedContractDetail.analysis.contract_identification.plan_sponsor_name || "Plan sponsor"}
                  {pickedContractDetail.filename && ` — ${pickedContractDetail.filename}`}
                </p>
              )}

              {pickedContractDetail.analysis.top_risks && pickedContractDetail.analysis.top_risks.length > 0 && (
                <div className="mb-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-1.5">Top risks</p>
                  <ul className="space-y-1">
                    {pickedContractDetail.analysis.top_risks.slice(0, 5).map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-700">
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold mt-0.5 ${
                          r.severity === "high" ? "bg-red-100 text-red-700" : r.severity === "medium" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                        }`}>
                          T{r.tier ?? "?"}
                        </span>
                        <span>{r.title}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {pickedContractDetail.analysis.redline_suggestions && pickedContractDetail.analysis.redline_suggestions.length > 0 && (
                <div className="mb-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-1.5">
                    Contract sections to be cited ({pickedContractDetail.analysis.redline_suggestions.length})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {pickedContractDetail.analysis.redline_suggestions.slice(0, 8).map((rl, i) => (
                      rl.section ? (
                        <span key={i} className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-700 border border-gray-200">
                          {rl.section}
                        </span>
                      ) : null
                    ))}
                  </div>
                </div>
              )}

              {pickedContractDetail.analysis.audit_implication && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-blue-700 mb-1">Audit interpretation</p>
                  <p className="text-xs text-gray-700 leading-relaxed">{pickedContractDetail.analysis.audit_implication}</p>
                </div>
              )}

              <p className="text-[11px] text-gray-500 mt-3 italic">
                The AI will use these findings as the basis for the letter&apos;s demands and legal authority sections. It will not invent facts beyond what&apos;s shown here.
              </p>
            </div>
          )}

          {/* Audit Type Info Checklist */}
          {auditTypeInfo && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
              <div className="flex items-center gap-2 mb-4">
                <ClipboardList className="w-4 h-4 text-primary-600" />
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                  {auditTypeInfo.audit_type === "financial" ? "Financial" : "Process"} Audit Checklist
                </h3>
              </div>
              {auditTypeInfo.description && (
                <p className="text-sm text-gray-600 mb-3">{auditTypeInfo.description}</p>
              )}
              <ul className="space-y-2">
                {auditTypeInfo.checklist.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-emerald-500 mt-0.5 flex-shrink-0">&#10003;</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ═══ Loading / error / empty / structured letter render ═══ */}
          {loading ? (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
              <AIAnalysisProgress
                variant="audit_letter"
                filename={form.pbmName ? `${form.pbmName} audit letter` : null}
                estimatedSeconds={28}
              />
            </div>
          ) : error ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-amber-900">Audit letter generation failed</p>
              <p className="text-sm text-amber-800 mt-1">{error}</p>
            </div>
          ) : letterPayload || letter ? (
            <>
              {/* Data provenance banner — tells the user EXACTLY what the
                  letter was grounded in. Without this they have no way to
                  know whether the letter cited their actual contract
                  findings or was written from generic templates. */}
              {provenance && (
                <div className={`rounded-xl border p-4 ${
                  provenance.has_analyzed_contract
                    ? "bg-emerald-50 border-emerald-200"
                    : "bg-amber-50 border-amber-200"
                }`}>
                  <div className="flex items-start gap-3">
                    {provenance.has_analyzed_contract ? (
                      <Check className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-semibold ${provenance.has_analyzed_contract ? "text-emerald-900" : "text-amber-900"}`}>
                        {provenance.has_analyzed_contract ? "Generated from your uploaded contract" : "Generated without a contract analysis"}
                      </p>
                      <p className={`text-xs mt-1 leading-relaxed ${provenance.has_analyzed_contract ? "text-emerald-800" : "text-amber-800"}`}>
                        {provenance.has_analyzed_contract
                          ? `This letter cites findings from ${provenance.contract_filename || "your uploaded contract"}${provenance.contract_analysis_date ? ` (analyzed ${provenance.contract_analysis_date.split(" ")[0]})` : ""}.`
                          : "No contract was analyzed — the letter was written using generic ERISA audit language. For a stronger draft, upload a PBM contract on the Plan Intelligence page first."}
                        {" "}
                        {provenance.has_real_claims_data
                          ? "Claims data was available — the letter references specific reconciliation findings."
                          : "No claims data was uploaded — the letter requests data rather than asserting findings about it."}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* ═══ Structured letter sections ═══ */}
              {letterPayload?.subject_line && (
                <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Subject Line</p>
                    <button onClick={() => copySection(letterPayload.subject_line || "", "Subject")} className="text-[11px] text-gray-500 hover:text-gray-900 inline-flex items-center gap-1">
                      <Copy className="w-3 h-3" /> Copy
                    </button>
                  </div>
                  <p className="text-base font-bold text-gray-900">{letterPayload.subject_line}</p>
                </div>
              )}

              {letterPayload?.recipient_block && (
                <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500 mb-2">Recipient</p>
                  <p className="text-sm text-gray-800 whitespace-pre-line leading-relaxed">{letterPayload.recipient_block}</p>
                </div>
              )}

              {(letterPayload?.opening_paragraph || letterPayload?.background_paragraph) && (
                <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500 mb-2">Background</p>
                  {letterPayload.opening_paragraph && (
                    <p className="text-sm text-gray-800 leading-relaxed mb-3">{letterPayload.opening_paragraph}</p>
                  )}
                  {letterPayload.background_paragraph && (
                    <p className="text-sm text-gray-800 leading-relaxed">{letterPayload.background_paragraph}</p>
                  )}
                </div>
              )}

              {letterPayload?.specific_demands && letterPayload.specific_demands.length > 0 && (
                <div className="bg-white rounded-xl border-2 border-primary-200 shadow-[var(--shadow-card)] overflow-hidden">
                  <div className="px-5 py-3 bg-primary-50 border-b border-primary-100 flex items-center gap-2">
                    <Send className="w-4 h-4 text-primary-600" />
                    <h3 className="text-sm font-bold text-primary-900 uppercase tracking-wider">Specific Demands</h3>
                    <span className="ml-auto text-xs text-primary-700">{letterPayload.specific_demands.length} {letterPayload.specific_demands.length === 1 ? "ask" : "asks"}</span>
                  </div>
                  <ol className="divide-y divide-gray-100">
                    {letterPayload.specific_demands.map((d, i) => (
                      <li key={i} className="px-5 py-4">
                        <div className="flex items-start gap-3">
                          <span className="flex-shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary-600 text-white text-xs font-bold">
                            {i + 1}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-gray-900 leading-relaxed">{d.demand}</p>
                            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                              {d.contract_section && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                                  <FileText className="w-3 h-3 mr-1" />
                                  {d.contract_section}
                                </span>
                              )}
                              {d.data_requested && (
                                <span className="text-[11px] text-gray-500">{d.data_requested}</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {letterPayload?.legal_authority && letterPayload.legal_authority.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
                  <div className="px-5 py-3 bg-blue-50 border-b border-blue-100 flex items-center gap-2">
                    <Scale className="w-4 h-4 text-blue-700" />
                    <h3 className="text-sm font-bold text-blue-900 uppercase tracking-wider">Legal Authority</h3>
                  </div>
                  <ul className="divide-y divide-gray-100">
                    {letterPayload.legal_authority.map((a, i) => (
                      <li key={i} className="px-5 py-3">
                        <div className="flex items-start gap-3">
                          <BookOpen className="w-4 h-4 text-blue-700 flex-shrink-0 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-gray-900">{a.citation}</p>
                            <p className="text-xs text-gray-600 mt-1 leading-relaxed">{a.explanation}</p>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {letterPayload?.response_deadline_paragraph && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700 mb-2">Response Deadline</p>
                  <p className="text-sm text-amber-900 leading-relaxed">{letterPayload.response_deadline_paragraph}</p>
                  {letterPayload.deadline_iso && (
                    <p className="text-xs text-amber-800 mt-2 font-semibold">Calculated deadline: {letterPayload.deadline_iso}</p>
                  )}
                </div>
              )}

              {(letterPayload?.closing_paragraph || letterPayload?.signature_block) && (
                <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
                  {letterPayload.closing_paragraph && (
                    <p className="text-sm text-gray-800 leading-relaxed mb-3">{letterPayload.closing_paragraph}</p>
                  )}
                  {letterPayload.signature_block && (
                    <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">{letterPayload.signature_block}</p>
                  )}
                </div>
              )}

              {/* Full-letter actions footer — copy/download the entire
                  assembled letter at once for users who want to drop it
                  into Word and reformat from there. */}
              {letter && (
                <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-4 flex items-center justify-between gap-3">
                  <p className="text-xs text-gray-500">Need the whole letter as a single block?</p>
                  <div className="flex gap-2">
                    <button
                      onClick={handleCopy}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      {copied ? (
                        <Check className="w-3.5 h-3.5 text-emerald-500" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                      {copied ? "Copied!" : "Copy full letter"}
                    </button>
                    <button
                      onClick={handleDownload}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download .txt
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
              <div className="flex flex-col items-center justify-center py-16 text-gray-400">
                <Mail className="w-12 h-12 mb-3" />
                <p className="text-sm text-center">
                  Fill in the form and click Generate to draft your audit letter.
                </p>
                <p className="text-xs text-center mt-1 max-w-xs">
                  The letter will be structured into discrete sections so you can review, edit, and copy each piece independently.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
