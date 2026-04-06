"""
Contract upload flow — the #1 MVP feature.

These tests are the deploy gate. If they fail, do not ship.
"""
import io


def test_contract_upload_txt(client, mock_ai, sample_contract_text):
    r = client.post(
        "/api/contracts/upload",
        files={"file": ("sample.txt", sample_contract_text, "text/plain")},
    )
    assert r.status_code == 200, r.text

    body = r.json()
    assert body["status"] == "success"
    assert body["filename"] == "sample.txt"
    assert body["file_size"] == len(sample_contract_text)
    assert body["extracted_text_length"] >= 50
    assert body["pdf_parsed"] is False  # txt file, not PDF

    # The core gate: weighted_assessment.deal_score must be populated.
    # This is what the dashboard reads at main.py:190.
    analysis = body["analysis"]
    assert "weighted_assessment" in analysis
    assert analysis["weighted_assessment"]["deal_score"] is not None
    assert isinstance(analysis["weighted_assessment"]["deal_score"], (int, float))

    # Audit rights benchmark should run (real code path, not mocked).
    assert "audit_rights_benchmark" in body
    assert "score" in body["audit_rights_benchmark"]


def test_contract_upload_rejects_empty_filename(client, mock_ai):
    r = client.post(
        "/api/contracts/upload",
        files={"file": ("", b"some bytes", "text/plain")},
    )
    # FastAPI/Starlette treats empty filename specially — either 400 from the
    # endpoint or 422 from request validation is acceptable.
    assert r.status_code in (400, 422)


def test_contract_upload_rejects_bad_extension(client, mock_ai):
    r = client.post(
        "/api/contracts/upload",
        files={"file": ("virus.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert r.status_code == 400
    assert "Unsupported" in r.json()["detail"]


def test_contract_upload_rejects_oversize(client, mock_ai):
    # 51MB — one over the MAX_FILE_SIZE = 50MB limit.
    big = b"x" * (51 * 1024 * 1024)
    r = client.post(
        "/api/contracts/upload",
        files={"file": ("huge.txt", big, "text/plain")},
    )
    assert r.status_code == 400
    assert "too large" in r.json()["detail"].lower()


def test_contract_upload_surfaces_ai_failure_as_503(client, monkeypatch, sample_contract_text):
    """
    When the AI pipeline raises, the router must translate the failure into
    HTTP 503 with a clear detail message — NOT silently serve mock data.

    Regression for the mock-fallback deletion in services/ai_service.py.
    """
    async def boom(text):
        raise RuntimeError("OpenAI API key invalid")

    import routers.contracts as contracts_router
    monkeypatch.setattr(contracts_router, "run_contract_pipeline", boom)

    r = client.post(
        "/api/contracts/upload",
        files={"file": ("real.txt", sample_contract_text, "text/plain")},
    )
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert "unavailable" in detail.lower()
    assert "OpenAI API key invalid" in detail


def test_contract_upload_rejects_short_text(client, mock_ai):
    """
    If extracted text is < 50 chars, the router used to silently substitute
    built-in demo contract text and return a fake analysis. That hid real
    failures (e.g. scanned PDFs with no OCR) as successes. It now returns
    422 with a clear message telling the user why the upload didn't work.
    """
    r = client.post(
        "/api/contracts/upload",
        files={"file": ("tiny.txt", b"hi", "text/plain")},
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "meaningful text" in detail
    assert "OCR" in detail  # guide the user toward the actual limitation
