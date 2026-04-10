"""
OpenAI integration for ClearScript.
Provides AI-powered contract analysis, disclosure review, audit letter generation, and report analysis.

If OPENAI_API_KEY is unset or the API call fails, these functions raise.
Callers (routers) are expected to translate the exception into an HTTP 503
so the frontend can surface a real error instead of silently serving stale
or canned data.
"""

import os
import re
import json
import asyncio
import logging
import threading
import time
import inspect
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from services.usage_service import log_ai_call

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

def _extract_first_json_object(text: str) -> str:
    """
    Pull the first complete JSON object out of a model response and return
    it as a clean string ready for json.loads(). Robust to:

      - leading whitespace
      - leading non-JSON preamble (e.g. "Here is the analysis:" before {)
      - trailing content after the closing brace (extra commentary, a
        second JSON object, or a stray newline followed by anything)
      - markdown fences (already stripped earlier in _generate but
        belt-and-suspenders here too)

    The error this fixes was:
        Extra data: line 2 column 1 (char 52)
    which Python's json.loads raises when the response is something like:
        {"deal_score": 5, ...}
        {"some_other_object": ...}
    json.loads parses the first object, then refuses to silently drop
    the trailing content. raw_decode is the canonical Python way to
    parse one JSON value and tell us where it ended, so we can
    deliberately ignore everything after.

    Raises ValueError if no JSON object is present at all — the caller
    surfaces that as a 503 with a clear message.
    """
    text = text.strip()
    if not text:
        raise ValueError("Empty response — nothing to parse as JSON")

    # Strip a stray code fence if one slipped through (the main strip is
    # in _generate, but raw model output sometimes wraps JSON in ```json…```
    # with trailing whitespace that the simpler strip in _generate misses).
    if text.startswith("```"):
        text = text[3:]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.lstrip("\n").rstrip()
        if text.endswith("```"):
            text = text[:-3].rstrip()

    # Find the first opening brace — anything before it is preamble we
    # silently drop. This handles "Here is your analysis:\n\n{...}".
    first_brace = text.find("{")
    if first_brace == -1:
        raise ValueError(
            f"No JSON object found in response (got {len(text)} chars, starts with {text[:60]!r})"
        )

    decoder = json.JSONDecoder()
    try:
        obj, _end = decoder.raw_decode(text[first_brace:])
    except json.JSONDecodeError as e:
        # Re-raise with a snippet of the offending response so we can
        # actually debug it from the error message in production logs.
        snippet = text[first_brace : first_brace + 200]
        raise ValueError(
            f"Could not parse JSON object from model response: {e}. "
            f"First 200 chars after the opening brace: {snippet!r}"
        ) from e

    # Re-serialize to canonical form so downstream json.loads is trivial.
    return json.dumps(obj)


def _infer_operation_name() -> str:
    """
    Walk the call stack to find the public function that triggered this
    AI call (e.g. analyze_contract, generate_audit_letter, parse_spc).
    Used to label the row in ai_calls so usage queries can be split by
    feature without manual tagging at every call site.
    """
    try:
        for frame_info in inspect.stack()[1:8]:
            name = frame_info.function
            if name.startswith("_") or name in ("_generate", "_call", "wrapper"):
                continue
            if name in (
                "analyze_contract",
                "analyze_disclosure",
                "generate_audit_letter",
                "analyze_report",
                "parse_spc",
                "compare_spcs",
                "cross_reference_contract_and_plan",
            ):
                return name
        return "ai_generate"
    except Exception:
        return "ai_generate"


async def _generate(system_prompt: str, user_prompt: str, max_tokens: int = 16000) -> str:
    """
    Run OpenAI generation in a thread to keep it async-compatible.

    Every call is logged to the ai_calls table via usage_service. The
    log captures: operation name, model, full prompts, full response,
    token counts, latency, cost estimate, and any error. This is the
    raw data the product analytics layer reads from.

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
    operation = _infer_operation_name()
    started = time.perf_counter()
    response_text: str | None = None
    prompt_tokens = 0
    completion_tokens = 0
    error_str: str | None = None
    request_id: str | None = None

    def _call():
        nonlocal prompt_tokens, completion_tokens, request_id
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        # Capture token usage + the OpenAI request id for cost analytics
        # and reproduction. Tolerate missing fields on older SDKs.
        try:
            usage = response.usage
            if usage is not None:
                prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
                completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        except Exception:
            pass
        try:
            request_id = getattr(response, "id", None)
        except Exception:
            request_id = None

        text = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        if not text:
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
        # Make the response robust to "valid JSON + trailing content" or
        # leading preamble — gpt-5 reasoning models occasionally violate
        # response_format=json_object by appending stray newlines or a
        # second object. _extract_first_json_object isolates the first
        # complete JSON object so downstream json.loads always succeeds.
        return _extract_first_json_object(text)

    try:
        response_text = await asyncio.wait_for(asyncio.to_thread(_call), timeout=120.0)
        return response_text
    except asyncio.TimeoutError as e:
        error_str = "timeout after 120 seconds"
        raise TimeoutError("OpenAI API call timed out after 120 seconds") from e
    except Exception as e:
        error_str = f"{type(e).__name__}: {e}"
        raise
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            log_ai_call(
                operation=operation,
                model=MODEL,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_text=response_text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                error=error_str,
                request_id=request_id,
            )
        except Exception as log_err:
            # Logging must never break the request path.
            logger.debug(f"AI call logging failed: {log_err}")

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
  "contract_identification": {
    "plan_sponsor_name": "exact name of the employer / plan sponsor as written in the contract preamble",
    "pbm_name": "exact name of the PBM as written in the contract preamble",
    "effective_date": "ISO date YYYY-MM-DD if found in the contract — null if not stated",
    "initial_term_months": 36,
    "current_term_end_date": "ISO date YYYY-MM-DD when the current term expires — null if uncomputable",
    "termination_notice_days": 180,
    "renewal_mechanism": "one-line description of how the contract renews (e.g. 'Auto-renewal for successive 1-year terms unless either party gives 180 days written notice')"
  },
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

   AUDIT RIGHTS REDLINES MUST BE SPLIT: Do NOT generate one combined audit-rights redline. Generate up to 5 distinct redlines, each with its own section name and copyable language: (1) Audit Rights — Frequency & Auditor of Choice, (2) Audit Rights — Notice & Lookback, (3) Audit Rights — Scope & Manufacturer Access, (4) Audit Rights — Cost Allocation & Data Delivery, (5) Audit Rights — Post-Termination Survival. Each must be individually actionable so the plan sponsor can take them to PBM negotiation one at a time.

   SOURCE FIELD: The `source` field on each redline is required and must cite a specific external authority — model contract section number (e.g. "NASHP Model PBM Contract §4.2"), statute (e.g. "ERISA §404(a)(1)", "CAA 2021 §201", "DOL Transparency Rule 29 CFR 2520.408b-2(c)(1)(iv)"), or recognized industry standard. Never leave it blank or write "industry best practice" — the plan sponsor's counsel needs to be able to verify the citation.
9. DECISION LAYER: Do not treat all issues equally. Weight the output explicitly:
   - Tier 1: rebate structure, spread pricing, specialty control
   - Tier 2: MAC pricing, formulary control, channel requirements
   - Tier 3: notice, termination, and other administrative terms
10. FINANCIAL EXPOSURE: Keep estimates directional, not fake precision. Express exposure as ranges or percentages of spend, not invented exact dollars unless the contract itself supports it.
11. AUDIT IMPLICATIONS: Move beyond missing-provision lists. State plainly when the current audit language means the plan sponsor cannot verify pricing, rebate flows, manufacturer compensation, or specialty economics.
12. NO BOILERPLATE IMPLICATIONS: The `implication` and `assessment` fields on control_map entries, top_risks, observations, and benchmark cards must be SPECIFIC to the contract being analyzed. Reference exact section numbers, exact dollar amounts, exact percentages, or exact dispensing-fee/admin-fee figures from the contract whenever the contract supplies them. NEVER write generic phrases like "Plan cannot verify net claim economics" or "Plan loses negotiating leverage" — these are true of every PBM contract and provide zero analytical value. Bad: "Plan cannot verify pharmacy reimbursement." Good: "Section 3.4 prohibits the plan sponsor from auditing the difference between the AWP-15% billed amount and actual pharmacy reimbursement, so the $1.50/claim dispensing fee cannot be reconciled against pharmacy cost." If a generic phrase is the best you can do, the field should be omitted entirely rather than filled with filler.
13. CONTRACT-GROUNDED LANGUAGE: Every analytical claim must be defensible by pointing at a specific clause. If you write "the rebate definition is narrow" you must be able to quote the language in the same sentence ("Section 4.4 defines rebates as 'only those payments specifically designated as rebates by manufacturers,' excluding admin fees and price protection"). Treat anything you can't ground in the contract text as an inference and either drop it or label it explicitly.
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


def _attach_critical_dates(analysis: dict) -> None:
    """
    Compute notice deadline + days-until counters from the AI-extracted
    contract_identification block.

    The AI extracts the raw fields (effective_date, initial_term_months,
    current_term_end_date, termination_notice_days). This helper turns
    them into the dates a benefits manager actually needs:

      - notice_deadline_date: latest date you can give written notice
        without paying the early-termination fee
        (= current_term_end_date - termination_notice_days)

      - days_until_term_end: how many days until the current term
        expires

      - days_until_notice_deadline: how many days until the notice
        deadline (negative = the deadline has passed)

      - rfp_start_recommended_date: 60 days before notice deadline,
        which is roughly the time a sponsor needs to RFP alternatives
        and have credible negotiating leverage at the table

    The fields are merged back into analysis["contract_identification"]
    so the frontend can render them without doing any date math.

    Best-effort: if any field is missing or unparseable the function
    leaves the existing fields untouched. Failures never raise.
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
            # Accept ISO YYYY-MM-DD; tolerant of "YYYY-MM-DDTHH:MM:SS" too
            return _dt.fromisoformat(str(value).split("T")[0]).date()
        except (ValueError, TypeError):
            return None

    effective = _parse_date(cid.get("effective_date"))
    term_end = _parse_date(cid.get("current_term_end_date"))

    # Derive current_term_end if the AI didn't supply it but we have
    # effective_date + initial_term_months.
    if term_end is None and effective is not None:
        try:
            months = int(cid.get("initial_term_months") or 0)
            if months > 0:
                # Naive month math: add months × 30.4375 days. Good enough
                # for "deadline is roughly Y months from now" — we're not
                # computing leap years here.
                term_end = effective + _td(days=int(round(months * 30.4375)))
                cid["current_term_end_date"] = term_end.isoformat()
        except (ValueError, TypeError):
            pass

    if term_end is None:
        return

    # Notice deadline = term end - termination notice days
    try:
        notice_days = int(cid.get("termination_notice_days") or 0)
    except (ValueError, TypeError):
        notice_days = 0

    if notice_days > 0:
        notice_deadline = term_end - _td(days=notice_days)
        cid["notice_deadline_date"] = notice_deadline.isoformat()
        cid["days_until_notice_deadline"] = (notice_deadline - today).days
        # Recommend starting an RFP 60 days before the notice deadline
        # so the sponsor has alternatives lined up before they have to
        # commit to giving notice.
        rfp_start = notice_deadline - _td(days=60)
        cid["rfp_start_recommended_date"] = rfp_start.isoformat()
        cid["days_until_rfp_start"] = (rfp_start - today).days

    cid["days_until_term_end"] = (term_end - today).days


def _attach_dollar_exposure(analysis: dict) -> None:
    """
    Mutate `analysis["financial_exposure"]` to include dollar-denominated
    estimates derived from real or synthetic claims totals.

    Each leakage entry (rebate_leakage, spread_exposure, specialty_control)
    has an `estimate` string like "3-6% of brand spend" that we parse for
    a percentage range and a denominator keyword. We multiply both ends of
    the range by the matching subtotal from `get_claims_totals()` to
    produce a `dollar_estimate_low` / `dollar_estimate_high` pair.

    The function is best-effort: if parsing fails for any entry the
    string estimate is left untouched. Failures never raise.
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

    # Annotate exposure with claims context the frontend can render
    # ("Based on 1,247 uploaded claims" vs "Illustrative — based on
    # synthetic sample data").
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
        # default: total claims spend
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

    The leakage model in `_attach_dollar_exposure` already produces three
    dollar-denominated buckets (rebate_leakage, spread_exposure,
    specialty_control). Each redline addresses one of those buckets, so
    we can take the relevant `dollar_estimate_low` / `dollar_estimate_high`
    pair and copy it onto the redline. That turns each editorial change
    into a real economic ask: "Tighten this clause → recover $340k–$680k."

    Audit rights redlines get a fractional credit because audit rights
    don't appear as a standalone exposure bucket — instead they unlock
    visibility into the other three. We attribute 15% of total leakage to
    each audit redline (capped at 5 redlines), reflecting that without
    audit rights the leakage is uncollectable, but no single audit clause
    is the sole driver.

    Best-effort. Failures never raise — a missing savings field just
    means the frontend doesn't render the chip.
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
    audit_share = 0.15  # each audit redline unlocks ~15% of total leakage visibility

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
            # Formulary and MAC moves typically yield 1-3% of total spend.
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
# Each entry pulls from the gold-standard NASHP/NASTAD model contract language
# already cited in the system prompt, but split by topic so the plan sponsor
# can take them to PBM negotiation one at a time.
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
    5-card pack when audit rights are deficient.

    The previous behavior — letting the AI emit one giant audit-rights
    redline covering scope, frequency, costs, and remediation in a single
    mega-block — meant the user had to mentally parse what was actually
    being asked for. Splitting it into 5 discrete redlines makes each ask
    individually copyable into a renegotiation document.

    We only replace if audit_rights are flagged as PBM-favorable (penalty
    >= 0.45). If the contract already has strong audit rights, we leave
    whatever the AI generated alone.
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

    # Drop any existing redline whose section name contains "audit",
    # then append the canonical 5. We deep-copy so downstream mutations
    # (e.g. _attach_redline_savings) don't bleed back into the constant.
    non_audit = [
        r for r in redlines
        if not (isinstance(r, dict) and "audit" in str(r.get("section", "")).lower())
    ]
    canonical = copy.deepcopy(_AUDIT_RIGHTS_CANONICAL_REDLINES)
    analysis["redline_suggestions"] = non_audit + canonical


def _control_posture_for(analysis: dict) -> dict:
    # Always start from the deterministic 5-lever baseline. This guarantees
    # the Control Map has rows for Rebates, Pricing, Specialty, Formulary,
    # and Audit / Data even when the AI returns a partial control_map of
    # only 2-3 entries (which it has been doing intermittently). The
    # previous version skipped the deterministic map whenever the AI's
    # version was non-empty, producing a 2-lever map that was both
    # incomplete and contradicted the rest of the analysis.
    control_map = analysis.get("control_map")
    if not isinstance(control_map, list) or not control_map:
        control_map = _control_map_for(analysis)
        analysis["control_map"] = control_map

    pbm_controlled = [item for item in control_map if str(item.get("controller", "")).lower() == "pbm"]
    shared = [item for item in control_map if str(item.get("controller", "")).lower() == "shared"]
    total = len(control_map) or 1

    # Use the RATIO of PBM-controlled levers, not the absolute count.
    # The previous bucketing (`>= 4` PBM → controlled, `>= 2` → mixed)
    # produced the bug where a 2-of-2 control map (100% PBM) was
    # labeled "Mixed control" because 2 < 4. A 100% PBM-controlled
    # map should always say "PBM-controlled" no matter how many
    # levers are in it.
    pbm_ratio = len(pbm_controlled) / total

    if pbm_ratio >= 0.8:
        label = "PBM-controlled"
        level = "high"
        summary = "PBM controls most of the economic and governance levers, so leakage estimates should be read as consequences of structural control rather than isolated clause defects."
    elif pbm_ratio >= 0.4:
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
    # Dedup by (category, tier). Two contract terms with the same category
    # and tier (e.g. rebate_passthrough + eligible_rebate_definition both
    # being "Rebates / Tier 1") used to produce two separate observation
    # cards saying basically the same thing, with the same supporting
    # leakage estimate, the same implication, and nearly identical
    # recommendations. That looked like AI slop. We now keep only the
    # highest-penalty term per (category, tier) slot — _ordered_term_scores
    # returns terms in descending penalty order, so first-seen wins.
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
        # Cap at 6 considerations so the page stays readable. Each
        # (category, tier) slot can contribute at most one observation.
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

    if not analysis.get("financial_exposure"):
        analysis["financial_exposure"] = _financial_exposure_for(analysis)
    claims_backed_exposure = _claims_backed_exposure_for(analysis)
    if claims_backed_exposure:
        analysis["financial_exposure"] = claims_backed_exposure
    # Convert percentage-range estimates ("3-6% of brand spend") into
    # real dollar figures using the user's actual claims if uploaded,
    # falling back to the synthetic dataset otherwise. This is the only
    # number a benefits manager actually cares about — the percentage
    # is meaningless without a denominator.
    _attach_dollar_exposure(analysis)

    # Split any audit-rights mega-redline into 5 discrete, copyable redlines
    # using the canonical NASHP/NASTAD-sourced pack. Must run BEFORE
    # _attach_redline_savings so the savings model sees the post-split list.
    _ensure_audit_rights_redlines(analysis)

    # Attach per-redline dollar savings by mapping each redline's section
    # text to the matching financial_exposure category. Turns each redline
    # into a real economic ask instead of an editorial suggestion.
    _attach_redline_savings(analysis)

    # Compute the notice deadline + days-until counters from the AI's
    # contract_identification block. After this runs, the frontend has
    # everything it needs to render the Contract Identification card and
    # the Critical Dates card without doing any date math itself.
    _attach_critical_dates(analysis)

    # Always merge the AI's control_map with the deterministic 5-lever
    # baseline. The AI sometimes returns only 2-3 levers; the merged
    # version is guaranteed to have entries for Rebates, Pricing,
    # Specialty, Formulary, and Audit / Data. AI-provided assessment
    # text wins where present (it's grounded in the actual contract).
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
    result = await _generate(CONTRACT_SYSTEM_PROMPT, f"Analyze this PBM contract:\n\n{text[:12000]}", 16000)
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
    result = await _generate(DISCLOSURE_SYSTEM_PROMPT, f"Analyze this PBM disclosure document for DOL compliance:\n\n{text[:12000]}", 16000)
    parsed = json.loads(result)
    parsed["_generated_by"] = "ai"
    return parsed


# ─── Audit Letter Generation ────────────────────────────────────────────────────

AUDIT_LETTER_SYSTEM_PROMPT = """You are a benefits attorney drafting a formal audit request letter from an employer plan sponsor to their PBM.

Generate a professional audit request letter that:
1. Cites specific DOL rule provisions and ERISA fiduciary obligations
2. References findings from the contract analysis ONLY when they are present in the input — never invent or fabricate findings
3. Specifies exact data the employer is legally entitled to receive
4. Includes a 10-business-day response deadline
5. Notes that failure to comply may constitute a fiduciary breach

ABSOLUTE RULES — DO NOT VIOLATE THESE:

- DO NOT invent or fabricate any specific dollar amounts, percentages, spread figures, rebate amounts, reconciliation totals, claim counts, drug names, NDC codes, pharmacy NPIs, or any numeric figure that is not literally present in the inputs.
- DO NOT pretend to have findings the inputs do not contain. If the input has no analyzed_contract, do NOT claim "your contract specifies X percent rebate passthrough" or similar — instead REQUEST that information.
- DO NOT claim a reconciliation has been performed if no claims data is present in the inputs. If `_data_provenance.has_real_claims_data` is false, the letter must REQUEST claims data, not assert findings about it.
- DO NOT include placeholder numbers like "$X", "[amount]", or fabricated "industry averages" presented as the employer's actual figures.
- If the inputs say a category has no data, write that section as a forward-looking REQUEST ("we are requesting documentation of...") rather than as a backward-looking ASSERTION ("your records show...").
- The `_data_provenance` field in the input tells you what is grounded in real data. Honor it.

When in doubt, write the letter generically. A letter that requests data is professionally appropriate. A letter that fabricates findings is malpractice.

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
        16000,
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
        16000,
    )
    return json.loads(result)
