"""Unit tests for health_monitor (Step 0.4)."""

from unittest.mock import MagicMock, patch

import pytest

from automation_scripts.orchestrators.health_monitor.health_monitor import (
    check_vm_health,
    get_health_status,
    VMHealthStatus,
    _status_cache,
)
from automation_scripts.orchestrators.health_monitor.metrics_collector import SystemMetrics, HealthCheckError
from automation_scripts.orchestrators.health_monitor.alert_manager import Alert, AlertLevel


@pytest.fixture
def miniconfig():
    return {
        "vms": {
            "vm01": {"ip": "192.168.1.1", "ssh_user": "u", "ssh_port": 22, "enabled": True},
        },
        "remote_execution": {},
        "health_monitoring": {
            "health_check_script_path": {"vm01": "/opt/th_timmy/hosts/vm01-ingest/health_check.sh", "default": "/opt/th_timmy/hosts/vm04-orchestrator/health_check.sh"},
            "thresholds": {"cpu_warning": 80, "memory_critical": 90},
        },
    }


def setup_function():
    _status_cache.clear()


@patch("automation_scripts.orchestrators.health_monitor.health_monitor.collect_system_metrics")
@patch("automation_scripts.orchestrators.health_monitor.health_monitor.execute_remote_command")
def test_check_vm_health_healthy(mock_exec, mock_collect, miniconfig):
    mock_exec.return_value = MagicMock(exit_code=0, stdout="[OK] check", stderr="")
    mock_collect.return_value = SystemMetrics(
        vm_id="vm01",
        cpu_percent=50,
        load_avg=[0.5, 0.5, 0.5],
        memory_percent=50,
        memory_used=1000,
        memory_total=2000,
        disk_percent=50,
        disk_free=50,
        disk_total=100,
        network_sent=0,
        network_recv=0,
        response_time_sec=0.5,
        uptime_sec=3600,
        error_count=0,
        unreachable=False,
        raw={},
    )
    with patch("automation_scripts.orchestrators.health_monitor.health_monitor.check_thresholds") as mock_thresh:
        mock_thresh.return_value = []
        status = check_vm_health("vm01", config=miniconfig)
    assert status.status == "healthy"
    assert status.metrics is not None
    assert status.vm_id == "vm01"


@patch("automation_scripts.orchestrators.health_monitor.health_monitor.execute_remote_command")
def test_check_vm_health_no_script_path(mock_exec, miniconfig):
    miniconfig["health_monitoring"]["health_check_script_path"] = {}
    status = check_vm_health("vm01", config=miniconfig)
    assert status.status == "degraded"
    assert "No health_check_script_path" in status.message
    mock_exec.assert_not_called()


@patch("automation_scripts.orchestrators.health_monitor.health_monitor.collect_system_metrics")
@patch("automation_scripts.orchestrators.health_monitor.health_monitor.execute_remote_command")
def test_check_vm_health_unreachable(mock_exec, mock_collect, miniconfig):
    mock_exec.return_value = MagicMock(exit_code=0, stdout="", stderr="")
    mock_collect.side_effect = HealthCheckError("VM unreachable")
    status = check_vm_health("vm01", config=miniconfig)
    assert status.status == "unreachable"


def test_get_health_status_cached():
    _status_cache["vm01"] = VMHealthStatus(vm_id="vm01", status="healthy", message="")
    status = get_health_status("vm01")
    assert status.vm_id == "vm01"
    assert status.status == "healthy"


def test_get_health_status_unknown_vm():
    status = get_health_status("vm99")
    assert status.vm_id == "vm99"
    assert status.status == "unknown"


@patch("automation_scripts.orchestrators.health_monitor.health_monitor.collect_system_metrics")
@patch("automation_scripts.orchestrators.health_monitor.health_monitor._run_health_check_local")
def test_check_vm_health_vm04_local(mock_local, mock_collect, miniconfig):
    """vm04 uruchamia health_check lokalnie, bez SSH."""
    miniconfig["vms"]["vm04"] = {"ip": "192.168.1.4", "ssh_user": "u", "ssh_port": 22, "enabled": True}
    miniconfig["health_monitoring"]["health_check_script_path"]["vm04"] = "/opt/th_timmy/hosts/vm04-orchestrator/health_check.sh"
    mock_local.return_value = MagicMock(exit_code=0, stdout="[OK] check", stderr="")
    mock_collect.return_value = SystemMetrics(
        vm_id="vm04",
        cpu_percent=30,
        load_avg=[0.3, 0.3, 0.3],
        memory_percent=40,
        memory_used=800,
        memory_total=2000,
        disk_percent=35,
        disk_free=65,
        disk_total=100,
        network_sent=0,
        network_recv=0,
        response_time_sec=0.1,
        uptime_sec=7200,
        error_count=0,
        unreachable=False,
        raw={},
    )
    with patch("automation_scripts.orchestrators.health_monitor.health_monitor.check_thresholds") as mock_thresh:
        mock_thresh.return_value = []
        status = check_vm_health("vm04", config=miniconfig)
    assert status.status == "healthy"
    mock_local.assert_called_once()
