"""
Synthetic data generation for ClearScript PBM Disclosure Audit Engine.
Generates realistic pharmacy claims, benchmark, formulary, network, and compliance data
with deliberate PBM overcharging patterns for demo purposes.
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

random.seed(42)

# ─── Drug Master List ───────────────────────────────────────────────────────────

DRUGS = [
    {"name": "Atorvastatin 40mg",     "ndc": "00071015523", "generic": True,  "class": "Statin",            "nadac_unit": 0.06,  "awp_unit": 0.45},
    {"name": "Lisinopril 20mg",       "ndc": "00093007201", "generic": True,  "class": "ACE Inhibitor",     "nadac_unit": 0.04,  "awp_unit": 0.38},
    {"name": "Metformin 500mg",       "ndc": "00093107201", "generic": True,  "class": "Antidiabetic",      "nadac_unit": 0.03,  "awp_unit": 0.32},
    {"name": "Amlodipine 10mg",       "ndc": "00069154066", "generic": True,  "class": "CCB",               "nadac_unit": 0.05,  "awp_unit": 0.42},
    {"name": "Omeprazole 20mg",       "ndc": "00186100131", "generic": True,  "class": "PPI",               "nadac_unit": 0.07,  "awp_unit": 0.52},
    {"name": "Sertraline 100mg",      "ndc": "00049490066", "generic": True,  "class": "SSRI",              "nadac_unit": 0.08,  "awp_unit": 0.55},
    {"name": "Levothyroxine 100mcg",  "ndc": "00074696390", "generic": True,  "class": "Thyroid",           "nadac_unit": 0.15,  "awp_unit": 0.89},
    {"name": "Albuterol HFA",         "ndc": "00173068220", "generic": True,  "class": "Bronchodilator",    "nadac_unit": 3.50,  "awp_unit": 7.20},
    {"name": "Gabapentin 300mg",      "ndc": "00228264311", "generic": True,  "class": "Anticonvulsant",    "nadac_unit": 0.05,  "awp_unit": 0.48},
    {"name": "Hydrochlorothiazide 25mg","ndc":"00591274101","generic": True,  "class": "Diuretic",          "nadac_unit": 0.03,  "awp_unit": 0.25},
    # Brand drugs (some favored over generics for rebate manipulation)
    {"name": "Lipitor 40mg",          "ndc": "00071015740", "generic": False, "class": "Statin",            "nadac_unit": 5.80,  "awp_unit": 9.50,  "rebate_pct": 0.55, "generic_alt": "Atorvastatin 40mg"},
    {"name": "Crestor 20mg",          "ndc": "00310075590", "generic": False, "class": "Statin",            "nadac_unit": 8.20,  "awp_unit": 13.40, "rebate_pct": 0.62, "generic_alt": "Rosuvastatin 20mg"},
    {"name": "Nexium 40mg",           "ndc": "00186501031", "generic": False, "class": "PPI",               "nadac_unit": 9.50,  "awp_unit": 15.80, "rebate_pct": 0.58, "generic_alt": "Omeprazole 20mg"},
    {"name": "Eliquis 5mg",           "ndc": "00003089321", "generic": False, "class": "Anticoagulant",     "nadac_unit": 8.70,  "awp_unit": 16.20, "rebate_pct": 0.35},
    {"name": "Jardiance 25mg",        "ndc": "00597014290", "generic": False, "class": "Antidiabetic",      "nadac_unit": 17.50, "awp_unit": 28.60, "rebate_pct": 0.42},
    {"name": "Ozempic 1mg",           "ndc": "00169416412", "generic": False, "class": "GLP-1 Agonist",     "nadac_unit": 35.20, "awp_unit": 58.00, "rebate_pct": 0.38},
    {"name": "Humira 40mg",           "ndc": "00074403902", "generic": False, "class": "Biologic (TNF)",    "nadac_unit": 2750.00,"awp_unit":3800.00,"rebate_pct": 0.48, "specialty": True},
    {"name": "Stelara 90mg",          "ndc": "57894003001", "generic": False, "class": "Biologic (IL-23)",  "nadac_unit": 3200.00,"awp_unit":4500.00,"rebate_pct": 0.40, "specialty": True},
    {"name": "Keytruda 200mg",        "ndc": "00006304502", "generic": False, "class": "Oncology",          "nadac_unit": 4800.00,"awp_unit":6200.00,"rebate_pct": 0.15, "specialty": True},
    {"name": "Dupixent 300mg",        "ndc": "00024583600", "generic": False, "class": "Biologic (IL-4)",   "nadac_unit": 1850.00,"awp_unit":2700.00,"rebate_pct": 0.32, "specialty": True},
    # Additional generics
    {"name": "Rosuvastatin 20mg",     "ndc": "00093717898", "generic": True,  "class": "Statin",            "nadac_unit": 0.12,  "awp_unit": 0.75},
    {"name": "Montelukast 10mg",      "ndc": "00006027531", "generic": True,  "class": "Leukotriene",       "nadac_unit": 0.10,  "awp_unit": 0.65},
    {"name": "Escitalopram 10mg",     "ndc": "00456201001", "generic": True,  "class": "SSRI",              "nadac_unit": 0.09,  "awp_unit": 0.58},
    {"name": "Losartan 50mg",         "ndc": "00093737598", "generic": True,  "class": "ARB",               "nadac_unit": 0.06,  "awp_unit": 0.44},
    {"name": "Tamsulosin 0.4mg",      "ndc": "00597003901", "generic": True,  "class": "Alpha Blocker",     "nadac_unit": 0.08,  "awp_unit": 0.52},
    # More brands
    {"name": "Trulicity 1.5mg",       "ndc": "00002773590", "generic": False, "class": "GLP-1 Agonist",     "nadac_unit": 28.50, "awp_unit": 45.00, "rebate_pct": 0.45},
    {"name": "Xarelto 20mg",          "ndc": "50458058030", "generic": False, "class": "Anticoagulant",     "nadac_unit": 15.20, "awp_unit": 22.80, "rebate_pct": 0.30},
    {"name": "Entresto 97/103mg",     "ndc": "00078062035", "generic": False, "class": "Heart Failure",     "nadac_unit": 10.80, "awp_unit": 18.50, "rebate_pct": 0.28},
    {"name": "Symbicort 160/4.5",     "ndc": "00186037020", "generic": False, "class": "Inhaler",           "nadac_unit": 12.50, "awp_unit": 21.00, "rebate_pct": 0.50, "generic_alt": "Budesonide/Formoterol"},
    {"name": "Vyvanse 50mg",          "ndc": "59417010510", "generic": False, "class": "ADHD",              "nadac_unit": 12.80, "awp_unit": 19.50, "rebate_pct": 0.22},
    # Additional generics to reach 50
    {"name": "Metoprolol Succ 50mg",  "ndc": "00378181501", "generic": True,  "class": "Beta Blocker",      "nadac_unit": 0.05,  "awp_unit": 0.40},
    {"name": "Pantoprazole 40mg",     "ndc": "00093018201", "generic": True,  "class": "PPI",               "nadac_unit": 0.06,  "awp_unit": 0.45},
    {"name": "Duloxetine 60mg",       "ndc": "00002323360", "generic": True,  "class": "SNRI",              "nadac_unit": 0.15,  "awp_unit": 0.85},
    {"name": "Pregabalin 75mg",       "ndc": "00071101968", "generic": True,  "class": "Anticonvulsant",    "nadac_unit": 0.12,  "awp_unit": 0.72},
    {"name": "Trazodone 50mg",        "ndc": "00093073301", "generic": True,  "class": "Antidepressant",    "nadac_unit": 0.04,  "awp_unit": 0.30},
    {"name": "Meloxicam 15mg",        "ndc": "00093053601", "generic": True,  "class": "NSAID",             "nadac_unit": 0.05,  "awp_unit": 0.38},
    {"name": "Clopidogrel 75mg",      "ndc": "00093738956", "generic": True,  "class": "Antiplatelet",      "nadac_unit": 0.07,  "awp_unit": 0.50},
    {"name": "Fluticasone Spray",     "ndc": "00093800116", "generic": True,  "class": "Nasal Steroid",     "nadac_unit": 0.80,  "awp_unit": 2.50},
    {"name": "Cyclobenzaprine 10mg",  "ndc": "00591522101", "generic": True,  "class": "Muscle Relaxant",   "nadac_unit": 0.04,  "awp_unit": 0.32},
    {"name": "Valacyclovir 1g",       "ndc": "00093710898", "generic": True,  "class": "Antiviral",         "nadac_unit": 0.55,  "awp_unit": 2.10},
    {"name": "Spironolactone 25mg",   "ndc": "00093079101", "generic": True,  "class": "Diuretic",          "nadac_unit": 0.08,  "awp_unit": 0.50},
    {"name": "Carvedilol 25mg",       "ndc": "00093085201", "generic": True,  "class": "Beta Blocker",      "nadac_unit": 0.06,  "awp_unit": 0.42},
    {"name": "Amoxicillin 500mg",     "ndc": "00093315401", "generic": True,  "class": "Antibiotic",        "nadac_unit": 0.05,  "awp_unit": 0.35},
    {"name": "Azithromycin 250mg",    "ndc": "00093720906", "generic": True,  "class": "Antibiotic",        "nadac_unit": 0.60,  "awp_unit": 2.20},
    {"name": "Prednisone 10mg",       "ndc": "00591543901", "generic": True,  "class": "Corticosteroid",    "nadac_unit": 0.06,  "awp_unit": 0.40},
    {"name": "Sumatriptan 100mg",     "ndc": "00093531801", "generic": True,  "class": "Triptan",           "nadac_unit": 0.85,  "awp_unit": 3.50},
    {"name": "Insulin Glargine",      "ndc": "00088250205", "generic": False, "class": "Insulin",           "nadac_unit": 18.50, "awp_unit": 32.00, "rebate_pct": 0.52},
    {"name": "Bupropion XL 150mg",    "ndc": "00093321901", "generic": True,  "class": "Antidepressant",    "nadac_unit": 0.20,  "awp_unit": 1.10},
    {"name": "Methylphenidate ER 36mg","ndc":"00093537201", "generic": True,  "class": "ADHD",              "nadac_unit": 0.95,  "awp_unit": 3.80},
    {"name": "Aripiprazole 10mg",     "ndc": "00093522001", "generic": True,  "class": "Antipsychotic",     "nadac_unit": 0.25,  "awp_unit": 1.50},
]

# ─── Pharmacy Master List ────────────────────────────────────────────────────────

PHARMACIES = [
    {"id": "PH001", "name": "CVS Pharmacy #4521",       "npi": "1234567890", "type": "retail",    "chain": "CVS",       "city": "Chicago",     "state": "IL", "zip": "60601", "active": True},
    {"id": "PH002", "name": "Walgreens #1892",           "npi": "2345678901", "type": "retail",    "chain": "Walgreens", "city": "Chicago",     "state": "IL", "zip": "60605", "active": True},
    {"id": "PH003", "name": "CVS Pharmacy #7834",        "npi": "3456789012", "type": "retail",    "chain": "CVS",       "city": "Naperville",  "state": "IL", "zip": "60540", "active": True},
    {"id": "PH004", "name": "Walmart Pharmacy #2190",    "npi": "4567890123", "type": "retail",    "chain": "Walmart",   "city": "Schaumburg",  "state": "IL", "zip": "60173", "active": True},
    {"id": "PH005", "name": "Rite Aid #6543",            "npi": "5678901234", "type": "retail",    "chain": "Rite Aid",  "city": "Evanston",    "state": "IL", "zip": "60201", "active": True},
    {"id": "PH006", "name": "OptumRx Mail Order",        "npi": "6789012345", "type": "mail",      "chain": "OptumRx",   "city": "Carlsbad",    "state": "CA", "zip": "92008", "active": True},
    {"id": "PH007", "name": "Express Scripts Mail",      "npi": "7890123456", "type": "mail",      "chain": "ESI",       "city": "St. Louis",   "state": "MO", "zip": "63006", "active": True},
    {"id": "PH008", "name": "BrightSpring Specialty",    "npi": "8901234567", "type": "specialty", "chain": "BrightSpring","city":"Louisville",  "state": "KY", "zip": "40202", "active": True},
    {"id": "PH009", "name": "Accredo Specialty Pharmacy", "npi": "9012345678", "type": "specialty", "chain": "Accredo",   "city": "Memphis",     "state": "TN", "zip": "38118", "active": True},
    # Phantom pharmacies (flagged as suspicious)
    {"id": "PH010", "name": "MedFirst Rx #9991",         "npi": "0000000001", "type": "retail",    "chain": "MedFirst",  "city": "Chicago",     "state": "IL", "zip": "60699", "active": False, "phantom": True, "flag_reason": "NPI not found in NPPES registry, no physical location verified"},
    {"id": "PH011", "name": "QuickCare Pharmacy",        "npi": "0000000002", "type": "retail",    "chain": "QuickCare", "city": "Joliet",      "state": "IL", "zip": "60431", "active": False, "phantom": True, "flag_reason": "Address is vacant lot per USPS verification, 0 claims in last 90 days"},
]

# ─── Claims Generation ──────────────────────────────────────────────────────────

def _generate_claim_id(i: int) -> str:
    return f"CLM-2025-{str(i).zfill(6)}"

def _pick_channel_pharmacy(drug: dict) -> dict:
    if drug.get("specialty"):
        ph = random.choice([p for p in PHARMACIES if p["type"] == "specialty"])
        return {**ph, "channel": "specialty"}
    channel = random.choices(["retail", "mail"], weights=[0.72, 0.28])[0]
    pool = [p for p in PHARMACIES if p["type"] == channel and not p.get("phantom")]
    # 3% of retail claims go to phantom pharmacies
    if channel == "retail" and random.random() < 0.03:
        pool = [p for p in PHARMACIES if p.get("phantom")]
    ph = random.choice(pool)
    return {**ph, "channel": channel}

def generate_claims(n: int = 500) -> List[Dict[str, Any]]:
    claims = []
    base_date = datetime(2025, 1, 1)
    for i in range(1, n + 1):
        drug = random.choice(DRUGS)
        pharmacy = _pick_channel_pharmacy(drug)
        qty = random.choice([30, 60, 90]) if not drug.get("specialty") else 1
        days_supply = qty if not drug.get("specialty") else 28

        nadac_cost = round(drug["nadac_unit"] * qty, 2)
        # PBM markup: spread pricing (retail gets worst spread)
        spread_factor = {"retail": random.uniform(1.8, 4.5), "mail": random.uniform(1.2, 2.0), "specialty": random.uniform(1.05, 1.3)}
        channel = pharmacy["channel"]
        plan_paid = round(nadac_cost * spread_factor[channel], 2)
        pharmacy_reimbursed = round(nadac_cost * random.uniform(1.05, 1.25), 2)
        spread = round(plan_paid - pharmacy_reimbursed, 2)

        # Rebate info for brand drugs
        rebate_amount = 0.0
        rebate_passed = 0.0
        if not drug["generic"]:
            rebate_pct = drug.get("rebate_pct", 0.20)
            rebate_amount = round(plan_paid * rebate_pct, 2)
            # PBM keeps a chunk: only passes 60-80% of what they claim
            passthrough_rate = random.uniform(0.58, 0.82)
            rebate_passed = round(rebate_amount * passthrough_rate, 2)

        fill_date = base_date + timedelta(days=random.randint(0, 180))
        member_id = f"MEM-{random.randint(10000, 99999)}"
        copay = round(random.choice([5, 10, 15, 25, 35, 50, 75]) if not drug.get("specialty") else random.choice([100, 150, 250]), 2)

        claims.append({
            "claim_id": _generate_claim_id(i),
            "fill_date": fill_date.strftime("%Y-%m-%d"),
            "member_id": member_id,
            "drug_name": drug["name"],
            "ndc": drug["ndc"],
            "generic": drug["generic"],
            "drug_class": drug["class"],
            "quantity": qty,
            "days_supply": days_supply,
            "pharmacy_id": pharmacy["id"],
            "pharmacy_name": pharmacy["name"],
            "pharmacy_npi": pharmacy["npi"],
            "channel": channel,
            "nadac_unit_cost": drug["nadac_unit"],
            "nadac_total": nadac_cost,
            "awp_unit_cost": drug["awp_unit"],
            "plan_paid": plan_paid,
            "pharmacy_reimbursed": pharmacy_reimbursed,
            "spread": spread,
            "copay": copay,
            "rebate_amount": rebate_amount,
            "rebate_passed_to_plan": rebate_passed,
            "rebate_retained_by_pbm": round(rebate_amount - rebate_passed, 2),
            "is_specialty": drug.get("specialty", False),
        })
    return claims

# ─── Benchmark Data ──────────────────────────────────────────────────────────────

def generate_benchmarks() -> Dict[str, Any]:
    employer_sizes = [
        {"label": "Small (50-200 lives)",  "key": "small"},
        {"label": "Mid-market (200-1000)", "key": "mid"},
        {"label": "Large (1000-5000)",     "key": "large"},
        {"label": "Jumbo (5000+)",         "key": "jumbo"},
    ]
    metrics = []
    for size in employer_sizes:
        gdr = round(random.uniform(0.82, 0.92), 3)
        metrics.append({
            "segment": size["label"],
            "segment_key": size["key"],
            "avg_cost_per_script": round(random.uniform(55, 120), 2),
            "rebate_passthrough_pct": round(random.uniform(0.65, 0.95), 3),
            "specialty_spend_pct": round(random.uniform(0.38, 0.55), 3),
            "generic_dispensing_rate": gdr,
            "avg_spread_per_claim": round(random.uniform(3.50, 18.00), 2),
            "mail_order_utilization": round(random.uniform(0.15, 0.35), 3),
            "plan_count": random.randint(45, 320),
        })

    # "Your plan" data (deliberately worse than peers to highlight issues)
    your_plan = {
        "segment": "Your Plan (Mid-market)",
        "segment_key": "your_plan",
        "avg_cost_per_script": 98.50,
        "rebate_passthrough_pct": 0.68,
        "specialty_spend_pct": 0.52,
        "generic_dispensing_rate": 0.79,
        "avg_spread_per_claim": 15.40,
        "mail_order_utilization": 0.18,
        "plan_count": 1,
    }

    return {
        "peer_benchmarks": metrics,
        "your_plan": your_plan,
        "analysis": {
            "rebate_gap": "Your rebate passthrough (68%) is 14 percentage points below the mid-market average (82%). This represents approximately $420,000 in annual rebate leakage.",
            "gdr_gap": "Your generic dispensing rate (79%) is 8 points below peers (87%). Formulary manipulation may be steering members to brand drugs with higher PBM rebates.",
            "spread_alert": "Your average spread per claim ($15.40) is 2.3x the mid-market average ($6.70), indicating significant spread pricing.",
            "specialty_alert": "Specialty spend at 52% of total is above the 46% peer average. Review specialty pharmacy steering.",
            "rank": {
                "cost_per_script": "78th percentile (worse than 78% of peers)",
                "rebate_passthrough": "22nd percentile (worse than 78% of peers)",
                "generic_rate": "15th percentile (worse than 85% of peers)",
                "overall_value": "18th percentile — Bottom quintile"
            }
        }
    }

# ─── Formulary Data ──────────────────────────────────────────────────────────────

def generate_formulary_data() -> Dict[str, Any]:
    six_months_ago = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    # Deliberate manipulation: generics moved to higher tier, brands with rebates favored
    changes = [
        {
            "drug_name": "Atorvastatin 40mg",
            "type": "generic",
            "previous_tier": 1,
            "current_tier": 2,
            "previous_copay": 5,
            "current_copay": 15,
            "change_date": "2025-03-15",
            "brand_alternative": "Lipitor 40mg",
            "brand_tier": 2,
            "brand_copay": 25,
            "estimated_rebate_per_script": 45.00,
            "manipulation_flag": True,
            "flag_reason": "Generic moved to same tier as brand. Rebate on brand ($45/script) creates PBM incentive to steer utilization.",
        },
        {
            "drug_name": "Omeprazole 20mg",
            "type": "generic",
            "previous_tier": 1,
            "current_tier": 2,
            "previous_copay": 5,
            "current_copay": 20,
            "change_date": "2025-04-01",
            "brand_alternative": "Nexium 40mg",
            "brand_tier": 2,
            "brand_copay": 30,
            "estimated_rebate_per_script": 62.00,
            "manipulation_flag": True,
            "flag_reason": "Generic PPI moved up coinciding with new Nexium rebate contract. Net cost to plan increases while PBM rebate revenue rises.",
        },
        {
            "drug_name": "Rosuvastatin 20mg",
            "type": "generic",
            "previous_tier": 1,
            "current_tier": 2,
            "previous_copay": 5,
            "current_copay": 15,
            "change_date": "2025-02-01",
            "brand_alternative": "Crestor 20mg",
            "brand_tier": 2,
            "brand_copay": 35,
            "estimated_rebate_per_script": 78.00,
            "manipulation_flag": True,
            "flag_reason": "Tier change correlates with 62% rebate on Crestor. Members steered from $0.12/unit generic to $8.20/unit brand.",
        },
        {
            "drug_name": "Humira 40mg",
            "type": "specialty_brand",
            "previous_tier": 4,
            "current_tier": 3,
            "previous_copay": 250,
            "current_copay": 150,
            "change_date": "2025-03-01",
            "brand_alternative": None,
            "brand_tier": None,
            "brand_copay": None,
            "estimated_rebate_per_script": 1824.00,
            "manipulation_flag": True,
            "flag_reason": "Specialty drug moved to lower tier despite biosimilar availability. 48% rebate ($1,824/script) retained largely by PBM.",
        },
        {
            "drug_name": "Symbicort 160/4.5",
            "type": "brand",
            "previous_tier": 3,
            "current_tier": 2,
            "previous_copay": 45,
            "current_copay": 25,
            "change_date": "2025-05-01",
            "brand_alternative": None,
            "brand_tier": None,
            "brand_copay": None,
            "estimated_rebate_per_script": 52.50,
            "manipulation_flag": True,
            "flag_reason": "Brand inhaler moved to preferred tier with no therapeutic justification. 50% rebate benefits PBM.",
        },
        # Legitimate changes (no manipulation)
        {
            "drug_name": "Metformin 500mg",
            "type": "generic",
            "previous_tier": 1,
            "current_tier": 1,
            "previous_copay": 5,
            "current_copay": 5,
            "change_date": None,
            "brand_alternative": None,
            "brand_tier": None,
            "brand_copay": None,
            "estimated_rebate_per_script": 0,
            "manipulation_flag": False,
            "flag_reason": None,
        },
        {
            "drug_name": "Lisinopril 20mg",
            "type": "generic",
            "previous_tier": 1,
            "current_tier": 1,
            "previous_copay": 5,
            "current_copay": 5,
            "change_date": None,
            "brand_alternative": None,
            "brand_tier": None,
            "brand_copay": None,
            "estimated_rebate_per_script": 0,
            "manipulation_flag": False,
            "flag_reason": None,
        },
    ]

    total_impact = sum(c["estimated_rebate_per_script"] * random.randint(50, 200) for c in changes if c["manipulation_flag"])

    return {
        "snapshot_previous": six_months_ago,
        "snapshot_current": today,
        "total_drugs_reviewed": len(DRUGS),
        "changes_detected": len([c for c in changes if c["change_date"]]),
        "manipulation_flags": len([c for c in changes if c["manipulation_flag"]]),
        "changes": changes,
        "estimated_annual_cost_impact": round(total_impact, 2),
        "summary": f"Detected {len([c for c in changes if c['manipulation_flag']])} formulary changes correlated with rebate incentives. "
                   f"Estimated annual cost impact: ${round(total_impact):,}. "
                   f"Pattern: generics moved to higher tiers while corresponding brands with high rebates remain at same or lower tiers.",
    }

# ─── Network Data ────────────────────────────────────────────────────────────────

def generate_network_data() -> List[Dict[str, Any]]:
    return PHARMACIES

def generate_network_analysis(zip_codes: List[str]) -> Dict[str, Any]:
    coverage_areas = []
    total_pharmacies = 0
    phantom_count = 0
    gap_areas = []

    for zc in zip_codes:
        nearby = [p for p in PHARMACIES if not p.get("phantom")]
        # Simulate some zips having fewer pharmacies
        zc_hash = int(hashlib.md5(zc.encode()).hexdigest()[:8], 16)
        count = (zc_hash % 5) + 1
        has_gap = count <= 1

        if has_gap:
            gap_areas.append(zc)

        coverage_areas.append({
            "zip_code": zc,
            "pharmacies_within_5mi": count,
            "pharmacies_within_10mi": count + random.randint(1, 4),
            "has_retail": count >= 1,
            "has_mail_order": True,
            "has_specialty": count >= 3,
            "adequacy_met": not has_gap,
        })
        total_pharmacies += count

    phantoms = [p for p in PHARMACIES if p.get("phantom")]

    adequacy_score = round((1 - len(gap_areas) / max(len(zip_codes), 1)) * 100, 1)

    return {
        "zip_codes_analyzed": len(zip_codes),
        "total_network_pharmacies": len([p for p in PHARMACIES if not p.get("phantom")]),
        "phantom_pharmacies_detected": len(phantoms),
        "phantom_details": [
            {"id": p["id"], "name": p["name"], "npi": p["npi"], "reason": p.get("flag_reason", "Unverified")}
            for p in phantoms
        ],
        "coverage_areas": coverage_areas,
        "gap_areas": gap_areas,
        "adequacy_score": adequacy_score,
        "adequacy_threshold": 90.0,
        "adequacy_met": adequacy_score >= 90.0,
        "recommendations": [
            f"ZIP {z}: Below CMS adequacy standard — fewer than 2 retail pharmacies within 5 miles"
            for z in gap_areas
        ] + [
            f"Phantom pharmacy flagged: {p['name']} ({p['npi']}) — {p.get('flag_reason', 'N/A')}"
            for p in phantoms
        ],
    }

# ─── Compliance Deadlines ────────────────────────────────────────────────────────

def generate_compliance_deadlines() -> List[Dict[str, Any]]:
    today = datetime.now()
    deadlines = [
        {
            "id": "DOL-2025",
            "name": "DOL Prescription Drug Cost Reporting Rule",
            "description": "Requires group health plans and issuers to report prescription drug cost information to the Departments annually, including total spending, rebates received, and cost-sharing.",
            "deadline": "2025-12-27",
            "authority": "Department of Labor",
            "regulation": "29 CFR 2520.101-2",
            "category": "federal",
            "action_required": "Submit annual Rx data report via DOL portal. Include total Rx spend, rebates, top 50 drugs by spend, and generic vs brand utilization.",
        },
        {
            "id": "CAA-GSHP-2026",
            "name": "CAA Gag Clause Prohibition Compliance Attestation",
            "description": "Annual attestation that PBM contract does not contain gag clauses preventing disclosure of cost or quality information.",
            "deadline": "2026-06-01",
            "authority": "CMS / DOL / Treasury",
            "regulation": "Consolidated Appropriations Act, 2021 - Section 201",
            "category": "federal",
            "action_required": "Submit attestation via CMS portal confirming no gag clauses in PBM contracts.",
        },
        {
            "id": "HR7148-2028",
            "name": "HR 7148 — PBM Rebate Delinking Act",
            "description": "Requires PBMs to delink compensation from drug list prices. Rebate passthrough to plan sponsors becomes mandatory. PBM spread pricing prohibited.",
            "deadline": "2028-01-01",
            "authority": "Congress (pending)",
            "regulation": "HR 7148 (proposed)",
            "category": "federal_pending",
            "action_required": "Begin contract renegotiation. Ensure PBM contracts will comply with passthrough requirements and spread pricing bans by effective date.",
        },
        {
            "id": "IL-SB1239",
            "name": "Illinois PBM Transparency Act",
            "description": "Requires PBMs operating in Illinois to report aggregate rebate data and spread pricing amounts to the Department of Insurance annually.",
            "deadline": "2026-03-31",
            "authority": "Illinois Department of Insurance",
            "regulation": "SB 1239",
            "category": "state",
            "action_required": "Ensure PBM provides required transparency data for Illinois-covered lives. File annual report.",
        },
        {
            "id": "NY-A7614",
            "name": "New York PBM Regulation",
            "description": "Mandates PBM registration and reporting of rebate pass-through rates, pharmacy reimbursement methods, and formulary change justifications.",
            "deadline": "2026-07-01",
            "authority": "NY Department of Financial Services",
            "regulation": "A.7614 / S.6144",
            "category": "state",
            "action_required": "Verify PBM registration status. Request rebate transparency report for NY-covered lives.",
        },
        {
            "id": "TX-SB622",
            "name": "Texas PBM Audit Rights Act",
            "description": "Grants plan sponsors enhanced audit rights over PBMs including access to pharmacy-level claims data and rebate contracts.",
            "deadline": "2026-09-01",
            "authority": "Texas Department of Insurance",
            "regulation": "SB 622",
            "category": "state",
            "action_required": "Exercise expanded audit rights. Request pharmacy-level claims data from PBM.",
        },
        {
            "id": "CA-AB1286",
            "name": "California Prescription Drug Pricing Transparency",
            "description": "Requires annual reporting of drug pricing data including wholesale acquisition costs, rebate amounts, and patient cost-sharing impact.",
            "deadline": "2026-04-01",
            "authority": "California OSHPD",
            "regulation": "AB 1286",
            "category": "state",
            "action_required": "Compile and submit Rx pricing data for California-covered employees.",
        },
    ]

    for d in deadlines:
        dl = datetime.strptime(d["deadline"], "%Y-%m-%d")
        days_until = (dl - today).days
        d["days_until"] = days_until
        if days_until < 0:
            d["status"] = "overdue"
            d["urgency"] = "critical"
        elif days_until <= 30:
            d["status"] = "imminent"
            d["urgency"] = "high"
        elif days_until <= 90:
            d["status"] = "upcoming"
            d["urgency"] = "medium"
        else:
            d["status"] = "scheduled"
            d["urgency"] = "low"

    return sorted(deadlines, key=lambda x: x["days_until"])

# ─── Spread Analysis ─────────────────────────────────────────────────────────────

def analyze_spread(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_channel = {"retail": [], "mail": [], "specialty": []}
    for c in claims:
        by_channel[c["channel"]].append(c)

    channel_summary = {}
    total_spread = 0
    for ch, ch_claims in by_channel.items():
        if not ch_claims:
            continue
        spreads = [c["spread"] for c in ch_claims]
        total = sum(spreads)
        total_spread += total
        channel_summary[ch] = {
            "claim_count": len(ch_claims),
            "total_spread": round(total, 2),
            "avg_spread": round(total / len(ch_claims), 2),
            "max_spread": round(max(spreads), 2),
            "min_spread": round(min(spreads), 2),
            "median_spread": round(sorted(spreads)[len(spreads) // 2], 2),
            "pct_of_total_spread": 0,
        }

    for ch in channel_summary:
        channel_summary[ch]["pct_of_total_spread"] = round(channel_summary[ch]["total_spread"] / total_spread * 100, 1) if total_spread else 0

    # Worst offender drugs
    drug_spreads = {}
    for c in claims:
        key = c["drug_name"]
        if key not in drug_spreads:
            drug_spreads[key] = {"total_spread": 0, "count": 0, "generic": c["generic"]}
        drug_spreads[key]["total_spread"] += c["spread"]
        drug_spreads[key]["count"] += 1

    worst = sorted(drug_spreads.items(), key=lambda x: x[1]["total_spread"], reverse=True)[:10]
    worst_drugs = [
        {
            "drug_name": name,
            "total_spread": round(data["total_spread"], 2),
            "avg_spread_per_claim": round(data["total_spread"] / data["count"], 2),
            "claim_count": data["count"],
            "is_generic": data["generic"],
        }
        for name, data in worst
    ]

    return {
        "total_spread_captured": round(total_spread, 2),
        "total_claims_analyzed": len(claims),
        "avg_spread_per_claim": round(total_spread / len(claims), 2) if claims else 0,
        "by_channel": channel_summary,
        "worst_offender_drugs": worst_drugs,
        "annualized_spread": round(total_spread * 2, 2),
        "alert": f"PBM captured ${round(total_spread):,} in spread pricing over 6 months (${round(total_spread * 2):,} annualized). Retail channel accounts for the largest spread at ${round(channel_summary.get('retail', {}).get('total_spread', 0)):,}.",
    }

# ─── Rebate Analysis ─────────────────────────────────────────────────────────────

def analyze_rebates(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    brand_claims = [c for c in claims if not c["generic"]]
    total_rebates = sum(c["rebate_amount"] for c in brand_claims)
    total_passed = sum(c["rebate_passed_to_plan"] for c in brand_claims)
    total_retained = sum(c["rebate_retained_by_pbm"] for c in brand_claims)

    passthrough_rate = round(total_passed / total_rebates * 100, 1) if total_rebates else 0
    leakage_pct = round(100 - passthrough_rate, 1)

    # Drug-level analysis
    drug_rebates = {}
    for c in brand_claims:
        key = c["drug_name"]
        if key not in drug_rebates:
            drug_rebates[key] = {"total_rebate": 0, "passed": 0, "retained": 0, "count": 0, "has_generic_alt": False}
        drug_rebates[key]["total_rebate"] += c["rebate_amount"]
        drug_rebates[key]["passed"] += c["rebate_passed_to_plan"]
        drug_rebates[key]["retained"] += c["rebate_retained_by_pbm"]
        drug_rebates[key]["count"] += 1

    # Check which brands have generic alternatives
    for drug in DRUGS:
        if drug.get("generic_alt") and drug["name"] in drug_rebates:
            drug_rebates[drug["name"]]["has_generic_alt"] = True
            drug_rebates[drug["name"]]["generic_alt_name"] = drug["generic_alt"]

    # Formulary manipulation: brands favored over generics
    manipulation_flags = []
    for name, data in drug_rebates.items():
        if data.get("has_generic_alt"):
            generic_drug = next((d for d in DRUGS if d["name"] == data.get("generic_alt_name")), None)
            if generic_drug:
                cost_diff = round(data["total_rebate"] / data["count"] - generic_drug["nadac_unit"] * 30, 2)
                manipulation_flags.append({
                    "brand_drug": name,
                    "generic_alternative": data["generic_alt_name"],
                    "brand_claims": data["count"],
                    "rebate_per_script": round(data["total_rebate"] / data["count"], 2),
                    "generic_cost_per_script": round(generic_drug["nadac_unit"] * 30, 2),
                    "cost_increase_per_script": cost_diff,
                    "flag": f"High-rebate brand ({name}) favored over cheaper generic ({data['generic_alt_name']}). PBM earns ${round(data['retained'] / data['count'], 2)}/script in retained rebates.",
                })

    top_leakers = sorted(drug_rebates.items(), key=lambda x: x[1]["retained"], reverse=True)[:10]
    top_leakers_list = [
        {
            "drug_name": name,
            "total_rebate": round(data["total_rebate"], 2),
            "amount_passed": round(data["passed"], 2),
            "amount_retained_by_pbm": round(data["retained"], 2),
            "passthrough_rate": round(data["passed"] / data["total_rebate"] * 100, 1) if data["total_rebate"] else 0,
            "claim_count": data["count"],
        }
        for name, data in top_leakers
    ]

    return {
        "total_rebates_earned": round(total_rebates, 2),
        "rebates_passed_to_plan": round(total_passed, 2),
        "rebates_retained_by_pbm": round(total_retained, 2),
        "passthrough_rate_pct": passthrough_rate,
        "leakage_pct": leakage_pct,
        "brand_claims_count": len(brand_claims),
        "total_claims": len(claims),
        "annualized_leakage": round(total_retained * 2, 2),
        "top_leakage_drugs": top_leakers_list,
        "formulary_manipulation_flags": manipulation_flags,
        "summary": f"Of ${round(total_rebates):,} in total manufacturer rebates, only ${round(total_passed):,} ({passthrough_rate}%) was passed through to the plan. "
                   f"The PBM retained ${round(total_retained):,} ({leakage_pct}%). "
                   f"Annualized rebate leakage: ${round(total_retained * 2):,}. "
                   f"Detected {len(manipulation_flags)} drugs where high-rebate brands are favored over cheaper generics.",
    }

# ─── Report Audit ────────────────────────────────────────────────────────────────

def audit_report(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_plan_paid = sum(c["plan_paid"] for c in claims)
    total_nadac = sum(c["nadac_total"] for c in claims)
    total_rebates_reported = sum(c["rebate_amount"] for c in claims)
    total_rebates_passed = sum(c["rebate_passed_to_plan"] for c in claims)

    # Calculate what rebates SHOULD be based on volume
    brand_claims = [c for c in claims if not c["generic"]]
    expected_rebates = sum(c["plan_paid"] * 0.42 for c in brand_claims)  # Industry avg rebate

    discrepancies = []

    # Rebate discrepancy
    if total_rebates_reported < expected_rebates * 0.85:
        discrepancies.append({
            "type": "rebate_underreporting",
            "severity": "high",
            "description": f"PBM reported ${round(total_rebates_reported):,} in rebates, but claim volume suggests approximately ${round(expected_rebates):,}. Potential underreporting of ${round(expected_rebates - total_rebates_reported):,}.",
            "expected": round(expected_rebates, 2),
            "reported": round(total_rebates_reported, 2),
            "gap": round(expected_rebates - total_rebates_reported, 2),
        })

    # Spread pricing anomaly
    total_spread = sum(c["spread"] for c in claims)
    if total_spread > total_plan_paid * 0.08:
        discrepancies.append({
            "type": "excessive_spread",
            "severity": "high",
            "description": f"Total spread pricing of ${round(total_spread):,} represents {round(total_spread / total_plan_paid * 100, 1)}% of total plan spend — well above the 3-5% industry norm.",
            "spread_total": round(total_spread, 2),
            "spread_pct": round(total_spread / total_plan_paid * 100, 1),
            "industry_norm_pct": "3-5%",
        })

    # AWP vs NADAC gap
    awp_total = sum(c["awp_unit_cost"] * c["quantity"] for c in claims)
    if total_plan_paid > awp_total * 0.95:
        discrepancies.append({
            "type": "awp_pricing_concern",
            "severity": "medium",
            "description": f"Plan-paid amounts (${round(total_plan_paid):,}) are close to or exceed AWP (${round(awp_total):,}). Most contracts guarantee discounts below AWP.",
            "plan_paid": round(total_plan_paid, 2),
            "awp_total": round(awp_total, 2),
        })

    # Phantom pharmacy claims
    phantom_claims = [c for c in claims if any(p.get("phantom") and p["id"] == c["pharmacy_id"] for p in PHARMACIES)]
    if phantom_claims:
        discrepancies.append({
            "type": "phantom_pharmacy",
            "severity": "critical",
            "description": f"Found {len(phantom_claims)} claims routed through pharmacies with unverifiable NPIs or addresses. Total: ${round(sum(c['plan_paid'] for c in phantom_claims)):,}.",
            "claim_count": len(phantom_claims),
            "total_amount": round(sum(c["plan_paid"] for c in phantom_claims), 2),
        })

    # Generic utilization concern
    generic_claims = [c for c in claims if c["generic"]]
    gdr = len(generic_claims) / len(claims) if claims else 0
    if gdr < 0.83:
        discrepancies.append({
            "type": "low_generic_rate",
            "severity": "medium",
            "description": f"Generic dispensing rate of {round(gdr * 100, 1)}% is below the industry benchmark of 88-92%. Potential formulary steering toward higher-cost brand drugs.",
            "gdr": round(gdr * 100, 1),
            "benchmark": "88-92%",
        })

    return {
        "audit_period": "2025-01-01 to 2025-06-30",
        "total_claims": len(claims),
        "total_plan_paid": round(total_plan_paid, 2),
        "total_nadac_cost": round(total_nadac, 2),
        "total_rebates_reported": round(total_rebates_reported, 2),
        "total_rebates_expected": round(expected_rebates, 2),
        "total_spread": round(total_spread, 2),
        "generic_dispensing_rate": round(gdr * 100, 1),
        "discrepancies": discrepancies,
        "risk_score": min(100, sum(30 if d["severity"] == "critical" else 20 if d["severity"] == "high" else 10 for d in discrepancies)),
        "recommendation": "Immediate independent audit recommended. Multiple high-severity discrepancies detected across rebate reporting, spread pricing, and pharmacy network integrity.",
    }


# ─── Cached singleton ───────────────────────────────────────────────────────────

_claims_cache = None
_custom_claims_loaded = False
_custom_claims_info: Dict[str, Any] = {}

def get_claims() -> List[Dict[str, Any]]:
    global _claims_cache
    if _claims_cache is None:
        _claims_cache = generate_claims(500)
    return _claims_cache

def set_claims_data(claims_list: List[Dict[str, Any]], info: Optional[Dict[str, Any]] = None) -> None:
    """Replace current claims data with uploaded claims."""
    global _claims_cache, _custom_claims_loaded, _custom_claims_info
    _claims_cache = claims_list
    _custom_claims_loaded = True
    _custom_claims_info = info or {}

def reset_claims_data() -> None:
    """Reset claims back to synthetic data."""
    global _claims_cache, _custom_claims_loaded, _custom_claims_info
    _claims_cache = None
    _custom_claims_loaded = False
    _custom_claims_info = {}
    # Force regeneration
    get_claims()

def get_claims_status() -> Dict[str, Any]:
    """Return whether custom or synthetic claims are loaded."""
    global _custom_claims_loaded, _custom_claims_info
    claims = get_claims()
    return {
        "custom_data_loaded": _custom_claims_loaded,
        "claims_count": len(claims),
        **_custom_claims_info,
    }

def get_drugs() -> List[Dict[str, Any]]:
    return DRUGS

def get_pharmacies() -> List[Dict[str, Any]]:
    return PHARMACIES
