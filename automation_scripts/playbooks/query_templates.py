"""
Query templates – placeholder mapping and substitution for query generation.

Defines timestamp formats per tool (elk, ms_defender) and mode (manual, API).
Used by query_generator when playbooks contain {{timestamp_start}}, {{timestamp_end}}, {{days}}.
Current playbooks use relative time (ago(7d), now-7d); placeholders prepare for future migration.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, Optional

SUPPORTED_TOOLS = ["elk", "ms_defender"]

# Format patterns: {tool: {manual: str, api: str}} – use {{days}} for time range
TIMESTAMP_FORMATS = {
    "elk": {
        "manual": "NOW() - INTERVAL '{{days}} days'",
        "api": "now-{{days}}d",
    },
    "ms_defender": {
        "manual": "ago({{days}}d)",
        "api": "ago({{days}}d)",
    },
}


def get_timestamp_substitutions(
    tool: str,
    mode: str,
    time_range_days: int = 7,
) -> Dict[str, str]:
    """
    Return placeholder substitutions for timestamp_start, timestamp_end, days.

    Args:
        tool: elk or ms_defender
        mode: manual or API
        time_range_days: Number of days for time range (default 7)

    Returns:
        Dict with keys {{timestamp_start}}, {{timestamp_end}}, {{days}} and values
        in format appropriate for the tool.

    Raises:
        ValueError: If tool not in SUPPORTED_TOOLS or mode not in (manual, API)
    """
    if tool not in SUPPORTED_TOOLS:
        raise ValueError(f"Unsupported tool: {tool}. Supported: {SUPPORTED_TOOLS}")
    mode_lower = mode.lower()
    if mode_lower not in ("manual", "api"):
        raise ValueError(f"Mode must be 'manual' or 'API', got: {mode}")

    end = datetime.utcnow()
    start = end - timedelta(days=time_range_days)
    ts_start = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_end = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    formats = TIMESTAMP_FORMATS.get(tool, {})
    fmt = formats.get(mode_lower, formats.get("manual", "ago({{days}}d)"))
    time_expr = fmt.replace("{{days}}", str(time_range_days))

    return {
        "{{timestamp_start}}": ts_start,
        "{{timestamp_end}}": ts_end,
        "{{days}}": str(time_range_days),
        "{{time_expr}}": time_expr,
    }


def substitute_placeholders(content: str, params: Dict[str, str]) -> str:
    """
    Replace placeholders in content with values from params.

    Args:
        content: Query string possibly containing {{placeholder}}
        params: Dict mapping placeholder names (with braces) to values

    Returns:
        Content with all placeholders replaced. Unknown placeholders left as-is.
    """
    result = content
    for key, value in params.items():
        result = result.replace(key, value)
    return result


def has_placeholders(content: str) -> bool:
    """Check if content contains any {{placeholder}} patterns."""
    return bool(re.search(r"\{\{[a-zA-Z0-9_]+\}\}", content))
