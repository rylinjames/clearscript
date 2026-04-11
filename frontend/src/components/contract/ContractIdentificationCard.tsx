import type { ContractIdentification } from "@/types/contract";
import { formatLongDate, formatRelativeDays } from "@/lib/contract-utils";

interface Props {
  contractIdentification: ContractIdentification | undefined;
}

/**
 * Paired "who/when" header cards for an analyzed contract.
 *
 * Left card (Contract Identification): parties, effective date, term length,
 * renewal mechanism — answers "which contract did we just analyze."
 *
 * Right card (Critical Dates): notice deadline, days-until counters, RFP
 * recommended start date — answers "when do I need to act." Populated by
 * the backend's _attach_critical_dates helper, so an analysis missing
 * those fields just doesn't render the right card.
 *
 * Returns null entirely when no identification data is present so old
 * analyses without the contract_identification prompt block degrade
 * gracefully to the rest of the page.
 */
export default function ContractIdentificationCard({ contractIdentification }: Props) {
  if (!contractIdentification) return null;
  const cid = contractIdentification;
  if (!cid.plan_sponsor_name && !cid.pbm_name && !cid.effective_date) return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
      {/* Contract Identification */}
      <div className="bg-white rounded-xl border border-gray-200/60 shadow-[var(--shadow-card)] p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500 mb-3">Contract Identification</p>
        <div className="space-y-2.5">
          {(cid.plan_sponsor_name || cid.pbm_name) && (
            <div>
              <p className="text-base font-bold text-gray-900 leading-snug">
                {cid.pbm_name || "PBM"}
                <span className="text-gray-400 mx-2 font-normal">×</span>
                {cid.plan_sponsor_name || "Plan Sponsor"}
              </p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3 text-sm">
            {cid.effective_date && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-gray-500">Effective</p>
                <p className="font-medium text-gray-900">{formatLongDate(cid.effective_date)}</p>
              </div>
            )}
            {cid.initial_term_months != null && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-gray-500">Initial Term</p>
                <p className="font-medium text-gray-900">{cid.initial_term_months} months</p>
              </div>
            )}
            {cid.current_term_end_date && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-gray-500">Current Term Ends</p>
                <p className="font-medium text-gray-900">{formatLongDate(cid.current_term_end_date)}</p>
              </div>
            )}
            {cid.termination_notice_days != null && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-gray-500">Notice Required</p>
                <p className="font-medium text-gray-900">{cid.termination_notice_days} days</p>
              </div>
            )}
          </div>
          {cid.renewal_mechanism && (
            <p className="text-xs text-gray-500 leading-relaxed pt-1">
              {cid.renewal_mechanism}
            </p>
          )}
        </div>
      </div>

      {/* Critical Dates */}
      {(cid.notice_deadline_date || cid.days_until_term_end != null) && (
        <div className="bg-gradient-to-br from-amber-50 to-white rounded-xl border border-amber-200 p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700 mb-3">Critical Dates</p>
          <div className="space-y-3">
            {cid.notice_deadline_date && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-amber-700">Notice Deadline</p>
                <p className="text-lg font-bold text-gray-900">
                  {formatLongDate(cid.notice_deadline_date)}
                </p>
                {cid.days_until_notice_deadline != null && (
                  <p className={`text-xs mt-0.5 ${
                    cid.days_until_notice_deadline < 0
                      ? "text-red-700 font-semibold"
                      : cid.days_until_notice_deadline < 90
                      ? "text-red-700 font-semibold"
                      : "text-gray-600"
                  }`}>
                    {cid.days_until_notice_deadline < 0
                      ? `Deadline passed ${Math.abs(cid.days_until_notice_deadline)} days ago — early termination fee likely applies`
                      : `${formatRelativeDays(cid.days_until_notice_deadline)} to give notice without penalty`}
                  </p>
                )}
              </div>
            )}
            {cid.rfp_start_recommended_date && cid.days_until_rfp_start != null && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-amber-700">Begin RFP Process By</p>
                <p className="text-base font-semibold text-gray-900">
                  {formatLongDate(cid.rfp_start_recommended_date)}
                </p>
                <p className="text-xs text-gray-600 mt-0.5">
                  {cid.days_until_rfp_start < 0
                    ? "Recommended start date passed — begin immediately"
                    : `${formatRelativeDays(cid.days_until_rfp_start)} — gives you negotiating leverage at the renewal table`}
                </p>
              </div>
            )}
            {cid.current_term_end_date && cid.days_until_term_end != null && (
              <div className="pt-2 border-t border-amber-100">
                <p className="text-xs text-gray-500">
                  Current term ends in {cid.days_until_term_end > 0 ? `${cid.days_until_term_end} days` : `${Math.abs(cid.days_until_term_end)} days ago`}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
