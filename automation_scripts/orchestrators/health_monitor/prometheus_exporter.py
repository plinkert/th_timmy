"""
Prometheus exposition – register gauges and update from SystemMetrics.

Expose /metrics on VM04 (e.g. port 9090) for Prometheus scrape. Call
update_prometheus_metrics(metrics) after each collection; optionally
start_prometheus_exporter(port) to run the HTTP server in a background thread.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from .metrics_collector import SystemMetrics

_prometheus_gauges: Dict[str, Any] = {}
_server_thread: Optional[threading.Thread] = None


def _ensure_gauges() -> None:
    if _prometheus_gauges:
        return
    try:
        from prometheus_client import Gauge
    except ImportError:
        return
    _prometheus_gauges["cpu_percent"] = Gauge("th_timmy_cpu_percent", "CPU usage percent", ["vm_id"])
    _prometheus_gauges["memory_percent"] = Gauge("th_timmy_memory_percent", "Memory usage percent", ["vm_id"])
    _prometheus_gauges["disk_percent"] = Gauge("th_timmy_disk_percent", "Disk usage percent", ["vm_id"])
    _prometheus_gauges["load_1"] = Gauge("th_timmy_load_1", "Load average 1 min", ["vm_id"])
    _prometheus_gauges["load_5"] = Gauge("th_timmy_load_5", "Load average 5 min", ["vm_id"])
    _prometheus_gauges["load_15"] = Gauge("th_timmy_load_15", "Load average 15 min", ["vm_id"])
    _prometheus_gauges["response_time_sec"] = Gauge("th_timmy_response_time_sec", "Health check response time", ["vm_id"])
    _prometheus_gauges["uptime_sec"] = Gauge("th_timmy_uptime_sec", "System uptime seconds", ["vm_id"])
    _prometheus_gauges["error_count"] = Gauge("th_timmy_error_count", "Error count from health check", ["vm_id"])
    _prometheus_gauges["unreachable"] = Gauge("th_timmy_unreachable", "1 if VM unreachable", ["vm_id"])


def update_prometheus_metrics(metrics: SystemMetrics) -> None:
    """Update Prometheus gauges from SystemMetrics. No-op if prometheus_client not installed."""
    _ensure_gauges()
    if not _prometheus_gauges:
        return
    vm_id = metrics.vm_id
    _prometheus_gauges["cpu_percent"].labels(vm_id=vm_id).set(metrics.cpu_percent)
    _prometheus_gauges["memory_percent"].labels(vm_id=vm_id).set(metrics.memory_percent)
    _prometheus_gauges["disk_percent"].labels(vm_id=vm_id).set(metrics.disk_percent)
    if metrics.load_avg:
        _prometheus_gauges["load_1"].labels(vm_id=vm_id).set(metrics.load_avg[0] if len(metrics.load_avg) > 0 else 0)
        _prometheus_gauges["load_5"].labels(vm_id=vm_id).set(metrics.load_avg[1] if len(metrics.load_avg) > 1 else 0)
        _prometheus_gauges["load_15"].labels(vm_id=vm_id).set(metrics.load_avg[2] if len(metrics.load_avg) > 2 else 0)
    _prometheus_gauges["response_time_sec"].labels(vm_id=vm_id).set(metrics.response_time_sec)
    _prometheus_gauges["uptime_sec"].labels(vm_id=vm_id).set(metrics.uptime_sec)
    _prometheus_gauges["error_count"].labels(vm_id=vm_id).set(metrics.error_count)
    _prometheus_gauges["unreachable"].labels(vm_id=vm_id).set(1 if metrics.unreachable else 0)


def start_prometheus_exporter(
    port: int = 9090,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
) -> None:
    """Start Prometheus HTTP server in a background thread. No-op if already started or prometheus_client missing."""
    global _server_thread
    if _server_thread is not None and _server_thread.is_alive():
        return
    if config is None and config_path is None:
        config_path = Path.cwd() / "configs" / "config.yml"
    if config is None and config_path is not None:
        path = Path(config_path).resolve()
        if path.is_file():
            with open(path) as f:
                config = yaml.safe_load(f) or {}
    if config:
        port = int((config.get("health_monitoring") or {}).get("prometheus_expose_port", port))
    try:
        from prometheus_client import start_http_server
    except ImportError:
        return
    _ensure_gauges()
    if not _prometheus_gauges:
        return

    def _run():
        start_http_server(port)

    _server_thread = threading.Thread(target=_run, daemon=True)
    _server_thread.start()


def stop_prometheus_exporter() -> None:
    """Stop Prometheus HTTP server (if running in background thread)."""
    global _server_thread
    _server_thread = None
