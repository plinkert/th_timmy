"""Unit tests for Playbook Engine (Step 2.1)."""

from pathlib import Path

import pytest

from automation_scripts.data_package import DataPackage
from automation_scripts.playbooks.playbook_engine import (
    Finding,
    _normalize_record,
    _parse_event_time,
    run_analysis,
)


def _make_data_package(data: list, source: str = "elk") -> DataPackage:
    return DataPackage(
        id="test-pkg",
        source=source,
        timestamp="2025-01-27T12:00:00Z",
        data=data,
        anonymized=True,
        context={},
    )


def test_empty_data_returns_empty_findings():
    """Empty data -> []."""
    dp = _make_data_package([])
    meta = {"mitre_technique_id": "T1059", "analysis_rules": [{"type": "threshold", "threshold": 10}]}
    findings = run_analysis(dp, meta)
    assert findings == []


def test_threshold_below_no_finding():
    """9 events, threshold 10 -> 0 findings."""
    base = {"@timestamp": "2025-01-27T12:00:00Z", "source": {"ip": "10.0.0.1"}}
    data = [{**base, "event": {"type": "login"}} for _ in range(9)]
    dp = _make_data_package(data)
    meta = {
        "mitre_technique_id": "T1059",
        "analysis_rules": [
            {"type": "threshold", "threshold": 10, "group_by": "src_ip"}
        ],
    }
    findings = run_analysis(dp, meta)
    assert len(findings) == 0


def test_threshold_above_one_finding():
    """11 events, threshold 10 -> 1 finding with 11 evidence_ids."""
    base = {"@timestamp": "2025-01-27T12:00:00Z", "source": {"ip": "10.0.0.1"}}
    data = [{**base, "event": {"type": "login"}} for _ in range(11)]
    dp = _make_data_package(data)
    meta = {
        "mitre_technique_id": "T1059",
        "analysis_rules": [
            {"type": "threshold", "threshold": 10, "group_by": "src_ip"}
        ],
    }
    findings = run_analysis(dp, meta)
    assert len(findings) == 1
    assert findings[0].severity == "medium"
    assert findings[0].evidence_ids == list(range(11))
    assert findings[0].playbook_id == "T1059"
    assert len(findings[0].finding_id) > 0


def test_finding_has_required_fields():
    """Finding has finding_id, description, severity, evidence_ids, timestamp, playbook_id, context."""
    base = {"@timestamp": "2025-01-27T12:00:00Z", "source": {"ip": "10.0.0.2"}}
    data = [{**base} for _ in range(12)]
    dp = _make_data_package(data)
    meta = {
        "mitre_technique_id": "T1234",
        "analysis_rules": [{"type": "threshold", "threshold": 5}],
    }
    findings = run_analysis(dp, meta)
    assert len(findings) == 1
    f = findings[0]
    assert f.finding_id
    assert f.description
    assert f.severity in ("low", "medium", "high")
    assert f.evidence_ids == list(range(12))
    assert "T" in f.timestamp or "Z" in f.timestamp
    assert f.playbook_id == "T1234"
    assert isinstance(f.context, dict)


def test_playbook_metadata_from_dict():
    """run_analysis accepts dict as playbook_metadata."""
    dp = _make_data_package([{"@timestamp": "2025-01-27T12:00:00Z", "source": {"ip": "1.2.3.4"}}] * 3)
    meta = {"name": "TestPlaybook", "analysis_rules": [{"type": "threshold", "threshold": 2}]}
    findings = run_analysis(dp, meta)
    assert len(findings) == 1
    assert findings[0].playbook_id == "TestPlaybook"


def test_normalize_record_default_mapping():
    """_normalize_record maps source.ip -> src_ip, @timestamp -> event_time."""
    record = {"@timestamp": "2025-01-27T12:00:00Z", "source": {"ip": "10.0.0.1"}}
    norm = _normalize_record(record)
    assert norm.get("event_time") == "2025-01-27T12:00:00Z"
    assert norm.get("src_ip") == "10.0.0.1"


def test_parse_event_time_iso():
    """_parse_event_time handles ISO string."""
    dt = _parse_event_time("2025-01-27T12:00:00Z")
    assert dt is not None
    assert dt.year == 2025 and dt.month == 1 and dt.day == 27


def test_parse_event_time_epoch():
    """_parse_event_time handles epoch (s)."""
    dt = _parse_event_time(1738000000)  # ~2025
    assert dt is not None


def test_run_analysis_requires_datapackage():
    """run_analysis with non-DataPackage raises TypeError."""
    with pytest.raises(TypeError, match="DataPackage"):
        run_analysis({"data": []}, {"analysis_rules": []})


def test_finding_to_dict():
    """Finding.to_dict() returns dict with required fields."""
    f = Finding(
        finding_id="f1",
        description="Test",
        severity="high",
        evidence_ids=[0, 1],
        timestamp="2025-01-27T12:00:00Z",
        playbook_id="T1059",
        context={"k": "v"},
    )
    d = f.to_dict()
    assert d["finding_id"] == "f1"
    assert d["evidence_ids"] == [0, 1]
    assert d["context"]["k"] == "v"
