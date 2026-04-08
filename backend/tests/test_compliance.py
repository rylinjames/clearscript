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

    # Sum of legacy buckets should equal total.
    bucketed = summary["overdue"] + summary["imminent"] + summary["upcoming"] + summary["scheduled"]
    assert bucketed == summary["total_deadlines"]

    # Every deadline carries the new rich-format fields.
    valid_phases = {"past", "today", "this_week", "this_month", "next_quarter", "this_year", "future", "unknown"}
    for deadline in data["deadlines"]:
        assert "id" in deadline
        assert "name" in deadline
        assert "what_it_is" in deadline
        assert "why_it_matters" in deadline
        assert "when_it_applies" in deadline
        assert "who_acts" in deadline
        assert "statutory_basis" in deadline
        assert "action_items" in deadline
        assert isinstance(deadline["action_items"], list)
        assert "timing_phase" in deadline
        assert deadline["timing_phase"] in valid_phases
        assert "timing_label" in deadline
        # Backward-compat aliases for legacy clients still present
        assert "deadline" in deadline
        assert "description" in deadline
