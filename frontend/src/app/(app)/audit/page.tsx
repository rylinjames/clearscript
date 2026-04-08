"use client";

import { useState, useEffect } from "react";
import { usePageTitle } from "@/components/PageTitle";
import { useToast } from "@/components/Toast";
import { Mail, Loader2, Copy, Download, Check, ClipboardList, FileText } from "lucide-react";

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

export default function AuditPage() {
  usePageTitle("Audit Generator");
  const { toast } = useToast();
  const [form, setForm] = useState({
    employerName: "",
    pbmName: "",
    contractDate: "",
    concerns: "",
  });
  const [auditType, setAuditType] = useState<"financial" | "process">("financial");
  const [loading, setLoading] = useState(false);
  const [letter, setLetter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [auditTypeInfo, setAuditTypeInfo] = useState<AuditTypeInfo | null>(null);
  const [copied, setCopied] = useState(false);

  // Contract picker state — populated by /api/contracts/list on mount.
  // selectedContractId === null means "use the most recently uploaded
  // contract" (the backend default). Any other value pins the audit
  // letter to that specific persisted contract.
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [contractsLoading, setContractsLoading] = useState(true);
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);

  useEffect(() => {
    const fetchContracts = async () => {
      try {
        const res = await fetch("/api/contracts/list");
        if (!res.ok) return;
        const data = await res.json();
        const list: ContractListItem[] = Array.isArray(data?.contracts) ? data.contracts : [];
        setContracts(list);
      } catch {
        /* picker is optional — silently leave the list empty */
      } finally {
        setContractsLoading(false);
      }
    };
    fetchContracts();
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    setLetter(null);
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
      const resolvedLetter =
        typeof data.letter === "string"
          ? data.letter
          : typeof data.letter?.letter_text === "string"
            ? data.letter.letter_text
            : typeof data.letter_payload?.letter_text === "string"
              ? data.letter_payload.letter_text
              : null;
      if (!resolvedLetter) {
        throw new Error("Audit letter response was empty. The AI engine returned no letter text — please retry.");
      }
      setLetter(resolvedLetter);
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

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Mail className="w-7 h-7 text-primary-600" />
          Audit Request Generator
        </h1>
        <p className="text-gray-500 mt-1">
          Generate a professional audit request letter based on your contract terms
        </p>
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
                onChange={(e) =>
                  setForm({ ...form, employerName: e.target.value })
                }
                placeholder="Acme Corporation"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                PBM Name
              </label>
              <input
                type="text"
                value={form.pbmName}
                onChange={(e) =>
                  setForm({ ...form, pbmName: e.target.value })
                }
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
                onChange={(e) =>
                  setForm({ ...form, contractDate: e.target.value })
                }
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

          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                Letter Preview
              </h3>
              {letter && (
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
                    {copied ? "Copied!" : "Copy"}
                  </button>
                  <button
                    onClick={handleDownload}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                </div>
              )}
            </div>
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 gap-3">
                <Loader2 className="w-6 h-6 text-primary-600 animate-spin" />
                <p className="text-xs text-gray-400">Generating letter...</p>
              </div>
            ) : error ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <p className="text-sm font-semibold text-amber-900">Audit letter generation failed</p>
                <p className="text-sm text-amber-800 mt-1">{error}</p>
              </div>
            ) : letter ? (
              <pre className="text-xs text-gray-700 whitespace-pre-wrap bg-gray-50 rounded-lg p-4 max-h-[600px] overflow-y-auto font-mono leading-relaxed border border-gray-100">
                {letter}
              </pre>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                <Mail className="w-12 h-12 mb-3" />
                <p className="text-sm">
                  Fill in the form and click Generate to create your audit letter
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
