"use client";

import { useState } from "react";
import { usePageTitle } from "@/components/PageTitle";
import { useToast } from "@/components/Toast";
import { Mail, Loader2, Copy, Download, Check, ClipboardList } from "lucide-react";

const demoLetter = `[YOUR COMPANY LETTERHEAD]

Date: March 22, 2026

Re: Formal Audit Request Pursuant to Section 8.2 of PBM Services Agreement

Dear OptumRx Audit & Compliance Department,

Pursuant to Section 8.2 (Audit Rights) of the Pharmacy Benefit Management Services Agreement dated January 15, 2024, between Acme Corporation ("Plan Sponsor") and OptumRx ("PBM"), this letter constitutes a formal request to conduct an audit of PBM operations and financial records.

SCOPE OF AUDIT

The audit will examine the following areas for the period of January 1, 2025 through December 31, 2025:

1. REBATE PASSTHROUGH VERIFICATION
   - All manufacturer rebate agreements and rebate revenue received
   - Documentation of rebate passthrough calculations
   - Reconciliation of rebates received vs. rebates passed through to Plan Sponsor

2. PRICING AND SPREAD ANALYSIS
   - Ingredient cost paid to pharmacies vs. amounts billed to Plan Sponsor
   - MAC list pricing methodology and updates
   - Dispensing fee schedules by channel (retail, mail, specialty)

3. CLAIMS PROCESSING ACCURACY
   - Random sample of 500+ claims for pricing verification
   - Duplicate claim identification
   - Correct application of plan design (copays, coinsurance, deductibles)

4. FORMULARY MANAGEMENT
   - Documentation of all formulary changes during audit period
   - Evidence of required advance notifications
   - Analysis of therapeutic substitution patterns

5. NETWORK ADEQUACY
   - Current pharmacy network composition
   - Any phantom or terminated pharmacy billing
   - Network access standards compliance

AUDIT TIMELINE

Per our agreement, we are providing 60 days advance notice. The on-site audit is expected to commence on or about May 22, 2026. We request that all electronic data be made available no later than May 8, 2026.

AUDIT TEAM

The audit will be conducted by [Audit Firm Name], our designated independent auditor, with full access rights as specified in Section 8.2(c) of our agreement.

DATA REQUIREMENTS

Please prepare the following data extracts in electronic format:
- Complete claims file (all fields) for the audit period
- Rebate receipts and allocation reports
- Pharmacy reimbursement records
- Formulary change logs with effective dates
- Network pharmacy directory with status codes

CONFIDENTIALITY

All audit activities will be conducted in accordance with the confidentiality provisions of our agreement and applicable HIPAA regulations.

Please confirm receipt of this audit request and designate a point of contact for coordination within 10 business days.

Sincerely,

[Authorized Representative]
[Title]
Acme Corporation
[Contact Information]

cc: [Internal Counsel]
    [Benefits Director]`;

const auditTypeDescriptions = {
  financial: "Verify numbers -- claims, rebates, spreads match contract terms",
  process: "Evaluate PBM administration -- formulary compliance, PA turnaround, claims accuracy",
};

interface AuditTypeInfo {
  audit_type: string;
  description: string;
  checklist: string[];
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
  const [auditTypeInfo, setAuditTypeInfo] = useState<AuditTypeInfo | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    setLetter(null);
    setAuditTypeInfo(null);

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
        }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      const resolvedLetter =
        typeof data.letter === "string"
          ? data.letter
          : typeof data.letter?.letter_text === "string"
            ? data.letter.letter_text
            : typeof data.letter_payload?.letter_text === "string"
              ? data.letter_payload.letter_text
              : demoLetter;
      setLetter(resolvedLetter);
      if (data.audit_type_info) {
        setAuditTypeInfo({
          audit_type: data.audit_type_info.audit_type || auditType,
          description: data.audit_type_info.description || "",
          checklist: data.audit_type_info.checklist || data.audit_type_info.checks || [],
        });
      }
    } catch {
      setLetter(demoLetter);
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
