"""
Public AI entry points for ClearScript.

This module holds the long-form system prompts (contract / disclosure /
cross-reference / audit letter / report) and the async entry points the
routers call. Low-level OpenAI plumbing lives in ai_service_core.py and
post-processing of AI contract output lives in contract_enrichment.py.

Symbols imported below are re-exported so existing callers and tests can
keep importing them from `services.ai_service` unchanged.
"""

import json

from services.ai_service_core import (
    _generate,
    _extract_first_json_object,
    MODEL,
)
from services.contract_enrichment import (
    enrich_contract_analysis,
    _attach_critical_dates,
    _attach_dollar_exposure,
    _attach_redline_savings,
    _ensure_audit_rights_redlines,
    _AUDIT_RIGHTS_CANONICAL_REDLINES,
)


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
  "deal_diagnosis": "one-line plain-English diagnosis leading with the dollar consequence (e.g. 'This contract leaks an estimated 3-8% of total Rx spend through narrow rebate definitions, retained spread, and exclusive specialty routing')",
  "financial_exposure": {
    "summary": "1-2 sentence summary grounded in the contract's actual pricing, rebate, and channel terms",
    "rebate_leakage": {"level": "high|moderate|low", "estimate": "percentage range of brand spend — derive from the rebate definition language and passthrough terms in THIS contract, not a default", "driver": "cite the specific contract section and clause language"},
    "spread_exposure": {"level": "high|moderate|low", "estimate": "percentage range of total claims spend — derive from the spread/pricing terms in THIS contract", "driver": "cite the specific contract section"},
    "specialty_control": {"level": "high|moderate|low", "estimate": "percentage of Rx spend subject to PBM channel control per THIS contract's specialty terms", "driver": "cite the specific contract section"}
  },
  "control_map": [
    {"lever": "Rebates", "controller": "PBM|Shared|Employer", "assessment": "contract-specific assessment citing section numbers and quoting clause language", "implication": "contract-specific consequence citing the dollar or percentage impact from THIS contract's terms"},
    {"lever": "Pricing", "controller": "PBM|Shared|Employer", "assessment": "...", "implication": "..."},
    {"lever": "Specialty", "controller": "PBM|Shared|Employer", "assessment": "...", "implication": "..."},
    {"lever": "Formulary", "controller": "PBM|Shared|Employer", "assessment": "...", "implication": "..."},
    {"lever": "Audit / Data", "controller": "PBM|Shared|Employer", "assessment": "...", "implication": "..."}
  ],
  "top_risks": [
    {"title": "contract-specific risk title", "tier": 1, "severity": "high|medium|low", "why_it_matters": "contract-specific explanation citing section numbers", "recommendation": "contract-specific action item tied to the specific clause language"}
  ],
  "benchmark_observations": [
    {
      "kind": "consideration",
      "title": "contract-specific observation title (e.g. 'Rebate passthrough falls short of benchmark')",
      "category": "Rebates|Pricing|Specialty|Audit|Formulary|Administrative|Governance",
      "tier": 1,
      "severity": "high|medium|low",
      "benchmark_label": "what the employer-favorable benchmark looks like (e.g. 'Full manufacturer compensation passthrough')",
      "benchmark": "description of the benchmark standard",
      "benchmark_source": "specific citation — NASHP Model PBM Contract §X.Y, NASTAD PBM Contract Language Bank, statute, or named industry standard. Only cite sources whose standards you can articulate specifically.",
      "observation": "what THIS contract actually says — cite section numbers and quote clause language",
      "implication": "contract-specific consequence — reference dollar amounts, percentages, or section numbers from THIS contract",
      "recommendation": "specific action tied to THIS contract's language",
      "supporting_detail": "leakage estimate or audit implication grounded in THIS contract's terms, or null if no quantifiable impact"
    }
  ],
  "immediate_actions": [
    "contract-specific action item 1 — cite the section and the specific change needed",
    "contract-specific action item 2",
    "contract-specific action item 3"
  ],
  "audit_implication": "state explicitly what the plan sponsor cannot verify under the current audit language — cite the specific audit section and list the categories of data that are excluded from audit scope",
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
14. NO DEFAULT VALUES: The example values in this JSON schema are structural guides, not defaults. Every estimate, recommendation, implication, and observation MUST be derived from the specific contract text being analyzed. If the contract does not contain enough information to produce a contract-specific value for a field, set that field to null rather than using a generic placeholder. The user will see these values and assume they were computed from their specific contract — do not betray that trust with template text.
15. BENCHMARK OBSERVATIONS: Generate 4-7 benchmark_observations. Each must have a real benchmark_source you can defend. For each observation, quote the specific contract section that falls short of the benchmark. For "consideration" entries, pair each with a quantified supporting_detail (e.g. "Supporting leakage estimate: the Section 4.4 rebate exclusions affect an estimated 3-6% of brand spend based on the contract's passthrough structure"). For "strength" entries (employer-favorable terms), keep supporting_detail null and recommendation as "Preserve this language while renegotiating higher-impact terms."
"""


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
    "critical_gaps": [
      {
        "missing_item": "what is missing from the disclosure",
        "why_required": "specific DOL rule, statute, or regulatory citation that requires this item (e.g. 'DOL Transparency Rule 29 CFR 2520.408b-2(c)(1)(iv)')",
        "recommendation": "specific action to take — what the PBM should disclose and in what format"
      }
    ],
    "moderate_gaps": [same structure],
    "minor_gaps": [same structure]
  },
  "summary": str
}

IMPORTANT: Each gap in critical_gaps, moderate_gaps, and minor_gaps MUST be a JSON object with three fields (missing_item, why_required, recommendation), NOT a plain string. The frontend renders these as separate columns.
"""


async def analyze_disclosure(text: str) -> dict:
    """Score a PBM disclosure against DOL-required items. Raises on failure."""
    result = await _generate(DISCLOSURE_SYSTEM_PROMPT, f"Analyze this PBM disclosure document for DOL compliance:\n\n{text[:12000]}", 8000)
    parsed = json.loads(result)
    parsed["_generated_by"] = "ai"
    return parsed


DISCLOSURE_CROSS_REF_PROMPT = """You are a PBM disclosure compliance analyst cross-referencing a PBM's disclosure report against the actual PBM contract terms.

You are given two inputs:
1. The PBM disclosure document text
2. Key terms extracted from the PBM contract analysis (rebate passthrough %, audit scope, spread pricing terms, formulary provisions, etc.)

Your job is to find DISCREPANCIES between what the contract promises and what the disclosure actually reports. For each discrepancy, cite the specific contract section and the specific disclosure section/number.

Return structured JSON:

{
  "discrepancies": [
    {
      "category": "Rebates|Pricing|Audit|Formulary|Specialty|Administrative",
      "severity": "high|medium|low",
      "contract_says": "what the contract promises, citing the section number",
      "disclosure_says": "what the disclosure reports or omits",
      "gap": "plain-English description of the discrepancy and its financial implication",
      "recommendation": "what the plan sponsor should demand"
    }
  ],
  "confirmations": [
    {
      "category": str,
      "contract_says": str,
      "disclosure_confirms": str
    }
  ],
  "overall_alignment_score": int (0-100, where 100 = disclosure fully matches contract terms),
  "summary": "1-2 sentence summary of the disclosure's alignment with contract terms"
}

RULES:
- Only flag discrepancies you can defend by pointing at specific language in both documents.
- If the disclosure omits something the contract requires to be disclosed, that IS a discrepancy.
- If the disclosure reports a number that differs from a contract guarantee, cite both numbers.
- Do NOT invent contract terms or disclosure data that are not in the inputs.
"""


async def analyze_disclosure_with_contract(disclosure_text: str, contract_analysis: dict) -> dict:
    """
    Cross-reference a PBM disclosure against a contract analysis.
    Returns discrepancies, confirmations, and an alignment score.
    """
    contract_summary = {
        "rebate_passthrough": contract_analysis.get("rebate_passthrough"),
        "eligible_rebate_definition": contract_analysis.get("eligible_rebate_definition"),
        "spread_pricing": contract_analysis.get("spread_pricing"),
        "audit_rights": contract_analysis.get("audit_rights"),
        "formulary_clauses": contract_analysis.get("formulary_clauses"),
        "specialty_channel": contract_analysis.get("specialty_channel"),
        "mac_pricing": contract_analysis.get("mac_pricing"),
        "termination_provisions": contract_analysis.get("termination_provisions"),
        "contract_identification": contract_analysis.get("contract_identification"),
        "financial_exposure": contract_analysis.get("financial_exposure"),
    }
    result = await _generate(
        DISCLOSURE_CROSS_REF_PROMPT,
        f"Cross-reference this PBM disclosure against the contract terms:\n\n"
        f"DISCLOSURE DOCUMENT:\n{disclosure_text[:8000]}\n\n"
        f"CONTRACT TERMS:\n{json.dumps(contract_summary, indent=2, default=str)[:6000]}",
        6000,
    )
    return json.loads(result)


# ─── Audit Letter Generation ────────────────────────────────────────────────────

AUDIT_LETTER_SYSTEM_PROMPT = """You are a benefits attorney drafting a formal audit request letter from an employer plan sponsor to their PBM.

The letter must be structured into discrete, defensible sections — NOT a freeform wall of text. The frontend will render each section as its own card so the plan sponsor can review, edit, and copy each section independently.

ABSOLUTE RULES — DO NOT VIOLATE THESE:

- DO NOT invent or fabricate any specific dollar amounts, percentages, spread figures, rebate amounts, reconciliation totals, claim counts, drug names, NDC codes, pharmacy NPIs, or any numeric figure that is not literally present in the inputs.
- DO NOT pretend to have findings the inputs do not contain. If the input has no analyzed_contract, do NOT claim "your contract specifies X percent rebate passthrough" — instead REQUEST that information.
- DO NOT claim a reconciliation has been performed if no claims data is present. If `_data_provenance.has_real_claims_data` is false, the letter must REQUEST claims data, not assert findings about it.
- DO NOT include placeholder numbers like "$X", "[amount]", or fabricated "industry averages" presented as the employer's actual figures.
- If the inputs say a category has no data, write the corresponding demand as a forward-looking REQUEST ("we are requesting documentation of...") rather than as a backward-looking ASSERTION ("your records show...").
- The `_data_provenance` field in the input tells you what is grounded in real data. Honor it.

WHEN IN DOUBT: write a letter that REQUESTS data. A letter that requests data is professionally appropriate. A letter that fabricates findings is malpractice.

ANCHORING TO THE CONTRACT: When the analyzed_contract input contains a `redline_suggestions`, `top_risks`, `audit_implication`, or `contract_identification` block, every demand you make should reference those findings explicitly. If a redline cites "Section 3.4 — Spread Pricing" the corresponding demand should say "regarding Section 3.4 of the Agreement..." This anchoring is the difference between a credible audit request and an AI-generated form letter.

Return JSON with EXACTLY this shape:

{
  "subject_line": "Formal Audit Request — [PBM Name] PBM Services Agreement",
  "recipient_block": "Recipient name and title\\nPBM legal department\\nAddress",
  "opening_paragraph": "1-2 sentence professional opening identifying the parties and the contract under review",
  "background_paragraph": "1 paragraph (3-5 sentences) summarizing the basis for the audit request, citing specific contract sections where possible",
  "specific_demands": [
    {
      "demand": "1-2 sentence specific data or document the plan sponsor is requesting",
      "contract_section": "Section number from the analyzed contract this demand relates to, or null if generic",
      "data_requested": "Plain-English description of the data category (e.g. 'Claim-level pharmacy reimbursement records')"
    }
  ],
  "legal_authority": [
    {
      "citation": "Specific statute, regulation, or model contract section (e.g. 'ERISA §404(a)(1)', 'CAA 2021 §201', 'DOL Transparency Rule 29 CFR 2520.408b-2(c)(1)(iv)')",
      "explanation": "1 sentence explaining how this authority applies to the specific demands above"
    }
  ],
  "response_deadline_paragraph": "1-2 sentence deadline statement specifying business days and the consequences of non-response",
  "closing_paragraph": "1 sentence professional closing",
  "signature_block": "Signature line(s) — leave name placeholder as 'Plan Sponsor Authorized Representative'",
  "deadline_iso": "YYYY-MM-DD calculated as 10 business days from today",
  "letter_text": "The full assembled letter as a single string with all sections concatenated in order, ready to copy/paste into Word. Include section spacing but NO markdown."
}

Generate between 4 and 8 specific_demands and between 2 and 5 legal_authority entries. Generate fewer if the input data does not support more.
"""


async def generate_audit_letter(contract_data: dict, findings: dict) -> dict:
    """Draft a formal audit request letter. Raises on failure."""
    result = await _generate(
        AUDIT_LETTER_SYSTEM_PROMPT,
        f"Generate an audit request letter based on these inputs:\n\n"
        f"Contract Analysis:\n{json.dumps(contract_data, indent=2)[:6000]}\n\n"
        f"Audit Findings:\n{json.dumps(findings, indent=2)[:3000]}",
        6000,
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
    """Analyze a semiannual PBM report against claims data. Raises on failure."""
    result = await _generate(
        REPORT_SYSTEM_PROMPT,
        f"Analyze this PBM report against claims data:\n\n"
        f"Report:\n{report_text[:6000]}\n\n"
        f"Claims Summary:\n{json.dumps(claims_data, indent=2)[:4000]}",
        16000,
    )
    return json.loads(result)
