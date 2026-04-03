import logging
logger = logging.getLogger(__name__)
"""
CMS NADAC pricing service.
Primary source: local CSV from data.medicaid.gov (388K rows).
Fallback: per-request API calls for NDCs not in the local dataset.
"""

import csv
import os
import re
import httpx
import time
from typing import Dict, List, Optional, Any

NADAC_API_URL = "https://data.medicaid.gov/resource/4grx-u2cs.json"

# Path to the local NADAC CSV (relative to this file)
_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "cms", "nadac_current.csv"
)

# Lazy-loaded local data: NDC (11-digit str) -> record dict
_local_data: Optional[Dict[str, Dict[str, Any]]] = None

# In-memory cache for API fallback: key -> (timestamp, data)
_cache: Dict[str, tuple] = {}
CACHE_TTL = 3600  # 1 hour


def _ensure_local_data() -> Dict[str, Dict[str, Any]]:
    """Lazy-load the NADAC CSV into a dict keyed by 11-digit NDC string.
    Called once on first access, then cached for the lifetime of the process."""
    global _local_data
    if _local_data is not None:
        return _local_data

    _local_data = {}
    csv_path = os.path.normpath(_CSV_PATH)
    if not os.path.exists(csv_path):
        logger.warning("NADAC CSV not found at %s — local lookup disabled", csv_path)
        return _local_data

    logger.info("Loading NADAC CSV from %s …", csv_path)
    try:
        with open(csv_path, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                ndc = (row.get("ndc") or "").strip()
                if not ndc:
                    continue
                # Keep the latest effective_date per NDC (file is not guaranteed sorted)
                existing = _local_data.get(ndc)
                if existing and existing["effective_date"] >= (row.get("effective_date") or ""):
                    continue
                try:
                    nadac_val = float(row.get("nadac_per_unit") or 0)
                except (ValueError, TypeError):
                    nadac_val = 0.0

                _local_data[ndc] = {
                    "ndc": ndc,
                    "drug_name": (row.get("ndc_description") or "").strip(),
                    "nadac_per_unit": nadac_val,
                    "effective_date": (row.get("effective_date") or "").strip(),
                    "pricing_unit": (row.get("pricing_unit") or "").strip(),
                    "classification_for_rate_setting": (row.get("classification_for_rate_setting") or "").strip(),
                    "otc": (row.get("otc") or "").strip(),
                    "source": "CMS NADAC (local)",
                }
        logger.info("NADAC CSV loaded: %d unique NDCs", len(_local_data))
    except Exception as e:
        logger.error("Failed to load NADAC CSV: %s", e)

    return _local_data


def _cache_get(key: str) -> Optional[Any]:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _cache_set(key: str, data: Any):
    _cache[key] = (time.time(), data)


def _lookup_local(ndc: str) -> Optional[Dict[str, Any]]:
    """Look up a single NDC in the local dataset."""
    data = _ensure_local_data()
    clean = ndc.replace("-", "").strip()
    return data.get(clean)


async def get_nadac_prices(ndc_codes: List[str]) -> List[Dict[str, Any]]:
    """Fetch NADAC prices for a list of NDC codes.
    Tries local CSV first, then in-memory cache, then API fallback."""
    results = []
    need_api: List[str] = []

    for ndc in ndc_codes:
        clean_ndc = ndc.replace("-", "").strip()

        # 1. Try local CSV
        local = _lookup_local(clean_ndc)
        if local:
            results.append(local)
            continue

        # 2. Try API cache
        cached = _cache_get(f"ndc:{clean_ndc}")
        if cached:
            results.append(cached)
            continue

        # 3. Mark for API fetch
        need_api.append(clean_ndc)

    if need_api:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for ndc in need_api:
                    params = {
                        "$where": f"ndc=\"{ndc}\"",
                        "$order": "effective_date DESC",
                        "$limit": 1,
                    }
                    resp = await client.get(NADAC_API_URL, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data:
                            record = {
                                "ndc": ndc,
                                "drug_name": data[0].get("ndc_description", ""),
                                "nadac_per_unit": float(data[0].get("nadac_per_unit", 0)),
                                "effective_date": data[0].get("effective_date", ""),
                                "pricing_unit": data[0].get("pricing_unit", ""),
                                "pharmacy_type_indicator": data[0].get("pharmacy_type_indicator", ""),
                                "otc": data[0].get("otc", ""),
                                "explanation_code": data[0].get("explanation_code", ""),
                                "classification_for_rate_setting": data[0].get("classification_for_rate_setting", ""),
                                "source": "CMS NADAC (API)",
                            }
                            _cache_set(f"ndc:{ndc}", record)
                            results.append(record)
                        else:
                            results.append({
                                "ndc": ndc,
                                "drug_name": "Not found in NADAC",
                                "nadac_per_unit": None,
                                "source": "CMS NADAC",
                                "error": "NDC not found",
                            })
        except Exception as e:
            logger.error(f"NADAC API error: {e}")
            for ndc in need_api:
                if not any(r["ndc"] == ndc for r in results):
                    results.append({
                        "ndc": ndc,
                        "drug_name": "API unavailable",
                        "nadac_per_unit": None,
                        "source": "CMS NADAC",
                        "error": str(e),
                    })

    return results


async def search_drugs(name: str) -> List[Dict[str, Any]]:
    """Search for drugs by name — case-insensitive substring match on local CSV,
    with API fallback if local dataset is empty."""
    data = _ensure_local_data()

    if data:
        needle = name.lower()
        matches = [
            rec for rec in data.values()
            if needle in rec["drug_name"].lower()
        ]
        # Sort by drug name, limit to 20
        matches.sort(key=lambda r: r["drug_name"])
        if matches:
            return matches[:20]

    # Fallback: API search (or if local data empty)
    cache_key = f"search:{name.lower()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            sanitized = re.sub(r"[^a-zA-Z0-9 \-]", "", name)
            params = {
                "$where": f"upper(ndc_description) like '%{sanitized.upper()}%'",
                "$order": "effective_date DESC",
                "$limit": 20,
            }
            resp = await client.get(NADAC_API_URL, params=params)
            if resp.status_code == 200:
                api_data = resp.json()
                results = [
                    {
                        "ndc": item.get("ndc", ""),
                        "drug_name": item.get("ndc_description", ""),
                        "nadac_per_unit": float(item.get("nadac_per_unit", 0)),
                        "effective_date": item.get("effective_date", ""),
                        "pricing_unit": item.get("pricing_unit", ""),
                        "pharmacy_type_indicator": item.get("pharmacy_type_indicator", ""),
                        "source": "CMS NADAC (API)",
                    }
                    for item in api_data
                ]
                _cache_set(cache_key, results)
                return results
    except Exception as e:
        logger.error(f"NADAC search error: {e}")

    return [{"error": "Search unavailable", "query": name}]


async def get_price_by_ndc(ndc: str) -> Dict[str, Any]:
    """Get the latest NADAC price for a single NDC."""
    results = await get_nadac_prices([ndc])
    return results[0] if results else {"ndc": ndc, "error": "Not found"}
