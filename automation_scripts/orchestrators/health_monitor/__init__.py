"""
Health Monitoring Service (Step 0.4).

Central collection of VM metrics (CPU, memory, disk, etc.), threshold evaluation,
alerts (e-mail, Slack, SMS), and Prometheus exposition. Uses Step 0.1 (remote_executor).
"""

from .health_monitor import (
    check_vm_health,
    schedule_health_checks,
    get_health_status,
    VMHealthStatus,
)
from .metrics_collector import collect_system_metrics, SystemMetrics, HealthCheckError
from .alert_manager import check_thresholds, send_alert, Alert, AlertLevel

__all__ = [
    "check_vm_health",
    "schedule_health_checks",
    "get_health_status",
    "HealthCheckError",
    "VMHealthStatus",
    "collect_system_metrics",
    "SystemMetrics",
    "check_thresholds",
    "send_alert",
    "Alert",
    "AlertLevel",
]
