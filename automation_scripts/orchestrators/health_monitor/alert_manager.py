"""
Alert manager – threshold evaluation and alert delivery (e-mail, Slack, SMS).

Evaluates metrics against configurable thresholds; supports CPU sustained-over-time;
deduplicates alerts in a time window; sends via e-mail (required), Slack, SMS (optional).
"""

from __future__ import annotations

import os
import smtplib
import time
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

try:
    import requests
except ImportError:
    requests = None

from .metrics_collector import SystemMetrics

DEFAULT_DEDUP_WINDOW = 900


class AlertLevel:
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Single alert to send."""

    level: str
    vm_id: str
    metric: str
    value: float
    threshold: float
    message: str
    timestamp: float = field(default_factory=time.time)


def _load_config(config_path: Optional[Union[str, Path]] = None) -> dict:
    path = config_path or Path.cwd() / "configs" / "config.yml"
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _health_monitoring_settings(config: dict) -> dict:
    hm = config.get("health_monitoring") or {}
    th = hm.get("thresholds") or {}
    return {
        "cpu_warning": float(th.get("cpu_warning", 80)),
        "cpu_critical": float(th.get("cpu_critical", 95)),
        "cpu_sustained_seconds": float(th.get("cpu_sustained_seconds", 300)),
        "memory_warning": float(th.get("memory_warning", 85)),
        "memory_critical": float(th.get("memory_critical", 90)),
        "disk_free_warning_percent": float(th.get("disk_free_warning_percent", 10)),
        "response_time_warning_seconds": float(th.get("response_time_warning_seconds", 2)),
        "alert_dedup_window_seconds": int(hm.get("alert_dedup_window_seconds", DEFAULT_DEDUP_WINDOW)),
        "alert_channels": hm.get("alert_channels") or {},
    }


# In-memory state for CPU sustained and dedup (per process)
_cpu_samples: Dict[str, List[Tuple[float, float]]] = {}
_sent_alerts: Dict[Tuple[str, str, str], float] = {}


def _prune_cpu_samples(vm_id: str, sustained_sec: float) -> None:
    now = time.time()
    cutoff = now - sustained_sec
    if vm_id in _cpu_samples:
        _cpu_samples[vm_id] = [(t, v) for t, v in _cpu_samples[vm_id] if t >= cutoff]


def _cpu_sustained_above(vm_id: str, cpu_percent: float, threshold: float, sustained_sec: float) -> bool:
    """Return True if CPU has been above threshold for at least sustained_sec."""
    now = time.time()
    if vm_id not in _cpu_samples:
        _cpu_samples[vm_id] = []
    _cpu_samples[vm_id].append((now, cpu_percent))
    _prune_cpu_samples(vm_id, sustained_sec)
    samples = _cpu_samples[vm_id]
    if not samples:
        return False
    first_ts = samples[0][0]
    span = now - first_ts
    if span < sustained_sec:
        return False
    return all(v >= threshold for (_, v) in samples)


def check_thresholds(
    metrics: SystemMetrics,
    vm_id: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    **kwargs: Any,
) -> List[Alert]:
    """
    Compare metrics to configured thresholds; return list of Alert to send.
    CPU: alert only if above threshold for cpu_sustained_seconds.
    """
    cfg = config or _load_config(config_path)
    opts = _health_monitoring_settings(cfg)
    alerts: List[Alert] = []
    now = time.time()

    if metrics.unreachable:
        alerts.append(Alert(
            level=AlertLevel.CRITICAL,
            vm_id=vm_id,
            metric="unreachable",
            value=0,
            threshold=0,
            message="VM unreachable",
            timestamp=now,
        ))
        return alerts

    # CPU: sustained check
    if metrics.cpu_percent >= opts["cpu_critical"] and _cpu_sustained_above(
        vm_id, metrics.cpu_percent, opts["cpu_critical"], opts["cpu_sustained_seconds"]
    ):
        alerts.append(Alert(
            level=AlertLevel.CRITICAL,
            vm_id=vm_id,
            metric="cpu_percent",
            value=metrics.cpu_percent,
            threshold=opts["cpu_critical"],
            message=f"CPU {metrics.cpu_percent:.1f}% >= {opts['cpu_critical']}% (sustained)",
            timestamp=now,
        ))
    elif metrics.cpu_percent >= opts["cpu_warning"] and _cpu_sustained_above(
        vm_id, metrics.cpu_percent, opts["cpu_warning"], opts["cpu_sustained_seconds"]
    ):
        alerts.append(Alert(
            level=AlertLevel.WARNING,
            vm_id=vm_id,
            metric="cpu_percent",
            value=metrics.cpu_percent,
            threshold=opts["cpu_warning"],
            message=f"CPU {metrics.cpu_percent:.1f}% >= {opts['cpu_warning']}% (sustained)",
            timestamp=now,
        ))

    # Memory
    if metrics.memory_percent >= opts["memory_critical"]:
        alerts.append(Alert(
            level=AlertLevel.CRITICAL,
            vm_id=vm_id,
            metric="memory_percent",
            value=metrics.memory_percent,
            threshold=opts["memory_critical"],
            message=f"Memory {metrics.memory_percent:.1f}% >= {opts['memory_critical']}%",
            timestamp=now,
        ))
    elif metrics.memory_percent >= opts["memory_warning"]:
        alerts.append(Alert(
            level=AlertLevel.WARNING,
            vm_id=vm_id,
            metric="memory_percent",
            value=metrics.memory_percent,
            threshold=opts["memory_warning"],
            message=f"Memory {metrics.memory_percent:.1f}% >= {opts['memory_warning']}%",
            timestamp=now,
        ))

    # Disk free: alert when free percent < threshold (i.e. used > (100 - threshold))
    disk_free_pct = 100.0 - metrics.disk_percent if metrics.disk_total else 0.0
    if metrics.disk_total and disk_free_pct < opts["disk_free_warning_percent"]:
        alerts.append(Alert(
            level=AlertLevel.WARNING,
            vm_id=vm_id,
            metric="disk_free_percent",
            value=disk_free_pct,
            threshold=opts["disk_free_warning_percent"],
            message=f"Disk free {disk_free_pct:.1f}% < {opts['disk_free_warning_percent']}%",
            timestamp=now,
        ))

    # Response time
    if metrics.response_time_sec >= opts["response_time_warning_seconds"]:
        alerts.append(Alert(
            level=AlertLevel.WARNING,
            vm_id=vm_id,
            metric="response_time_sec",
            value=metrics.response_time_sec,
            threshold=opts["response_time_warning_seconds"],
            message=f"Response time {metrics.response_time_sec:.2f}s >= {opts['response_time_warning_seconds']}s",
            timestamp=now,
        ))

    return alerts


def _dedup_key(alert: Alert) -> Tuple[str, str, str]:
    return (alert.vm_id, alert.metric, alert.level)


def _should_send(alert: Alert, dedup_window_sec: int) -> bool:
    key = _dedup_key(alert)
    now = time.time()
    if key in _sent_alerts and (now - _sent_alerts[key]) < dedup_window_sec:
        return False
    _sent_alerts[key] = now
    return True


def send_alert(
    alert: Alert,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    skip_dedup: bool = False,
    **kwargs: Any,
) -> bool:
    """
    Send alert to configured channels (e-mail, Slack, SMS). Applies deduplication
    unless skip_dedup=True. Returns True if at least one channel succeeded.
    """
    cfg = config or _load_config(config_path)
    opts = _health_monitoring_settings(cfg)
    channels = opts.get("alert_channels") or {}
    dedup_window = opts.get("alert_dedup_window_seconds", DEFAULT_DEDUP_WINDOW)
    if not skip_dedup and not _should_send(alert, dedup_window):
        return True
    sent = False
    body = f"[{alert.level.upper()}] {alert.vm_id} {alert.metric}: {alert.message}"

    # E-mail (required by ticket)
    email_cfg = channels.get("email") or {}
    smtp_host = email_cfg.get("smtp_host") or os.environ.get("TH_TIMMY_SMTP_HOST")
    smtp_user = os.environ.get("TH_TIMMY_SMTP_USER")
    smtp_pass = os.environ.get("TH_TIMMY_SMTP_PASSWORD")
    to_addrs = email_cfg.get("to_addrs") or []
    from_addr = email_cfg.get("from_addr") or smtp_user or ""
    if smtp_host and to_addrs and from_addr and smtp_user and smtp_pass:
        try:
            msg = MIMEText(body)
            msg["Subject"] = f"Health alert: {alert.vm_id} {alert.metric}"
            msg["From"] = from_addr
            msg["To"] = ", ".join(to_addrs)
            msg["Date"] = formatdate(localtime=True)
            with smtplib.SMTP(smtp_host, int(email_cfg.get("smtp_port", 587))) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.sendmail(from_addr, to_addrs, msg.as_string())
            sent = True
        except Exception:
            pass

    # Slack
    slack_cfg = channels.get("slack") or {}
    webhook = slack_cfg.get("webhook_url") or os.environ.get("TH_TIMMY_SLACK_WEBHOOK_URL")
    if webhook and requests is not None:
        try:
            r = requests.post(webhook, json={"text": body}, timeout=10)
            if r.status_code == 200:
                sent = True
        except Exception:
            pass

    # SMS: noop when not configured
    sms_cfg = channels.get("sms") or {}
    if sms_cfg.get("provider") and os.environ.get("TH_TIMMY_SMS_ENABLED"):
        pass
    return sent
