import { FileText, Loader2, History, Clock } from "lucide-react";
import type { PastContract } from "@/types/contract";

interface Props {
  pastContracts: PastContract[];
  pastContractsLoading: boolean;
  loadedFromHistoryId: number | null;
  loadingPastId: number | null;
  uploadInProgress: boolean;
  onSelect: (id: number) => void;
}

/**
 * "Recent Analyses" picker — one-click shortcut back into any previously
 * analyzed contract without re-uploading. Each row loads /api/contracts/{id}
 * and re-populates the parent page state via onSelect.
 *
 * Solves the "I clicked Draft Audit Letter and now I can't get back to my
 * analysis without rescanning" problem. Renders nothing when there are no
 * past contracts or when a fresh upload is currently running.
 */
export default function RecentAnalysesPicker({
  pastContracts,
  pastContractsLoading,
  loadedFromHistoryId,
  loadingPastId,
  uploadInProgress,
  onSelect,
}: Props) {
  if (pastContracts.length === 0 || uploadInProgress) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-primary-600" />
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Recent Analyses</h3>
        </div>
        <span className="text-xs text-gray-500">
          {pastContracts.length} analyzed contract{pastContracts.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="space-y-1.5 max-h-72 overflow-y-auto">
        {pastContractsLoading ? (
          <div className="text-xs text-gray-500 py-2">Loading...</div>
        ) : (
          pastContracts.map((c) => {
            const isCurrent = loadedFromHistoryId === c.id;
            const isLoading = loadingPastId === c.id;
            const dateStr = c.analysis_date ? c.analysis_date.split(" ")[0] : "unknown date";
            const scoreColor =
              c.deal_score === null ? "bg-gray-100 text-gray-700"
              : c.deal_score >= 60 ? "bg-emerald-100 text-emerald-700"
              : c.deal_score >= 30 ? "bg-amber-100 text-amber-700"
              : "bg-red-100 text-red-700";
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => onSelect(c.id)}
                disabled={isLoading || uploadInProgress}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg border text-left transition-colors ${
                  isCurrent
                    ? "bg-blue-50 border-blue-200 cursor-default"
                    : "bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300"
                } disabled:opacity-50`}
              >
                <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{c.filename}</p>
                  <p className="text-[11px] text-gray-500 flex items-center gap-1.5 mt-0.5">
                    <Clock className="w-2.5 h-2.5" />
                    {dateStr}
                    {c.risk_level && <span className="capitalize">· {c.risk_level} risk</span>}
                  </p>
                </div>
                {c.deal_score !== null && (
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${scoreColor}`}>
                    {c.deal_score}/100
                  </span>
                )}
                {isCurrent && (
                  <span className="text-[11px] font-semibold text-blue-700 px-2 py-0.5 bg-white border border-blue-200 rounded">Viewing</span>
                )}
                {isLoading && <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />}
              </button>
            );
          })
        )}
      </div>
      <p className="text-[11px] text-gray-500 mt-3 leading-relaxed">
        Click any contract to reopen its full analysis without re-uploading.
      </p>
    </div>
  );
}
