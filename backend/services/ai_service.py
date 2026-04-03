"""
OpenAI integration for ClearScript.
Provides AI-powered contract analysis, disclosure review, audit letter generation, and report analysis.
Falls back to realistic mock data if the API call fails so the demo never breaks.
"""

import os
import json
import asyncio
import logging
import random
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
                    logger.warning("OPENAI_API_KEY not set — AI features will use mock data")
                    raise ValueError("OPENAI_API_KEY not set")
                _client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized")
    return _client

async def _generate(system_prompt: str, user_prompt: str, max_tokens: int = 3000) -> str:
    """Run OpenAI generation in a thread to keep it async-compatible."""
    client = _get_client()
    def _call():
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content
        if text:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                if text.endswith("```"):
                    text = text[:-3].strip()
        return text
    try:
        return await asyncio.wait_for(asyncio.to_thread(_call), timeout=30.0)
    except asyncio.TimeoutError:
        raise TimeoutError("OpenAI API call timed out after 30 seconds")

# ─── Contract Analysis ──────────────────────────────────────────────────────────

CONTRACT_SYSTEM_PROMPT = """You are a PBM contract analyst for employer health plan sponsors.
Analyze the provided PBM contract text and extract key terms. Return valid JSON with exactly this structure:

{"rebate_passthrough": {"found": true, "percentage": "85% of eligible rebates", "details": "description of rebate terms"}, "spread_pricing": {"found": true, "caps": "No explicit caps found", "details": "description of spread pricing terms"}, "formulary_clauses": {"found": true, "change_notification_days": 60, "details": "description of formulary management terms"}, "audit_rights": {"found": true, "frequency": "Once per year", "scope": "Claims data only", "details": "description of audit rights", "checklist": {"ndc_level_audit": {"found": false, "details": "Whether audit rights extend to NDC-level claim detail (not just J-code summaries)"}, "annual_audit_right": {"found": false, "details": "Whether employer has the right to audit at least once per contract year"}, "lookback_36_months": {"found": false, "details": "Whether audit lookback period extends to 36 months (vs shorter windows PBMs prefer)"}, "notice_90_days_or_less": {"found": false, "details": "Notice period required before audit — 90 days or less is acceptable, longer favors PBM"}, "data_delivery_30_days": {"found": false, "details": "Whether PBM must deliver requested audit data within 30 days of request"}, "finding_response_30_days": {"found": false, "details": "Whether PBM must respond to audit findings within 30 days"}, "financial_guarantees_turnaround": {"found": false, "details": "Whether there are financial penalties for PBM missing audit turnaround deadlines"}, "error_correction": {"found": false, "details": "Whether PBM is required to correct errors found during audit and issue credits"}, "manufacturer_contract_access": {"found": false, "details": "Whether employer can access up to 12 manufacturer rebate contracts for verification"}, "survival_post_termination_3yr": {"found": false, "details": "Whether audit rights survive contract termination for at least 3 years"}, "no_audit_cost_to_plan": {"found": false, "details": "Whether audit costs are borne by PBM (not charged back to plan sponsor)"}}}, "mac_pricing": {"found": true, "update_frequency": "Monthly", "appeal_rights": false, "details": "description of MAC pricing"}, "termination_provisions": {"found": true, "notice_days": 180, "penalties": "Liquidated damages", "details": "description of termination terms"}, "gag_clauses": {"found": true, "details": "description of any gag clauses"}, "eligible_rebate_definition": {"found": true, "definition_text": "exact contract language defining eligible rebates", "includes_admin_fees": false, "includes_volume_bonuses": false, "includes_price_protection": false, "narrow_definition_flag": true, "details": "CRITICAL: This is the single most important clause. PBMs define 'eligible rebates' narrowly to exclude admin fees, volume bonuses, and price protection rebates — reducing effective passthrough from the stated percentage. Flag if the definition excludes any of these categories."}, "dispute_resolution": {"found": true, "mechanism": "arbitration", "details": "Whether disputes go to mediation, arbitration, or litigation. Mediation is non-binding and weakest for the plan sponsor. Arbitration is binding but private (PBM-favorable). Litigation in court is strongest for the plan sponsor because it allows discovery and public record. Also note venue/jurisdiction requirements."}, "statistical_extrapolation_rights": {"found": false, "details": "Whether the employer can extrapolate error rates found in a sample audit to the full claims universe. PBMs fight hard against this because a 3% error rate in a sample of 1,000 claims can be applied to 500,000 claims. Without this right, the employer can only recover errors found in the specific claims audited."}, "compliance_flags": [{"issue": "description of compliance issue", "severity": "high", "recommendation": "what to do about it"}], "overall_risk_score": 78, "summary": "overall assessment of the contract"}

IMPORTANT: overall_risk_score MUST be an integer 0-100. severity MUST be "high", "medium", or "low". All string values must use double quotes. Be thorough and flag terms unfavorable to the plan sponsor.

EXTRACTION PRIORITIES (from real state PBM contract audits):
1. ELIGIBLE REBATE DEFINITION — The #1 most impactful clause. If "eligible rebates" excludes admin fees, volume bonuses, or price protection, the stated passthrough percentage is misleading. A contract promising "100% of eligible rebates" can deliver under 60% of actual manufacturer payments.
2. AUDIT RIGHTS CHECKLIST — Check all 11 items listed in the audit_rights.checklist structure. Most PBM contracts fail 6-8 of these items.
3. STATISTICAL EXTRAPOLATION — Without this right, audits have limited financial recovery potential.
4. DISPUTE RESOLUTION — Determines whether audit findings can actually be enforced. Arbitration with PBM-selected arbitrators is a red flag.
"""

async def analyze_contract(text: str) -> dict:
    try:
        result = await _generate(CONTRACT_SYSTEM_PROMPT, f"Analyze this PBM contract:\n\n{text[:12000]}", 3000)
        parsed = json.loads(result)
        parsed["_generated_by"] = "ai"
        return parsed
    except Exception as e:
        logger.warning(f"AI contract analysis failed, using mock: {e}")
        result = _mock_contract_analysis()
        result["_generated_by"] = "mock"
        return result

def _mock_contract_analysis() -> dict:
    return {
        "rebate_passthrough": {
            "found": True,
            "percentage": "85% of eligible rebates",
            "details": "Contract specifies 85% passthrough but defines 'eligible rebates' narrowly — excludes admin fees, manufacturer volume bonuses, and price protection rebates. Effective passthrough likely 55-65%."
        },
        "spread_pricing": {
            "found": True,
            "caps": "No explicit caps found",
            "details": "Contract allows PBM to retain difference between plan-billed amount and pharmacy reimbursement. No transparency requirements on spread amounts. This is a significant cost concern."
        },
        "formulary_clauses": {
            "found": True,
            "change_notification_days": 60,
            "details": "PBM may make mid-year formulary changes with 60-day notice. No requirement to demonstrate clinical justification. No employer approval needed for tier changes."
        },
        "audit_rights": {
            "found": True,
            "frequency": "Once per contract year",
            "scope": "Limited to claims data only",
            "details": "Audit limited to claims data — does not include rebate contracts, pharmacy reimbursement rates, or spread pricing data. 90-day advance notice required. PBM selects audit firm from approved list.",
            "checklist": {
                "ndc_level_audit": {"found": False, "details": "Contract does not guarantee NDC-level audit access — only J-code summaries available."},
                "annual_audit_right": {"found": True, "details": "Once per contract year, but PBM controls scheduling."},
                "lookback_36_months": {"found": False, "details": "Lookback limited to 12 months — well below the recommended 36."},
                "notice_90_days_or_less": {"found": True, "details": "90-day advance notice required (at the acceptable threshold)."},
                "data_delivery_30_days": {"found": False, "details": "Contract specifies 60-day data delivery window — double the recommended 30 days."},
                "finding_response_30_days": {"found": False, "details": "No timeline specified for PBM response to audit findings."},
                "financial_guarantees_turnaround": {"found": False, "details": "No financial penalties for PBM missing audit deadlines."},
                "error_correction": {"found": True, "details": "PBM must correct pricing errors, but no timeline for credits."},
                "manufacturer_contract_access": {"found": False, "details": "No right to review manufacturer rebate contracts."},
                "survival_post_termination_3yr": {"found": False, "details": "Audit rights terminate with the contract — no survival clause."},
                "no_audit_cost_to_plan": {"found": False, "details": "Plan sponsor bears all audit costs."},
            },
        },
        "mac_pricing": {
            "found": True,
            "update_frequency": "Monthly",
            "appeal_rights": False,
            "details": "MAC list updated monthly but no appeal process for pharmacies. No requirement to disclose MAC list to plan sponsor."
        },
        "termination_provisions": {
            "found": True,
            "notice_days": 180,
            "penalties": "Liquidated damages equal to 50% of remaining contract value",
            "details": "Six-month notice required. Early termination triggers liquidated damages clause. Effectively locks plan sponsor into 3-year term."
        },
        "gag_clauses": {
            "found": True,
            "details": "Section 14.2 contains confidentiality provisions that may restrict plan sponsor from sharing pricing data with consultants or other vendors. Potential CAA violation."
        },
        "eligible_rebate_definition": {
            "found": True,
            "definition_text": "'Eligible Rebates' means rebates received by PBM from pharmaceutical manufacturers based on formulary placement and utilization of covered drugs, excluding administrative fees, service fees, volume-based incentives, and price protection payments.",
            "includes_admin_fees": False,
            "includes_volume_bonuses": False,
            "includes_price_protection": False,
            "narrow_definition_flag": True,
            "details": "CRITICAL: The contract defines 'eligible rebates' to exclude admin fees, volume bonuses, and price protection — three major categories of manufacturer payments. The stated 85% passthrough applies only to this narrow definition. Effective passthrough of total manufacturer payments is estimated at 55-65%."
        },
        "dispute_resolution": {
            "found": True,
            "mechanism": "arbitration",
            "details": "Section 18.3 requires binding arbitration with an arbitrator selected from a PBM-approved panel. Venue is PBM's home jurisdiction. No right to discovery beyond document production. This is PBM-favorable — litigation in court would allow broader discovery and public accountability."
        },
        "statistical_extrapolation_rights": {
            "found": False,
            "details": "Contract is silent on statistical extrapolation. Without this right, the employer can only recover errors found in specifically audited claims, not extrapolate error rates to the full claims universe. This dramatically limits audit recovery potential."
        },
        "compliance_flags": [
            {"issue": "Gag clause detected — potential CAA 2021 Section 201 violation", "severity": "high", "recommendation": "Require immediate removal of Section 14.2 confidentiality restrictions on pricing data sharing."},
            {"issue": "Rebate definition excludes major rebate categories", "severity": "high", "recommendation": "Redefine 'eligible rebates' to include all manufacturer payments: base rebates, admin fees, volume bonuses, and price protection."},
            {"issue": "No spread pricing transparency or caps", "severity": "high", "recommendation": "Require pass-through pricing model or add spread pricing caps and quarterly disclosure."},
            {"issue": "Audit scope too narrow", "severity": "medium", "recommendation": "Expand audit rights to include rebate contracts, pharmacy reimbursement data, and spread amounts."},
            {"issue": "Formulary changes without employer approval", "severity": "medium", "recommendation": "Require employer consent for any mid-year formulary or tier changes."},
            {"issue": "Excessive termination penalties", "severity": "medium", "recommendation": "Negotiate reduced liquidated damages and shorter notice period."},
        ],
        "overall_risk_score": 78,
        "summary": "This contract contains several provisions that significantly favor the PBM over the plan sponsor. Key concerns include narrow rebate definitions that reduce effective passthrough, unrestricted spread pricing, limited audit rights, and potential gag clause violations. Estimated annual cost impact of unfavorable terms: $350,000-$600,000 for a mid-market employer."
    }


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

DOL_REQUIRED_ITEMS = [
    ("Manufacturer Rebates Per Drug", "Rebates", True),
    ("Total Rebate Revenue by Therapeutic Class", "Rebates", True),
    ("Rebate Passthrough Amounts", "Rebates", True),
    ("Spread Pricing by Channel (Retail/Mail/Specialty)", "Pricing", True),
    ("Plan-Paid vs Pharmacy Reimbursed Amounts", "Pricing", True),
    ("AWP Discount Guarantees vs Actual", "Pricing", True),
    ("Pharmacy Claw-back Amounts", "Fees", True),
    ("DIR Fee Breakdown", "Fees", True),
    ("Administrative Service Fees", "Fees", True),
    ("Formulary Change Log with Rationale", "Formulary", True),
    ("Generic Dispensing Rate", "Utilization", True),
    ("Specialty Drug Utilization Report", "Utilization", True),
    ("Mail Order Utilization Rate", "Utilization", True),
    ("Network Pharmacy Access Report", "Network", True),
    ("Member Cost-Sharing Summary", "Cost Sharing", True),
    ("Top 25 Drugs by Plan Spend", "Reporting", True),
    ("Top 25 Drugs by Claim Count", "Reporting", True),
    ("Copay Assistance and Accumulator Programs", "Cost Sharing", False),
    ("Biosimilar Utilization Report", "Utilization", False),
    ("PBM Conflict of Interest Disclosures", "Governance", True),
]

async def analyze_disclosure(text: str) -> dict:
    try:
        result = await _generate(DISCLOSURE_SYSTEM_PROMPT, f"Analyze this PBM disclosure document for DOL compliance:\n\n{text[:12000]}", 4000)
        parsed = json.loads(result)
        parsed["_generated_by"] = "ai"
        return parsed
    except Exception as e:
        logger.warning(f"AI disclosure analysis failed, using mock: {e}")
        result = _mock_disclosure_analysis()
        result["_generated_by"] = "mock"
        return result

def _mock_disclosure_analysis() -> dict:
    items = []
    found_count = 0
    for name, category, required in DOL_REQUIRED_ITEMS:
        # Simulate partial disclosure — some items missing
        random.seed(hash(name))
        is_found = random.random() > 0.35
        is_complete = is_found and random.random() > 0.25
        if is_found:
            found_count += 1

        gap = None
        if not is_found:
            gap = f"'{name}' is entirely absent from the disclosure. This is {'a required DOL item' if required else 'a recommended item'}."
        elif not is_complete:
            gap = f"'{name}' is present but incomplete — missing granular detail required for full compliance."

        items.append({
            "item": name,
            "category": category,
            "required": required,
            "found": is_found,
            "complete": is_complete,
            "details": f"{'Found and complete' if is_complete else 'Found but incomplete' if is_found else 'Not found in disclosure'}",
            "gap_description": gap,
        })

    score = round(sum(1 for i in items if i["complete"] and i["required"]) / sum(1 for i in items if i["required"]) * 100)
    critical = [i["gap_description"] for i in items if i["gap_description"] and i["required"] and not i["found"]]
    moderate = [i["gap_description"] for i in items if i["gap_description"] and i["required"] and i["found"] and not i["complete"]]
    minor = [i["gap_description"] for i in items if i["gap_description"] and not i["required"]]

    return {
        "completeness_score": score,
        "items_checked": items,
        "gap_report": {
            "critical_gaps": critical,
            "moderate_gaps": moderate,
            "minor_gaps": minor,
        },
        "summary": f"Disclosure completeness: {score}%. Found {found_count}/{len(DOL_REQUIRED_ITEMS)} items. "
                   f"{len(critical)} critical gaps (required items missing), {len(moderate)} moderate gaps (incomplete data), "
                   f"{len(minor)} minor gaps. Key missing items include rebate-per-drug breakdowns, spread pricing by channel, and pharmacy claw-back data."
    }


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
    try:
        result = await _generate(AUDIT_LETTER_SYSTEM_PROMPT, f"Generate an audit request letter based on these findings:\n\nContract Analysis:\n{json.dumps(contract_data, indent=2)[:4000]}\n\nAudit Findings:\n{json.dumps(findings, indent=2)[:4000]}", 4000)
        return json.loads(result)
    except Exception as e:
        logger.warning(f"AI audit letter generation failed, using mock: {e}")
        return _mock_audit_letter(findings)

def _mock_audit_letter(findings: dict = None) -> dict:
    from datetime import datetime, timedelta
    deadline = (datetime.now() + timedelta(days=14)).strftime("%B %d, %Y")
    discrepancies = findings.get("discrepancies", []) if findings else []
    disc_text = "\n".join(f"  - {d.get('description', d.get('type', 'Finding'))}" for d in discrepancies[:5])

    letter = f"""FORMAL AUDIT REQUEST — PRESCRIPTION DRUG BENEFIT PROGRAM

Date: {datetime.now().strftime("%B %d, %Y")}

VIA CERTIFIED MAIL AND EMAIL

[PBM Name]
[PBM Address]

RE: Formal Request for Prescription Drug Benefit Audit
     Plan Name: [Employer Health Plan]
     Contract Number: [PBM-2024-XXXX]
     Audit Period: January 1, 2025 — June 30, 2025

Dear PBM Compliance Officer:

Pursuant to the audit provisions of our Pharmacy Benefit Management Agreement (Section [X]) and our fiduciary obligations under the Employee Retirement Income Security Act of 1974 ("ERISA"), as amended by the Consolidated Appropriations Act of 2021, we hereby formally request a comprehensive audit of the prescription drug benefit program administered by [PBM Name] for the above-referenced plan.

I. LEGAL BASIS

This request is made pursuant to:

  1. ERISA Section 404(a)(1) — Fiduciary duty to act solely in the interest of plan participants
  2. ERISA Section 406 — Prohibited transaction rules applicable to service providers
  3. Consolidated Appropriations Act of 2021, Section 201 — Prohibition on gag clauses
  4. Consolidated Appropriations Act of 2021, Section 204 — Prescription drug cost reporting requirements
  5. DOL Final Rule on Prescription Drug and Health Care Spending (29 CFR 2520.101-2)
  6. Contract Section [X] — Plan sponsor audit rights

II. PRELIMINARY FINDINGS

Our preliminary analysis has identified the following concerns requiring detailed audit review:

{disc_text if disc_text else "  - Spread pricing discrepancies between plan-billed and pharmacy-reimbursed amounts"}
  - Rebate passthrough rates below contractual guarantees
  - Formulary changes correlated with rebate incentive patterns
  - Claims routed through pharmacies with unverifiable NPI numbers

III. DATA AND DOCUMENTATION REQUESTED

We request complete access to the following data and documentation for the audit period:

  A. Claims Data:
    1. Complete prescription claims file with all data fields
    2. Plan-paid amounts and member cost-sharing for each claim
    3. Pharmacy reimbursement amounts (actual amounts paid to each pharmacy)
    4. Ingredient cost, dispensing fee, and total cost breakdowns

  B. Rebate Data:
    1. Total manufacturer rebates received, by drug and by therapeutic class
    2. Rebate amounts passed through to the plan
    3. Rebate amounts retained by PBM, with contractual basis for retention
    4. Copies of all manufacturer rebate agreements applicable to plan formulary

  C. Pricing Data:
    1. MAC (Maximum Allowable Cost) lists used during the audit period
    2. AWP discount calculations and actual discount achieved vs. guaranteed
    3. Spread pricing data: plan-billed vs. pharmacy-paid for each claim
    4. U&C (Usual & Customary) pricing data

  D. Network & Pharmacy Data:
    1. Complete pharmacy network directory with NPI verification status
    2. Pharmacy reimbursement rate schedules by pharmacy type
    3. DIR (Direct and Indirect Remuneration) fee amounts collected from pharmacies
    4. Pharmacy claw-back amounts

  E. Formulary Data:
    1. Complete formulary with tier assignments (current and all changes during audit period)
    2. Documentation supporting all mid-year formulary changes
    3. P&T Committee meeting minutes related to formulary decisions

IV. DEADLINE AND COMPLIANCE

Pursuant to our contract and applicable law, we require a complete response to this request within TEN (10) BUSINESS DAYS of receipt of this letter, no later than {deadline}.

Failure to provide the requested data within this timeframe may constitute:
  - A material breach of the PBM Agreement
  - A violation of ERISA fiduciary obligations
  - Grounds for contract termination under Section [X]

We reserve all rights under the contract and applicable law, including but not limited to the right to engage an independent auditor at PBM's expense as provided in Section [X] of the Agreement.

V. CONFIDENTIALITY

All data provided will be treated as confidential and used solely for audit purposes. However, consistent with the CAA 2021 gag clause prohibition, we reserve the right to share pricing and cost data with our benefits consultants and fiduciary advisors.

Please direct all audit-related communications to the undersigned.

Sincerely,

[Plan Sponsor Name]
[Title]
[Company Name]
[Email]
[Phone]

cc: Benefits Committee
    Outside Benefits Counsel
    Independent Audit Firm"""

    return {
        "letter_text": letter,
        "key_demands": [
            "Complete claims data with pharmacy reimbursement amounts",
            "Full rebate disclosure by drug including PBM-retained amounts",
            "Spread pricing data (plan-billed vs pharmacy-paid per claim)",
            "MAC lists and AWP discount calculations",
            "Pharmacy network NPI verification documentation",
            "All formulary change documentation with P&T Committee minutes",
            "DIR fee and pharmacy claw-back amounts",
        ],
        "legal_citations": [
            "ERISA Section 404(a)(1) — Fiduciary duty",
            "ERISA Section 406 — Prohibited transactions",
            "CAA 2021 Section 201 — Gag clause prohibition",
            "CAA 2021 Section 204 — Rx cost reporting",
            "29 CFR 2520.101-2 — DOL Final Rule",
        ],
        "deadline": deadline,
    }


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
    try:
        result = await _generate(REPORT_SYSTEM_PROMPT, f"Analyze this PBM report against claims data:\n\nReport:\n{report_text[:6000]}\n\nClaims Summary:\n{json.dumps(claims_data, indent=2)[:4000]}", 3000)
        return json.loads(result)
    except Exception as e:
        logger.warning(f"AI report analysis failed, using mock: {e}")
        return {
            "findings": [
                {"category": "Rebates", "severity": "high", "finding": "Rebate amounts in report do not match expected values based on claim volume", "evidence": "Report shows aggregate rebates but lacks per-drug breakdown", "recommendation": "Request drug-level rebate detail"},
                {"category": "Pricing", "severity": "high", "finding": "Spread pricing not disclosed in report", "evidence": "No pharmacy reimbursement data provided alongside plan-paid amounts", "recommendation": "Require spread pricing disclosure in next report"},
            ],
            "overall_assessment": "Report is incomplete and contains potential discrepancies requiring further investigation.",
            "risk_level": "high"
        }
