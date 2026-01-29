#!/usr/bin/env python3
"""
Health Monitor runner – starts Prometheus exporter and runs schedule_health_checks.
Designed for systemd service. Keeps running to maintain /metrics endpoint for Prometheus.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from automation_scripts.orchestrators.health_monitor import (
    start_prometheus_exporter,
    schedule_health_checks,
)


def main() -> None:
    config_path = _project_root / "configs" / "config.yml"
    start_prometheus_exporter(config_path=config_path)
    schedule_health_checks(config_path=config_path, run_once=False)


if __name__ == "__main__":
    main()
