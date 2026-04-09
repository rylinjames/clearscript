"""
Unit tests for the lower-level helpers in services/ai_service.py.

These don't hit OpenAI — they exercise pure-Python parsing helpers
that the AI call path depends on.
"""
import json
from datetime import date, datetime, timedelta

import pytest

from services.ai_service import _extract_first_json_object, _attach_critical_dates


def test_extract_clean_json_object():
    src = '{"deal_score": 5, "risk_level": "high"}'
    out = _extract_first_json_object(src)
    parsed = json.loads(out)
    assert parsed["deal_score"] == 5
    assert parsed["risk_level"] == "high"


def test_extract_with_leading_whitespace():
    src = '   \n\n{"foo": 1}'
    parsed = json.loads(_extract_first_json_object(src))
    assert parsed["foo"] == 1


def test_extract_with_trailing_content_extra_object():
    """
    The exact production bug: gpt-5 returns a valid JSON object followed
    by a newline and a second object (or commentary). Plain json.loads
    raises 'Extra data: line 2 column 1 (char N)'. _extract_first_json_object
    must isolate the first object and silently drop everything after.
    """
    src = '{"deal_score": 5}\n{"some_other_thing": "ignored"}'
    parsed = json.loads(_extract_first_json_object(src))
    assert parsed == {"deal_score": 5}


def test_extract_with_trailing_commentary():
    src = '{"a": 1, "b": 2}\n\nThat concludes the analysis.'
    parsed = json.loads(_extract_first_json_object(src))
    assert parsed == {"a": 1, "b": 2}


def test_extract_with_leading_preamble():
    src = 'Here is your contract analysis:\n\n{"score": 99}'
    parsed = json.loads(_extract_first_json_object(src))
    assert parsed == {"score": 99}


def test_extract_with_markdown_fences():
    src = '```json\n{"x": "y"}\n```'
    parsed = json.loads(_extract_first_json_object(src))
    assert parsed == {"x": "y"}


def test_extract_with_markdown_fences_and_trailing():
    src = '```json\n{"x": "y"}\n```\n\nDone.'
    parsed = json.loads(_extract_first_json_object(src))
    assert parsed == {"x": "y"}


def test_extract_nested_object():
    src = '{"outer": {"inner": [1, 2, 3]}, "k": null}'
    parsed = json.loads(_extract_first_json_object(src))
    assert parsed["outer"]["inner"] == [1, 2, 3]
    assert parsed["k"] is None


def test_extract_with_unicode():
    src = '{"em_dash": "—", "bullet": "•"}\n'
    parsed = json.loads(_extract_first_json_object(src))
    assert parsed["em_dash"] == "—"
    assert parsed["bullet"] == "•"


def test_extract_raises_on_no_json():
    with pytest.raises(ValueError, match="No JSON object"):
        _extract_first_json_object("just plain text with no braces anywhere")


def test_extract_raises_on_empty():
    with pytest.raises(ValueError, match="Empty response"):
        _extract_first_json_object("")


def test_extract_raises_on_truncated_json():
    """A genuinely malformed response should raise with a helpful snippet."""
    with pytest.raises(ValueError, match="Could not parse JSON"):
        _extract_first_json_object('{"deal_score": 5, "risk_level":')


# ─── _attach_critical_dates ────────────────────────────────────────────────


def test_critical_dates_full_data():
    """Standard case: AI extracted all fields, helper computes derived dates."""
    today = date.today()
    term_end = today + timedelta(days=730)  # 2 years from today
    analysis = {
        "contract_identification": {
            "plan_sponsor_name": "Acme Corp",
            "pbm_name": "PharmaFirst PBM",
            "effective_date": "2024-01-01",
            "initial_term_months": 36,
            "current_term_end_date": term_end.isoformat(),
            "termination_notice_days": 180,
        }
    }
    _attach_critical_dates(analysis)
    cid = analysis["contract_identification"]
    # Notice deadline = term end - 180 days
    expected_notice = term_end - timedelta(days=180)
    assert cid["notice_deadline_date"] == expected_notice.isoformat()
    assert cid["days_until_term_end"] == 730
    assert cid["days_until_notice_deadline"] == 730 - 180
    # RFP recommended start = notice deadline - 60 days
    expected_rfp = expected_notice - timedelta(days=60)
    assert cid["rfp_start_recommended_date"] == expected_rfp.isoformat()
    assert cid["days_until_rfp_start"] == 730 - 180 - 60


def test_critical_dates_derives_term_end_from_effective_plus_months():
    """If AI didn't supply current_term_end, derive it from effective_date + initial_term_months."""
    analysis = {
        "contract_identification": {
            "effective_date": "2024-01-01",
            "initial_term_months": 36,
            "termination_notice_days": 180,
            # current_term_end_date deliberately omitted
        }
    }
    _attach_critical_dates(analysis)
    cid = analysis["contract_identification"]
    # 36 months × 30.4375 days/month ≈ 1095.75 → 1096 days
    derived = date(2024, 1, 1) + timedelta(days=1096)
    assert cid["current_term_end_date"] == derived.isoformat()
    assert "notice_deadline_date" in cid


def test_critical_dates_handles_missing_data_gracefully():
    """No contract_identification block at all → no-op, no exception."""
    analysis = {}
    _attach_critical_dates(analysis)
    assert "contract_identification" not in analysis


def test_critical_dates_handles_empty_block():
    """Empty contract_identification → fields stay empty, no exception."""
    analysis = {"contract_identification": {}}
    _attach_critical_dates(analysis)
    cid = analysis["contract_identification"]
    assert "notice_deadline_date" not in cid
    assert "days_until_term_end" not in cid


def test_critical_dates_handles_malformed_dates():
    """Garbage date strings → no exception, no derived fields."""
    analysis = {
        "contract_identification": {
            "effective_date": "garbage",
            "current_term_end_date": "also garbage",
            "termination_notice_days": "not a number",
        }
    }
    _attach_critical_dates(analysis)
    cid = analysis["contract_identification"]
    assert "notice_deadline_date" not in cid


def test_critical_dates_zero_notice_days_skips_deadline():
    """If termination_notice_days is missing or zero, skip notice deadline computation
    but still compute days_until_term_end."""
    today = date.today()
    term_end = today + timedelta(days=365)
    analysis = {
        "contract_identification": {
            "current_term_end_date": term_end.isoformat(),
            # termination_notice_days deliberately omitted
        }
    }
    _attach_critical_dates(analysis)
    cid = analysis["contract_identification"]
    assert cid["days_until_term_end"] == 365
    assert "notice_deadline_date" not in cid


def test_critical_dates_passed_deadline_negative_days():
    """If the notice deadline is already in the past, days_until_notice_deadline goes negative."""
    today = date.today()
    term_end = today + timedelta(days=30)  # 30 days from today
    analysis = {
        "contract_identification": {
            "current_term_end_date": term_end.isoformat(),
            "termination_notice_days": 180,  # > 30 days, so deadline already passed
        }
    }
    _attach_critical_dates(analysis)
    cid = analysis["contract_identification"]
    # Notice deadline = today + 30 - 180 = today - 150 days
    assert cid["days_until_notice_deadline"] == 30 - 180  # negative
    assert cid["days_until_notice_deadline"] < 0
