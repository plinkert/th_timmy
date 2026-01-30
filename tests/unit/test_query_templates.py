"""Unit tests for query_templates (Step 1.2)."""

import pytest

from automation_scripts.playbooks.query_templates import (
    SUPPORTED_TOOLS,
    get_timestamp_substitutions,
    has_placeholders,
    substitute_placeholders,
)


def test_get_timestamp_substitutions_elk_manual():
    """get_timestamp_substitutions for elk manual returns correct values."""
    params = get_timestamp_substitutions("elk", "manual", 7)
    assert "{{timestamp_start}}" in params
    assert "{{timestamp_end}}" in params
    assert "{{days}}" in params
    assert params["{{days}}"] == "7"
    assert "{{time_expr}}" in params
    assert "INTERVAL" in params["{{time_expr}}"] or "7" in params["{{time_expr}}"]


def test_get_timestamp_substitutions_elk_api():
    """get_timestamp_substitutions for elk API returns now-7d style."""
    params = get_timestamp_substitutions("elk", "API", 7)
    assert params["{{days}}"] == "7"
    assert "now-7d" in params["{{time_expr}}"] or "7" in params["{{time_expr}}"]


def test_get_timestamp_substitutions_ms_defender_manual():
    """get_timestamp_substitutions for ms_defender manual returns ago(7d)."""
    params = get_timestamp_substitutions("ms_defender", "manual", 7)
    assert params["{{days}}"] == "7"
    assert "ago(7d)" in params["{{time_expr}}"]


def test_get_timestamp_substitutions_ms_defender_api():
    """get_timestamp_substitutions for ms_defender API returns ago format."""
    params = get_timestamp_substitutions("ms_defender", "API", 14)
    assert params["{{days}}"] == "14"
    assert "ago(14d)" in params["{{time_expr}}"]


def test_get_timestamp_substitutions_unsupported_tool():
    """Unsupported tool raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        get_timestamp_substitutions("splunk", "manual", 7)
    assert "Unsupported" in str(exc_info.value) or "splunk" in str(exc_info.value)


def test_get_timestamp_substitutions_invalid_mode():
    """Invalid mode raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        get_timestamp_substitutions("elk", "invalid", 7)
    assert "manual" in str(exc_info.value) or "API" in str(exc_info.value)


def test_substitute_placeholders():
    """substitute_placeholders replaces all placeholders."""
    content = "SELECT * WHERE ts >= {{timestamp_start}} AND ts <= {{timestamp_end}}"
    params = {
        "{{timestamp_start}}": "2025-01-01T00:00:00Z",
        "{{timestamp_end}}": "2025-01-07T23:59:59Z",
    }
    result = substitute_placeholders(content, params)
    assert "{{timestamp_start}}" not in result
    assert "{{timestamp_end}}" not in result
    assert "2025-01-01T00:00:00Z" in result
    assert "2025-01-07T23:59:59Z" in result


def test_substitute_placeholders_days():
    """substitute_placeholders replaces {{days}}."""
    content = "WHERE timestamp >= NOW() - INTERVAL '{{days}} days'"
    params = {"{{days}}": "7"}
    result = substitute_placeholders(content, params)
    assert "{{days}}" not in result
    assert "7" in result


def test_substitute_placeholders_no_placeholders():
    """substitute_placeholders leaves content unchanged when no placeholders."""
    content = "SELECT * FROM events WHERE timestamp > ago(7d)"
    params = {"{{timestamp_start}}": "2025-01-01"}
    result = substitute_placeholders(content, params)
    assert result == content


def test_has_placeholders_true():
    """has_placeholders returns True when placeholders present."""
    assert has_placeholders("SELECT * WHERE ts >= {{timestamp_start}}") is True
    assert has_placeholders("{{days}} days ago") is True


def test_has_placeholders_false():
    """has_placeholders returns False when no placeholders."""
    assert has_placeholders("SELECT * FROM events WHERE timestamp > ago(7d)") is False
    assert has_placeholders("now-7d") is False


def test_supported_tools():
    """SUPPORTED_TOOLS contains elk and ms_defender."""
    assert "elk" in SUPPORTED_TOOLS
    assert "ms_defender" in SUPPORTED_TOOLS
