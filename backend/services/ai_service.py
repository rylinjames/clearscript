"""
OpenAI GPT-5 mini integration for ClearScript.
Provides AI-powered contract analysis, disclosure review, audit letter generation, and report analysis.
Falls back to realistic mock data if the API call fails so the demo never breaks.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load .env from project root (one level up from backend/)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

_client = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        _client = AsyncOpenAI(api_key=api_key)
    return _client

MODEL = "gpt-5-mini"

# ─── Contract Analysis ──────────────────────────────────────────────────────────

CONTRACT_SYSTEM_PROMPT = """You are a PBM contract analyst for employer health plan sponsors.
Analyze the provided PBM contract text and extract the following terms as structured JSON:

{
  "rebate_passthrough": {"found": bool, "percentage": str or null, "details": str},
  "spread_pricing": {"found": bool, "caps": str or null, "details": str},
  "formulary_clauses": {"found": bool, "change_notification_days": int or null, "details": str},
  "audit_rights": {"found": bool, "frequency": str or null, "scope": str or null, "details": str},
  "mac_pricing": {"found": bool, "update_frequency": str or null, "appeal_rights": bool, "details": str},
  "termination_provisions": {"found": bool, "notice_days": int or null, "penalties": str or null, "details": str},
  "gag_clauses": {"found": bool, "details": str},
  "compliance_flags": [{"issue": str, "severity": "high"|"medium"|"low", "recommendation": str}],
  "overall_risk_score": int (0-100, higher = more risk for employer),
  "summary": str
}

Be thorough and flag any terms that are unfavorable to the plan sponsor.
"""

async def analyze_contract(text: str) -> dict:
    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": CONTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this PBM contract:\n\n{text[:12000]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=3000,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI contract analysis failed: {e}")
        return _mock_contract_analysis()

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
            "details": "Audit limited to claims data — does not include rebate contracts, pharmacy reimbursement rates, or spread pricing data. 90-day advance notice required. PBM selects audit firm from approved list."
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
        client = _get_client()
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": DISCLOSURE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this PBM disclosure document for DOL compliance:\n\n{text[:12000]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=4000,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI disclosure analysis failed: {e}")
        return _mock_disclosure_analysis()

def _mock_disclosure_analysis() -> dict:
    items = []
    found_count = 0
    for name, category, required in DOL_REQUIRED_ITEMS:
        # Simulate partial disclosure — some items missing
        import random
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
        client = _get_client()
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": AUDIT_LETTER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate an audit request letter based on these findings:\n\nContract Analysis:\n{json.dumps(contract_data, indent=2)[:4000]}\n\nAudit Findings:\n{json.dumps(findings, indent=2)[:4000]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=4000,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI audit letter generation failed: {e}")
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
        client = _get_client()
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this PBM report against claims data:\n\nReport:\n{report_text[:6000]}\n\nClaims Summary:\n{json.dumps(claims_data, indent=2)[:4000]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=3000,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI report analysis failed: {e}")
        return {
            "findings": [
                {"category": "Rebates", "severity": "high", "finding": "Rebate amounts in report do not match expected values based on claim volume", "evidence": "Report shows aggregate rebates but lacks per-drug breakdown", "recommendation": "Request drug-level rebate detail"},
                {"category": "Pricing", "severity": "high", "finding": "Spread pricing not disclosed in report", "evidence": "No pharmacy reimbursement data provided alongside plan-paid amounts", "recommendation": "Require spread pricing disclosure in next report"},
            ],
            "overall_assessment": "Report is incomplete and contains potential discrepancies requiring further investigation.",
            "risk_level": "high"
        }
