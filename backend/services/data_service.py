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

def _static_compliance_items() -> List[Dict[str, Any]]:
    """
    Static, statute-driven compliance items every self-insured employer
    plan sponsor needs to track. Each item is structured for the
    educational rendering on the frontend — `what_it_is`, `why_it_matters`,
    `when_it_applies`, `who_acts`, `statutory_basis`, `action_items`,
    `educational_summary`. The frontend renders these instead of a stress-
    inducing "URGENT / DUE / UPCOMING" bucket label.
    """
    return [
        {
            "id": "RXDC-ANNUAL",
            "name": "RxDC Prescription Drug Data Collection",
            "category": "Federal — Annual Filing",
            "due_date": "2026-06-01",
            "recurrence": "Annual, due by June 1 covering the prior calendar year",
            "what_it_is": (
                "An annual data submission to CMS describing the plan's "
                "prescription drug spending, rebate revenue, top therapeutic "
                "classes, and impact of rebates on premiums."
            ),
            "why_it_matters": (
                "RxDC is the federal mechanism that surfaces PBM economics "
                "to regulators. Missing or late filings expose the plan "
                "fiduciary to ERISA penalties and forfeit visibility into "
                "what the PBM is doing with the plan's money."
            ),
            "when_it_applies": (
                "Every self-insured group health plan that covered employees "
                "in the prior plan year. The PBM typically files on behalf "
                "of the plan but the fiduciary obligation rests with the "
                "employer."
            ),
            "who_acts": "Plan sponsor (with PBM as data source)",
            "statutory_basis": "CAA 2021 Section 204 — 42 U.S.C. § 300gg-120",
            "action_items": [
                "Confirm with the PBM in writing that they will file RxDC files D1–D8 on the plan's behalf.",
                "Request a copy of the plan-specific D1 and D2 files for the plan sponsor's records before submission.",
                "Cross-check the rebate totals reported on D6 against the PBM's quarterly reconciliation reports.",
                "Retain confirmation of submission for at least 7 years as part of ERISA recordkeeping.",
            ],
            "educational_summary": (
                "RxDC is the single most important federal lever a plan "
                "sponsor has for understanding what the PBM is actually "
                "doing with rebates and pricing. The data flows to CMS but "
                "the plan sponsor can request the same data files for its "
                "own records — that is the entry point to a real audit."
            ),
            "contract_derived": False,
        },
        {
            "id": "GAG-ATTESTATION",
            "name": "Gag Clause Prohibition Compliance Attestation",
            "category": "Federal — Annual Filing",
            "due_date": "2026-12-31",
            "recurrence": "Annual, due by December 31 each year",
            "what_it_is": (
                "An annual attestation submitted to CMS confirming that the "
                "plan's PBM and TPA contracts do not contain gag clauses "
                "preventing disclosure of cost or quality information to "
                "plan participants, plan fiduciaries, or referring providers."
            ),
            "why_it_matters": (
                "Gag clauses are explicitly prohibited by the CAA. A plan "
                "fiduciary that signs a PBM contract containing one — or "
                "fails to attest annually — exposes the company and its "
                "ERISA committee to direct fiduciary breach claims."
            ),
            "when_it_applies": (
                "Every group health plan, self-insured or fully insured, "
                "that contracts with a third-party administrator or PBM."
            ),
            "who_acts": "Plan sponsor (the named plan fiduciary signs)",
            "statutory_basis": "CAA 2021 Section 201 — 42 U.S.C. § 300gg-120(a)",
            "action_items": [
                "Run the ClearScript contract analyzer over the active PBM agreement and check the 'Gag Clauses' finding.",
                "If a clause that arguably restricts cost-data sharing exists, request a written amendment from the PBM removing it.",
                "Have the plan fiduciary submit the attestation through the CMS Health Insurance Oversight System (HIOS).",
                "Document the attestation with a board resolution or ERISA committee minute entry.",
            ],
            "educational_summary": (
                "The gag clause attestation looks like a paperwork exercise "
                "but it is the cleanest enforcement hook the federal "
                "government has against PBMs. Filing it forces the plan "
                "fiduciary to actually look at the contract."
            ),
            "contract_derived": False,
        },
        {
            "id": "DOL-TRANSPARENCY-RULE",
            "name": "DOL Transparency Rule — PBM Disclosure & Audit Rights",
            "category": "Federal — Standing Right",
            "due_date": "2026-01-30",
            "recurrence": "Standing right, effective January 30, 2026",
            "what_it_is": (
                "A final DOL rule under ERISA that grants self-insured "
                "employer plan sponsors unrestricted audit rights over their "
                "PBM, with a ten-business-day PBM response window once an "
                "audit request is delivered."
            ),
            "why_it_matters": (
                "Before this rule, PBMs could effectively block plan-sponsor "
                "audits behind contractual scope limitations. The rule "
                "removes that defense and creates a usable enforcement "
                "deadline for the first time."
            ),
            "when_it_applies": (
                "Any time the plan sponsor delivers a written audit request "
                "to the PBM. The 10-business-day clock starts on receipt."
            ),
            "who_acts": "Plan sponsor initiates; PBM must respond",
            "statutory_basis": "29 CFR 2520.101-2; ERISA § 404(a)(1)",
            "action_items": [
                "Use the ClearScript Audit Letter generator to draft a request citing the rule and the 10-day deadline.",
                "Deliver the request by both certified mail and the PBM's contractually designated electronic method.",
                "Calendar the 10-business-day deadline and document any failure to respond.",
                "If the PBM fails to respond, escalate to ERISA counsel — the failure itself is a fiduciary breach indicator.",
            ],
            "educational_summary": (
                "This rule is not a calendar deadline for the employer — "
                "it is a calendar deadline for the PBM, triggered when the "
                "employer sends an audit letter. It is the most powerful "
                "tool a plan sponsor has gained in a decade."
            ),
            "contract_derived": False,
        },
        {
            "id": "HR7148-DELINKING",
            "name": "HR 7148 — PBM Rebate Delinking Act",
            "category": "Federal — Future Effective Date",
            "due_date": "2028-01-01",
            "recurrence": "One-time effective date; Medicare Part D delinking begins 2028, commercial rolls in through 2029",
            "what_it_is": (
                "Federal legislation signed February 3, 2026 that requires "
                "PBMs to delink their compensation from drug list prices, "
                "mandates 100% rebate passthrough for Medicare Part D, and "
                "extends 'any willing pharmacy' protections."
            ),
            "why_it_matters": (
                "Every PBM contract executed before 2028 will need to be "
                "renegotiated to comply. Plan sponsors that wait until the "
                "effective date will be negotiating from weakness; sponsors "
                "that prepare now can extract concessions in exchange for "
                "early adoption."
            ),
            "when_it_applies": (
                "Medicare Part D arrangements: January 1, 2028. Commercial "
                "self-insured plan arrangements: phased through 2029 per "
                "implementing regulations."
            ),
            "who_acts": "Plan sponsor must renegotiate; PBM must comply",
            "statutory_basis": "HR 7148 (signed Feb 3, 2026), Pub. L. — pending implementing regs",
            "action_items": [
                "Inventory every active PBM contract and identify renewal dates between now and 2028.",
                "For any contract that auto-renews past the effective date, calendar a renegotiation milestone at least 6 months prior.",
                "Use the ClearScript contract analyzer to identify clauses that will be facially non-compliant with delinking and 100% passthrough.",
                "Open a dialogue with your benefits broker about market alternatives in case the incumbent PBM cannot or will not comply.",
            ],
            "educational_summary": (
                "HR 7148 is the single most consequential PBM legislation "
                "in two decades. The 2028 effective date sounds far away "
                "but the negotiation window is right now."
            ),
            "contract_derived": False,
        },
        {
            "id": "ERISA-5500-SCHED-A-C",
            "name": "ERISA Form 5500 — Schedule A & Schedule C Filing",
            "category": "Federal — Annual Filing",
            "due_date": "2026-07-31",
            "recurrence": "Annual, due 7 months after the plan year end (typically July 31 for calendar-year plans)",
            "what_it_is": (
                "The annual ERISA filing that documents service-provider "
                "compensation. Schedule C in particular requires disclosure "
                "of indirect compensation paid to PBMs, which includes "
                "spread pricing and rebate retention amounts."
            ),
            "why_it_matters": (
                "Inaccurate or incomplete Schedule C disclosures are a "
                "common DOL enforcement target. A PBM that claims its "
                "compensation is fully passthrough but actually retains "
                "indirect compensation can expose the plan fiduciary to "
                "personal liability."
            ),
            "when_it_applies": (
                "Every employee benefit plan with 100+ participants files "
                "annually. Smaller plans may qualify for Form 5500-SF."
            ),
            "who_acts": "Plan administrator (typically the employer)",
            "statutory_basis": "ERISA § 103, 104; 29 CFR 2520.103-1",
            "action_items": [
                "Request a written 408(b)(2) disclosure from the PBM including all forms of indirect compensation.",
                "Cross-check the PBM's stated indirect compensation against the rebate and spread findings from ClearScript.",
                "File Form 5500 electronically through EFAST2 by the deadline.",
                "Retain all underlying records for 7 years.",
            ],
            "educational_summary": (
                "Schedule C is where the PBM's hidden compensation has to "
                "show up on paper. If the numbers do not match the plan's "
                "internal data, that is the clearest paper-trail signal "
                "that something is wrong."
            ),
            "contract_derived": False,
        },
        {
            "id": "MENTAL-HEALTH-PARITY-NQTL",
            "name": "Mental Health Parity NQTL Comparative Analysis",
            "category": "Federal — On-Demand Documentation",
            "due_date": "2026-07-01",
            "recurrence": "Documented before any non-quantitative treatment limitation is applied; produced on DOL request",
            "what_it_is": (
                "A written comparative analysis demonstrating that any "
                "non-quantitative treatment limitations applied to mental "
                "health and substance use disorder benefits are no more "
                "stringent than those applied to medical/surgical benefits."
            ),
            "why_it_matters": (
                "DOL has been actively requesting these analyses on audit. "
                "Plans without one face penalties, and the PBM's prior auth "
                "and step therapy programs are typically the source of "
                "parity violations."
            ),
            "when_it_applies": (
                "Continuous obligation. The DOL can request the analysis at "
                "any time and a plan must produce it within 30 days."
            ),
            "who_acts": "Plan sponsor with PBM data",
            "statutory_basis": "MHPAEA — 29 CFR 2590.712; CAA 2021 Section 203",
            "action_items": [
                "Request from the PBM a list of every NQTL applied to MH/SUD drugs (prior auth, step therapy, fail-first, refill limits).",
                "Compare that list to NQTLs applied to medical/surgical drugs in the same therapeutic class.",
                "Document the comparative analysis in writing using the DOL's six-step framework.",
                "Update the analysis annually or whenever the formulary changes materially.",
            ],
            "educational_summary": (
                "Parity is the most technically complex compliance "
                "requirement plan sponsors face, and PBM-administered "
                "programs are the most common source of violations."
            ),
            "contract_derived": False,
        },
    ]


def _derive_contract_deadlines() -> List[Dict[str, Any]]:
    """
    Build compliance items derived from contracts the user has actually
    uploaded — renewal-window milestones, audit-letter deadlines, and so on.

    Returns an empty list if no contracts have been uploaded yet, so the
    Compliance Tracker only shows information the user themselves provided
    rather than guessing.
    """
    try:
        from services.db_service import list_contract_analyses
    except Exception:
        return []

    items: List[Dict[str, Any]] = []
    contracts = list_contract_analyses(limit=20)

    for c in contracts:
        analysis_date_raw = c.get("analysis_date")
        if not analysis_date_raw:
            continue
        try:
            # SQLite datetime('now') returns "YYYY-MM-DD HH:MM:SS" in UTC
            analysis_dt = datetime.strptime(analysis_date_raw, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            try:
                analysis_dt = datetime.fromisoformat(analysis_date_raw)
            except (ValueError, TypeError):
                continue

        filename = c.get("filename") or "Uploaded contract"

        # Item 1: 90-day check-in milestone — when the renegotiation window
        # for an HR 7148 transition typically opens.
        items.append({
            "id": f"CONTRACT-{c['id']}-RENEG-WINDOW",
            "name": f"Begin HR 7148 renegotiation review for {filename}",
            "category": "Contract-Derived — Renegotiation Window",
            "due_date": (analysis_dt + timedelta(days=90)).strftime("%Y-%m-%d"),
            "recurrence": "One-time, 90 days after the contract was first analyzed",
            "what_it_is": (
                "A self-imposed milestone to revisit this contract 90 days "
                "after the initial ClearScript analysis. By that point you "
                "should have decided whether to renegotiate the highest-risk "
                "provisions before the next renewal cycle."
            ),
            "why_it_matters": (
                "The HR 7148 effective dates are fixed and the negotiation "
                "leverage is highest when you raise concerns proactively, "
                "not at the renewal table."
            ),
            "when_it_applies": (
                "Once, 90 days after the first ClearScript analysis of this "
                "specific PBM contract."
            ),
            "who_acts": "Plan sponsor (typically with broker or ERISA counsel)",
            "statutory_basis": "Internal milestone driven by HR 7148 effective dates",
            "action_items": [
                "Review the deal score and top risks from the original ClearScript analysis.",
                "Decide which 2–3 provisions warrant a written amendment request before the next renewal.",
                "Send a formal redline request to the PBM citing the analysis findings.",
                "Document the PBM's response (or non-response) in writing.",
            ],
            "educational_summary": (
                "Contract analysis is only useful if it leads to action. "
                "The 90-day window is when the recommendations from the "
                "initial analysis are still fresh and the PBM still has "
                "time to respond before the next renewal cycle."
            ),
            "contract_derived": True,
            "source_contract_id": c.get("id"),
            "source_contract_filename": filename,
            "source_contract_analysis_date": analysis_date_raw,
        })

        # Item 2: Audit letter response deadline — if the user has already
        # generated an audit letter, the 10-business-day clock from the new
        # DOL transparency rule starts running. We don't know if they sent
        # it, so we treat the analysis date as the proxy.
        # 10 business days ≈ 14 calendar days
        items.append({
            "id": f"CONTRACT-{c['id']}-AUDIT-DEADLINE",
            "name": f"PBM audit-response window for {filename}",
            "category": "Contract-Derived — Audit Window",
            "due_date": (analysis_dt + timedelta(days=14)).strftime("%Y-%m-%d"),
            "recurrence": "One-time, 10 business days after an audit letter is sent",
            "what_it_is": (
                "Under the DOL transparency rule effective January 30, 2026, "
                "a PBM must respond to a plan-sponsor audit request within "
                "ten business days. This item tracks that response window "
                "for the audit letter associated with this contract."
            ),
            "why_it_matters": (
                "Failure to respond within the 10-business-day window is "
                "itself evidence of fiduciary breach and gives the plan "
                "sponsor strong grounds to escalate, terminate, or pursue "
                "regulatory complaint."
            ),
            "when_it_applies": (
                "Triggered when the plan sponsor delivers a written audit "
                "request. The 14 calendar days approximates the 10 business "
                "days the rule allows."
            ),
            "who_acts": "PBM must respond; plan sponsor enforces",
            "statutory_basis": "29 CFR 2520.101-2 (DOL transparency rule)",
            "action_items": [
                "Confirm the audit letter was actually delivered (certified mail recommended).",
                "Calendar the 10-business-day deadline.",
                "Log every interim communication from the PBM during the window.",
                "If the deadline passes without a complete response, escalate immediately to ERISA counsel.",
            ],
            "educational_summary": (
                "The 10-day window is the most concrete enforcement hook "
                "any plan sponsor has gained in years. The clock starts on "
                "delivery — not on the date you want to start counting from."
            ),
            "contract_derived": True,
            "source_contract_id": c.get("id"),
            "source_contract_filename": filename,
            "source_contract_analysis_date": analysis_date_raw,
        })

    return items


def _annotate_deadline(d: Dict[str, Any], today: datetime) -> Dict[str, Any]:
    """
    Add days_until + a neutral, non-stress-inducing time framing.
    Replaces the old "URGENT / DUE / UPCOMING" labels with plain English
    that explains what the date means rather than shouting at the user.
    """
    try:
        dl = datetime.strptime(d["due_date"], "%Y-%m-%d")
    except (ValueError, TypeError):
        d["days_until"] = None
        d["timing_label"] = "Date unavailable"
        d["timing_phase"] = "unknown"
        return d

    days_until = (dl - today).days
    d["days_until"] = days_until

    # Neutral phase categories. The frontend uses these for grouping and
    # color but the language never uses words like "urgent" or "overdue".
    if days_until < 0:
        d["timing_phase"] = "past"
        if days_until == -1:
            d["timing_label"] = "Was due yesterday — action still required"
        else:
            d["timing_label"] = f"Was due {abs(days_until)} days ago — action still required"
    elif days_until == 0:
        d["timing_phase"] = "today"
        d["timing_label"] = "Due today"
    elif days_until == 1:
        d["timing_phase"] = "this_week"
        d["timing_label"] = "Due tomorrow"
    elif days_until <= 7:
        d["timing_phase"] = "this_week"
        d["timing_label"] = f"Due in {days_until} days (this week)"
    elif days_until <= 30:
        d["timing_phase"] = "this_month"
        d["timing_label"] = f"Due in about {round(days_until / 7)} weeks"
    elif days_until <= 90:
        d["timing_phase"] = "next_quarter"
        d["timing_label"] = f"Due in about {round(days_until / 30)} months (next quarter)"
    elif days_until <= 365:
        d["timing_phase"] = "this_year"
        d["timing_label"] = f"Due in about {round(days_until / 30)} months"
    else:
        d["timing_phase"] = "future"
        years = days_until / 365
        if years < 1.5:
            d["timing_label"] = "Due in about a year"
        else:
            d["timing_label"] = f"Due in about {round(years)} years"
    return d


def generate_compliance_deadlines() -> List[Dict[str, Any]]:
    """
    Build the compliance tracker payload.

    Combines:
      1. Static, statute-driven items every plan sponsor needs to track,
         each annotated with rich educational metadata.
      2. Contract-derived items pulled from the contracts the user has
         actually uploaded — renegotiation windows, audit deadlines.

    Sorted by `days_until` ascending so the soonest item is first, but
    the frontend is free to render in calendar or list mode.
    """
    today = datetime.now()
    items = _static_compliance_items() + _derive_contract_deadlines()
    for item in items:
        _annotate_deadline(item, today)

    # Backward-compatible field aliases for older frontend code that still
    # reads `deadline`, `description`, `regulation`, `action_required`.
    for item in items:
        item.setdefault("deadline", item.get("due_date"))
        item.setdefault("description", item.get("what_it_is"))
        item.setdefault("regulation", item.get("statutory_basis"))
        item.setdefault("authority", item.get("who_acts"))
        item.setdefault("action_required", "; ".join(item.get("action_items", [])))

    return sorted(
        items,
        key=lambda x: (x.get("days_until") if x.get("days_until") is not None else 99999),
    )

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


# Representative spend totals for an "illustrative" benchmark plan that
# we use when the user has not uploaded their own claims data. The
# previous implementation used the synthetic 500-claim sample dataset
# (~$432k brand spend, ~$128k specialty spend, ~$450k total) which
# made the dollar-denominated leakage figures look misleadingly small
# — a CFO would see "rebate leakage $13k-$26k" and think the problem
# was rounding error.
#
# These benchmark totals are sized for a typical 1,000-employee
# self-insured employer plan. Sources:
#   - KFF Employer Health Benefits Survey (avg Rx spend per employee
#     for self-insured plans is ~$2,000-2,500/yr in commercial market)
#   - PSG specialty drug share has trended from 25% in 2015 to ~52%
#     in 2024; we use 50% as the midpoint
#   - Generic dispensing rate ~88% of scripts but only ~15% of dollars
#     because brand drugs are more expensive per script
#
# Total plan paid:    $2.5M  (1,000 employees × $2,500/yr Rx spend)
# Brand spend:        $2.1M  (~85% of total — generics are cheap per script)
# Generic spend:      $0.4M  (~15% of total)
# Specialty spend:    $1.25M (~50% of total Rx spend, per PSG)
_BENCHMARK_PLAN_TOTALS = {
    "total_plan_paid": 2_500_000.00,
    "brand_spend":     2_100_000.00,
    "generic_spend":     400_000.00,
    "specialty_spend": 1_250_000.00,
    "claims_count":       28_000,   # ~28 claims/employee/yr × 1,000 employees
    "covered_lives":       1_000,
}


def get_claims_totals() -> Dict[str, Any]:
    """
    Return spend subtotals used by `enrich_contract_analysis` to convert
    percentage-based leakage estimates from the AI into real dollar
    figures the user can act on.

    Two modes:

      - **claims_backed** (preferred): the user has uploaded their own
        claims via /api/claims/upload, so we sum across the real data.
        `custom_data_loaded` is True. This produces dollar figures
        anchored to the user's actual spend.

      - **illustrative** (fallback): no real claims yet, so we return
        the _BENCHMARK_PLAN_TOTALS constants representing a typical
        1,000-employee self-insured plan. `custom_data_loaded` is False
        so the frontend can label the figures as illustrative.

    The previous illustrative path summed across the synthetic 500-claim
    sample dataset (~$450k total spend). That made every dollar figure
    look two orders of magnitude smaller than reality and undermined
    the whole point of the leakage analysis. The benchmark plan totals
    fix that without misrepresenting them as the user's actual data.

    Returns a dict with the four subtotals the leakage model needs:
      - total_plan_paid: denominator for "% of total claims spend"
      - brand_spend:     denominator for "% of brand drug spend"
      - generic_spend:   denominator for "% of generic spend"
      - specialty_spend: denominator for "% of specialty Rx spend"
    """
    global _custom_claims_loaded

    # Illustrative mode: return the benchmark plan totals.
    if not _custom_claims_loaded:
        return {
            "custom_data_loaded": False,
            "claims_count": _BENCHMARK_PLAN_TOTALS["claims_count"],
            "covered_lives": _BENCHMARK_PLAN_TOTALS["covered_lives"],
            "total_plan_paid": _BENCHMARK_PLAN_TOTALS["total_plan_paid"],
            "brand_spend": _BENCHMARK_PLAN_TOTALS["brand_spend"],
            "generic_spend": _BENCHMARK_PLAN_TOTALS["generic_spend"],
            "specialty_spend": _BENCHMARK_PLAN_TOTALS["specialty_spend"],
            "is_benchmark": True,
        }

    # Claims-backed mode: sum across the real uploaded claims dataset.
    claims = get_claims()
    total_plan_paid = 0.0
    brand_spend = 0.0
    generic_spend = 0.0
    specialty_spend = 0.0
    for c in claims:
        try:
            paid = float(c.get("plan_paid", 0) or 0)
        except (TypeError, ValueError):
            paid = 0.0
        total_plan_paid += paid
        if c.get("generic"):
            generic_spend += paid
        else:
            brand_spend += paid
        if (c.get("channel") or "").lower() == "specialty":
            specialty_spend += paid
    return {
        "custom_data_loaded": True,
        "claims_count": len(claims),
        "total_plan_paid": round(total_plan_paid, 2),
        "brand_spend": round(brand_spend, 2),
        "generic_spend": round(generic_spend, 2),
        "specialty_spend": round(specialty_spend, 2),
        "is_benchmark": False,
    }

def get_drugs() -> List[Dict[str, Any]]:
    return DRUGS

def get_pharmacies() -> List[Dict[str, Any]]:
    return PHARMACIES
