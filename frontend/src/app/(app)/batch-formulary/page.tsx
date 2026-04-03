"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { usePageTitle } from "@/components/PageTitle";
import MetricCard from "@/components/MetricCard";
import StatusBadge from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import {
  Loader2,
  FolderUp,
  FileCheck,
  Upload,
  Search,
  FileSpreadsheet,
  Layers,
  Pill,
  MapPin,
} from "lucide-react";

interface ProcessingStats {
  filesParsed: number;
  totalDrugs: number;
  plansIndexed: number;
}

interface DrugTierResult {
  drugName: string;
  ndc: string;
  plans: { planName: string; state: string; tier: string }[];
}

interface StateComparison {
  state: string;
  planCount: number;
  avgFormularySize: number;
  avgTier1Pct: number;
  avgTier4Pct: number;
}

export default function BatchFormularyPage() {
  const { toast } = useToast();
  usePageTitle("Batch Formulary");
  const [files, setFiles] = useState<File[]>([]);
  const [processing, setProcessing] = useState(false);
  const [stats, setStats] = useState<ProcessingStats | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<DrugTierResult[]>([]);
  const [states, setStates] = useState<StateComparison[]>([]);
  const [loadingStates, setLoadingStates] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const handleFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleProcess = async () => {
    if (files.length === 0) return;
    setProcessing(true);
    setStats(null);
    setSearchResults([]);
    setStates([]);
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    try {
      const res = await fetch("/api/batch-formulary/process", { method: "POST", body: formData });
      if (res.ok) {
        setStats(await res.json());
        toast(`${files.length} files processed successfully`, "success");
      } else {
        toast("Failed to process formulary files", "error");
      }
    } catch {
      toast("Failed to process formulary files", "error");
    }
    setProcessing(false);
  };

  const searchDrugs = useCallback(async (q: string) => {
    if (q.length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(`/api/batch-formulary/search?q=${encodeURIComponent(q)}`);
      if (res.ok) setSearchResults(await res.json());
    } catch {
      /* silent */
    }
    setSearching(false);
  }, []);

  useEffect(() => {
    if (!stats) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => searchDrugs(searchQuery), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery, searchDrugs, stats]);

  const fetchStates = useCallback(async () => {
    setLoadingStates(true);
    try {
      const res = await fetch("/api/batch-formulary/states");
      if (res.ok) setStates(await res.json());
    } catch {
      /* silent */
    }
    setLoadingStates(false);
  }, []);

  useEffect(() => {
    if (stats) fetchStates();
  }, [stats, fetchStates]);

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <FolderUp className="w-7 h-7 text-primary-600" />
          Batch Formulary Processor
        </h1>
        <p className="text-gray-500 mt-1">
          Upload multiple Cigna formulary PDFs to index, search, and compare across plans and states
        </p>
      </div>

      {/* Multi-file Upload */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Upload Formulary PDFs
        </h3>
        <div
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
            files.length > 0
              ? "border-emerald-400 bg-emerald-50"
              : "border-gray-300 bg-gray-50 hover:border-primary-600 hover:bg-blue-50/50"
          }`}
        >
          {files.length > 0 ? (
            <div className="flex flex-col items-center gap-2">
              <FileCheck className="w-10 h-10 text-emerald-500" />
              <p className="text-sm font-medium text-emerald-700">{files.length} file(s) selected</p>
              <p className="text-xs text-gray-500">
                {files.map((f) => f.name).join(", ")}
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-10 h-10 text-gray-400" />
              <p className="text-sm font-medium text-gray-700">Click to select formulary PDFs</p>
              <p className="text-xs text-gray-500">Select multiple PDF files</p>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFilesChange}
            className="hidden"
          />
        </div>
        <div className="mt-4 flex justify-center">
          <button
            onClick={handleProcess}
            disabled={files.length === 0 || processing}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
          >
            {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4" />}
            Process Files
          </button>
        </div>
      </div>

      {/* Processing Stats */}
      {stats && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <MetricCard icon={FileSpreadsheet} label="Files Parsed" value={String(stats.filesParsed)} color="blue" />
            <MetricCard icon={Pill} label="Total Drugs" value={stats.totalDrugs.toLocaleString()} color="green" />
            <MetricCard icon={Layers} label="Plans Indexed" value={String(stats.plansIndexed)} color="blue" />
          </div>

          {/* Drug Search Across Plans */}
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
              Search Drugs Across Plans
            </h3>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by drug name..."
                className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              />
              {searching && <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-primary-600 animate-spin" />}
            </div>
          </div>

          {searchResults.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                  Tier by Plan/State
                </h3>
              </div>
              {searchResults.map((drug, i) => (
                <div key={i} className="p-6 border-b border-gray-100 last:border-b-0">
                  <p className="text-sm font-semibold text-gray-900 mb-2">{drug.drugName} <span className="text-xs text-gray-400 font-mono ml-2">{drug.ndc}</span></p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    {drug.plans.map((p, j) => (
                      <div key={j} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                        <div>
                          <p className="text-xs font-medium text-gray-900">{p.planName}</p>
                          <p className="text-xs text-gray-500">{p.state}</p>
                        </div>
                        <StatusBadge
                          status={p.tier === "Tier 1" ? "good" : p.tier === "Tier 4" ? "critical" : "info"}
                          label={p.tier}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* State Comparison Table */}
          {loadingStates ? (
            <div className="flex items-center justify-center py-8 gap-2">
              <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
              <span className="text-sm text-gray-500">Loading state comparison...</span>
            </div>
          ) : states.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-primary-600" />
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                  State Comparison
                </h3>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">State</th>
                    <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Plans</th>
                    <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Avg Formulary Size</th>
                    <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Tier 1 %</th>
                    <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Tier 4 %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {states.map((s, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-gray-900">{s.state}</td>
                      <td className="px-6 py-3 text-right text-gray-700">{s.planCount}</td>
                      <td className="px-6 py-3 text-right text-gray-700">{s.avgFormularySize.toLocaleString()}</td>
                      <td className="px-6 py-3 text-right text-emerald-700 font-medium">{s.avgTier1Pct}%</td>
                      <td className="px-6 py-3 text-right text-red-700 font-medium">{s.avgTier4Pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
