"""Benchmarking endpoints — pure data reads, no AI."""


def test_benchmarks_data(client):
    r = client.get("/api/benchmarks/data")
    # Route exists per main.py; should return 200 with data regardless of
    # whether any claims have been uploaded (synthetic fallback).
    assert r.status_code == 200
    assert isinstance(r.json(), (dict, list))


def test_benchmarks_public_data(client):
    r = client.get("/api/benchmarks/public-data")
    assert r.status_code == 200
    assert isinstance(r.json(), (dict, list))


def test_dashboard_stats(client):
    r = client.get("/api/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    # These are the exact keys the frontend dashboard reads.
    for key in ("contracts_parsed", "contracts", "latest_analysis"):
        assert key in data
    assert isinstance(data["contracts"], list)


def test_dashboard_stats_survives_bad_analysis_shape(client, mock_ai, sample_contract_text):
    """
    Regression: /api/dashboard/stats used to 500 with
        'str' object has no attribute 'get'
    when `enrich_contract_analysis` received an unexpected shape. The endpoint
    now wraps that call in try/except and falls back to the raw analysis.

    We exercise the crash path by uploading a contract (which persists to the
    DB via save_contract_analysis), then hitting the dashboard. Even if
    enrichment explodes internally, the endpoint must return 200.
    """
    # Seed the DB with an analysis
    upload = client.post(
        "/api/contracts/upload",
        files={"file": ("seed.txt", sample_contract_text, "text/plain")},
    )
    assert upload.status_code == 200

    r = client.get("/api/dashboard/stats")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["contracts_parsed"] >= 1
    assert data["latest_analysis"] is not None
