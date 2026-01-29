"""
Health monitor – check_vm_health, schedule_health_checks, get_health_status.

Runs health_check.sh remotely (path from config), collects metrics, evaluates
thresholds, sends alerts. Handles unreachable VM and missing script (degraded).
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from automation_scripts.orchestrators.remote_executor import (
    execute_remote_command,
    RemoteExecutionResult,
)
from automation_scripts.orchestrators.remote_executor.audit_logger import log_operation

from .alert_manager import check_thresholds, send_alert, Alert
from .metrics_collector import (
    collect_system_metrics,
    HealthCheckError,
    SystemMetrics,
    HEALTH_MONITOR_USER,
    DEFAULT_TIMEOUT,
)
from .prometheus_exporter import update_prometheus_metrics

HEALTH_CHECK_TIMEOUT = 60.0
_status_cache: Dict[str, "VMHealthStatus"] = {}


@dataclass
class VMHealthStatus:
    """Health status for one VM."""

    vm_id: str
    status: str  # healthy | warning | critical | unreachable | degraded
    metrics: Optional[SystemMetrics] = None
    alerts: List[Alert] = field(default_factory=list)
    response_time_sec: float = 0.0
    error_count: int = 0
    message: str = ""


def _load_config(config_path: Optional[Union[str, Path]] = None) -> dict:
    path = config_path or Path.cwd() / "configs" / "config.yml"
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _allowed_vm_ids(config: dict) -> list[str]:
    re_cfg = config.get("remote_execution") or {}
    if "allowed_vm_ids" in re_cfg:
        return list(re_cfg["allowed_vm_ids"])
    vms = config.get("vms") or {}
    return [k for k, v in vms.items() if v.get("enabled", True)]


def _get_health_check_script_path(config: dict, vm_id: str) -> Optional[str]:
    hm = config.get("health_monitoring") or {}
    paths = hm.get("health_check_script_path") or {}
    return paths.get(vm_id) or paths.get("default")


def _shell_quote(s: str) -> str:
    if not s:
        return "''"
    if all(c.isalnum() or c in "/_.-" for c in s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _ts_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_health_check_local(script_path: str, timeout: float) -> RemoteExecutionResult:
    """Uruchom health_check.sh lokalnie (dla vm04-orchestrator)."""
    cmd = f"bash -- {script_path} 2>/dev/null || true"
    start_utc = _ts_utc()
    start_time = time.perf_counter()

    if not os.path.isfile(script_path):
        end_utc = _ts_utc()
        log_operation(
            HEALTH_MONITOR_USER,
            "vm04",
            cmd[:200],
            start_utc,
            end_utc,
            "error",
            exit_code=127,
            extra={"execution_time_sec": 0.0, "reason": "script not found"},
        )
        return RemoteExecutionResult(
            stdout="",
            stderr=f"Script not found: {script_path}",
            exit_code=127,
            execution_time=0.0,
            timestamp=end_utc,
            vm_id="vm04",
            command=cmd,
            success=False,
        )
    try:
        proc = subprocess.run(
            ["bash", "--", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(script_path) or None,
        )
        elapsed = time.perf_counter() - start_time
        end_utc = _ts_utc()
        status = "success" if proc.returncode == 0 else "error"
        log_operation(
            HEALTH_MONITOR_USER,
            "vm04",
            cmd[:200],
            start_utc,
            end_utc,
            status,
            exit_code=proc.returncode,
            extra={"execution_time_sec": round(elapsed, 3)},
        )
        return RemoteExecutionResult(
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            exit_code=proc.returncode,
            execution_time=elapsed,
            timestamp=end_utc,
            vm_id="vm04",
            command=cmd,
            success=proc.returncode == 0,
        )
    except subprocess.TimeoutExpired as e:
        elapsed = time.perf_counter() - start_time
        end_utc = _ts_utc()
        log_operation(
            HEALTH_MONITOR_USER,
            "vm04",
            cmd[:200],
            start_utc,
            end_utc,
            "error",
            exit_code=124,
            extra={"execution_time_sec": round(elapsed, 3), "exception": "timeout"},
        )
        return RemoteExecutionResult(
            stdout=e.stdout or "",
            stderr=str(e),
            exit_code=124,
            execution_time=timeout,
            timestamp=end_utc,
            vm_id="vm04",
            command=cmd,
            success=False,
        )
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        end_utc = _ts_utc()
        log_operation(
            HEALTH_MONITOR_USER,
            "vm04",
            cmd[:200],
            start_utc,
            end_utc,
            "error",
            exit_code=1,
            extra={"execution_time_sec": round(elapsed, 3), "exception": str(e)},
        )
        return RemoteExecutionResult(
            stdout="",
            stderr=str(e),
            exit_code=1,
            execution_time=elapsed,
            timestamp=end_utc,
            vm_id="vm04",
            command=cmd,
            success=False,
        )


def check_vm_health(
    vm_id: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    **kwargs: Any,
) -> VMHealthStatus:
    """
    Run health_check.sh on VM, collect metrics, evaluate thresholds, send alerts.
    Returns VMHealthStatus (healthy/warning/critical/unreachable/degraded).
    Missing script path or script not found -> degraded. VM unreachable -> unreachable.
    """
    cfg = config or _load_config(config_path)
    if vm_id not in _allowed_vm_ids(cfg):
        raise ValueError(f"vm_id {vm_id} not allowed")
    script_path = _get_health_check_script_path(cfg, vm_id)
    if not script_path:
        status = VMHealthStatus(
            vm_id=vm_id,
            status="degraded",
            metrics=None,
            alerts=[],
            response_time_sec=0.0,
            error_count=0,
            message="No health_check_script_path for vm_id",
        )
        _status_cache[vm_id] = status
        return status

    response_time_sec = 0.0
    error_count = 0
    cmd = f"bash -- {_shell_quote(script_path)} 2>/dev/null || true"
    try:
        start = time.perf_counter()
        if vm_id == "vm04":
            # Lokalne uruchomienie na orchestratorze – bez SSH do samego siebie
            result = _run_health_check_local(script_path, HEALTH_CHECK_TIMEOUT)
        else:
            result = execute_remote_command(
                vm_id,
                cmd,
                HEALTH_MONITOR_USER,
                HEALTH_CHECK_TIMEOUT,
                config_path=config_path,
                config=cfg,
                **kwargs,
            )
        response_time_sec = time.perf_counter() - start
        if result.exit_code != 0:
            error_count = 1
        else:
            error_count = (result.stdout or "").count("[ERROR]") + (result.stderr or "").count("[ERROR]")
    except Exception as e:
        status = VMHealthStatus(
            vm_id=vm_id,
            status="unreachable",
            metrics=None,
            alerts=[],
            response_time_sec=0.0,
            error_count=0,
            message=str(e),
        )
        _status_cache[vm_id] = status
        return status

    try:
        metrics = collect_system_metrics(
            vm_id,
            config_path=config_path,
            config=cfg,
            response_time_sec=response_time_sec,
            error_count=error_count,
            **kwargs,
        )
    except HealthCheckError as e:
        status = VMHealthStatus(
            vm_id=vm_id,
            status="unreachable",
            metrics=None,
            alerts=[],
            response_time_sec=response_time_sec,
            error_count=error_count,
            message=str(e),
        )
        _status_cache[vm_id] = status
        return status

    try:
        update_prometheus_metrics(metrics)
    except Exception:
        pass
    alerts = check_thresholds(metrics, vm_id, config=cfg, **kwargs)
    for alert in alerts:
        send_alert(alert, config=cfg, **kwargs)

    if any(a.level == "critical" for a in alerts):
        status_str = "critical"
    elif any(a.level == "warning" for a in alerts):
        status_str = "warning"
    else:
        status_str = "healthy"

    status = VMHealthStatus(
        vm_id=vm_id,
        status=status_str,
        metrics=metrics,
        alerts=alerts,
        response_time_sec=response_time_sec,
        error_count=error_count,
        message="",
    )
    _status_cache[vm_id] = status
    return status


def schedule_health_checks(
    interval: float = 300.0,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    run_once: bool = False,
    **kwargs: Any,
) -> None:
    """
    Run check_vm_health for all enabled VMs every interval seconds.
    If run_once=True, run one round and return. Otherwise loop (e.g. for external scheduler).
    """
    cfg = config or _load_config(config_path)
    vm_ids = _allowed_vm_ids(cfg)
    check_interval = (cfg.get("health_monitoring") or {}).get("check_interval") or interval
    while True:
        for vm_id in vm_ids:
            try:
                check_vm_health(vm_id, config_path=config_path, config=cfg, **kwargs)
            except Exception:
                pass
        if run_once:
            return
        time.sleep(check_interval)


def get_health_status(
    vm_id: Optional[str] = None,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    refresh: bool = False,
    **kwargs: Any,
) -> Union[VMHealthStatus, Dict[str, VMHealthStatus]]:
    """
    Return cached health status for vm_id or all VMs. If refresh=True, run check_vm_health first.
    """
    if refresh and vm_id:
        cfg = config or _load_config(config_path)
        check_vm_health(vm_id, config_path=config_path, config=cfg, **kwargs)
    if refresh and not vm_id:
        cfg = config or _load_config(config_path)
        for vid in _allowed_vm_ids(cfg):
            try:
                check_vm_health(vid, config_path=config_path, config=cfg, **kwargs)
            except Exception:
                pass
    if vm_id:
        return _status_cache.get(vm_id) or VMHealthStatus(vm_id=vm_id, status="unknown", message="No cached result")
    return dict(_status_cache)
