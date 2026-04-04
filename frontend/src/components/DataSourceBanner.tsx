"use client";

import { useClaimsStatus } from "./ClaimsContext";
import { Database, CheckCircle2, RefreshCw, AlertTriangle } from "lucide-react";

interface Props {
  onRefresh?: () => void;
  refreshing?: boolean;
  error?: string | null;
  generatedBy?: "ai" | "mock" | null;
}

export default function DataSourceBanner({ onRefresh, refreshing, error, generatedBy }: Props) {
  const { status } = useClaimsStatus();

  return (
    <div className="space-y-2 mb-4">
      {/* Data source indicator */}
      <div className={`rounded-lg border px-4 py-2.5 flex items-center justify-between ${
        status?.custom_data_loaded
          ? "bg-emerald-50 border-emerald-200"
          : "bg-blue-50 border-blue-200"
      }`}>
        <div className="flex items-center gap-2">
          {status?.custom_data_loaded ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          ) : (
            <Database className="w-4 h-4 text-blue-600" />
          )}
          <span className={`text-sm font-medium ${status?.custom_data_loaded ? "text-emerald-800" : "text-blue-800"}`}>
            {status?.custom_data_loaded
              ? `Your Uploaded Data (${status.claims_count?.toLocaleString()} claims)`
              : "Demo analysis based on publicly available sources"}
          </span>
          {generatedBy && (
            <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
              generatedBy === "ai"
                ? "bg-emerald-100 text-emerald-700"
                : "bg-amber-100 text-amber-700"
            }`}>
              {generatedBy === "ai" ? "AI Analysis" : "Demo Analysis"}
            </span>
          )}
        </div>
        {onRefresh && (
          <button onClick={onRefresh} disabled={refreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600" />
          <span className="text-sm text-red-800">{error}</span>
        </div>
      )}
    </div>
  );
}
