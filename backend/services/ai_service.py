"""
OpenAI integration for ClearScript.
Provides AI-powered contract analysis, disclosure review, audit letter generation, and report analysis.

If OPENAI_API_KEY is unset or the API call fails, these functions raise.
Callers (routers) are expected to translate the exception into an HTTP 503
so the frontend can surface a real error instead of silently serving stale
or canned data.
"""

import os
import json
import asyncio
import logging
import threading
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

# Load .env from project root (one level up from backend/)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

_client = None
_client_lock = threading.Lock()
MODEL = "gpt-5.4-mini"

def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.error("OPENAI_API_KEY not set — AI features will fail")
                    raise ValueError("OPENAI_API_KEY not set")
                _client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized")
    return _client

async def _generate(system_prompt: str, user_prompt: str, max_tokens: int = 16000) -> str:
    """
    Run OpenAI generation in a thread to keep it async-compatible.

    Notes on the gpt-5 family:
      * It rejects the legacy `max_tokens` parameter — use
        `max_completion_tokens` instead.
      * It rejects any `temperature` other than the default 1.
      * `max_completion_tokens` is a budget for BOTH reasoning tokens
        AND output tokens combined. If the budget is too small the model
        spends all of it on internal reasoning and returns an empty
        message body, which then crashes `json.loads("")`. The default
        here is set high enough (16k) that reasoning + structured JSON
        output both fit comfortably.

    The argument name on this function stays `max_tokens` so the six
    callers in ai_service / spc_service / plan_crossref_service don't
    have to change.
    """
    client = _get_client()
    def _call():
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        text = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        if not text:
            # gpt-5 reasoning models return empty content when the
            # max_completion_tokens budget is consumed entirely by
            # internal reasoning. Surface that as a real error instead
            # of letting json.loads("") raise a confusing "Expecting
            # value: line 1 column 1" downstream.
            raise RuntimeError(
                f"OpenAI returned empty content (finish_reason={finish_reason}). "
                f"This usually means max_completion_tokens={max_tokens} was "
                f"consumed entirely by reasoning. Increase the budget."
            )
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3].strip()
        return text
    try:
        # gpt-5 reasoning runs are slower than legacy chat models, so
        # the 30s timeout that worked for gpt-4o-mini is too tight.
        return await asyncio.wait_for(asyncio.to_thread(_call), timeout=120.0)
    except asyncio.TimeoutError:
        raise TimeoutError("OpenAI API call timed out after 120 seconds")

# ─── Contract Analysis ──────────────────────────────────────────────────────────

CONTRACT_SYSTEM_PROMPT = """You are a PBM contract analyst advising employer health plan sponsors. Your job is to assess whether each contract provision favors the EMPLOYER or the PBM.

CRITICAL FRAMING: Do NOT use "compliant" vs "non-compliant." Instead, rate each provision on this scale:
- "employer_favorable" — term protects the employer's interests
- "neutral" — standard industry language, neither side strongly advantaged
- "pbm_favorable" — term protects PBM interests at employer's expense

Return valid JSON with this structure:

{
  "rebate_passthrough": {
    "found": true,
    "percentage": "85% of eligible rebates",
    "effective_passthrough": "Estimated 55-65% of total manufacturer payments",
    "favorability": "pbm_favorable",
    "details": "description"
  },
  "spread_pricing": {
    "found": true,
    "caps": "No explicit caps",
    "favorability": "pbm_favorable",
    "details": "description"
  },
  "formulary_clauses": {
    "found": true,
    "change_notification_days": 60,
    "favorability": "pbm_favorable",
    "details": "description",
    "lower_net_cost_language": false,
    "lower_net_cost_details": "If contract uses 'lower net cost' language it signals PBM optimizing for rebates over ingredient cost"
  },
  "audit_rights": {
    "found": true,
    "frequency": "Once per year",
    "scope": "Limited",
    "favorability": "pbm_favorable",
    "details": "description",
    "checklist": {
      "ndc_level_audit": {"found": false, "details": ""},
      "annual_audit_right": {"found": false, "details": ""},
      "lookback_36_months": {"found": false, "details": ""},
      "notice_90_days_or_less": {"found": false, "details": ""},
      "data_delivery_30_days": {"found": false, "details": ""},
      "finding_response_30_days": {"found": false, "details": ""},
      "financial_guarantees_turnaround": {"found": false, "details": ""},
      "error_correction": {"found": false, "details": ""},
      "manufacturer_contract_access": {"found": false, "details": ""},
      "survival_post_termination_3yr": {"found": false, "details": ""},
      "no_audit_cost_to_plan": {"found": false, "details": ""}
    }
  },
  "mac_pricing": {
    "found": true,
    "update_frequency": "Monthly",
    "appeal_rights": false,
    "favorability": "pbm_favorable",
    "details": "description"
  },
  "termination_provisions": {
    "found": true,
    "notice_days": 180,
    "penalties": "Liquidated damages",
    "favorability": "pbm_favorable",
    "details": "description"
  },
  "gag_clauses": {
    "found": true,
    "favorability": "pbm_favorable",
    "details": "description"
  },
  "specialty_channel": {
    "found": true,
    "external_routing_rights": false,
    "vendor_channel_optionality": false,
    "pricing_transparency": false,
    "favorability": "pbm_favorable",
    "details": "Assess whether employer has optionality over specialty drug sourcing — routing rights, choice of specialty pharmacy vendor, and pricing visibility. The issue is NOT whether a carve-out exists, but whether the employer has any control or optionality."
  },
  "eligible_rebate_definition": {
    "found": true,
    "definition_text": "exact contract language",
    "includes_admin_fees": false,
    "includes_volume_bonuses": false,
    "includes_price_protection": false,
    "narrow_definition_flag": true,
    "favorability": "pbm_favorable",
    "details": "description"
  },
  "dispute_resolution": {
    "found": true,
    "mechanism": "arbitration",
    "favorability": "pbm_favorable",
    "details": "description"
  },
  "statistical_extrapolation_rights": {
    "found": false,
    "favorability": "pbm_favorable",
    "details": "description"
  },
  "linked_findings": [
    {
      "title": "Rebate Passthrough Undermined by Narrow Definition",
      "terms_involved": ["rebate_passthrough", "eligible_rebate_definition"],
      "explanation": "Contract states X% passthrough but narrow eligible rebate definition limits effective passthrough to Y%",
      "economic_impact": "description of dollar impact"
    }
  ],
  "economic_linkages": [
    "MAC opacity + pass-through pricing creates hidden PBM margin",
    "Formulary control + narrow rebate definitions allow PBM to maximize retained rebates",
    "Specialty channel lock-in + lack of routing rights eliminates employer price competition",
    "Audit scope limits + rebate exclusions prevent discovery of true PBM economics"
  ],
  "redline_suggestions": [
    {
      "section": "Section 5.2 — Eligible Rebate Definition",
      "current_language": "Exact quote from the contract being analyzed",
      "suggested_language": "Employer-favorable replacement language",
      "rationale": "Why this change matters and what it fixes",
      "source": "Gold-standard state PBM contract language or ERISA best practice",
      "impact": "high"
    }
  ],
  "compliance_flags": [
    {"issue": "description", "severity": "high", "favorability": "pbm_favorable", "recommendation": "what to do"}
  ],
  "deal_diagnosis": "one-line plain-English diagnosis of the contract structure",
  "financial_exposure": {
    "summary": "directional financial exposure summary",
    "rebate_leakage": {"level": "high", "estimate": "3-6% of brand spend", "driver": "narrow rebate definition"},
    "spread_exposure": {"level": "high", "estimate": "1-3% of total claims spend", "driver": "spread retained by PBM"},
    "specialty_control": {"level": "high", "estimate": "30-50% of total Rx spend subject to PBM channel control", "driver": "exclusive specialty routing"}
  },
  "control_map": [
    {"lever": "Rebates", "controller": "PBM", "assessment": "PBM retains control through exclusion-based rebate definition", "implication": "Plan cannot verify full manufacturer compensation"},
    {"lever": "Pricing", "controller": "PBM", "assessment": "Spread pricing retained with limited transparency", "implication": "Plan cannot validate net claim economics"}
  ],
  "top_risks": [
    {"title": "Narrow rebate definition", "tier": 1, "severity": "high", "why_it_matters": "Passthrough promise is materially reduced", "recommendation": "Expand eligible rebate definition"},
    {"title": "Spread pricing retained", "tier": 1, "severity": "high", "why_it_matters": "PBM can keep undisclosed margin", "recommendation": "Require pass-through pricing"},
    {"title": "Restricted specialty control", "tier": 1, "severity": "high", "why_it_matters": "Highest-cost channel remains under PBM control", "recommendation": "Add vendor optionality and transparent specialty pricing"}
  ],
  "immediate_actions": [
    "Renegotiate eligible rebate definition before renewal",
    "Require spread pricing prohibition or quarterly reconciliation",
    "Expand audit rights to manufacturer contracts, network agreements, and specialty economics"
  ],
  "audit_implication": "state explicitly what the plan sponsor cannot verify under the current audit language",
  "overall_risk_score": 78,
  "summary": "overall assessment"
}

KEY ANALYSIS RULES:
1. LINK RELATED FINDINGS: If passthrough % is high but rebate definition is narrow, these MUST appear in linked_findings showing the effective passthrough is lower than stated. Never present these as independent good+bad findings.
2. TERMINATION: Notice periods >90 days, liquidated damages, auto-renewal = PBM-favorable. Only flag as employer-favorable if: short notice (<60 days), no penalties, no auto-renewal, survival of data/audit rights.
3. SPECIALTY CHANNEL: Do NOT flag "no specialty carve-out" as a standalone issue. Instead assess routing rights, vendor optionality, and pricing transparency. The employer needs OPTIONS, not necessarily a carve-out.
4. NET COST LANGUAGE: If contract references "lower net cost" drugs rather than "lower ingredient cost," flag this — it signals PBM optimizing for rebate revenue over actual drug cost to the plan.
5. ECONOMIC LINKAGES: Identify cross-cutting patterns where multiple contract terms combine to create PBM economic advantage (MAC opacity + pass-through, formulary control + rebate definitions, audit limits + rebate exclusions).
6. ELIGIBLE REBATE DEFINITION: This is the #1 most impactful clause. If it excludes admin fees, volume bonuses, or price protection, the stated passthrough is misleading.
7. AUDIT RIGHTS CHECKLIST: Check all 11 items. Most PBM contracts fail 6-8.
8. REDLINE SUGGESTIONS: For EVERY term rated "pbm_favorable", generate a specific redline suggestion with:
   - The exact current language from the contract (quote it)
   - Replacement language that shifts the term to employer-favorable
   - Use these gold-standard templates as your source:

   REBATE DEFINITION: "Eligible Rebates shall include all compensation received by PBM from pharmaceutical manufacturers, including but not limited to base rebates, administrative fees, volume bonuses, price protection payments, market share incentives, data fees, and service fees, regardless of how such payments are characterized by the manufacturer or PBM."

   AUDIT RIGHTS: "The Plan Sponsor or its designee shall have the right to audit annually, with an auditor of its choice, for both claims and rebates, with full cooperation of the selected PBM, the claims, services and pricing and/or rebates, including the manufacturer or aggregator rebate contracts held by the PBM, to verify compliance with all program requirements and contractual guarantees with no additional charge from the PBM."

   AUDIT LOOKBACK: "The Plan Sponsor or its designee shall have the right to audit up to 36 months of claims data at no additional charge from the PBM."

   AUDIT NOTICE: "The Plan Sponsor shall have the right to audit, with an auditor of its choice, at any time provided the Plan Sponsor gives 90-days advance notice."

   DATA DELIVERY: "PBM will provide complete claim files and documentation (i.e., full claim files, financial reconciliation reports, inclusion files, and plan documentation) to the auditor within 30 days of receipt of the audit data request."

   FINDING RESPONSE: "PBM agrees to a 30-day turnaround time to provide the full responses to all of the sample claims and claims audit findings."

   FINANCIAL GUARANTEES: "PBM agrees to financial guarantees for turnaround times for each stage of the audit process."

   ERROR CORRECTION: "PBM will correct any errors that the Plan Sponsor, or its representative, brings to the PBM's attention whether identified by an audit or otherwise."

   MANUFACTURER ACCESS: "The Plan Sponsor or its designee shall have the right to audit up to 12 pharmaceutical manufacturer contracts during an on-site rebate audit."

   POST-TERMINATION: "The Plan Sponsor's right to audit shall survive the termination of the agreement between the parties for a period of 3 years."

   NO COST TO PLAN: "The Plan Sponsor will not be held responsible for time or miscellaneous costs incurred by the PBM in association with any audit process including, all costs associated with provision of data, audit finding response reports, or systems access, provided to the Plan Sponsor or its designee by the PBM during the life of the contract."

   SPREAD PRICING: "PBM shall operate on a pass-through pricing model. The amount billed to Plan Sponsor for each claim shall equal the actual amount reimbursed to the dispensing pharmacy plus a transparent, pre-agreed administrative fee. PBM shall not retain any spread between the plan-billed amount and pharmacy reimbursement."

   TERMINATION: "Either party may terminate this Agreement upon 60 days written notice. No early termination fees, liquidated damages, or penalties shall apply. PBM shall provide transition assistance at no additional cost for 90 days following termination."

   GAG CLAUSE: "Nothing in this Agreement shall restrict Plan Sponsor from disclosing pricing, rebate, or cost data to its benefits consultants, brokers, fiduciary advisors, auditors, or legal counsel. This provision is consistent with CAA 2021 Section 201."

   FORMULARY: "PBM shall not make mid-year changes to formulary tier placement without prior written approval of Plan Sponsor. All formulary changes must be accompanied by clinical justification and 90-day advance notice."

   SPECIALTY CHANNEL: "Plan Sponsor retains the right to designate or approve the specialty pharmacy vendor(s) used for dispensing specialty medications. PBM shall provide transparent pricing for specialty drugs including acquisition cost, dispensing fees, and any channel-specific markups."

   Only generate redlines for terms that are pbm_favorable. Do not generate redlines for employer_favorable or neutral terms.
9. DECISION LAYER: Do not treat all issues equally. Weight the output explicitly:
   - Tier 1: rebate structure, spread pricing, specialty control
   - Tier 2: MAC pricing, formulary control, channel requirements
   - Tier 3: notice, termination, and other administrative terms
10. FINANCIAL EXPOSURE: Keep estimates directional, not fake precision. Express exposure as ranges or percentages of spend, not invented exact dollars unless the contract itself supports it.
11. AUDIT IMPLICATIONS: Move beyond missing-provision lists. State plainly when the current audit language means the plan sponsor cannot verify pricing, rebate flows, manufacturer compensation, or specialty economics.
"""

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


def _control_posture_for(analysis: dict) -> dict:
    control_map = analysis.get("control_map")
    if not isinstance(control_map, list) or not control_map:
        control_map = _control_map_for(analysis)

    pbm_controlled = [item for item in control_map if str(item.get("controller", "")).lower() == "pbm"]
    shared = [item for item in control_map if str(item.get("controller", "")).lower() == "shared"]
    total = len(control_map) or 1

    if len(pbm_controlled) >= 4:
        label = "PBM-controlled"
        level = "high"
        summary = "PBM controls most of the economic and governance levers, so leakage estimates should be read as consequences of structural control rather than isolated clause defects."
    elif len(pbm_controlled) >= 2:
        label = "Mixed control"
        level = "moderate"
        summary = "Control is split, but the PBM still holds enough leverage to influence pricing, rebates, or specialty economics without full employer verification."
    else:
        label = "Shared / employer-leaning"
        level = "low"
        summary = "Core economic levers are not concentrated solely with the PBM, reducing structural leakage risk."

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

    floor = 0
    level = "low"
    rationale = "No structural override triggered."

    if len(severe_tier1_keys) >= 4:
        floor = 88
        level = "high"
        rationale = "Multiple Tier 1 economics and control failures outweigh any secondary employer-friendly terms."
    elif len(severe_tier1_keys) >= 3:
        floor = 82
        level = "high"
        rationale = "Three or more Tier 1 drivers are materially PBM-favorable, so the contract should not read as balanced."
    elif (
        penalties.get("eligible_rebate_definition", 0) >= 0.85
        and penalties.get("spread_pricing", 0) >= 0.85
        and penalties.get("audit_rights", 0) >= 0.45
    ):
        floor = 78
        level = "high"
        rationale = "Rebate leakage, spread pricing, and limited audit rights combine into a structurally PBM-favorable deal."
    elif len(severe_tier1_keys) >= 2:
        floor = 70
        level = "moderate"
        rationale = "Two Tier 1 economics/control failures create a contract structure that is more adverse than an equal-weight score suggests."

    return {
        "triggered": floor > 0,
        "level": level,
        "minimum_weighted_risk_score": floor,
        "drivers": driver_labels[:4],
        "headline": "Structural risk override triggered" if floor > 0 else "Weighted scoring only",
        "rationale": rationale,
    }


def _audit_implication_for(analysis: dict) -> str:
    audit = analysis.get("audit_rights", {}) if isinstance(analysis, dict) else {}
    details = str(audit.get("details", "")).lower()
    exposure = analysis.get("financial_exposure", {}) if isinstance(analysis, dict) else {}
    claims_context = exposure.get("claims_context", {}) if isinstance(exposure, dict) else {}
    if claims_context:
        specialty_spend = claims_context.get("specialty_spend", 0)
        total_spend = claims_context.get("total_spend", 0)
        return (
            "Current audit language leaves the plan sponsor unable to verify pharmacy reimbursement, full manufacturer compensation, "
            f"or specialty economics across ${specialty_spend:,.2f} of observed specialty spend and ${total_spend:,.2f} of uploaded claim volume."
        )
    if not audit or "limited" in details or "not include" in details or "claims data only" in details:
        return "Current audit language leaves the plan sponsor unable to verify pharmacy reimbursement, full manufacturer compensation, network economics, or specialty channel performance."
    return "Audit language appears broader, but pricing, rebate, and specialty data should still be tested in practice."


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

    for item in ordered:
        key = item["key"]
        penalty = item["penalty"]
        if penalty <= 0:
            continue
        benchmark = BENCHMARK_LIBRARY.get(key)
        if not benchmark:
            continue
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
        if len([obs for obs in observations if obs["kind"] == "consideration"]) >= 3:
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

    if not analysis.get("financial_exposure"):
        analysis["financial_exposure"] = _financial_exposure_for(analysis)
    claims_backed_exposure = _claims_backed_exposure_for(analysis)
    if claims_backed_exposure:
        analysis["financial_exposure"] = claims_backed_exposure

    if not analysis.get("control_map"):
        analysis["control_map"] = _control_map_for(analysis)

    if not analysis.get("control_posture"):
        analysis["control_posture"] = _control_posture_for(analysis)

    if not analysis.get("structural_risk_override"):
        analysis["structural_risk_override"] = _structural_risk_override_for(analysis)

    if not analysis.get("audit_implication"):
        analysis["audit_implication"] = _audit_implication_for(analysis)

    if not analysis.get("benchmark_observations"):
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

async def analyze_contract(text: str) -> dict:
    """
    Run a PBM contract through the OpenAI-powered analyzer.

    Raises on any failure (missing key, network error, bad JSON, rate limit).
    The caller is responsible for turning the exception into an HTTP error
    the frontend can display.
    """
    result = await _generate(CONTRACT_SYSTEM_PROMPT, f"Analyze this PBM contract:\n\n{text[:12000]}", 3000)
    parsed = json.loads(result)
    parsed["_generated_by"] = "ai"
    return enrich_contract_analysis(parsed)



# ─── Disclosure Analysis ────────────────────────────────────────────────────────

DISCLOSURE_SYSTEM_PROMPT = """You are a PBM disclosure compliance analyst. Review the provided PBM disclosure document against DOL-required items for prescription drug reporting.

Check for the presence and completeness of each required item and return structured JSON:

{
  "completeness_score": int (0-100),
  "items_checked": [
    {
      "item": str,
      "category": str,
      "required": bool,
      "found": bool,
      "complete": bool,
      "details": str,
      "gap_description": str or null
    }
  ],
  "gap_report": {
    "critical_gaps": [str],
    "moderate_gaps": [str],
    "minor_gaps": [str]
  },
  "summary": str
}
"""

async def analyze_disclosure(text: str) -> dict:
    """
    Score a PBM disclosure against DOL-required items. Raises on failure.
    """
    result = await _generate(DISCLOSURE_SYSTEM_PROMPT, f"Analyze this PBM disclosure document for DOL compliance:\n\n{text[:12000]}", 4000)
    parsed = json.loads(result)
    parsed["_generated_by"] = "ai"
    return parsed


# ─── Audit Letter Generation ────────────────────────────────────────────────────

AUDIT_LETTER_SYSTEM_PROMPT = """You are a benefits attorney drafting a formal audit request letter from an employer plan sponsor to their PBM.

Generate a professional audit request letter that:
1. Cites specific DOL rule provisions and ERISA fiduciary obligations
2. References specific findings from the contract analysis
3. Specifies exact data the employer is legally entitled to receive
4. Includes a 10-business-day response deadline
5. Notes that failure to comply may constitute a fiduciary breach

Return JSON with:
{
  "letter_text": str (full formatted letter),
  "key_demands": [str],
  "legal_citations": [str],
  "deadline": str
}
"""

async def generate_audit_letter(contract_data: dict, findings: dict) -> dict:
    """
    Draft a formal audit request letter. Raises on failure.
    """
    result = await _generate(
        AUDIT_LETTER_SYSTEM_PROMPT,
        f"Generate an audit request letter based on these findings:\n\n"
        f"Contract Analysis:\n{json.dumps(contract_data, indent=2)[:4000]}\n\n"
        f"Audit Findings:\n{json.dumps(findings, indent=2)[:4000]}",
        4000,
    )
    return json.loads(result)


# ─── Report Analysis ────────────────────────────────────────────────────────────

REPORT_SYSTEM_PROMPT = """You are a PBM reporting auditor. Analyze the provided semiannual PBM report and claims data to identify discrepancies, anomalies, and areas of concern.

Return structured JSON:
{
  "findings": [{"category": str, "severity": str, "finding": str, "evidence": str, "recommendation": str}],
  "overall_assessment": str,
  "risk_level": "low" | "medium" | "high" | "critical"
}
"""

async def analyze_report(report_text: str, claims_data: dict) -> dict:
    """
    Analyze a semiannual PBM report against claims data. Raises on failure.
    """
    result = await _generate(
        REPORT_SYSTEM_PROMPT,
        f"Analyze this PBM report against claims data:\n\n"
        f"Report:\n{report_text[:6000]}\n\n"
        f"Claims Summary:\n{json.dumps(claims_data, indent=2)[:4000]}",
        3000,
    )
    return json.loads(result)
