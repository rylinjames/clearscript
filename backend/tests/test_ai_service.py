"""
Unit tests for the lower-level helpers in services/ai_service.py.

These don't hit OpenAI — they exercise pure-Python parsing helpers
that the AI call path depends on.
"""
import json
import pytest

from services.ai_service import _extract_first_json_object


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
