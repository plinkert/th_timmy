"""
Playbook Engine (Step 2.1) – deterministic analysis of DataPackage according to playbook rules.

API: run_analysis(data_package, playbook_metadata, analysis_rules=None) -> List[Finding].
Uses analysis_rules from metadata (e.g. type: threshold, event_type, threshold, window_minutes, group_by)
and optional field_mapping to map source fields to the canonical model.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import yaml

if TYPE_CHECKING:
    from automation_scripts.data_package import DataPackage

logger = logging.getLogger(__name__)

# --- Canonical field names (data model for analysis) ---
CANONICAL_EVENT_TIME = "event_time"
CANONICAL_SRC_IP = "src_ip"
CANONICAL_DST_IP = "dst_ip"
CANONICAL_USER = "user"
CANONICAL_HOST = "host"
CANONICAL_EVENT_TYPE = "event_type"
CANONICAL_SEVERITY = "severity"

# Default mapping: canonical_key -> list of source keys (nested with dot)
DEFAULT_FIELD_MAPPING: Dict[str, List[str]] = {
    CANONICAL_EVENT_TIME: ["@timestamp", "TimeGenerated", "event_time", "timestamp"],
    CANONICAL_SRC_IP: ["source.ip", "client_ip", "SrcIp", "src_ip", "SourceIp"],
    CANONICAL_DST_IP: ["destination.ip", "destination_ip", "dst_ip", "DestIp"],
    CANONICAL_USER: ["user.name", "UserName", "user", "Account"],
    CANONICAL_HOST: ["host.name", "Computer", "host", "DeviceName"],
    CANONICAL_EVENT_TYPE: ["event.type", "ActionType", "event_type", "EventType"],
    CANONICAL_SEVERITY: ["event.severity", "Severity", "severity"],
}


@dataclass
class Finding:
    """
    Analysis result: one finding with references to records in DataPackage.data (evidence).

    evidence_ids are indices into data_package.data (int), not record identifiers.
    """

    finding_id: str
    description: str
    severity: str  # e.g. "high", "medium", "low"
    evidence_ids: List[int]  # indices into DataPackage.data
    timestamp: str  # ISO 8601
    playbook_id: str
    context: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "description": self.description,
            "severity": self.severity,
            "evidence_ids": self.evidence_ids,
            "timestamp": self.timestamp,
            "playbook_id": self.playbook_id,
            "context": self.context or {},
        }


def _get_nested(obj: Dict[str, Any], path: str) -> Any:
    """Get value by dotted path 'key.nested', e.g. source.ip."""
    if not path:
        return None
    parts = path.split(".")
    current: Any = obj
    for p in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(p)
    return current


def _first_value(record: Dict[str, Any], keys: List[str]) -> Any:
    """Return the first non-empty value for any of the keys (dotted paths)."""
    for k in keys:
        v = _get_nested(record, k)
        if v is not None and v != "":
            return v
    return None


def _normalize_record(
    record: Dict[str, Any],
    field_mapping: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Map record to canonical model (event_time, src_ip, ...).
    field_mapping overrides default source keys; missing value = None.
    """
    mapping = field_mapping if field_mapping is not None else DEFAULT_FIELD_MAPPING
    out: Dict[str, Any] = {}
    for canonical, source_keys in mapping.items():
        out[canonical] = _first_value(record, source_keys)
    return out


def _parse_event_time(value: Any) -> Optional[datetime]:
    """Parse event_time to datetime (UTC). Handles ISO string or epoch (s/ms)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo is None else value
    if isinstance(value, (int, float)):
        if value > 1e12:
            value = value / 1000.0
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _apply_threshold_rule(
    data: List[Dict[str, Any]],
    normalized_with_idx: List[tuple[int, Dict[str, Any]]],
    rule: Dict[str, Any],
    playbook_id: str,
) -> List[Finding]:
    """
    Threshold rule: group_by in time window window_minutes, count >= threshold → Finding.
    rule: event_type (optional filter), threshold (int), window_minutes (int), group_by (canonical key).
    """
    event_type = rule.get("event_type")
    threshold = rule.get("threshold")
    window_minutes = rule.get("window_minutes")
    group_by_key = rule.get("group_by") or CANONICAL_SRC_IP

    if threshold is None or not isinstance(threshold, (int, float)):
        logger.warning("threshold rule missing 'threshold', skipping")
        return []
    threshold = int(threshold)
    if window_minutes is not None:
        window_seconds = int(window_minutes) * 60
    else:
        window_seconds = None

    # Filter by event_type if provided
    if event_type is not None:
        filtered = [
            (idx, n)
            for idx, n in normalized_with_idx
            if n.get(CANONICAL_EVENT_TYPE) == event_type
        ]
    else:
        filtered = list(normalized_with_idx)

    # Group by group_by_key; for each group collect (idx, event_time)
    groups: Dict[Any, List[tuple[int, Optional[datetime]]]] = {}
    for idx, norm in filtered:
        key = norm.get(group_by_key)
        if key is None:
            key = "__unknown__"
        dt = _parse_event_time(norm.get(CANONICAL_EVENT_TIME))
        if key not in groups:
            groups[key] = []
        groups[key].append((idx, dt))

    findings: List[Finding] = []
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for group_key, items in groups.items():
        if window_seconds is not None:
            # In time window: take latest event_time as window end, keep only events in [end - window, end]
            with_time = [(idx, dt) for idx, dt in items if dt is not None]
            if not with_time:
                continue
            with_time.sort(key=lambda x: x[1] or datetime.min.replace(tzinfo=timezone.utc))
            end = with_time[-1][1]
            start = end.timestamp() - window_seconds
            in_window = [idx for idx, dt in with_time if dt and dt.timestamp() >= start]
        else:
            in_window = [idx for idx, _ in items]

        if len(in_window) >= threshold:
            finding_id = str(uuid.uuid4())
            desc = (
                rule.get("description")
                or f"Threshold exceeded: {len(in_window)} events (≥{threshold}) for {group_by_key}={group_key}"
            )
            severity = rule.get("severity") or "medium"
            findings.append(
                Finding(
                    finding_id=finding_id,
                    description=desc,
                    severity=severity,
                    evidence_ids=in_window,
                    timestamp=now_iso,
                    playbook_id=playbook_id,
                    context={"rule_type": "threshold", "group_by_value": group_key},
                )
            )

    return findings


def _load_playbook_metadata(playbook_metadata: Union[Dict[str, Any], Path]) -> Dict[str, Any]:
    """If Path – load metadata.yml from playbook directory, otherwise return dict."""
    if isinstance(playbook_metadata, (Path, str)):
        path = Path(playbook_metadata).resolve()
        meta_file = path / "metadata.yml" if path.is_dir() else path
        if not meta_file.is_file():
            raise FileNotFoundError(f"Playbook metadata not found: {meta_file}")
        with open(meta_file, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return dict(playbook_metadata)


def run_analysis(
    data_package: "DataPackage",
    playbook_metadata: Union[Dict[str, Any], Path],
    analysis_rules: Optional[List[Dict[str, Any]]] = None,
) -> List[Finding]:
    """
    Run deterministic analysis: rules from metadata (or analysis_rules) on data_package.data.

    Args:
        data_package: DataPackage with data field (list of records).
        playbook_metadata: Path to playbook directory (metadata.yml) or dict with metadata.
        analysis_rules: Optional list of rules (overrides analysis_rules from metadata).

    Returns:
        List of Finding (evidence_ids are indices into data_package.data).
    """
    from automation_scripts.data_package import DataPackage as DP

    if not isinstance(data_package, DP):
        raise TypeError("data_package must be a DataPackage instance")

    meta = _load_playbook_metadata(playbook_metadata)
    playbook_id = meta.get("mitre_technique_id") or meta.get("name") or "unknown"
    field_mapping = meta.get("field_mapping")  # optional override
    rules = analysis_rules if analysis_rules is not None else meta.get("analysis_rules") or []

    data = data_package.data
    if not data:
        return []

    normalized_with_idx: List[tuple[int, Dict[str, Any]]] = []
    for i, record in enumerate(data):
        if not isinstance(record, dict):
            continue
        norm = _normalize_record(record, field_mapping)
        normalized_with_idx.append((i, norm))

    all_findings: List[Finding] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rule_type = rule.get("type") or "threshold"
        if rule_type == "threshold":
            all_findings.extend(
                _apply_threshold_rule(data, normalized_with_idx, rule, playbook_id)
            )
        else:
            logger.warning("Unknown rule type %s, skipping", rule_type)

    return all_findings
