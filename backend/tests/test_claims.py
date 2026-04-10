"""
Claims CSV upload — the onboarding step that unlocks the other 20+ modules.

No AI involved; this exercises CSV parsing, validation, and SQLite persistence.
"""


def test_claims_upload_happy_path(client, sample_claims_csv):
    r = client.post(
        "/api/claims/upload",
        files={"file": ("claims.csv", sample_claims_csv, "text/csv")},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["status"] == "success"
    assert "3 claims" in body["message"]

    summary = body["summary"]
    assert summary["total_claims"] == 3
    assert summary["unique_drugs"] == 3  # Atorvastatin, Humira, Metformin
    assert summary["unique_pharmacies"] == 3
    assert summary["total_plan_paid"] > 0
    assert summary["total_rebates"] > 0


def test_claims_status_after_upload(client, sample_claims_csv):
    client.post(
        "/api/claims/upload",
        files={"file": ("claims.csv", sample_claims_csv, "text/csv")},
    )
    r = client.get("/api/claims/status")
    assert r.status_code == 200
    status = r.json()
    assert status["custom_data_loaded"] is True
    assert status["claims_count"] == 3


def test_claims_upload_rejects_non_csv(client):
    r = client.post(
        "/api/claims/upload",
        files={"file": ("claims.xlsx", b"PK\x03\x04", "application/vnd.ms-excel")},
    )
    assert r.status_code == 400
    assert "CSV" in r.json()["detail"]


def test_claims_upload_rejects_missing_columns(client):
    bad_csv = b"claim_id,drug_name\nCLM-1,Atorvastatin\n"
    r = client.post(
        "/api/claims/upload",
        files={"file": ("bad.csv", bad_csv, "text/csv")},
    )
    assert r.status_code == 400
    assert "missing required columns" in r.json()["detail"]


def test_claims_upload_rejects_empty_file(client):
    r = client.post(
        "/api/claims/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert r.status_code == 400


def test_claims_reset(client, sample_claims_csv):
    client.post(
        "/api/claims/upload",
        files={"file": ("claims.csv", sample_claims_csv, "text/csv")},
    )
    r = client.delete("/api/claims/reset")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    # After reset, claims are cleared — no synthetic regeneration.
    # The platform shows empty states until the user uploads real claims.
    assert body["claims_count"] == 0
