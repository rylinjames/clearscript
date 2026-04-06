"""
Compliance deadline tracker — no AI, pure data logic. This test acts as the
'is the server alive and returning sane shapes' canary.
"""


def test_compliance_deadlines_shape(client):
    r = client.get("/api/compliance/deadlines")
    assert r.status_code == 200
    data = r.json()

    assert data["status"] == "success"
    assert "summary" in data
    assert "deadlines" in data

    summary = data["summary"]
    for key in ("total_deadlines", "overdue", "imminent", "upcoming", "scheduled"):
        assert key in summary
        assert isinstance(summary[key], int)

    # Sum of buckets should equal total.
    bucketed = summary["overdue"] + summary["imminent"] + summary["upcoming"] + summary["scheduled"]
    assert bucketed == summary["total_deadlines"]

    # Each deadline should have a status that matches one of the buckets.
    valid_statuses = {"overdue", "imminent", "upcoming", "scheduled"}
    for deadline in data["deadlines"]:
        assert deadline["status"] in valid_statuses
