"""
Metrics collector – gather system metrics from VMs via execute_remote_command.

Parses output of standard Linux commands (top, free, df, uptime, /proc) into
SystemMetrics. Handles timeout and unreachable VM without blocking.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union

import yaml

from automation_scripts.orchestrators.remote_executor import execute_remote_command
from automation_scripts.orchestrators.remote_executor.audit_logger import log_operation

HEALTH_MONITOR_USER = "health_monitor"
DEFAULT_TIMEOUT = 30.0


class HealthCheckError(Exception):
    """Raised when VM is unreachable or metrics collection fails."""

    pass


@dataclass
class SystemMetrics:
    """System metrics for one VM."""

    vm_id: str
    cpu_percent: float
    load_avg: List[float]
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_percent: float
    disk_free: int
    disk_total: int
    network_sent: int
    network_recv: int
    response_time_sec: float
    uptime_sec: float
    error_count: int
    unreachable: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)


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


def _metrics_script() -> str:
    """Single remote script that outputs key=value lines for parsing. Uses awk for float math (no bc)."""
    return r"""
set -e
out() { echo "METRIC_$1=$2"; }
# CPU usage from /proc/stat (1 sample)
read -r _ user nice system idle iowait irq softirq steal guest guest_nice < /proc/stat
total=$((user + nice + system + idle + iowait + irq + softirq + steal))
idle_total=$((idle + iowait))
[ "$total" -gt 0 ] && cpu_pct=$(awk "BEGIN {printf \"%.2f\", 100*(1-$idle_total/$total)}") || cpu_pct=0
out "CPU_PERCENT" "${cpu_pct:-0}"
# Load average
read -r _ _ _ load1 load5 load15 _ < /proc/loadavg 2>/dev/null || true
out "LOAD_1" "${load1:-0}"
out "LOAD_5" "${load5:-0}"
out "LOAD_15" "${load15:-0}"
# Memory: used/total * 100
eval $(free -b | awk '/^Mem:/{printf "mem_used=%d mem_total=%d", $3, $2}')
[ "${mem_total:-0}" -gt 0 ] && mem_pct=$(awk "BEGIN {printf \"%.2f\", 100*$mem_used/$mem_total}") || mem_pct=0
out "MEMORY_USED" "${mem_used:-0}"
out "MEMORY_TOTAL" "${mem_total:-0}"
out "MEMORY_PERCENT" "${mem_pct:-0}"
# Disk: root filesystem
eval $(df -B1 / 2>/dev/null | awk 'NR==2{printf "disk_used=%d disk_total=%d disk_pct=%s", $3, $2, $5}')
disk_pct=${disk_pct%%%}
out "DISK_USED" "${disk_used:-0}"
out "DISK_TOTAL" "${disk_total:-0}"
out "DISK_PERCENT" "${disk_pct:-0}"
out "DISK_FREE" "$(( disk_total - disk_used ))"
# Network: sum rx/tx (skip loopback)
net_rx=0; net_tx=0
while read -r iface rx _ _ _ _ _ _ _ tx _; do
  case "$iface" in *:*) continue;; esac
  net_rx=$((net_rx + rx)); net_tx=$((net_tx + tx))
done < /proc/net/dev 2>/dev/null || true
out "NETWORK_RECV" "${net_rx:-0}"
out "NETWORK_SENT" "${net_tx:-0}"
# Uptime seconds
read -r uptime _ < /proc/uptime 2>/dev/null || true
out "UPTIME_SEC" "${uptime:-0}"
echo "METRIC_END=1"
"""


def _parse_metrics_output(stdout: str) -> Dict[str, str]:
    """Parse METRIC_KEY=value lines from script output."""
    result = {}
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("METRIC_") and "=" in line:
            k, _, v = line.partition("=")
            result[k] = v.strip()
    return result


def _float(s: str, default: float = 0.0) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def _int(s: str, default: int = 0) -> int:
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return default


def _ts_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_metrics_local(script: str, timeout: float) -> tuple[str, str, int]:
    """Uruchom skrypt metryk lokalnie (dla vm04-orchestrator). Zwraca (stdout, stderr, exit_code)."""
    cmd = f"bash -s << 'METRICSEOF'\n{script}\nMETRICSEOF"
    start_utc = _ts_utc()
    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            ["bash", "-s"],
            input=script,
            capture_output=True,
            text=True,
            timeout=timeout,
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
        return (proc.stdout or "", proc.stderr or "", proc.returncode)
    except subprocess.TimeoutExpired:
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
        raise HealthCheckError("VM vm04 metrics script timed out")
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
        raise HealthCheckError(f"VM vm04 metrics failed: {e}") from e


def collect_system_metrics(
    vm_id: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
    response_time_sec: float = 0.0,
    error_count: int = 0,
    **kwargs: Any,
) -> SystemMetrics:
    """
    Collect system metrics from VM via execute_remote_command.
    On timeout or connection error, raises HealthCheckError (or returns unreachable metrics if preferred).
    Dla vm04 (orchestrator) uruchamia skrypt lokalnie bez SSH.
    """
    cfg = config or _load_config(config_path)
    if vm_id not in _allowed_vm_ids(cfg):
        raise ValueError(f"vm_id {vm_id} not allowed")
    script = _metrics_script()
    if vm_id == "vm04":
        stdout, stderr, exit_code = _run_metrics_local(script, timeout)
        result = SimpleNamespace(stdout=stdout, stderr=stderr, exit_code=exit_code)
    else:
        cmd = f"bash -s << 'METRICSEOF'\n{script}\nMETRICSEOF"
        try:
            result = execute_remote_command(
                vm_id,
                cmd,
                HEALTH_MONITOR_USER,
                timeout,
                config_path=config_path,
                config=cfg,
                **kwargs,
            )
        except Exception as e:
            raise HealthCheckError(f"VM {vm_id} unreachable or metrics failed: {e}") from e
    if result.exit_code != 0:
        raise HealthCheckError(
            f"VM {vm_id} metrics script failed: exit_code={result.exit_code}, stderr={result.stderr!r}"
        )
    raw = _parse_metrics_output(result.stdout or "")
    return SystemMetrics(
        vm_id=vm_id,
        cpu_percent=_float(raw.get("METRIC_CPU_PERCENT"), 0.0),
        load_avg=[
            _float(raw.get("METRIC_LOAD_1"), 0.0),
            _float(raw.get("METRIC_LOAD_5"), 0.0),
            _float(raw.get("METRIC_LOAD_15"), 0.0),
        ],
        memory_percent=_float(raw.get("METRIC_MEMORY_PERCENT"), 0.0),
        memory_used=_int(raw.get("METRIC_MEMORY_USED"), 0),
        memory_total=_int(raw.get("METRIC_MEMORY_TOTAL"), 0),
        disk_percent=_float(raw.get("METRIC_DISK_PERCENT"), 0.0),
        disk_free=_int(raw.get("METRIC_DISK_FREE"), 0),
        disk_total=_int(raw.get("METRIC_DISK_TOTAL"), 0),
        network_sent=_int(raw.get("METRIC_NETWORK_SENT"), 0),
        network_recv=_int(raw.get("METRIC_NETWORK_RECV"), 0),
        response_time_sec=response_time_sec,
        uptime_sec=_float(raw.get("METRIC_UPTIME_SEC"), 0.0),
        error_count=error_count,
        unreachable=False,
        raw=raw,
    )
