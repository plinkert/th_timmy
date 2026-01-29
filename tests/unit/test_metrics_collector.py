"""Unit tests for metrics_collector (Step 0.4)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from automation_scripts.orchestrators.health_monitor.metrics_collector import (
    collect_system_metrics,
    SystemMetrics,
    HealthCheckError,
    _parse_metrics_output,
    _float,
    _int,
)


def test_parse_metrics_output():
    stdout = """
METRIC_CPU_PERCENT=45.2
METRIC_LOAD_1=0.5
METRIC_LOAD_5=0.4
METRIC_LOAD_15=0.3
METRIC_MEMORY_PERCENT=60.1
METRIC_MEMORY_USED=1234567890
METRIC_MEMORY_TOTAL=2048000000
METRIC_DISK_PERCENT=70
METRIC_DISK_FREE=50000000000
METRIC_DISK_TOTAL=100000000000
METRIC_NETWORK_SENT=1000
METRIC_NETWORK_RECV=2000
METRIC_UPTIME_SEC=86400.5
METRIC_END=1
"""
    parsed = _parse_metrics_output(stdout)
    assert parsed.get("METRIC_CPU_PERCENT") == "45.2"
    assert parsed.get("METRIC_MEMORY_PERCENT") == "60.1"
    assert parsed.get("METRIC_UPTIME_SEC") == "86400.5"


def test_float_helper():
    assert _float("12.5") == 12.5
    assert _float("", 3.0) == 3.0
    assert _float("invalid", 0.0) == 0.0


def test_int_helper():
    assert _int("100") == 100
    assert _int("12.7") == 12
    assert _int("", 5) == 5


@patch("automation_scripts.orchestrators.health_monitor.metrics_collector.execute_remote_command")
def test_collect_system_metrics_success(mock_exec, tmp_path):
    mock_exec.return_value = MagicMock(
        exit_code=0,
        stdout="""
METRIC_CPU_PERCENT=25.5
METRIC_LOAD_1=0.1
METRIC_LOAD_5=0.2
METRIC_LOAD_15=0.15
METRIC_MEMORY_PERCENT=50.0
METRIC_MEMORY_USED=1000000000
METRIC_MEMORY_TOTAL=2000000000
METRIC_DISK_PERCENT=40
METRIC_DISK_FREE=60000000000
METRIC_DISK_TOTAL=100000000000
METRIC_NETWORK_SENT=100
METRIC_NETWORK_RECV=200
METRIC_UPTIME_SEC=3600.0
METRIC_END=1
""",
        stderr="",
    )
    config = {
        "vms": {"vm01": {"ip": "192.168.1.1", "ssh_user": "u", "ssh_port": 22, "enabled": True}},
        "remote_execution": {},
    }
    metrics = collect_system_metrics("vm01", config=config, response_time_sec=0.5, error_count=0)
    assert metrics.vm_id == "vm01"
    assert metrics.cpu_percent == 25.5
    assert metrics.memory_percent == 50.0
    assert metrics.disk_percent == 40.0
    assert metrics.uptime_sec == 3600.0
    assert metrics.response_time_sec == 0.5
    assert metrics.unreachable is False


@patch("automation_scripts.orchestrators.health_monitor.metrics_collector.execute_remote_command")
def test_collect_system_metrics_unreachable(mock_exec):
    mock_exec.side_effect = ConnectionError("timeout")
    config = {
        "vms": {"vm01": {"ip": "192.168.1.1", "ssh_user": "u", "ssh_port": 22, "enabled": True}},
        "remote_execution": {},
    }
    with pytest.raises(HealthCheckError):
        collect_system_metrics("vm01", config=config)


@patch("automation_scripts.orchestrators.health_monitor.metrics_collector.execute_remote_command")
def test_collect_system_metrics_script_fails(mock_exec):
    mock_exec.return_value = MagicMock(exit_code=1, stdout="", stderr="script failed")
    config = {
        "vms": {"vm01": {"ip": "192.168.1.1", "ssh_user": "u", "ssh_port": 22, "enabled": True}},
        "remote_execution": {},
    }
    with pytest.raises(HealthCheckError):
        collect_system_metrics("vm01", config=config)


@patch("automation_scripts.orchestrators.health_monitor.metrics_collector.subprocess.run")
def test_collect_system_metrics_vm04_local(mock_subprocess):
    """vm04 zbiera metryki lokalnie, bez SSH."""
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout="""
METRIC_CPU_PERCENT=20.0
METRIC_LOAD_1=0.2
METRIC_LOAD_5=0.2
METRIC_LOAD_15=0.2
METRIC_MEMORY_PERCENT=45.0
METRIC_MEMORY_USED=900000000
METRIC_MEMORY_TOTAL=2000000000
METRIC_DISK_PERCENT=35
METRIC_DISK_FREE=65000000000
METRIC_DISK_TOTAL=100000000000
METRIC_NETWORK_SENT=50
METRIC_NETWORK_RECV=75
METRIC_UPTIME_SEC=18000.0
METRIC_END=1
""",
        stderr="",
    )
    config = {
        "vms": {"vm04": {"ip": "192.168.1.4", "ssh_user": "u", "ssh_port": 22, "enabled": True}},
        "remote_execution": {},
    }
    metrics = collect_system_metrics("vm04", config=config, response_time_sec=0.05, error_count=0)
    assert metrics.vm_id == "vm04"
    assert metrics.cpu_percent == 20.0
    assert metrics.memory_percent == 45.0
    assert metrics.unreachable is False
    mock_subprocess.assert_called_once()
