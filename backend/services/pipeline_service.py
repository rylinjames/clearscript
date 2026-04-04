import logging
logger = logging.getLogger(__name__)
"""
RocketRide Pipeline Service for ClearScript.
Runs PBM contract analysis through a multi-stage AI pipeline:
  Contract Input → Clause Extraction (Gemini) → Compliance Scoring (Gemini) → Output

Falls back to direct Gemini API calls if RocketRide engine is unavailable.
"""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

ROCKETRIDE_URI = os.getenv("ROCKETRIDE_URI", "ws://localhost:5565")
PIPELINE_FILE = str(Path(__file__).resolve().parent.parent.parent / "contract-analysis.pipe")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


async def run_contract_pipeline(contract_text: str) -> dict:
    """
    Run the contract analysis pipeline via RocketRide.
    Falls back to direct Gemini if RocketRide is unavailable.
    """
    try:
        from rocketride import RocketRide

        # Load pipeline config and substitute env vars
        with open(PIPELINE_FILE, "r") as f:
            pipeline_config = json.load(f)

        # Substitute GEMINI_API_KEY in component configs
        for component in pipeline_config.get("components", []):
            config = component.get("config", {})
            for key, val in config.items():
                if isinstance(val, str) and "${GEMINI_API_KEY}" in val:
                    config[key] = val.replace("${GEMINI_API_KEY}", GEMINI_API_KEY)

        async with RocketRide(uri=ROCKETRIDE_URI) as client:
            # Start the pipeline
            result = await client.use(pipeline=pipeline_config)
            token = result.get("token")

            if not token:
                raise RuntimeError("No token returned from pipeline")

            # Send the contract text to the pipeline
            response = await client.send(token, contract_text[:12000])

            # The response should contain the analysis
            from services.ai_service import enrich_contract_analysis
            if isinstance(response, dict):
                return enrich_contract_analysis(response)
            elif isinstance(response, str):
                return enrich_contract_analysis(json.loads(response))
            else:
                raise RuntimeError(f"Unexpected response type: {type(response)}")

    except Exception as e:
        logger.warning(f"RocketRide pipeline failed ({e}), falling back to direct Gemini API")
        # Fall back to direct Gemini call
        from services.ai_service import analyze_contract
        return await analyze_contract(contract_text)

async def get_pipeline_status() -> dict:
    """Check if RocketRide engine is available."""
    try:
        from rocketride import RocketRide
        async with RocketRide(uri=ROCKETRIDE_URI) as client:
            services = await client.get_services()
            return {
                "rocketride_available": True,
                "engine_uri": ROCKETRIDE_URI,
                "pipeline_file": PIPELINE_FILE,
                "services": len(services) if services else 0,
            }
    except Exception as e:
        return {
            "rocketride_available": False,
            "engine_uri": ROCKETRIDE_URI,
            "error": str(e),
            "fallback": "direct Gemini API",
        }
