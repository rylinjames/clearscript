"""
SPC (Summary of Plan Coverage) Parser Service.
Extracts structured benefit data from SPC text using Gemini AI.

From meeting notes: parsing SPC PDFs into structured data is a high-value feature
that people have spent "tens of thousands to hundreds of thousands" building.
LLMs make it newly feasible.
"""

import json
import logging

from services.ai_service import _generate

logger = logging.getLogger(__name__)

# ─── AI Prompts ────────────────────────────────────────────────────────────────

SPC_PARSE_SYSTEM_PROMPT = """You are a health insurance benefits analyst. Extract structured benefit data from the provided Summary of Plan Coverage (SPC) or Summary of Benefits and Coverage (SBC) document text.

Return valid JSON with exactly this structure:

{
  "plan_info": {
    "plan_name": "string or null",
    "carrier": "string or null",
    "effective_date": "string or null",
    "plan_type": "string or null (e.g. PPO, HMO, HDHP, POS)",
    "coverage_period": "string or null"
  },
  "deductible": {
    "individual_in_network": "string or null (e.g. '$1,500')",
    "individual_out_of_network": "string or null",
    "family_in_network": "string or null",
    "family_out_of_network": "string or null",
    "notes": "string or null (e.g. 'Deductible does not apply to preventive care')"
  },
  "out_of_pocket_maximum": {
    "individual_in_network": "string or null",
    "individual_out_of_network": "string or null",
    "family_in_network": "string or null",
    "family_out_of_network": "string or null",
    "notes": "string or null"
  },
  "copays": {
    "pcp_visit": "string or null (e.g. '$25 copay')",
    "specialist_visit": "string or null",
    "urgent_care": "string or null",
    "emergency_room": "string or null",
    "telehealth": "string or null",
    "mental_health_outpatient": "string or null",
    "notes": "string or null"
  },
  "coinsurance": {
    "in_network": "string or null (e.g. '80/20 after deductible')",
    "out_of_network": "string or null",
    "notes": "string or null"
  },
  "prescription_drugs": {
    "tier_1_generic": {"copay": "string or null", "mail_order": "string or null"},
    "tier_2_preferred_brand": {"copay": "string or null", "mail_order": "string or null"},
    "tier_3_non_preferred": {"copay": "string or null", "mail_order": "string or null"},
    "tier_4_specialty": {"copay": "string or null", "mail_order": "string or null"},
    "deductible_applies": "string or null (which tiers require deductible first)",
    "pbm_name": "string or null",
    "formulary_name": "string or null",
    "notes": "string or null"
  },
  "hospital_services": {
    "inpatient": "string or null",
    "outpatient_surgery": "string or null",
    "notes": "string or null"
  },
  "exclusions_and_limits": [
    "string — notable exclusion or limitation"
  ],
  "other_benefits": {
    "preventive_care": "string or null",
    "lab_work": "string or null",
    "imaging": "string or null",
    "rehabilitation": "string or null",
    "durable_medical_equipment": "string or null"
  },
  "confidence_score": 85
}

IMPORTANT:
- confidence_score MUST be an integer 0-100 reflecting how confident you are in the extraction accuracy.
- Use null for any field you cannot find in the text. Do not guess or fabricate values.
- Preserve exact dollar amounts and percentages as written in the document.
- All string values must use double quotes.
- Be thorough — these documents are dense and benefits may be described in different sections.
"""

SPC_COMPARE_SYSTEM_PROMPT = """You are a health insurance benefits analyst comparing two Summary of Plan Coverage (SPC) documents.

Analyze both plans and return a structured comparison. Return valid JSON with exactly this structure:

{
  "plan_a_name": "string",
  "plan_b_name": "string",
  "comparison": [
    {
      "category": "string (e.g. 'Deductible', 'Copays', 'Prescription Drugs')",
      "benefit": "string (specific benefit being compared)",
      "plan_a_value": "string",
      "plan_b_value": "string",
      "difference": "string (plain English description of the difference)",
      "advantage": "plan_a | plan_b | equal"
    }
  ],
  "cost_analysis": {
    "lower_premium_likely": "plan_a | plan_b | unclear",
    "lower_out_of_pocket_likely": "plan_a | plan_b | unclear",
    "better_for_healthy_individual": "plan_a | plan_b | equal",
    "better_for_high_utilizer": "plan_a | plan_b | equal",
    "better_rx_coverage": "plan_a | plan_b | equal",
    "notes": "string"
  },
  "prescription_drug_comparison": {
    "generic_advantage": "plan_a | plan_b | equal",
    "brand_advantage": "plan_a | plan_b | equal",
    "specialty_advantage": "plan_a | plan_b | equal",
    "mail_order_advantage": "plan_a | plan_b | equal",
    "notes": "string"
  },
  "key_differences": ["string — most important difference to highlight"],
  "recommendation": "string — overall assessment of which plan is better for different scenarios"
}

IMPORTANT: Be objective and thorough. Base all comparisons on the actual values extracted. If a value is missing from one plan, note it as 'Not specified'.
"""


async def parse_spc(text: str) -> dict:
    """
    Parse SPC/SBC document text into structured benefit data using Gemini AI.
    Falls back to mock data if AI is unavailable.

    Args:
        text: Raw text content extracted from the SPC/SBC PDF.

    Returns:
        Dict with structured benefit data.
    """
    try:
        result = await _generate(
            SPC_PARSE_SYSTEM_PROMPT,
            f"Extract structured benefit data from this Summary of Plan Coverage:\n\n{text[:15000]}",
            4000,
        )
        parsed = json.loads(result)
        parsed["_generated_by"] = "ai"
        logger.info(f"SPC parsed successfully via AI, confidence={parsed.get('confidence_score', 'N/A')}")
        return parsed
    except Exception as e:
        logger.warning(f"AI SPC parsing failed, using mock: {e}")
        result = _mock_spc_parse()
        result["_generated_by"] = "mock"
        return result


async def compare_spcs(text_a: str, text_b: str) -> dict:
    """
    Compare two SPC/SBC documents side by side using Gemini AI.
    Falls back to mock data if AI is unavailable.

    Args:
        text_a: Raw text of first SPC document.
        text_b: Raw text of second SPC document.

    Returns:
        Dict with structured comparison.
    """
    try:
        prompt = (
            "Compare these two Summary of Plan Coverage documents:\n\n"
            f"=== PLAN A ===\n{text_a[:8000]}\n\n"
            f"=== PLAN B ===\n{text_b[:8000]}"
        )
        result = await _generate(SPC_COMPARE_SYSTEM_PROMPT, prompt, 4000)
        parsed = json.loads(result)
        parsed["_generated_by"] = "ai"
        logger.info("SPC comparison completed via AI")
        return parsed
    except Exception as e:
        logger.warning(f"AI SPC comparison failed, using mock: {e}")
        result = _mock_spc_compare()
        result["_generated_by"] = "mock"
        return result


# ─── Mock Data Fallbacks ───────────────────────────────────────────────────────

def _mock_spc_parse() -> dict:
    return {
        "plan_info": {
            "plan_name": "Acme Corporation PPO Plan",
            "carrier": "Blue Cross Blue Shield",
            "effective_date": "January 1, 2025",
            "plan_type": "PPO",
            "coverage_period": "01/01/2025 - 12/31/2025",
        },
        "deductible": {
            "individual_in_network": "$1,500",
            "individual_out_of_network": "$3,000",
            "family_in_network": "$3,000",
            "family_out_of_network": "$6,000",
            "notes": "Deductible does not apply to preventive care or copay services.",
        },
        "out_of_pocket_maximum": {
            "individual_in_network": "$5,000",
            "individual_out_of_network": "$10,000",
            "family_in_network": "$10,000",
            "family_out_of_network": "$20,000",
            "notes": "Includes deductible, copays, and coinsurance.",
        },
        "copays": {
            "pcp_visit": "$25 copay",
            "specialist_visit": "$50 copay",
            "urgent_care": "$75 copay",
            "emergency_room": "$250 copay (waived if admitted)",
            "telehealth": "$15 copay",
            "mental_health_outpatient": "$25 copay",
            "notes": "Copays apply before deductible is met.",
        },
        "coinsurance": {
            "in_network": "80/20 after deductible (plan pays 80%, member pays 20%)",
            "out_of_network": "60/40 after deductible",
            "notes": "Coinsurance applies to most services after deductible.",
        },
        "prescription_drugs": {
            "tier_1_generic": {"copay": "$10", "mail_order": "$25 for 90-day supply"},
            "tier_2_preferred_brand": {"copay": "$35", "mail_order": "$87.50 for 90-day supply"},
            "tier_3_non_preferred": {"copay": "$70", "mail_order": "$175 for 90-day supply"},
            "tier_4_specialty": {"copay": "20% coinsurance up to $250/fill", "mail_order": "Not available"},
            "deductible_applies": "Tiers 3 and 4 only",
            "pbm_name": "OptumRx",
            "formulary_name": "Standard National Formulary",
            "notes": "Prior authorization required for specialty drugs. Step therapy may apply to certain drug classes.",
        },
        "hospital_services": {
            "inpatient": "$500 copay per admission plus 20% coinsurance after deductible",
            "outpatient_surgery": "$250 copay plus 20% coinsurance after deductible",
            "notes": "Pre-authorization required for inpatient stays.",
        },
        "exclusions_and_limits": [
            "Cosmetic surgery (unless medically necessary due to injury)",
            "Weight loss surgery (BMI must be >40 or >35 with comorbidities)",
            "Infertility treatments limited to 3 IVF cycles lifetime",
            "Dental and vision covered under separate plans",
            "Experimental or investigational treatments not covered",
            "Out-of-country coverage limited to emergency care only",
            "Chiropractic visits limited to 20 per year",
            "Physical/occupational therapy limited to 30 visits per year",
        ],
        "other_benefits": {
            "preventive_care": "Covered 100% in-network (no copay, no deductible)",
            "lab_work": "Covered at 80% after deductible (in-network)",
            "imaging": "$100 copay for advanced imaging (MRI, CT, PET)",
            "rehabilitation": "20% coinsurance after deductible, 30 visit limit",
            "durable_medical_equipment": "20% coinsurance after deductible",
        },
        "confidence_score": 92,
    }


def _mock_spc_compare() -> dict:
    return {
        "plan_a_name": "Acme Corporation PPO Plan",
        "plan_b_name": "Acme Corporation HDHP Plan",
        "comparison": [
            {
                "category": "Deductible",
                "benefit": "Individual In-Network",
                "plan_a_value": "$1,500",
                "plan_b_value": "$3,000",
                "difference": "Plan B has double the deductible ($1,500 higher)",
                "advantage": "plan_a",
            },
            {
                "category": "Deductible",
                "benefit": "Family In-Network",
                "plan_a_value": "$3,000",
                "plan_b_value": "$6,000",
                "difference": "Plan B family deductible is $3,000 higher",
                "advantage": "plan_a",
            },
            {
                "category": "Out-of-Pocket Max",
                "benefit": "Individual In-Network",
                "plan_a_value": "$5,000",
                "plan_b_value": "$5,000",
                "difference": "Same out-of-pocket maximum",
                "advantage": "equal",
            },
            {
                "category": "Copays",
                "benefit": "PCP Visit",
                "plan_a_value": "$25 copay",
                "plan_b_value": "20% after deductible",
                "difference": "Plan A has predictable flat copay. Plan B requires meeting deductible first, then coinsurance.",
                "advantage": "plan_a",
            },
            {
                "category": "Copays",
                "benefit": "Specialist Visit",
                "plan_a_value": "$50 copay",
                "plan_b_value": "20% after deductible",
                "difference": "Plan A has flat copay. Plan B may be cheaper if visit cost is under $250 after deductible.",
                "advantage": "plan_a",
            },
            {
                "category": "Prescription Drugs",
                "benefit": "Generic (Tier 1)",
                "plan_a_value": "$10 copay",
                "plan_b_value": "10% after deductible",
                "difference": "Plan A has flat $10 copay regardless of drug cost. Plan B requires deductible first.",
                "advantage": "plan_a",
            },
            {
                "category": "Prescription Drugs",
                "benefit": "Preferred Brand (Tier 2)",
                "plan_a_value": "$35 copay",
                "plan_b_value": "20% after deductible",
                "difference": "Plan A predictable at $35. Plan B depends on drug cost — cheaper for drugs under $175.",
                "advantage": "equal",
            },
            {
                "category": "Prescription Drugs",
                "benefit": "Specialty (Tier 4)",
                "plan_a_value": "20% up to $250/fill",
                "plan_b_value": "20% after deductible, no cap",
                "difference": "Plan A caps specialty copay at $250. Plan B has no cap — major risk for specialty drug users.",
                "advantage": "plan_a",
            },
            {
                "category": "Hospital",
                "benefit": "Inpatient Admission",
                "plan_a_value": "$500 + 20% coinsurance",
                "plan_b_value": "20% after deductible",
                "difference": "Plan B could be cheaper for short stays if deductible already met. Plan A more predictable.",
                "advantage": "equal",
            },
            {
                "category": "HSA Eligibility",
                "benefit": "Health Savings Account",
                "plan_a_value": "Not eligible",
                "plan_b_value": "HSA eligible — employer contributes $750/year",
                "difference": "Plan B qualifies for tax-advantaged HSA with employer seed funding.",
                "advantage": "plan_b",
            },
        ],
        "cost_analysis": {
            "lower_premium_likely": "plan_b",
            "lower_out_of_pocket_likely": "plan_a",
            "better_for_healthy_individual": "plan_b",
            "better_for_high_utilizer": "plan_a",
            "better_rx_coverage": "plan_a",
            "notes": "Plan B (HDHP) likely has lower premiums and includes HSA with employer contribution. Plan A (PPO) provides more predictable costs with copays and lower deductible. Break-even point is roughly $3,000-$4,000 in annual healthcare spending.",
        },
        "prescription_drug_comparison": {
            "generic_advantage": "plan_a",
            "brand_advantage": "equal",
            "specialty_advantage": "plan_a",
            "mail_order_advantage": "plan_a",
            "notes": "Plan A has consistent flat copays for all tiers with a $250 cap on specialty. Plan B requires meeting the full deductible before any Rx coverage kicks in, which is a major disadvantage for anyone on ongoing medications.",
        },
        "key_differences": [
            "Plan A (PPO): Lower deductible, copay-based, predictable costs, better for regular healthcare users and those on medications.",
            "Plan B (HDHP): Higher deductible, HSA-eligible with employer contribution, lower premiums, better for healthy individuals who rarely use healthcare.",
            "Specialty drug coverage is significantly better under Plan A due to $250/fill cap.",
            "Plan B's HSA tax advantages can offset higher deductible for disciplined savers.",
            "Emergency and hospital costs are more predictable under Plan A.",
        ],
        "recommendation": "Plan A (PPO) is recommended for employees with ongoing prescriptions, chronic conditions, families with children, or those who prefer cost predictability. Plan B (HDHP) is recommended for young, healthy individuals who want lower premiums and can maximize the HSA tax advantages. Employees taking specialty medications should strongly prefer Plan A due to the copay cap.",
    }
