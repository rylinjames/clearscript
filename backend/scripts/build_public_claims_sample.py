#!/usr/bin/env python3
"""
Build a ClearScript-compatible public claims sample from the official CMS
DE-SynPUF Prescription Drug Events sample.

Source:
https://downloads.cms.gov/files/DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_18.zip

This converts event-level public data into the CSV schema expected by the
claims uploader. Some fields required by ClearScript are not present in the
CMS file (for example pharmacy reimbursement, AWP, NADAC, rebate amount, and
pharmacy identifiers). Those fields are derived deterministically for demo and
benchmark use and should not be presented as raw CMS values.
"""

from __future__ import annotations

import csv
import hashlib
import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import clear_claims, save_claims
from routers.claims_upload import _csv_row_to_claim

SOURCE_URL = "https://downloads.cms.gov/files/DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_18.zip"
ZIP_PATH = Path("/Users/romirjain/Desktop/building projects/pbm/tmp_public_claims/de_pde_sample18.zip")
CSV_IN_ZIP = "DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_18.csv"
OUTPUT_DIR = Path("/Users/romirjain/Desktop/building projects/pbm/clearscript/backend/data/public_claims")
OUTPUT_CSV = OUTPUT_DIR / "cms_desynpuf_pde_sample18_clearscript.csv"
OUTPUT_MD = OUTPUT_DIR / "cms_desynpuf_pde_sample18_clearscript.md"
SAMPLE_SIZE = 1500

FIELDNAMES = [
    "claim_id", "drug_name", "ndc", "quantity", "days_supply",
    "date_filled", "channel", "pharmacy_name", "pharmacy_npi",
    "pharmacy_zip", "plan_paid", "pharmacy_reimbursed", "awp",
    "nadac_price", "rebate_amount", "formulary_tier",
]


def _stable_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16)


def _parse_date(raw: str) -> str:
    return datetime.strptime(raw, "%Y%m%d").strftime("%Y-%m-%d")


def _float(raw: str) -> float:
    return float(raw or 0)


def _choose_channel(total_rx_cost: float, days_supply: int, unit_cost: float) -> str:
    if total_rx_cost >= 1200 or unit_cost >= 75:
        return "specialty"
    if days_supply >= 84:
        return "mail"
    return "retail"


def _is_generic(total_rx_cost: float, unit_cost: float, days_supply: int) -> bool:
    return unit_cost <= 6 and total_rx_cost <= 75 and days_supply <= 34


def _formulary_tier(is_generic: bool, total_rx_cost: float, channel: str) -> int:
    if is_generic and total_rx_cost <= 20:
        return 1
    if is_generic:
        return 2
    if channel == "specialty" or total_rx_cost >= 1200:
        return 5
    if total_rx_cost >= 250:
        return 4
    return 3


def _convert_row(row: dict[str, str]) -> dict[str, str]:
    claim_id = row["PDE_ID"]
    member_id = row["DESYNPUF_ID"]
    ndc = row["PROD_SRVC_ID"].zfill(11)
    quantity = max(int(float(row["QTY_DSPNSD_NUM"] or 0)), 1)
    days_supply = max(int(float(row["DAYS_SUPLY_NUM"] or 0)), 30)
    patient_pay = _float(row["PTNT_PAY_AMT"])
    total_rx_cost = max(_float(row["TOT_RX_CST_AMT"]), patient_pay)
    plan_paid = round(max(total_rx_cost - patient_pay, total_rx_cost * 0.75), 2)
    unit_cost = total_rx_cost / quantity if quantity else total_rx_cost
    channel = _choose_channel(total_rx_cost, days_supply, unit_cost)
    generic = _is_generic(total_rx_cost, unit_cost, days_supply)
    tier = _formulary_tier(generic, total_rx_cost, channel)

    reimbursement_factor = {"retail": 0.96, "mail": 0.93, "specialty": 0.89}[channel]
    pharmacy_reimbursed = round(plan_paid * reimbursement_factor, 2)
    awp_factor = {"retail": 1.18, "mail": 1.16, "specialty": 1.14}[channel]
    awp = round(plan_paid * awp_factor, 2)
    nadac_factor = 0.84 if generic else 0.78 if channel != "specialty" else 0.74
    nadac_price = round(pharmacy_reimbursed * nadac_factor, 2)
    rebate_rate = 0.0 if generic else 0.12 if tier == 3 else 0.18 if tier == 4 else 0.24
    rebate_amount = round(plan_paid * rebate_rate, 2)

    stable = _stable_int(f"{member_id}:{claim_id}:{ndc}")
    pharmacy_num = stable % 40
    npi = str(10_000_000_000 + (stable % 899_999_999))
    zip_code = str(10000 + (stable % 89999)).zfill(5)

    return {
        "claim_id": claim_id,
        "drug_name": f"NDC {ndc}",
        "ndc": ndc,
        "quantity": str(quantity),
        "days_supply": str(days_supply),
        "date_filled": _parse_date(row["SRVC_DT"]),
        "channel": channel,
        "pharmacy_name": f"Public Sample Pharmacy {pharmacy_num:02d}",
        "pharmacy_npi": npi[:10],
        "pharmacy_zip": zip_code,
        "plan_paid": f"{plan_paid:.2f}",
        "pharmacy_reimbursed": f"{pharmacy_reimbursed:.2f}",
        "awp": f"{awp:.2f}",
        "nadac_price": f"{nadac_price:.2f}",
        "rebate_amount": f"{rebate_amount:.2f}",
        "formulary_tier": str(tier),
    }


def main() -> None:
    if not ZIP_PATH.exists():
        raise SystemExit(f"Missing source zip: {ZIP_PATH}\nDownload from: {SOURCE_URL}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    converted_rows: list[dict[str, str]] = []

    with zipfile.ZipFile(ZIP_PATH) as zf:
        with zf.open(CSV_IN_ZIP) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8")
            reader = csv.DictReader(text)
            for row in reader:
                try:
                    converted_rows.append(_convert_row(row))
                except Exception:
                    continue
                if len(converted_rows) >= SAMPLE_SIZE:
                    break

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(converted_rows)

    claims = [_csv_row_to_claim(row, index + 1) for index, row in enumerate(converted_rows)]
    clear_claims()
    save_claims(OUTPUT_CSV.name, claims)

    total_plan_paid = round(sum(float(r["plan_paid"]) for r in converted_rows), 2)
    total_rebates = round(sum(float(r["rebate_amount"]) for r in converted_rows), 2)
    total_spread = round(sum(float(r["plan_paid"]) - float(r["pharmacy_reimbursed"]) for r in converted_rows), 2)

    OUTPUT_MD.write_text(
        "\n".join(
            [
                "# CMS DE-SynPUF PDE Public Claims Sample",
                "",
                f"- Source: {SOURCE_URL}",
                f"- Source file: `{CSV_IN_ZIP}`",
                f"- Converted sample rows: {len(converted_rows)}",
                f"- Output CSV: `{OUTPUT_CSV.name}`",
                "",
                "## Notes",
                "",
                "- Base event rows come from the official CMS DE-SynPUF Prescription Drug Events public use file.",
                "- `plan_paid` is derived from total Rx cost minus patient pay where possible.",
                "- `pharmacy_reimbursed`, `awp`, `nadac_price`, `rebate_amount`, pharmacy identifiers, and channel labels are deterministic demo fields derived during conversion because the CMS source does not provide them directly.",
                "- This file is suitable for ClearScript demos, benchmarking, and claims-backed UI testing. It is not raw adjudicated employer claims data.",
                "",
                "## Summary",
                "",
                f"- Total plan paid: ${total_plan_paid:,.2f}",
                f"- Total rebates: ${total_rebates:,.2f}",
                f"- Total modeled spread: ${total_spread:,.2f}",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_CSV}")
    print(f"Wrote {OUTPUT_MD}")
    print(f"Persisted {len(claims)} claims to SQLite as {OUTPUT_CSV.name}")


if __name__ == "__main__":
    main()
