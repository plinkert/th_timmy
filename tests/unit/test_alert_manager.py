"""Unit tests for alert_manager (Step 0.4)."""

from unittest.mock import patch

import pytest

from automation_scripts.orchestrators.health_monitor.alert_manager import (
    check_thresholds,
    send_alert,
    Alert,
    AlertLevel,
    _cpu_samples,
    _sent_alerts,
)
from automation_scripts.orchestrators.health_monitor.metrics_collector import SystemMetrics


@pytest.fixture
def miniconfig():
    return {
        "health_monitoring": {
            "thresholds": {
                "cpu_warning": 80,
                "cpu_critical": 95,
                "cpu_sustained_seconds": 300,
                "memory_warning": 85,
                "memory_critical": 90,
                "disk_free_warning_percent": 10,
                "response_time_warning_seconds": 2,
            },
            "alert_dedup_window_seconds": 900,
        },
    }


def _metrics(cpu=50, memory=50, disk_percent=50, response_time=0.5, unreachable=False):
    return SystemMetrics(
        vm_id="vm01",
        cpu_percent=cpu,
        load_avg=[0.5, 0.5, 0.5],
        memory_percent=memory,
        memory_used=1000,
        memory_total=2000,
        disk_percent=disk_percent,
        disk_free=50,
        disk_total=100,
        network_sent=0,
        network_recv=0,
        response_time_sec=response_time,
        uptime_sec=3600,
        error_count=0,
        unreachable=unreachable,
        raw={},
    )


def test_check_thresholds_unreachable(miniconfig):
    metrics = _metrics(unreachable=True)
    alerts = check_thresholds(metrics, "vm01", config=miniconfig)
    assert len(alerts) == 1
    assert alerts[0].metric == "unreachable"
    assert alerts[0].level == AlertLevel.CRITICAL


def test_check_thresholds_memory_critical(miniconfig):
    metrics = _metrics(memory=92)
    alerts = check_thresholds(metrics, "vm01", config=miniconfig)
    memory_alerts = [a for a in alerts if a.metric == "memory_percent"]
    assert len(memory_alerts) >= 1
    assert any(a.level == AlertLevel.CRITICAL for a in memory_alerts)


def test_check_thresholds_disk_free(miniconfig):
    metrics = _metrics(disk_percent=95)
    alerts = check_thresholds(metrics, "vm01", config=miniconfig)
    disk_alerts = [a for a in alerts if a.metric == "disk_free_percent"]
    assert len(disk_alerts) >= 1
    assert disk_alerts[0].value == 5.0


def test_check_thresholds_response_time(miniconfig):
    metrics = _metrics(response_time=3.0)
    alerts = check_thresholds(metrics, "vm01", config=miniconfig)
    rt_alerts = [a for a in alerts if a.metric == "response_time_sec"]
    assert len(rt_alerts) >= 1


def test_check_thresholds_healthy(miniconfig):
    metrics = _metrics(cpu=50, memory=50, disk_percent=50, response_time=0.5)
    alerts = check_thresholds(metrics, "vm01", config=miniconfig)
    assert all(a.metric == "unreachable" for a in alerts) or len(alerts) == 0


def test_send_alert_dedup(miniconfig):
    _sent_alerts.clear()
    alert = Alert(level=AlertLevel.WARNING, vm_id="vm01", metric="memory_percent", value=86, threshold=85, message="test")
    miniconfig["health_monitoring"]["alert_dedup_window_seconds"] = 900
    miniconfig["health_monitoring"]["alert_channels"] = {}
    send_alert(alert, config=miniconfig)
    send_alert(alert, config=miniconfig, skip_dedup=False)
    assert _sent_alerts.get(("vm01", "memory_percent", "warning")) is not None


def test_send_alert_no_channels(miniconfig):
    miniconfig["health_monitoring"]["alert_channels"] = {}
    alert = Alert(level=AlertLevel.WARNING, vm_id="vm01", metric="test", value=1, threshold=0, message="test")
    result = send_alert(alert, config=miniconfig, skip_dedup=True)
    assert result is False
