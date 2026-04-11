"""
Post-processing for AI contract analysis.

The AI returns a structured JSON dict for each contract. This module takes
that dict and derives everything the frontend needs to render a full case
file: weighted risk scores, dollar-denominated exposure, per-redline
savings, benchmark observations, control posture, structural risk override,
critical dates, etc.

All functions here are pure Python — no OpenAI calls. The orchestrator
`enrich_contract_analysis()` is called once at the end of
`analyze_contract()` in ai_service.py.
"""

import re
import logging

logger = logging.getLogger(__name__)


TIER_WEIGHTS = {
    "rebate_passthrough": 24,
    "eligible_rebate_definition": 24,
    "spread_pricing": 22,
    "specialty_channel": 18,
    "audit_rights": 12,
    "mac_pricing": 8,
    "formulary_clauses": 7,
    "termination_provisions": 4,
    "gag_clauses": 5,
    "statistical_extrapolation_rights": 5,
}

TIER_LABELS = {
    "rebate_passthrough": 1,
    "eligible_rebate_definition": 1,
    "spread_pricing": 1,
    "specialty_channel": 1,
    "audit_rights": 1,
    "mac_pricing": 2,
    "formulary_clauses": 2,
    "termination_provisions": 3,
    "gag_clauses": 2,
    "statistical_extrapolation_rights": 2,
}

TERM_TITLES = {
    "rebate_passthrough": "Rebate passthrough",
    "eligible_rebate_definition": "Eligible rebate definition",
    "spread_pricing": "Spread pricing",
    "specialty_channel": "Specialty channel control",
    "audit_rights": "Audit rights",
    "mac_pricing": "MAC pricing",
    "formulary_clauses": "Formulary control",
    "termination_provisions": "Termination provisions",
    "gag_clauses": "Confidentiality / gag restrictions",
    "statistical_extrapolation_rights": "Statistical extrapolation",
}

BENCHMARK_LIBRARY = {
    "rebate_passthrough": {
        "category": "Rebates",
        "benchmark_label": "Full manufacturer compensation passthrough",
        "benchmark": "Employer-favorable benchmark language ties passthrough to all manufacturer compensation, not only payments labeled as rebates.",
        "source": "NASHP Model PBM Contract Terms; NASTAD PBM Contract Language Bank",
    },
    "eligible_rebate_definition": {
        "category": "Rebates",
        "benchmark_label": "Broad eligible rebate definition",
        "benchmark": "Benchmark language includes admin fees, volume incentives, price protection, data fees, and similar manufacturer payments in passthrough.",
        "source": "NASHP Model PBM Contract Terms; NASTAD PBM Contract Language Bank",
    },
    "spread_pricing": {
        "category": "Pricing",
        "benchmark_label": "Pass-through claim pricing",
        "benchmark": "Employer-favorable benchmark prohibits retained spread and requires claim-level transparency between plan charge and pharmacy reimbursement.",
        "source": "Public state PBM contract benchmarks; Ohio and Pennsylvania PBM audit findings",
    },
    "specialty_channel": {
        "category": "Specialty",
        "benchmark_label": "Employer optionality over specialty channel",
        "benchmark": "Benchmark structure preserves employer approval over specialty routing, vendor choice, and specialty pricing transparency.",
        "source": "Public state PBM contract benchmarks; FTC PBM reports",
    },
    "audit_rights": {
        "category": "Audit",
        "benchmark_label": "Full audit and data access",
        "benchmark": "Benchmark language extends audit rights to manufacturer contracts, pharmacy reimbursement, network agreements, and specialty economics.",
        "source": "NASTAD PBM Contract Language Bank; public payer audit rights benchmarks",
    },
    "mac_pricing": {
        "category": "Pricing",
        "benchmark_label": "Transparent MAC process",
        "benchmark": "Employer-favorable benchmark gives visibility into MAC methodology, updates, and appeals handling.",
        "source": "Public payer PBM audit benchmarks",
    },
    "formulary_clauses": {
        "category": "Formulary",
        "benchmark_label": "Employer oversight of formulary changes",
        "benchmark": "Benchmark language requires notice, justification, and employer approval for material mid-year formulary changes.",
        "source": "NASHP Model PBM Contract Terms",
    },
    "termination_provisions": {
        "category": "Administrative",
        "benchmark_label": "Low-friction exit rights",
        "benchmark": "Benchmark language allows short notice termination without liquidated damages and preserves transition support.",
        "source": "Public state procurement contract benchmarks",
    },
    "gag_clauses": {
        "category": "Governance",
        "benchmark_label": "Advisor disclosure rights",
        "benchmark": "Benchmark language permits sharing pricing and rebate data with advisors, auditors, and counsel.",
        "source": "CAA 2021 gag clause standards",
    },
    "statistical_extrapolation_rights": {
        "category": "Audit",
        "benchmark_label": "Audit recovery through extrapolation",
        "benchmark": "Benchmark language permits extrapolating validated audit errors across the broader claims population.",
        "source": "Public payer audit rights benchmarks",
    },
}

EXPOSURE_SUPPORT_MAP = {
    "rebate_passthrough": "rebate_leakage",
    "eligible_rebate_definition": "rebate_leakage",
    "spread_pricing": "spread_exposure",
    "specialty_channel": "specialty_control",
    "formulary_clauses": "rebate_leakage",
    "mac_pricing": "spread_exposure",
}


def _normalize_favorability(value) -> str:
    text = str(value or "").lower()
    if text in {"employer_favorable", "good"}:
        return "employer_favorable"
    if text in {"neutral", "warning"}:
        return "neutral"
    if text in {"pbm_favorable", "critical", "bad"}:
        return "pbm_favorable"
    return ""


def _term_penalty(term: dict, key: str) -> float:
    favorability = _normalize_favorability(term.get("favorability"))
    if favorability == "pbm_favorable":
        return 1.0
    if favorability == "neutral":
        return 0.45

    details = str(term.get("details", "")).lower()
    severe_markers = ["retain", "restrict", "exclusive", "sole discretion", "not disclose", "limited", "exclude"]
    if any(marker in details for marker in severe_markers):
        return 0.85
    if key in {"spread_pricing", "eligible_rebate_definition", "specialty_channel", "audit_rights"}:
        found = term.get("found")
        if found is False:
            return 0.85
    return 0.0


def _ordered_term_scores(analysis: dict) -> list[dict]:
    ordered = []
    for key, weight in TIER_WEIGHTS.items():
        term = analysis.get(key)
        if not isinstance(term, dict):
            continue
        penalty = _term_penalty(term, key)
        ordered.append({
            "key": key,
            "term": term,
            "penalty": penalty,
            "tier": TIER_LABELS.get(key, 3),
            "weight": weight,
            "weighted_score": weight * penalty,
        })
    ordered.sort(key=lambda item: item["weighted_score"], reverse=True)
    return ordered


def _financial_exposure_for(analysis: dict) -> dict:
    rebate = analysis.get("eligible_rebate_definition", {}) if isinstance(analysis, dict) else {}
    spread = analysis.get("spread_pricing", {}) if isinstance(analysis, dict) else {}
    specialty = analysis.get("specialty_channel", {}) if isinstance(analysis, dict) else {}

    narrow_rebate = bool(rebate.get("narrow_definition_flag")) or (
        rebate.get("includes_admin_fees") is False
        or rebate.get("includes_volume_bonuses") is False
        or rebate.get("includes_price_protection") is False
    )
    spread_hidden = _term_penalty(spread, "spread_pricing") >= 0.85
    specialty_locked = (
        specialty.get("external_routing_rights") is False
        or specialty.get("vendor_channel_optionality") is False
        or specialty.get("pricing_transparency") is False
    )

    rebate_exposure = {
        "level": "high" if narrow_rebate else "moderate",
        "estimate": "3-6% of brand spend" if narrow_rebate else "1-3% of brand spend",
        "driver": "Eligible rebate definition excludes admin fees, volume incentives, or price protection"
        if narrow_rebate else "Passthrough terms should still be validated against rebate definitions",
    }
    spread_exposure = {
        "level": "high" if spread_hidden else "moderate",
        "estimate": "1-3% of total claims spend" if spread_hidden else "Up to 1% of total claims spend",
        "driver": "PBM can retain the difference between pharmacy reimbursement and plan charge"
        if spread_hidden else "Pricing transparency should still be validated claim by claim",
    }
    specialty_exposure = {
        "level": "high" if specialty_locked else "moderate",
        "estimate": "30-50% of total Rx spend" if specialty_locked else "15-30% of total Rx spend",
        "driver": "Highest-cost drug category remains under PBM routing and pricing control"
        if specialty_locked else "Specialty sourcing rights should still be confirmed",
    }

    return {
        "mode": "directional",
        "summary": (
            "Directional exposure is concentrated in rebate leakage, undisclosed spread, and specialty channel control."
            if (narrow_rebate or spread_hidden or specialty_locked)
            else "Primary financial exposure appears moderate but still requires contract-level validation."
        ),
        "rebate_leakage": rebate_exposure,
        "spread_exposure": spread_exposure,
        "specialty_control": specialty_exposure,
    }


def _claims_backed_exposure_for(analysis: dict) -> dict | None:
    try:
        from services.data_service import get_claims, get_claims_status, analyze_spread, analyze_rebates
    except Exception:
        return None

    status = get_claims_status()
    if not status.get("custom_data_loaded"):
        return None

    claims = get_claims()
    if not claims:
        return None

    total_spend = sum(float(c.get("plan_paid", 0) or 0) for c in claims)
    brand_claims = [c for c in claims if not c.get("generic")]
    specialty_claims = [c for c in claims if c.get("is_specialty") or c.get("channel") == "specialty"]
    brand_spend = sum(float(c.get("plan_paid", 0) or 0) for c in brand_claims)
    specialty_spend = sum(float(c.get("plan_paid", 0) or 0) for c in specialty_claims)

    spread_analysis = analyze_spread(claims)
    rebate_analysis = analyze_rebates(claims)

    total_spread = float(spread_analysis.get("total_spread_captured", 0) or 0)
    total_retained_rebates = float(rebate_analysis.get("rebates_retained_by_pbm", 0) or 0)
    passthrough_rate = float(rebate_analysis.get("passthrough_rate_pct", 0) or 0)
    spread_pct_total = (total_spread / total_spend * 100) if total_spend else 0.0
    rebate_pct_brand = (total_retained_rebates / brand_spend * 100) if brand_spend else 0.0
    specialty_pct_total = (specialty_spend / total_spend * 100) if total_spend else 0.0

    def _level(pct: float) -> str:
        if pct >= 5:
            return "high"
        if pct >= 2:
            return "moderate"
        return "low"

    return {
        "mode": "claims_backed",
        "summary": (
            f"Claims-backed estimate based on {len(claims):,} uploaded claims. "
            f"Observed spread is ${round(total_spread, 2):,.2f}, retained rebates are ${round(total_retained_rebates, 2):,.2f}, "
            f"and specialty spend totals ${round(specialty_spend, 2):,.2f}."
        ),
        "rebate_leakage": {
            "level": _level(rebate_pct_brand),
            "estimate": f"${round(total_retained_rebates, 2):,.2f} observed ({rebate_pct_brand:.1f}% of brand spend)",
            "driver": f"Observed passthrough rate is {passthrough_rate:.1f}% across uploaded claims; contract exclusions may worsen this in practice.",
        },
        "spread_exposure": {
            "level": _level(spread_pct_total),
            "estimate": f"${round(total_spread, 2):,.2f} observed ({spread_pct_total:.1f}% of total spend)",
            "driver": f"Observed difference between plan-paid and pharmacy reimbursement across {spread_analysis.get('total_claims_analyzed', len(claims)):,} claims.",
        },
        "specialty_control": {
            "level": _level(specialty_pct_total),
            "estimate": f"${round(specialty_spend, 2):,.2f} observed ({specialty_pct_total:.1f}% of total Rx spend)",
            "driver": f"{len(specialty_claims):,} specialty claims in uploaded data are subject to specialty channel economics.",
        },
        "claims_context": {
            "claims_count": len(claims),
            "claims_filename": status.get("filename"),
            "date_range_start": status.get("date_range_start"),
            "date_range_end": status.get("date_range_end"),
            "total_spend": round(total_spend, 2),
            "brand_spend": round(brand_spend, 2),
            "specialty_spend": round(specialty_spend, 2),
        },
    }


def _control_map_for(analysis: dict) -> list[dict]:
    rebate = analysis.get("eligible_rebate_definition", {}) if isinstance(analysis, dict) else {}
    spread = analysis.get("spread_pricing", {}) if isinstance(analysis, dict) else {}
    specialty = analysis.get("specialty_channel", {}) if isinstance(analysis, dict) else {}
    audit = analysis.get("audit_rights", {}) if isinstance(analysis, dict) else {}
    formulary = analysis.get("formulary_clauses", {}) if isinstance(analysis, dict) else {}

    return [
        {
            "lever": "Rebates",
            "controller": "PBM" if rebate.get("narrow_definition_flag") or rebate.get("found") else "Shared",
            "assessment": rebate.get("details", "Rebate definition determines what compensation is actually passed through."),
            "implication": "Plan cannot assume stated passthrough equals full manufacturer compensation."
        },
        {
            "lever": "Pricing",
            "controller": "PBM" if _term_penalty(spread, "spread_pricing") >= 0.45 else "Shared",
            "assessment": spread.get("details", "Spread terms determine whether pharmacy reimbursement is transparent to the plan."),
            "implication": "Plan cannot verify net claim economics without claim-level reconciliation."
        },
        {
            "lever": "Specialty",
            "controller": "PBM" if specialty.get("vendor_channel_optionality") is False else "Shared",
            "assessment": specialty.get("details", "Specialty routing rights determine who controls the highest-cost channel."),
            "implication": "Plan loses negotiating leverage where the largest Rx dollars sit."
        },
        {
            "lever": "Formulary",
            "controller": "PBM" if _term_penalty(formulary, "formulary_clauses") >= 0.45 else "Shared",
            "assessment": formulary.get("details", "Formulary language determines who can move utilization and rebate mix."),
            "implication": "PBM can optimize toward rebate economics if employer approval is limited."
        },
        {
            "lever": "Audit / Data",
            "controller": "PBM" if _term_penalty(audit, "audit_rights") >= 0.45 else "Shared",
            "assessment": audit.get("details", "Audit scope determines whether the plan can verify economics or only receive PBM summaries."),
            "implication": "If audit scope is limited, the plan cannot independently validate pricing, rebates, or specialty economics."
        },
    ]


def _attach_critical_dates(analysis: dict) -> None:
    """
    Compute notice deadline + days-until counters from the AI-extracted
    contract_identification block. Best-effort: if any field is missing
    or unparseable the function leaves existing fields untouched.
    """
    from datetime import datetime as _dt, timedelta as _td

    cid = analysis.get("contract_identification")
    if not isinstance(cid, dict):
        return

    today = _dt.now().date()

    def _parse_date(value):
        if not value:
            return None
        try:
            return _dt.fromisoformat(str(value).split("T")[0]).date()
        except (ValueError, TypeError):
            return None

    effective = _parse_date(cid.get("effective_date"))
    term_end = _parse_date(cid.get("current_term_end_date"))

    if term_end is None and effective is not None:
        try:
            months = int(cid.get("initial_term_months") or 0)
            if months > 0:
                term_end = effective + _td(days=int(round(months * 30.4375)))
                cid["current_term_end_date"] = term_end.isoformat()
        except (ValueError, TypeError):
            pass

    if term_end is None:
        return

    try:
        notice_days = int(cid.get("termination_notice_days") or 0)
    except (ValueError, TypeError):
        notice_days = 0

    if notice_days > 0:
        notice_deadline = term_end - _td(days=notice_days)
        cid["notice_deadline_date"] = notice_deadline.isoformat()
        cid["days_until_notice_deadline"] = (notice_deadline - today).days
        rfp_start = notice_deadline - _td(days=60)
        cid["rfp_start_recommended_date"] = rfp_start.isoformat()
        cid["days_until_rfp_start"] = (rfp_start - today).days

    cid["days_until_term_end"] = (term_end - today).days


def _attach_dollar_exposure(analysis: dict) -> None:
    """
    Mutate `analysis["financial_exposure"]` to include dollar-denominated
    estimates derived from real or synthetic claims totals. Best-effort —
    failures never raise.
    """
    try:
        from services.data_service import get_claims_totals
    except Exception:
        return

    exposure = analysis.get("financial_exposure")
    if not isinstance(exposure, dict):
        return

    try:
        totals = get_claims_totals()
    except Exception as e:
        logger.debug(f"get_claims_totals failed in _attach_dollar_exposure: {e}")
        return

    custom_data = bool(totals.get("custom_data_loaded"))
    denominators = {
        "brand": float(totals.get("brand_spend") or 0),
        "specialty": float(totals.get("specialty_spend") or 0),
        "total": float(totals.get("total_plan_paid") or 0),
        "generic": float(totals.get("generic_spend") or 0),
    }

    exposure.setdefault("claims_context", {})
    if isinstance(exposure["claims_context"], dict):
        exposure["claims_context"]["custom_data_loaded"] = custom_data
        exposure["claims_context"]["claims_count"] = totals.get("claims_count")
        exposure["claims_context"]["total_plan_paid"] = totals.get("total_plan_paid")
        exposure["claims_context"]["brand_spend"] = totals.get("brand_spend")
        exposure["claims_context"]["specialty_spend"] = totals.get("specialty_spend")
    if custom_data:
        exposure["mode"] = "claims_backed"
    else:
        exposure.setdefault("mode", "illustrative")

    pct_range_pat = re.compile(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%")
    single_pct_pat = re.compile(r"(\d+(?:\.\d+)?)\s*%")

    def _denominator_for(estimate_text: str) -> tuple[float, str]:
        text = (estimate_text or "").lower()
        if "brand" in text:
            return denominators["brand"], "brand drug spend"
        if "specialty" in text:
            return denominators["specialty"], "specialty Rx spend"
        if "generic" in text:
            return denominators["generic"], "generic drug spend"
        return denominators["total"], "total claims spend"

    for key in ("rebate_leakage", "spread_exposure", "specialty_control"):
        entry = exposure.get(key)
        if not isinstance(entry, dict):
            continue
        estimate_text = str(entry.get("estimate") or "")
        if not estimate_text:
            continue

        denom, denom_label = _denominator_for(estimate_text)
        if denom <= 0:
            continue

        m = pct_range_pat.search(estimate_text)
        if m:
            low_pct = float(m.group(1)) / 100.0
            high_pct = float(m.group(2)) / 100.0
        else:
            m2 = single_pct_pat.search(estimate_text)
            if not m2:
                continue
            low_pct = high_pct = float(m2.group(1)) / 100.0

        low_dollars = round(denom * low_pct, 2)
        high_dollars = round(denom * high_pct, 2)
        entry["dollar_estimate_low"] = low_dollars
        entry["dollar_estimate_high"] = high_dollars
        entry["dollar_denominator"] = round(denom, 2)
        entry["dollar_denominator_label"] = denom_label
        entry["dollar_estimate_basis"] = "uploaded_claims" if custom_data else "synthetic_sample"


def _attach_redline_savings(analysis: dict) -> None:
    """
    Attach a `savings_low` / `savings_high` dollar range to each redline
    by mapping its section text to the matching financial_exposure category.
    Audit rights redlines get a 15% share of total leakage each (visibility
    unlock). Best-effort — failures never raise.
    """
    redlines = analysis.get("redline_suggestions")
    if not isinstance(redlines, list) or not redlines:
        return
    exposure = analysis.get("financial_exposure")
    if not isinstance(exposure, dict):
        return

    def _bucket_dollars(bucket_key: str) -> tuple[float, float] | None:
        bucket = exposure.get(bucket_key)
        if not isinstance(bucket, dict):
            return None
        low = bucket.get("dollar_estimate_low")
        high = bucket.get("dollar_estimate_high")
        if low is None or high is None:
            return None
        try:
            return float(low), float(high)
        except (TypeError, ValueError):
            return None

    rebate_dollars = _bucket_dollars("rebate_leakage")
    spread_dollars = _bucket_dollars("spread_exposure")
    specialty_dollars = _bucket_dollars("specialty_control")
    total_low = sum(d[0] for d in (rebate_dollars, spread_dollars, specialty_dollars) if d)
    total_high = sum(d[1] for d in (rebate_dollars, spread_dollars, specialty_dollars) if d)

    audit_redline_count = sum(
        1 for r in redlines
        if isinstance(r, dict) and "audit" in str(r.get("section", "")).lower()
    )
    audit_redline_count = max(audit_redline_count, 1)
    audit_share = 0.15

    for r in redlines:
        if not isinstance(r, dict):
            continue
        section = str(r.get("section", "")).lower()

        savings: tuple[float, float] | None = None
        category_label = ""
        if "rebate" in section:
            savings = rebate_dollars
            category_label = "rebate leakage recoverable"
        elif "spread" in section or "pass-through" in section or "passthrough" in section:
            savings = spread_dollars
            category_label = "spread exposure recoverable"
        elif "specialty" in section:
            savings = specialty_dollars
            category_label = "specialty channel exposure"
        elif "audit" in section:
            if total_low > 0 or total_high > 0:
                savings = (total_low * audit_share, total_high * audit_share)
                category_label = "leakage made auditable"
        elif "mac" in section or "formulary" in section:
            if rebate_dollars:
                savings = (rebate_dollars[0] * 0.3, rebate_dollars[1] * 0.3)
                category_label = "rebate optimization upside"

        if savings is None:
            continue
        low, high = savings
        if low <= 0 and high <= 0:
            continue
        r["savings_low"] = round(low, 2)
        r["savings_high"] = round(high, 2)
        r["savings_category"] = category_label
        r["savings_basis"] = exposure.get("claims_context", {}).get("custom_data_loaded") and "uploaded_claims" or "benchmark_plan"


# Canonical audit-rights redline pack. Used by _ensure_audit_rights_redlines
# to guarantee that when a contract has deficient audit rights, the user sees
# 5 discrete, copyable redlines instead of one undifferentiated wall of text.
_AUDIT_RIGHTS_CANONICAL_REDLINES = [
    {
        "section": "Audit Rights — Frequency & Auditor of Choice",
        "current_language": "Plan Sponsor shall have the right to conduct one (1) audit per contract year.",
        "suggested_language": (
            "The Plan Sponsor or its designee shall have the right to audit annually, with an "
            "auditor of its choice, for both claims and rebates, with full cooperation of the "
            "PBM, including the manufacturer or aggregator rebate contracts held by the PBM, "
            "to verify compliance with all program requirements and contractual guarantees with "
            "no additional charge from the PBM."
        ),
        "rationale": (
            "Restricting audits to once per year — and requiring the PBM to approve the auditor — "
            "lets known issues compound for up to 12 months before the plan sponsor can act."
        ),
        "source": "NASHP Model PBM Contract §8.1; NASTAD State Medicaid PBM Toolkit",
        "impact": "high",
    },
    {
        "section": "Audit Rights — Notice & Lookback",
        "current_language": "Plan Sponsor shall provide PBM with no less than sixty (60) days' prior written notice of its intent to conduct an audit.",
        "suggested_language": (
            "The Plan Sponsor shall have the right to audit, with an auditor of its choice, at "
            "any time provided the Plan Sponsor gives 90-days advance notice. The audit shall "
            "have the right to review up to 36 months of claims data at no additional charge "
            "from the PBM."
        ),
        "rationale": (
            "60-day notice gives the PBM time to remediate findings before the audit captures "
            "them. A 36-month lookback ensures errors that compound over multiple contract "
            "years are recoverable, not just the current cycle."
        ),
        "source": "NASHP Model PBM Contract §8.2; CAA 2021 §204 disclosure timelines",
        "impact": "high",
    },
    {
        "section": "Audit Rights — Scope & Manufacturer Access",
        "current_language": "Audits shall be limited to verification of pricing and rebate terms. Audits shall not include review of PBM's contracts with pharmaceutical manufacturers, pharmacy network agreements, or internal cost structures.",
        "suggested_language": (
            "The Plan Sponsor or its designee shall have the right to audit up to 12 "
            "pharmaceutical manufacturer contracts during an on-site rebate audit, plus full "
            "review of pharmacy network agreements and the PBM's internal cost structure as it "
            "pertains to pricing applied to Plan Sponsor's claims."
        ),
        "rationale": (
            "Without manufacturer-contract access, 'rebate audits' can only verify what the PBM "
            "chose to report. ERISA §404 fiduciary duty requires the plan sponsor to be able to "
            "verify total manufacturer compensation, not just the slice the PBM chooses to call "
            "'rebates.'"
        ),
        "source": "NASHP Model PBM Contract §8.3; ERISA §404(a)(1)(A)–(B)",
        "impact": "high",
    },
    {
        "section": "Audit Rights — Cost Allocation & Data Delivery",
        "current_language": "All costs associated with any audit shall be borne solely by Plan Sponsor.",
        "suggested_language": (
            "The Plan Sponsor will not be held responsible for time or miscellaneous costs "
            "incurred by the PBM in association with any audit process, including all costs "
            "associated with provision of data, audit finding response reports, or systems "
            "access. PBM will provide complete claim files and documentation (full claim files, "
            "financial reconciliation reports, inclusion files, and plan documentation) to the "
            "auditor within 30 days of receipt of the audit data request."
        ),
        "rationale": (
            "Charging the plan sponsor for audit cooperation is a structural disincentive to "
            "audit. A 30-day data-delivery SLA prevents the PBM from running out the clock on "
            "the audit window through delayed responses."
        ),
        "source": "NASHP Model PBM Contract §8.4; DOL Transparency Rule 29 CFR 2520.408b-2(c)(1)(iv)",
        "impact": "medium",
    },
    {
        "section": "Audit Rights — Post-Termination Survival",
        "current_language": "(No provision found for audit rights surviving termination.)",
        "suggested_language": (
            "The Plan Sponsor's right to audit shall survive the termination of this Agreement "
            "for a period of 3 years. PBM agrees to financial guarantees for turnaround times "
            "for each stage of the audit process and a 30-day turnaround time to provide full "
            "responses to all sample-claims and audit findings. PBM will correct any errors "
            "brought to its attention whether identified by an audit or otherwise."
        ),
        "rationale": (
            "Without survival clauses, the PBM can defeat any audit by terminating the contract "
            "first. ERISA's 3-year statute of limitations on fiduciary breach claims sets the "
            "minimum survival window."
        ),
        "source": "NASHP Model PBM Contract §8.5; ERISA §413 statute of limitations",
        "impact": "medium",
    },
]


def _ensure_audit_rights_redlines(analysis: dict) -> None:
    """
    Replace any AI-generated audit-rights redline(s) with the canonical
    5-card pack when audit rights are deficient. If the AI already produced
    3+ contract-specific audit redlines, keep them (their current_language
    quotes the real contract).
    """
    audit = analysis.get("audit_rights", {}) if isinstance(analysis, dict) else {}
    if not isinstance(audit, dict):
        return
    if _term_penalty(audit, "audit_rights") < 0.45:
        return

    import copy
    redlines = analysis.get("redline_suggestions")
    if not isinstance(redlines, list):
        analysis["redline_suggestions"] = copy.deepcopy(_AUDIT_RIGHTS_CANONICAL_REDLINES)
        return

    ai_audit_redlines = [
        r for r in redlines
        if isinstance(r, dict) and "audit" in str(r.get("section", "")).lower()
    ]
    if len(ai_audit_redlines) >= 3:
        return

    non_audit = [
        r for r in redlines
        if not (isinstance(r, dict) and "audit" in str(r.get("section", "")).lower())
    ]
    canonical = copy.deepcopy(_AUDIT_RIGHTS_CANONICAL_REDLINES)
    analysis["redline_suggestions"] = non_audit + canonical


def _control_posture_for(analysis: dict) -> dict:
    control_map = analysis.get("control_map")
    if not isinstance(control_map, list) or not control_map:
        control_map = _control_map_for(analysis)
        analysis["control_map"] = control_map

    pbm_controlled = [item for item in control_map if str(item.get("controller", "")).lower() == "pbm"]
    shared = [item for item in control_map if str(item.get("controller", "")).lower() == "shared"]
    total = len(control_map) or 1

    pbm_ratio = len(pbm_controlled) / total

    pbm_lever_names = [str(item.get("lever", "")).strip() for item in pbm_controlled if item.get("lever")]
    shared_lever_names = [str(item.get("lever", "")).strip() for item in shared if item.get("lever")]

    if pbm_ratio >= 0.8:
        label = "PBM-controlled"
        level = "high"
        summary = f"PBM controls {', '.join(pbm_lever_names)} — {len(pbm_controlled)} of {total} core levers."
    elif pbm_ratio >= 0.4:
        label = "Mixed control"
        level = "moderate"
        pbm_part = f"PBM controls {', '.join(pbm_lever_names)}" if pbm_lever_names else "PBM controls some levers"
        shared_part = f"; {', '.join(shared_lever_names)} are shared" if shared_lever_names else ""
        summary = f"{pbm_part}{shared_part}."
    else:
        label = "Shared / employer-leaning"
        level = "low"
        summary = f"Most levers are shared or employer-controlled ({', '.join(shared_lever_names + [str(item.get('lever', '')) for item in control_map if str(item.get('controller', '')).lower() not in ('pbm', 'shared')])})."

    return {
        "label": label,
        "level": level,
        "headline": f"{label} posture: PBM controls {len(pbm_controlled)} of {total} core levers",
        "summary": summary,
        "pbm_controlled_levers": len(pbm_controlled),
        "shared_levers": len(shared),
    }


def _structural_risk_override_for(analysis: dict) -> dict:
    ordered = _ordered_term_scores(analysis)
    penalties = {item["key"]: item["penalty"] for item in ordered}

    severe_tier1_keys = [
        key for key in ["rebate_passthrough", "eligible_rebate_definition", "spread_pricing", "specialty_channel", "audit_rights"]
        if penalties.get(key, 0) >= 0.85
    ]

    driver_labels = [TERM_TITLES.get(key, key.replace("_", " ")) for key in severe_tier1_keys]

    drivers_text = ", ".join(driver_labels) if driver_labels else ""

    floor = 0
    level = "low"
    rationale = "No structural override triggered — the weighted score reflects the contract accurately."

    if len(severe_tier1_keys) >= 4:
        floor = 88
        level = "high"
        rationale = f"{drivers_text} are all severely PBM-favorable, outweighing any secondary employer-friendly terms."
    elif len(severe_tier1_keys) >= 3:
        floor = 82
        level = "high"
        rationale = f"{drivers_text} are materially PBM-favorable, so the contract should not read as balanced."
    elif (
        penalties.get("eligible_rebate_definition", 0) >= 0.85
        and penalties.get("spread_pricing", 0) >= 0.85
        and penalties.get("audit_rights", 0) >= 0.45
    ):
        floor = 78
        level = "high"
        rationale = f"{TERM_TITLES.get('eligible_rebate_definition', 'Rebate definition')}, {TERM_TITLES.get('spread_pricing', 'spread pricing')}, and limited audit rights combine into a structurally PBM-favorable deal."
    elif len(severe_tier1_keys) >= 2:
        floor = 70
        level = "moderate"
        rationale = f"{drivers_text} create a contract structure that is more adverse than an equal-weight score suggests."

    return {
        "triggered": floor > 0,
        "level": level,
        "minimum_weighted_risk_score": floor,
        "drivers": driver_labels[:4],
        "headline": "Structural risk override triggered" if floor > 0 else "Weighted scoring only",
        "rationale": rationale,
    }


def _audit_implication_for(analysis: dict) -> str | None:
    """Return a contract-specific audit implication or None.

    Returns None if the AI didn't produce one — the frontend then
    doesn't render the Audit Interpretation callout for that contract.
    Never fakes a generic template.
    """
    return None


def _supporting_detail_for_observation(key: str, analysis: dict) -> str | None:
    exposure = analysis.get("financial_exposure", {}) if isinstance(analysis, dict) else {}
    if not isinstance(exposure, dict):
        return None

    if key == "audit_rights":
        return analysis.get("audit_implication")

    exposure_key = EXPOSURE_SUPPORT_MAP.get(key)
    item = exposure.get(exposure_key) if exposure_key else None
    if isinstance(item, dict) and item.get("estimate"):
        return f"Supporting leakage estimate: {item.get('estimate')}."
    return None


def _derive_benchmark_observations(analysis: dict) -> list[dict]:
    ordered = _ordered_term_scores(analysis)
    observations = []
    seen_slots: set[tuple[str, int]] = set()

    for item in ordered:
        key = item["key"]
        penalty = item["penalty"]
        if penalty <= 0:
            continue
        benchmark = BENCHMARK_LIBRARY.get(key)
        if not benchmark:
            continue
        slot = (benchmark["category"], item["tier"])
        if slot in seen_slots:
            continue
        seen_slots.add(slot)
        term = item["term"]
        observations.append({
            "kind": "consideration",
            "title": f"{TERM_TITLES.get(key, key.replace('_', ' ').title())} falls short of benchmark",
            "category": benchmark["category"],
            "tier": item["tier"],
            "severity": "high" if penalty >= 0.85 else "medium",
            "benchmark_label": benchmark["benchmark_label"],
            "benchmark": benchmark["benchmark"],
            "benchmark_source": benchmark["source"],
            "observation": term.get("details", "This term materially shifts economics or control toward the PBM."),
            "implication": next((entry.get("implication") for entry in analysis.get("control_map", []) if isinstance(entry, dict) and entry.get("lever", "").lower().startswith(benchmark["category"].split("/")[0].lower())), "") or "This term changes the economic or governance balance in favor of the PBM.",
            "recommendation": _derive_top_risks({key: term})[0]["recommendation"] if _derive_top_risks({key: term}) else "Renegotiate this term.",
            "supporting_detail": _supporting_detail_for_observation(key, analysis),
        })
        if len([obs for obs in observations if obs["kind"] == "consideration"]) >= 6:
            break

    strength_candidates = []
    for item in ordered:
        key = item["key"]
        term = item["term"]
        favorability = _normalize_favorability(term.get("favorability"))
        if favorability == "employer_favorable" or item["penalty"] == 0:
            benchmark = BENCHMARK_LIBRARY.get(key)
            if benchmark and term.get("found") is not False:
                strength_candidates.append({
                    "kind": "strength",
                    "title": f"{TERM_TITLES.get(key, key.replace('_', ' ').title())} is closer to benchmark",
                    "category": benchmark["category"],
                    "tier": item["tier"],
                    "severity": "low",
                    "benchmark_label": benchmark["benchmark_label"],
                    "benchmark": benchmark["benchmark"],
                    "benchmark_source": benchmark["source"],
                    "observation": term.get("details", "This term is closer to an employer-favorable benchmark."),
                    "implication": "This is not the main source of economic leakage and should be preserved while higher-impact terms are renegotiated.",
                    "recommendation": "Preserve this language while renegotiating higher-impact terms.",
                    "supporting_detail": None,
                })
    if strength_candidates:
        observations.append(strength_candidates[0])

    return observations


def _recommendations_from_observations(observations: list[dict]) -> list[str]:
    recommendations = []
    for observation in observations:
        if observation.get("kind") != "consideration":
            continue
        recommendation = str(observation.get("recommendation", "")).strip()
        if recommendation and recommendation not in recommendations:
            recommendations.append(recommendation)
    return recommendations[:3]


def _derive_top_risks(analysis: dict) -> list[dict]:
    risks = []
    recommendations = {
        "eligible_rebate_definition": "Expand the definition of eligible rebates to include all manufacturer compensation.",
        "spread_pricing": "Require pass-through pricing or quarterly claim-level spread reconciliation.",
        "specialty_channel": "Add specialty vendor optionality and transparent specialty pricing terms.",
        "audit_rights": "Expand audit rights to manufacturer contracts, network agreements, and specialty economics.",
        "mac_pricing": "Add MAC transparency, update standards, and appeals rights.",
        "formulary_clauses": "Require employer approval or stricter notice and justification for formulary changes.",
        "termination_provisions": "Shorten notice and remove termination penalties.",
        "gag_clauses": "Remove restrictions on sharing pricing and rebate data with advisors.",
        "rebate_passthrough": "Tie passthrough guarantees to an expanded rebate definition and remittance reporting.",
        "statistical_extrapolation_rights": "Permit statistical extrapolation for audited claim errors.",
    }
    for key, weight in TIER_WEIGHTS.items():
        term = analysis.get(key)
        if not isinstance(term, dict):
            continue
        penalty = _term_penalty(term, key)
        if penalty <= 0:
            continue
        risks.append({
            "title": TERM_TITLES.get(key, key.replace("_", " ")),
            "tier": TIER_LABELS.get(key, 3),
            "severity": "high" if penalty >= 0.85 else "medium",
            "why_it_matters": term.get("details", "This term materially shifts economics or control toward the PBM."),
            "recommendation": recommendations.get(key, "Renegotiate this term."),
            "_score": weight * penalty,
        })
    risks.sort(key=lambda item: item["_score"], reverse=True)
    return [{k: v for k, v in risk.items() if k != "_score"} for risk in risks[:3]]


def enrich_contract_analysis(analysis: dict) -> dict:
    if not isinstance(analysis, dict):
        return analysis

    total_weight = sum(TIER_WEIGHTS.values())
    weighted_penalty = 0.0
    tier_buckets = {1: {"label": "Tier 1", "score": 0.0, "weight": 0}, 2: {"label": "Tier 2", "score": 0.0, "weight": 0}, 3: {"label": "Tier 3", "score": 0.0, "weight": 0}}

    for key, weight in TIER_WEIGHTS.items():
        term = analysis.get(key)
        if not isinstance(term, dict):
            continue
        penalty = _term_penalty(term, key)
        weighted_penalty += weight * penalty
        tier = TIER_LABELS.get(key, 3)
        tier_buckets[tier]["score"] += weight * penalty
        tier_buckets[tier]["weight"] += weight

    weighted_score = round((weighted_penalty / total_weight) * 100)

    top_risks = analysis.get("top_risks")
    if not isinstance(top_risks, list) or not top_risks:
        top_risks = _derive_top_risks(analysis)
        analysis["top_risks"] = top_risks

    ai_exposure = analysis.get("financial_exposure")
    det_exposure = _financial_exposure_for(analysis)
    if isinstance(ai_exposure, dict):
        for subkey in ("rebate_leakage", "spread_exposure", "specialty_control"):
            if not isinstance(ai_exposure.get(subkey), dict):
                ai_exposure[subkey] = det_exposure.get(subkey)
            else:
                det_sub = det_exposure.get(subkey, {})
                for field in ("level", "estimate", "driver"):
                    if not ai_exposure[subkey].get(field):
                        ai_exposure[subkey][field] = det_sub.get(field)
        if not ai_exposure.get("summary"):
            ai_exposure["summary"] = det_exposure.get("summary")
        analysis["financial_exposure"] = ai_exposure
    else:
        analysis["financial_exposure"] = det_exposure
    claims_backed_exposure = _claims_backed_exposure_for(analysis)
    if claims_backed_exposure:
        analysis["financial_exposure"] = claims_backed_exposure
    _attach_dollar_exposure(analysis)

    _ensure_audit_rights_redlines(analysis)

    _attach_redline_savings(analysis)

    _attach_critical_dates(analysis)

    deterministic_map = _control_map_for(analysis)
    ai_map = analysis.get("control_map")
    if isinstance(ai_map, list) and ai_map:
        ai_by_lever = {}
        for item in ai_map:
            if isinstance(item, dict):
                key = str(item.get("lever", "")).strip().lower()
                if key:
                    ai_by_lever[key] = item
        merged = []
        for det in deterministic_map:
            key = str(det.get("lever", "")).strip().lower()
            if key in ai_by_lever:
                ai_item = ai_by_lever[key]
                merged.append({
                    "lever": det["lever"],
                    "controller": ai_item.get("controller") or det.get("controller"),
                    "assessment": ai_item.get("assessment") or det.get("assessment"),
                    "implication": ai_item.get("implication") or det.get("implication"),
                })
            else:
                merged.append(det)
        analysis["control_map"] = merged
    else:
        analysis["control_map"] = deterministic_map

    if not analysis.get("control_posture"):
        analysis["control_posture"] = _control_posture_for(analysis)

    if not analysis.get("structural_risk_override"):
        analysis["structural_risk_override"] = _structural_risk_override_for(analysis)

    if not analysis.get("audit_implication"):
        analysis["audit_implication"] = _audit_implication_for(analysis)

    ai_obs = analysis.get("benchmark_observations")
    if isinstance(ai_obs, list) and len(ai_obs) >= 2:
        required_fields = {"kind", "title", "category", "tier", "severity", "observation"}
        valid_obs = [
            obs for obs in ai_obs
            if isinstance(obs, dict) and required_fields.issubset(obs.keys())
        ]
        if len(valid_obs) >= 2:
            analysis["benchmark_observations"] = valid_obs
        else:
            analysis["benchmark_observations"] = _derive_benchmark_observations(analysis)
    else:
        analysis["benchmark_observations"] = _derive_benchmark_observations(analysis)

    if not analysis.get("benchmark_recommendations"):
        analysis["benchmark_recommendations"] = _recommendations_from_observations(analysis.get("benchmark_observations", []))

    if not analysis.get("immediate_actions"):
        analysis["immediate_actions"] = (
            analysis.get("benchmark_recommendations")
            or [risk["recommendation"] for risk in top_risks[:3]]
        )

    if not analysis.get("deal_diagnosis"):
        drivers = []
        if any(risk.get("title", "").lower().startswith("eligible rebate") or "rebate" in risk.get("title", "").lower() for risk in top_risks):
            drivers.append("rebate passthrough limited by exclusion-based definitions")
        if any("spread" in risk.get("title", "").lower() for risk in top_risks):
            drivers.append("spread pricing retained by the PBM")
        if any("specialty" in risk.get("title", "").lower() for risk in top_risks):
            drivers.append("specialty channel control retained by the PBM")
        if _term_penalty(analysis.get("audit_rights", {}), "audit_rights") >= 0.45:
            drivers.append("audit rights too limited to verify core economics")
        diagnosis = "PBM-favorable contract structure"
        if drivers:
            diagnosis += " with " + ", ".join(drivers[:3]) + "."
        analysis["deal_diagnosis"] = diagnosis

    structural_override = analysis.get("structural_risk_override", {})
    override_floor = int(structural_override.get("minimum_weighted_risk_score", 0) or 0) if isinstance(structural_override, dict) else 0
    adjusted_weighted_score = max(weighted_score, override_floor)
    analysis["overall_risk_score"] = max(int(analysis.get("overall_risk_score", 0) or 0), adjusted_weighted_score)

    analysis["weighted_assessment"] = {
        "deal_score": max(0, 100 - adjusted_weighted_score),
        "base_weighted_risk_score": weighted_score,
        "weighted_risk_score": adjusted_weighted_score,
        "risk_level": "high" if adjusted_weighted_score >= 65 else "moderate" if adjusted_weighted_score >= 35 else "low",
        "tier_scores": [
            {
                "tier": bucket["label"],
                "score": round((bucket["score"] / bucket["weight"]) * 100) if bucket["weight"] else 0,
                "weight": bucket["weight"],
            }
            for bucket in tier_buckets.values()
        ],
        "methodology": (
            "Tier 1 economics and control drivers outweigh administrative terms."
            + (" Structural override applied because multiple Tier 1 failures would otherwise look artificially balanced." if override_floor and override_floor > weighted_score else "")
        ),
        "structural_override_triggered": bool(override_floor and override_floor > weighted_score),
    }

    return analysis
