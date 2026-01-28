"""Unit tests for repo_sync.secret_scanner (scan_repository, SecretScanResult)."""

from unittest.mock import patch

import pytest

from automation_scripts.orchestrators.repo_sync.secret_scanner import (
    SecretScanResult,
    scan_repository,
)


def test_scan_repository_not_dir(tmp_path):
    """scan_repository returns has_secrets=False when path is not a directory."""
    res = scan_repository(tmp_path / "missing")
    assert res.has_secrets is False
    assert res.secrets_found == []
    assert "not a directory" in res.raw_output


def test_scan_repository_clean(tmp_path):
    """scan_repository returns has_secrets=False when gitleaks exits 0."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as m:
        m.return_value = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        res = scan_repository(tmp_path)
    assert res.has_secrets is False
    assert res.secrets_found == []


def test_scan_repository_secrets_found(tmp_path):
    """scan_repository returns has_secrets=True when gitleaks finds secrets (exit 1, JSON)."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as m:
        m.return_value = type("R", (), {
            "returncode": 1,
            "stdout": '[{"File":"x","RuleID":"y","StartLine":1}]',
            "stderr": "",
        })()
        res = scan_repository(tmp_path)
    assert res.has_secrets is True
    assert len(res.secrets_found) == 1
    assert res.secrets_found[0].get("file") == "x"
    assert res.secrets_found[0].get("rule_id") == "y"


def test_scan_repository_gitleaks_not_found(tmp_path):
    """scan_repository returns has_secrets=False when gitleaks binary is missing."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        res = scan_repository(tmp_path, gitleaks_path="nonexistent_gitleaks")
    assert res.has_secrets is False
    assert "not found" in res.raw_output.lower()
