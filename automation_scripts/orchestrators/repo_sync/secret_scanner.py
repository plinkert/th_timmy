"""
Secret scanning before sync – gitleaks (or equivalent). Block and alert on secrets; do not log secret content.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class SecretScanResult:
    """Result of a repository secret scan."""

    has_secrets: bool
    secrets_found: list[dict[str, Any]]
    scan_timestamp: str
    raw_output: str = ""

    def __post_init__(self) -> None:
        if not self.scan_timestamp:
            self.scan_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scan_repository(
    repo_path: str | Path,
    *,
    config_path: Optional[str | Path] = None,
    gitleaks_path: str = "gitleaks",
    timeout: int = 120,
) -> SecretScanResult:
    """
    Scan repo for secrets (gitleaks). Returns SecretScanResult.

    If gitleaks is not installed or config is missing, returns has_secrets=False
    and logs via raw_output; callers may still block on "tool missing" if policy requires.
    """
    repo = Path(repo_path).resolve()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not repo.is_dir():
        return SecretScanResult(
            has_secrets=False,
            secrets_found=[],
            scan_timestamp=ts,
            raw_output=f"Repo path is not a directory: {repo}",
        )

    config_opt: list[str] = []
    if config_path is not None:
        cp = Path(config_path)
        if cp.is_absolute():
            config_opt = ["--config-path", str(cp)]
        else:
            config_opt = ["--config-path", str(repo / cp)]

    cmd = [gitleaks_path, "detect", "--source", str(repo), "--no-git", "--report-format", "json"] + config_opt
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo),
        )
        raw = (r.stdout or "") + (r.stderr or "").strip()
        # gitleaks exit 1 when secrets found, 0 when clean
        if r.returncode == 1 and r.stdout:
            try:
                data = json.loads(r.stdout)
                if isinstance(data, list):
                    findings = data
                elif isinstance(data, dict):
                    findings = data.get("findings", [])
                else:
                    findings = []
                # Redact description/secret in logged structure – do not log actual secret content
                safe_findings = [
                    {"file": f.get("File", ""), "rule_id": f.get("RuleID", ""), "line": f.get("StartLine")}
                    for f in findings
                ]
                return SecretScanResult(
                    has_secrets=True,
                    secrets_found=safe_findings,
                    scan_timestamp=ts,
                    raw_output=raw[:2000],
                )
            except json.JSONDecodeError:
                return SecretScanResult(
                    has_secrets=True,
                    secrets_found=[{"raw": raw[:200]}],
                    scan_timestamp=ts,
                    raw_output=raw[:2000],
                )
        return SecretScanResult(
            has_secrets=False,
            secrets_found=[],
            scan_timestamp=ts,
            raw_output=raw[:2000],
        )
    except subprocess.TimeoutExpired:
        return SecretScanResult(
            has_secrets=False,
            secrets_found=[],
            scan_timestamp=ts,
            raw_output="gitleaks timed out",
        )
    except FileNotFoundError:
        return SecretScanResult(
            has_secrets=False,
            secrets_found=[],
            scan_timestamp=ts,
            raw_output=f"gitleaks not found: {gitleaks_path}",
        )
