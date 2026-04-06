"""Smoke tests for root and health endpoints."""


def test_root_lists_features(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["name"].startswith("ClearScript")
    assert data["version"] == "1.0.0"
    assert isinstance(data["features"], list)
    # Every mounted module should surface here. If this drops, main.py or the
    # feature list in `/` drifted — investigate before shipping.
    assert len(data["features"]) >= 20


def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_openapi_docs_reachable(client):
    """/docs should render the auto-generated Swagger UI without error."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    # Every critical MVP router must appear in the OpenAPI spec.
    paths = spec.get("paths", {})
    assert "/api/contracts/upload" in paths
    assert "/api/audit/generate" in paths
    assert "/api/compliance/deadlines" in paths
    assert "/api/claims/upload" in paths
    assert "/api/disclosure/analyze" in paths
