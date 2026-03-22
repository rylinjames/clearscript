"""
CMS NADAC API integration for real drug pricing data.
Fetches from https://data.medicaid.gov/resource/4grx-u2cs.json
with in-memory caching.
"""

import httpx
import time
from typing import Dict, List, Optional, Any

NADAC_API_URL = "https://data.medicaid.gov/resource/4grx-u2cs.json"

# In-memory cache: key -> (timestamp, data)
_cache: Dict[str, tuple] = {}
CACHE_TTL = 3600  # 1 hour

def _cache_get(key: str) -> Optional[Any]:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
        del _cache[key]
    return None

def _cache_set(key: str, data: Any):
    _cache[key] = (time.time(), data)


async def get_nadac_prices(ndc_codes: List[str]) -> List[Dict[str, Any]]:
    """Fetch NADAC prices for a list of NDC codes."""
    results = []
    uncached = []

    for ndc in ndc_codes:
        cached = _cache_get(f"ndc:{ndc}")
        if cached:
            results.append(cached)
        else:
            uncached.append(ndc)

    if uncached:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for ndc in uncached:
                    # NADAC uses 11-digit NDC format
                    clean_ndc = ndc.replace("-", "").strip()
                    params = {
                        "$where": f"ndc=\"{clean_ndc}\"",
                        "$order": "effective_date DESC",
                        "$limit": 1,
                    }
                    resp = await client.get(NADAC_API_URL, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data:
                            record = {
                                "ndc": clean_ndc,
                                "drug_name": data[0].get("ndc_description", ""),
                                "nadac_per_unit": float(data[0].get("nadac_per_unit", 0)),
                                "effective_date": data[0].get("effective_date", ""),
                                "pricing_unit": data[0].get("pricing_unit", ""),
                                "pharmacy_type_indicator": data[0].get("pharmacy_type_indicator", ""),
                                "otc": data[0].get("otc", ""),
                                "explanation_code": data[0].get("explanation_code", ""),
                                "classification_for_rate_setting": data[0].get("classification_for_rate_setting", ""),
                                "source": "CMS NADAC",
                            }
                            _cache_set(f"ndc:{clean_ndc}", record)
                            results.append(record)
                        else:
                            results.append({
                                "ndc": clean_ndc,
                                "drug_name": "Not found in NADAC",
                                "nadac_per_unit": None,
                                "source": "CMS NADAC",
                                "error": "NDC not found",
                            })
        except Exception as e:
            print(f"NADAC API error: {e}")
            # Return what we have from cache + error entries for uncached
            for ndc in uncached:
                if not any(r["ndc"] == ndc.replace("-", "") for r in results):
                    results.append({
                        "ndc": ndc.replace("-", ""),
                        "drug_name": "API unavailable",
                        "nadac_per_unit": None,
                        "source": "CMS NADAC",
                        "error": str(e),
                    })

    return results


async def search_drugs(name: str) -> List[Dict[str, Any]]:
    """Search for drugs by name in NADAC database."""
    cache_key = f"search:{name.lower()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            params = {
                "$where": f"upper(ndc_description) like '%{name.upper()}%'",
                "$order": "effective_date DESC",
                "$limit": 20,
            }
            resp = await client.get(NADAC_API_URL, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = [
                    {
                        "ndc": item.get("ndc", ""),
                        "drug_name": item.get("ndc_description", ""),
                        "nadac_per_unit": float(item.get("nadac_per_unit", 0)),
                        "effective_date": item.get("effective_date", ""),
                        "pricing_unit": item.get("pricing_unit", ""),
                        "pharmacy_type_indicator": item.get("pharmacy_type_indicator", ""),
                        "source": "CMS NADAC",
                    }
                    for item in data
                ]
                _cache_set(cache_key, results)
                return results
    except Exception as e:
        print(f"NADAC search error: {e}")

    return [{"error": "Search unavailable", "query": name}]


async def get_price_by_ndc(ndc: str) -> Dict[str, Any]:
    """Get the latest NADAC price for a single NDC."""
    results = await get_nadac_prices([ndc])
    return results[0] if results else {"ndc": ndc, "error": "Not found"}
