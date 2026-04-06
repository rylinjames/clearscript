"use client";

import { useState, useEffect, useCallback } from "react";
import { usePageTitle } from "@/components/PageTitle";
import StatusBadge from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import ExportButton from "@/components/ExportButton";
import { DollarSign, Loader2, AlertTriangle, RefreshCw, Database, CheckCircle2, Scale } from "lucide-react";

interface RebateDrug {
  drug: string;
  manufacturer: string;
  totalRebate: number;
  passedThrough: number;
  retained: number;
  retainedPct: number;
}

interface RebateData {
  totalRebates: number;
  totalPassedThrough: number;
  totalRetained: number;
  leakagePct: number;
  drugs: RebateDrug[];
}

function formatCurrency(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function FlowBar({ label, total, passed, retained }: { label: string; total: number; passed: number; retained: number }) {
  const passedPct = (passed / total) * 100;
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span>{formatCurrency(total)}</span>
      </div>
      <div className="h-6 bg-gray-100 rounded-full overflow-hidden flex">
        <div className="bg-emerald-500 h-full flex items-center justify-center text-[10px] text-white font-semibold" style={{ width: `${passedPct}%` }}>
          {passedPct.toFixed(0)}% passed
        </div>
        <div className="bg-red-400 h-full flex items-center justify-center text-[10px] text-white font-semibold" style={{ width: `${100 - passedPct}%` }}>
          {(100 - passedPct).toFixed(0)}% retained
        </div>
      </div>
    </div>
  );
}

interface ClaimsStatus {
  custom_data_loaded: boolean;
  claims_count: number;
  filename?: string;
}

export default function RebatesPage() {
  const { toast } = useToast();
  usePageTitle("Rebate Tracker");
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<RebateData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [claimsStatus, setClaimsStatus] = useState<ClaimsStatus | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchClaimsStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/claims/status");
      if (res.ok) setClaimsStatus(await res.json());
    } catch { /* ignore */ }
  }, []);

  const fetchData = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch("/api/rebates/analysis");
      if (!res.ok) {
        let detail = `Rebate analysis failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      const json = await res.json();
      const ra = json?.rebate_analysis;
      if (!ra) {
        throw new Error("Rebate analysis response was missing the expected `rebate_analysis` field.");
      }
      const manufacturers: Record<string, string> = {
        "Trulicity": "Eli Lilly", "Ozempic": "Novo Nordisk", "Humira": "AbbVie",
        "Insulin Glargine": "Sanofi", "Stelara": "J&J", "Eliquis": "BMS/Pfizer",
        "Jardiance": "Boehringer", "Keytruda": "Merck", "Dupixent": "Regeneron/Sanofi",
        "Skyrizi": "AbbVie", "Xarelto": "J&J/Bayer",
      };
      setData({
        totalRebates: ra.total_rebates_earned,
        totalPassedThrough: ra.rebates_passed_to_plan,
        totalRetained: ra.rebates_retained_by_pbm,
        leakagePct: ra.leakage_pct,
        drugs: (ra.top_leakage_drugs || []).map((d: Record<string, unknown>) => {
          const name = (d.drug_name as string) || "";
          const baseName = name.split(" ")[0];
          return {
            drug: name,
            manufacturer: manufacturers[baseName] || "Pharmaceutical Co.",
            totalRebate: (d.total_rebate as number) || 0,
            passedThrough: (d.amount_passed as number) || 0,
            retained: (d.amount_retained_by_pbm as number) || 0,
            retainedPct: d.passthrough_rate ? 100 - (d.passthrough_rate as number) : 0,
          };
        }),
      });
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : "Rebate analysis failed");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchClaimsStatus();
    fetchData();
  }, [fetchClaimsStatus, fetchData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    fetchClaimsStatus();
    await fetchData();
    toast("Analysis refreshed", "success");
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading rebate analysis...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="animate-fade-in">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <DollarSign className="w-7 h-7 text-primary-600" />
            Rebate Passthrough Tracker
          </h1>
          <p className="text-gray-500 mt-1">Track manufacturer rebate flow from PBM to plan sponsor</p>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-amber-900">Rebate analysis is unavailable</p>
              <p className="text-sm text-amber-800 mt-1">
                {error || "The rebate analysis service did not return data. Upload claims data on the Claims page, then come back."}
              </p>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-900 bg-white border border-amber-300 rounded-md hover:bg-amber-50 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <DollarSign className="w-7 h-7 text-primary-600" />
          Rebate Passthrough Tracker
        </h1>
        <p className="text-gray-500 mt-1">
          Track manufacturer rebate flow from PBM to plan sponsor
        </p>
      </div>

      {/* Data Source Banner */}
      <div className={`rounded-lg border px-4 py-2.5 mb-4 flex items-center justify-between ${
        claimsStatus?.custom_data_loaded
          ? "bg-emerald-50 border-emerald-200"
          : "bg-blue-50 border-blue-200"
      }`}>
        <div className="flex items-center gap-2">
          {claimsStatus?.custom_data_loaded ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          ) : (
            <Database className="w-4 h-4 text-blue-600" />
          )}
          <span className={`text-sm font-medium ${claimsStatus?.custom_data_loaded ? "text-emerald-800" : "text-blue-800"}`}>
            Analyzing: {claimsStatus?.custom_data_loaded
              ? `Your Uploaded Data (${claimsStatus.claims_count.toLocaleString()} claims)`
              : `Sample Claims Data (${claimsStatus?.claims_count?.toLocaleString() || "500"} claims)`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <ExportButton
            data={data.drugs.map(d => ({ Drug: d.drug, Manufacturer: d.manufacturer, "Total Rebate": d.totalRebate, "Passed Through": d.passedThrough, Retained: d.retained, "% Retained": d.retainedPct })) as unknown as Record<string, unknown>[]}
            filename="rebate-analysis"
            label="Export CSV"
          />
          <button onClick={handleRefresh} disabled={refreshing} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh Analysis
          </button>
        </div>
      </div>

      {/* Contract vs Reality Callout */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl p-5 mb-6 text-white">
        <div className="flex items-center gap-3">
          <Scale className="w-7 h-7 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold">Contract vs Reality</p>
            <p className="text-sm text-blue-200">
              Your contract guarantees 100% rebate passthrough (per HR 7148). Actual passthrough: <span className="font-bold text-white">{(100 - data.leakagePct).toFixed(1)}%</span>. Gap: <span className="font-bold text-amber-300">{data.leakagePct.toFixed(1)}%</span> ({formatCurrency(data.totalRetained)} retained by PBM)
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 text-center">
          <p className="text-sm text-gray-500">Total Rebates Received</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{formatCurrency(data.totalRebates)}</p>
        </div>
        <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-6 text-center">
          <p className="text-sm text-emerald-600">Passed Through to Plan</p>
          <p className="text-2xl font-bold text-emerald-700 mt-1">{formatCurrency(data.totalPassedThrough)}</p>
        </div>
        <div className="bg-red-50 rounded-xl border border-red-200 p-6 text-center">
          <p className="text-sm text-red-600">Retained by PBM</p>
          <p className="text-2xl font-bold text-red-700 mt-1">{formatCurrency(data.totalRetained)}</p>
        </div>
      </div>

      <div className="bg-gradient-to-r from-amber-500 to-red-500 rounded-xl p-6 mb-6 text-white flex items-center gap-4">
        <AlertTriangle className="w-10 h-10 flex-shrink-0" />
        <div>
          <p className="text-lg font-bold">Leakage Rate: {data.leakagePct}%</p>
          <p className="text-sm text-white/90">
            {formatCurrency(data.totalRetained)} in rebates retained by PBM instead of being passed through to the plan
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">
          Rebate Flow: Manufacturer &rarr; PBM &rarr; Plan
        </h3>
        {data.drugs.slice(0, 5).map((drug) => (
          <FlowBar
            key={drug.drug}
            label={`${drug.drug} (${drug.manufacturer})`}
            total={drug.totalRebate}
            passed={drug.passedThrough}
            retained={drug.retained}
          />
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Drug</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Manufacturer</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Total Rebate</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Passed Through</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Retained</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">% Retained</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.drugs.map((drug, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{drug.drug}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{drug.manufacturer}</td>
                <td className="px-6 py-4 text-sm text-gray-700 text-right">{formatCurrency(drug.totalRebate)}</td>
                <td className="px-6 py-4 text-sm text-emerald-600 text-right">{formatCurrency(drug.passedThrough)}</td>
                <td className="px-6 py-4 text-sm text-red-600 font-semibold text-right">{formatCurrency(drug.retained)}</td>
                <td className="px-6 py-4 text-sm text-right font-semibold">{drug.retainedPct.toFixed(1)}%</td>
                <td className="px-6 py-4">
                  <StatusBadge
                    status={drug.retainedPct > 15 ? "critical" : drug.retainedPct > 10 ? "warning" : "good"}
                    label={drug.retainedPct > 15 ? "High" : drug.retainedPct > 10 ? "Medium" : "Low"}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
