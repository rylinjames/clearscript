/**
 * Shared TypeScript interfaces for the PBM contract analysis shape
 * returned by /api/contracts/upload and /api/contracts/:id.
 *
 * These are hand-maintained against the Pydantic-free dict returned by
 * enrich_contract_analysis() on the backend. When adding a field on the
 * backend, update here too — a rename or a removal will otherwise
 * silently render as a blank field in the UI instead of a compile error.
 *
 * Previously duplicated inline at the top of contracts/page.tsx.
 */

export interface ExtractedTerm {
  clause: string;
  value: string;
  status: "good" | "warning" | "critical";
  note: string;
}

export interface AuditChecklistItem {
  item: string;
  found: boolean;
  details?: string;
}

export interface EligibleRebateDefinition {
  narrow_definition_flag: boolean;
  excludes_admin_fees?: boolean;
  excludes_volume_bonuses?: boolean;
  excludes_price_protection?: boolean;
  details?: string;
}

export interface AnalysisExtras {
  audit_rights?: {
    checklist?: AuditChecklistItem[];
    [key: string]: unknown;
  };
  eligible_rebate_definition?: EligibleRebateDefinition;
  [key: string]: unknown;
}

export interface PlanBenefits {
  plan_info?: {
    plan_name?: string;
    carrier?: string;
    plan_type?: string;
    effective_date?: string;
    coverage_period?: string;
  };
  deductible?: Record<string, string | null>;
  out_of_pocket_maximum?: Record<string, string | null>;
  copays?: Record<string, string | null>;
  coinsurance?: Record<string, string | null>;
  prescription_drugs?: Record<string, unknown>;
  hospital_services?: Record<string, string | null>;
  exclusions_and_limits?: string[];
  other_benefits?: Record<string, string | null>;
  confidence_score?: number;
  _generated_by?: string;
}

export interface CrossRefFinding {
  category: string;
  finding: string;
  severity: "high" | "medium" | "low";
  contract_says: string;
  plan_doc_says: string;
  recommendation: string;
}

export interface CrossRefResult {
  summary: string;
  overall_alignment_score: number;
  findings: CrossRefFinding[];
  action_items?: { priority: string; action: string; reason: string }[];
  missing_from_contract?: string[];
  missing_from_plan_doc?: string[];
  _generated_by?: string;
}

export interface WeightedAssessment {
  deal_score?: number;
  weighted_risk_score?: number;
  risk_level?: string;
  methodology?: string;
  tier_scores?: { tier: string; score: number; weight: number }[];
}

export interface TopRisk {
  title: string;
  tier: number;
  severity: "high" | "medium" | "low";
  why_it_matters: string;
  recommendation: string;
}

export interface ContractIdentification {
  plan_sponsor_name?: string | null;
  pbm_name?: string | null;
  effective_date?: string | null;
  initial_term_months?: number | null;
  current_term_end_date?: string | null;
  termination_notice_days?: number | null;
  renewal_mechanism?: string | null;
  // Computed by the backend's _attach_critical_dates helper:
  notice_deadline_date?: string | null;
  days_until_term_end?: number | null;
  days_until_notice_deadline?: number | null;
  rfp_start_recommended_date?: string | null;
  days_until_rfp_start?: number | null;
}

export interface FinancialExposureEntry {
  level: string;
  estimate: string;
  driver: string;
  // Dollar-denominated estimates added by the backend's
  // _attach_dollar_exposure helper. Present whenever the backend has
  // either real uploaded claims or the synthetic sample dataset to
  // multiply the percentage range against.
  dollar_estimate_low?: number;
  dollar_estimate_high?: number;
  dollar_denominator?: number;
  dollar_denominator_label?: string;
  dollar_estimate_basis?: "uploaded_claims" | "synthetic_sample";
}

export interface FinancialExposure {
  mode?: string;
  summary?: string;
  rebate_leakage?: FinancialExposureEntry;
  spread_exposure?: FinancialExposureEntry;
  specialty_control?: FinancialExposureEntry;
  claims_context?: {
    claims_count?: number;
    claims_filename?: string;
    date_range_start?: string;
    date_range_end?: string;
    custom_data_loaded?: boolean;
    total_plan_paid?: number;
    brand_spend?: number;
    specialty_spend?: number;
  };
}

export interface ControlMapItem {
  lever: string;
  controller: string;
  assessment: string;
  implication: string;
}

export interface ControlPosture {
  label: string;
  level: string;
  headline: string;
  summary: string;
  pbm_controlled_levers?: number;
  shared_levers?: number;
}

export interface StructuralRiskOverride {
  triggered: boolean;
  level: string;
  minimum_weighted_risk_score?: number;
  drivers?: string[];
  headline: string;
  rationale: string;
}

export interface PastContract {
  id: number;
  filename: string;
  analysis_date: string | null;
  deal_score: number | null;
  risk_level: string | null;
}

export interface BenchmarkObservation {
  kind: "strength" | "consideration";
  title: string;
  category: string;
  tier: number;
  severity: "high" | "medium" | "low";
  benchmark_label: string;
  benchmark: string;
  benchmark_source: string;
  observation: string;
  implication: string;
  recommendation: string;
  supporting_detail?: string | null;
}
