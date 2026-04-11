/**
 * Pure utility functions for rendering contract analysis.
 *
 * Formatters, status→className helpers, and the AI-response→table-row
 * mapper. Previously lived inline at the top of contracts/page.tsx.
 */

import type { ExtractedTerm } from "@/types/contract";

// Format a dollar amount as "$420k" for >$1k or "$420" for less.
// Used by the dollar-denominated leakage display.
export function formatUsdShort(n: number | undefined | null): string {
  if (n == null || !isFinite(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${Math.round(n / 1_000)}k`;
  return `$${Math.round(n)}`;
}

// Render an ISO YYYY-MM-DD date as "January 1, 2024" for the
// Contract Identification card. Returns "—" for null/undefined/garbage.
export function formatLongDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso + "T00:00:00");
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

// Render "in 267 days" / "267 days from today" / "21 days ago" as
// neutral plain English so a benefits manager can scan the date
// without doing math. Used by the Critical Dates card.
export function formatRelativeDays(days: number | null | undefined): string {
  if (days == null || !isFinite(days)) return "";
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days === -1) return "yesterday";
  if (days > 0) return `${days} days from today`;
  return `${Math.abs(days)} days ago`;
}

export function riskLevelStyles(level?: string) {
  if (level === "high") return "bg-red-50 border-red-200 text-red-700";
  if (level === "low") return "bg-emerald-50 border-emerald-200 text-emerald-700";
  return "bg-amber-50 border-amber-200 text-amber-700";
}

export function riskBadgeStyles(level?: string) {
  if (level === "high") return "bg-red-100 text-red-800";
  if (level === "low") return "bg-emerald-100 text-emerald-800";
  return "bg-amber-100 text-amber-800";
}

export function observationKindStyles(kind?: string) {
  if (kind === "strength") return "bg-emerald-100 text-emerald-800";
  return "bg-amber-100 text-amber-800";
}

export function formatRiskLevel(level?: string) {
  return (level || "moderate").replace(/^\w/, (c) => c.toUpperCase());
}

// Allow-list of contract clause keys that get rendered as rows in the
// extracted terms table. Anything not in this list is treated as
// post-processing metadata (control_map, top_risks, immediate_actions,
// benchmark_observations, weighted_assessment, redline_suggestions,
// financial_exposure, structural_risk_override, control_posture, etc.)
// and rendered by its own dedicated section elsewhere on the page.
//
// audit_rights is intentionally excluded — it has the eleven-point
// dedicated audit-rights scorecard rendered below (auditChecklist).
//
// IMPORTANT: whitelist, not a blacklist. A previous version iterated
// every key in the analysis JSON and skipped a hardcoded blacklist;
// every time enrich_contract_analysis or the AI prompt added a new
// top-level field, it would show up as a phantom "Not found" row in
// the table. Whitelist iteration is future-proof against that bug class.
export const CLAUSE_LABELS: Record<string, string> = {
  rebate_passthrough: "Rebate Passthrough",
  spread_pricing: "Spread Pricing",
  formulary_clauses: "Formulary Management",
  mac_pricing: "MAC Pricing",
  termination_provisions: "Termination Provisions",
  gag_clauses: "Gag Clauses",
  specialty_channel: "Specialty Channel Control",
};

export function mapApiToTerms(
  a: Record<string, Record<string, unknown>>
): ExtractedTerm[] {
  const terms: ExtractedTerm[] = [];
  // Iterate the whitelist, not the analysis object — guarantees we
  // only ever try to render real contract clauses.
  for (const key of Object.keys(CLAUSE_LABELS)) {
    const val = a[key];
    if (!val || typeof val !== "object") continue;
    // Use favorability from AI if available, fall back to heuristic
    const favorability = (val.favorability as string) || "";
    let status: "good" | "warning" | "critical";
    if (favorability === "employer_favorable") {
      status = "good";
    } else if (favorability === "neutral") {
      status = "warning";
    } else if (favorability === "pbm_favorable") {
      status = "critical";
    } else {
      const details = ((val.details as string) || "").toLowerCase();
      const hasIssue =
        details.includes("no ") ||
        details.includes("not ") ||
        details.includes("concern") ||
        details.includes("narrow") ||
        details.includes("limit") ||
        details.includes("restrict") ||
        details.includes("retain");
      status = hasIssue ? "critical" : "good";
    }
    const extractedValue = (val.percentage ||
      val.effective_passthrough ||
      val.caps ||
      (val.change_notification_days
        ? val.change_notification_days + " days"
        : null) ||
      val.scope ||
      val.notice_period ||
      (val.notice_days ? val.notice_days + " days" : null) ||
      val.mechanism ||
      (val.found ? "Found" : "Not found")) as string;
    terms.push({
      clause: CLAUSE_LABELS[key],
      value: extractedValue,
      status,
      note: (val.details as string) || "",
    });
  }
  return terms;
}
