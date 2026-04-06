"""Audit letter generator — the second half of the MVP 'wedge' product."""


def test_audit_generate_financial_default(client, mock_ai):
    r = client.post("/api/audit/generate", json={})
    assert r.status_code == 200, r.text

    body = r.json()
    assert body["status"] == "success"
    assert body["audit_type"] == "financial"
    assert "letter" in body
    assert len(body["letter"]) > 100  # real letter, not empty
    assert "DOL" in body["letter"] or "transparency" in body["letter"].lower()

    info = body["audit_type_info"]
    assert info["audit_type"] == "financial"
    assert "AWP discount guarantees vs actual" in info["checklist"]


def test_audit_generate_process_type(client, mock_ai):
    r = client.post(
        "/api/audit/generate",
        json={
            "employer_name": "TestCo",
            "pbm_name": "CVS Caremark",
            "audit_type": "process",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["audit_type"] == "process"
    assert "Formulary compliance" in body["audit_type_info"]["checklist"]


def test_audit_generate_rejects_invalid_type(client, mock_ai):
    r = client.post("/api/audit/generate", json={"audit_type": "nonsense"})
    # Pydantic Literal validation → 422
    assert r.status_code == 422


def test_audit_generate_surfaces_ai_failure_as_503(client, monkeypatch):
    """
    When generate_audit_letter raises, the router must return 503 with a
    clear message instead of silently falling back to a mock letter.
    """
    async def boom(contract_data, findings):
        raise RuntimeError("rate limit exceeded")

    import routers.audit as audit_router
    monkeypatch.setattr(audit_router, "generate_audit_letter", boom)

    r = client.post("/api/audit/generate", json={"audit_type": "financial"})
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert "unavailable" in detail.lower()
    assert "rate limit exceeded" in detail


def test_audit_generate_with_custom_findings(client, mock_ai):
    """Custom findings should bypass the claims → audit_report path."""
    r = client.post(
        "/api/audit/generate",
        json={
            "employer_name": "Custom Corp",
            "pbm_name": "Express Scripts",
            "custom_findings": {
                "spread_exposure": 150000,
                "rebate_leakage": 78000,
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"
