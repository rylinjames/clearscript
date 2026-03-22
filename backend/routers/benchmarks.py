"""Feature 9: Benchmarking Dashboard"""

from fastapi import APIRouter
from services.data_service import generate_benchmarks

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])


@router.get("/data")
async def benchmark_data():
    """
    Returns anonymized peer comparison data.
    Metrics: unit cost per script, rebate passthrough %,
    specialty drug spend %, generic dispensing rate.
    Shows employer's rank vs peers.
    """
    result = generate_benchmarks()

    return {
        "status": "success",
        "benchmarks": result,
    }
