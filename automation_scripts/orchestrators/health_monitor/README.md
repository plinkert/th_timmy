# Health Monitoring Service (Step 0.4)

Central collection of VM metrics (CPU, memory, disk, network, response time, uptime), threshold evaluation, alerts (e-mail, Slack, SMS), and Prometheus exposition.

**Package path:** `automation_scripts.orchestrators.health_monitor`

---

## Requirements

- **Step 0.1 (Remote Execution)** – `execute_remote_command` to run health_check.sh and collect metrics on VMs.
- **Step 0.2 (Repository Sync)** – repo with `hosts/vmXX/health_check.sh`; paths on remote VMs from config (e.g. after sync: `/home/thadmin/th_timmy/hosts/vm01-ingest/health_check.sh`).
- **configs/config.yml** – section **health_monitoring** (see `config.example.yml`).
- **prometheus_client** (optional) – for `/metrics` exposition on VM04.

---

## Config

In `configs/config.yml` add (or copy from `config.example.yml`):

```yaml
health_monitoring:
  check_interval: 300
  health_check_script_path:
    vm01: "/home/thadmin/th_timmy/hosts/vm01-ingest/health_check.sh"
    vm02: "/home/thadmin/th_timmy/hosts/vm02-database/health_check.sh"
    vm03: "/home/thadmin/th_timmy/hosts/vm03-analysis/health_check.sh"
    vm04: "/home/thadmin/th_timmy/hosts/vm04-orchestrator/health_check.sh"
    default: "/home/thadmin/th_timmy/hosts/vm04-orchestrator/health_check.sh"
  thresholds:
    cpu_warning: 80
    cpu_critical: 95
    cpu_sustained_seconds: 300
    memory_warning: 85
    memory_critical: 90
    disk_free_warning_percent: 10
    response_time_warning_seconds: 2
  alert_channels:
    email: { smtp_host: "", smtp_port: 587, from_addr: "", to_addrs: [] }
    slack: { webhook_url: "" }
    sms: { provider: "" }
  alert_dedup_window_seconds: 900
  prometheus_expose_port: 9090
```

- **health_check_script_path:** per vm_id or `default`; path on the **remote** VM. Missing path → status **degraded**, not crash.
- **E-mail:** required by ticket; set `TH_TIMMY_SMTP_USER`, `TH_TIMMY_SMTP_PASSWORD` (and smtp_host, to_addrs in config).
- **Slack:** optional; `webhook_url` or `TH_TIMMY_SLACK_WEBHOOK_URL`.
- **Prometheus:** start exporter with `start_prometheus_exporter(port)`; Prometheus scrapes VM04 at `:9090/metrics`.

---

## Usage

From project root with `PYTHONPATH` set (e.g. via `run_python.sh`):

```python
from automation_scripts.orchestrators.health_monitor import (
    check_vm_health,
    schedule_health_checks,
    get_health_status,
    collect_system_metrics,
    check_thresholds,
    send_alert,
    start_prometheus_exporter,
)

# Single VM health check (runs health_check.sh, collects metrics, evaluates thresholds, sends alerts)
status = check_vm_health("vm01")

# Cached status (or refresh first)
all_status = get_health_status(refresh=True)
vm01_status = get_health_status("vm01", refresh=True)

# Run one round for all VMs
schedule_health_checks(interval=300, run_once=True)

# Expose Prometheus /metrics on VM04 (e.g. port 9090)
start_prometheus_exporter(9090)
```

---

## Thresholds and alerts

- **CPU:** alert only if above threshold for **cpu_sustained_seconds** (e.g. 5 min) to avoid false alarms on short spikes.
- **Memory, disk free, response time:** compared to config thresholds; warning/critical levels.
- **Deduplication:** same (vm_id, metric, level) in **alert_dedup_window_seconds** → only one alert sent.
- **VM unreachable:** status `unreachable`; optional alert "VM unreachable"; monitor does not hang (timeout).

---

## Prometheus and Grafana

- **Exposition:** call `start_prometheus_exporter(port)` (e.g. from n8n or a small runner); metrics are updated on each `check_vm_health`. Gauges: `th_timmy_cpu_percent`, `th_timmy_memory_percent`, `th_timmy_disk_percent`, `th_timmy_response_time_sec`, `th_timmy_uptime_sec`, `th_timmy_error_count`, `th_timmy_unreachable` (labels: `vm_id`).
- **Prometheus:** add a scrape job for VM04, e.g. `http://vm04:9090/metrics`.
- **Grafana:** use Prometheus as data source; dashboards update on scrape interval.

---

## Tests

- **Unit:** `./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/test_metrics_collector.py tests/unit/test_alert_manager.py tests/unit/test_health_monitor.py -v`
- **Integration:** `./tests/integration/run_health_monitor_integration.sh` (from project root on VM04). See script header for run instructions and [docs/TESTING.md](../../../docs/TESTING.md).
