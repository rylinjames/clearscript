"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Upload,
  FileCheck,
  RefreshCw,
  Loader2,
  Database,
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
} from "lucide-react";

interface ClaimsStatus {
  custom_data_loaded: boolean;
  claims_count: number;
  date_range_start?: string;
  date_range_end?: string;
  unique_drugs?: number;
  unique_pharmacies?: number;
  uploaded_at?: string;
  filename?: string;
}

interface UploadSummary {
  total_claims: number;
  date_range: string;
  unique_drugs: number;
  unique_pharmacies: number;
  total_plan_paid: number;
  total_rebates: number;
}

const EXPECTED_COLUMNS = [
  "claim_id",
  "drug_name",
  "ndc",
  "quantity",
  "days_supply",
  "date_filled",
  "channel",
  "pharmacy_name",
  "pharmacy_npi",
  "pharmacy_zip",
  "plan_paid",
  "pharmacy_reimbursed",
  "awp",
  "nadac_price",
  "rebate_amount",
  "formulary_tier",
];

export default function ClaimsPage() {
  const [status, setStatus] = useState<ClaimsStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<UploadSummary | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/claims/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch {
      // Silently fail on status check
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError(null);
    setSummary(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("http://localhost:8000/api/claims/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }
      setSummary(data.summary);
      setSelectedFile(null);
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Please check the CSV format.");
    } finally {
      setUploading(false);
    }
  };

  const handleReset = async () => {
    setResetting(true);
    setError(null);
    setSummary(null);
    try {
      const res = await fetch("http://localhost:8000/api/claims/reset", {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Reset failed");
      setSelectedFile(null);
      await fetchStatus();
    } catch {
      setError("Failed to reset claims data.");
    } finally {
      setResetting(false);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.toLowerCase().endsWith(".csv")) {
      setSelectedFile(file);
      setError(null);
    } else {
      setError("Please upload a .csv file");
    }
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Database className="w-7 h-7 text-[#1e3a5f]" />
          Upload Claims Data
        </h1>
        <p className="text-gray-500 mt-1">
          Upload your pharmacy claims CSV to analyze your real data across all modules
        </p>
      </div>

      {/* Status Indicator */}
      <div className={`rounded-xl border p-4 mb-6 flex items-center gap-3 ${
        status?.custom_data_loaded
          ? "bg-emerald-50 border-emerald-200"
          : "bg-blue-50 border-blue-200"
      }`}>
        {status?.custom_data_loaded ? (
          <>
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-emerald-800">
                Custom Data Loaded — {status.claims_count.toLocaleString()} claims
                {status.filename && ` from ${status.filename}`}
              </p>
              {status.date_range_start && status.date_range_end && (
                <p className="text-xs text-emerald-600 mt-0.5">
                  Date range: {status.date_range_start} to {status.date_range_end}
                  {status.unique_drugs !== undefined && ` · ${status.unique_drugs} drugs`}
                  {status.unique_pharmacies !== undefined && ` · ${status.unique_pharmacies} pharmacies`}
                </p>
              )}
            </div>
          </>
        ) : (
          <>
            <Database className="w-5 h-5 text-blue-600 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-blue-800">
                Using Sample Data — {status?.claims_count?.toLocaleString() || "500"} synthetic claims
              </p>
              <p className="text-xs text-blue-600 mt-0.5">
                Upload your own claims CSV to replace the sample data
              </p>
            </div>
          </>
        )}
      </div>

      {/* Upload Area */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Upload Claims CSV
        </h3>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
            dragOver
              ? "border-[#1e3a5f] bg-blue-50"
              : selectedFile
              ? "border-emerald-400 bg-emerald-50"
              : "border-gray-300 bg-gray-50 hover:border-[#1e3a5f] hover:bg-blue-50/50"
          }`}
        >
          <label className="cursor-pointer flex flex-col items-center gap-3">
            {selectedFile ? (
              <>
                <FileCheck className="w-10 h-10 text-emerald-500" />
                <p className="text-sm font-medium text-emerald-700">{selectedFile.name}</p>
                <p className="text-xs text-gray-500">
                  {(selectedFile.size / 1024).toFixed(1)} KB &middot; Click or drag to replace
                </p>
              </>
            ) : (
              <>
                <Upload className="w-10 h-10 text-gray-400" />
                <p className="text-sm font-medium text-gray-700">
                  Drop your pharmacy claims CSV here
                </p>
                <p className="text-xs text-gray-500">
                  Drag &amp; drop or click to browse &middot; CSV files only
                </p>
              </>
            )}
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />
          </label>
        </div>

        <div className="mt-4 flex items-center gap-3 justify-center">
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#1e3a5f] text-white rounded-lg hover:bg-[#2a4f7f] transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Upload &amp; Analyze
              </>
            )}
          </button>

          {status?.custom_data_loaded && (
            <button
              onClick={handleReset}
              disabled={resetting}
              className="inline-flex items-center gap-2 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {resetting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Resetting...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Reset to Sample Data
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Upload Summary */}
      {summary && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            Upload Summary
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Total Claims</p>
              <p className="text-2xl font-bold text-gray-900">{summary.total_claims.toLocaleString()}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Date Range</p>
              <p className="text-sm font-semibold text-gray-900 mt-1">{summary.date_range}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Unique Drugs</p>
              <p className="text-2xl font-bold text-gray-900">{summary.unique_drugs.toLocaleString()}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Unique Pharmacies</p>
              <p className="text-2xl font-bold text-gray-900">{summary.unique_pharmacies.toLocaleString()}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Total Plan Paid</p>
              <p className="text-2xl font-bold text-gray-900">${summary.total_plan_paid.toLocaleString()}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase">Total Rebates</p>
              <p className="text-2xl font-bold text-gray-900">${summary.total_rebates.toLocaleString()}</p>
            </div>
          </div>
        </div>
      )}

      {/* Expected Format */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider flex items-center gap-2">
          <FileSpreadsheet className="w-4 h-4 text-[#1e3a5f]" />
          Expected CSV Format
        </h3>
        <p className="text-sm text-gray-600 mb-3">
          Your CSV file must include the following column headers (in any order):
        </p>
        <div className="bg-gray-50 rounded-lg p-4 overflow-x-auto">
          <code className="text-xs text-gray-800 whitespace-nowrap">
            {EXPECTED_COLUMNS.join(",")}
          </code>
        </div>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-gray-500">
          <div><span className="font-medium text-gray-700">claim_id</span> — Unique claim identifier</div>
          <div><span className="font-medium text-gray-700">drug_name</span> — Drug name and strength</div>
          <div><span className="font-medium text-gray-700">ndc</span> — National Drug Code</div>
          <div><span className="font-medium text-gray-700">quantity</span> — Quantity dispensed</div>
          <div><span className="font-medium text-gray-700">days_supply</span> — Days supply</div>
          <div><span className="font-medium text-gray-700">date_filled</span> — Fill date (YYYY-MM-DD)</div>
          <div><span className="font-medium text-gray-700">channel</span> — retail, mail, or specialty</div>
          <div><span className="font-medium text-gray-700">pharmacy_name</span> — Pharmacy name</div>
          <div><span className="font-medium text-gray-700">pharmacy_npi</span> — Pharmacy NPI number</div>
          <div><span className="font-medium text-gray-700">pharmacy_zip</span> — Pharmacy ZIP code</div>
          <div><span className="font-medium text-gray-700">plan_paid</span> — Amount plan paid</div>
          <div><span className="font-medium text-gray-700">pharmacy_reimbursed</span> — Pharmacy reimbursement</div>
          <div><span className="font-medium text-gray-700">awp</span> — Average Wholesale Price</div>
          <div><span className="font-medium text-gray-700">nadac_price</span> — NADAC price</div>
          <div><span className="font-medium text-gray-700">rebate_amount</span> — Rebate amount</div>
          <div><span className="font-medium text-gray-700">formulary_tier</span> — Formulary tier (1-4)</div>
        </div>
      </div>

      {/* Info Note */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <p className="text-sm text-amber-800">
          <span className="font-semibold">Note:</span> Once uploaded, all analysis pages (Report Auditor,
          Rebate Tracker, Spread Pricing, Formulary Detector, Benchmarks) will use your data instead of
          the built-in sample data. Use the &quot;Reset to Sample Data&quot; button to switch back at any time.
        </p>
      </div>
    </div>
  );
}
