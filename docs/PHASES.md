# Implementation Phases and Status

This document lists the main implementation steps (phases) of the Threat Hunting Lab and their current status. For each step you will find a short summary and links to the full guides: how to set things up, how to configure, and how to run tests.

---

## How to use this document

- **Status** tells you whether the step is done (closed) or still in progress.
- **What it does** gives a brief, plain-language description of the step.
- **Where to find more** points you to the right place for setup, configuration, and testing. Start with the module README for a full overview; use the Configuration and Testing guides when you need to change settings or run checks.

---

## Step 0.1 — Remote Execution

| | |
|---|---|
| **Status** | Closed |
| **What it does** | The orchestrator machine (VM04) can run commands and copy files on all four machines (VM01–VM04) over a secure connection. No one has to log in manually; everything is driven from VM04. Access uses keys instead of passwords, and all actions are logged. |
| **Module README** | [automation_scripts/orchestrators/remote_executor/README.md](../automation_scripts/orchestrators/remote_executor/README.md) — installation, usage, and troubleshooting. |
| **Configuration** | [Configuration Guide — Remote Execution](CONFIGURATION.md#remote-execution-step-01): where to set timeouts, key location, and machine addresses. |
| **Testing** | [Testing Guide — Remote Execution tests](TESTING.md#remote-execution-service-tests-step-01): how to run unit and integration tests. |
| **Security** | [Hardening Guide — SSH key management](HARDENING.md#ssh-key-management-remote-execution-step-01): key storage, rotation, and safe use. |

---

## Step 0.2 — Repository Sync

| | |
|---|---|
| **Status** | Closed |
| **What it does** | The project files are kept in sync from VM04 to the other machines (VM01–VM03). VM04 holds the main copy and pushes updates over the network. The other machines receive a copy of the files; they do not need to run version control themselves. This keeps everyone on the same version of scripts and config. |
| **Module README** | [automation_scripts/orchestrators/repo_sync/README.md](../automation_scripts/orchestrators/repo_sync/README.md) — requirements, configuration, and usage. |
| **Design and model** | [Repository Sync Design](REPO_SYNC_DESIGN.md): how sync works, what runs where, and how it fits with Step 0.1. |
| **Configuration** | [Configuration Guide](CONFIGURATION.md): central config file; repository paths and options are described there. |
| **Testing** | [Testing Guide — Repository Sync tests](TESTING.md#repository-sync-service-tests-step-02): how to run the sync-related tests. |

---

## Step 0.3 — Configuration Management Service

| | |
|---|---|
| **Status** | Closed |
| **What it does** | Central management and sync of config files on all VMs. Configs are validated (JSON Schema), backed up (encrypted, min. 90-day retention), and written atomically; on write failure, the previous version is restored from backup. |
| **Module README** | [automation_scripts/orchestrators/config_manager/README.md](../automation_scripts/orchestrators/config_manager/README.md) — requirements, config, usage, tests. |
| **Configuration** | [Configuration Guide](CONFIGURATION.md): `config_management` section (backup_location, config_paths, config_schemas, schema_dir). |
| **Testing** | [Testing Guide — Configuration Management tests](TESTING.md#configuration-management-service-tests-step-03): unit and integration tests. |

---

## Step 0.4 — Health Monitoring Service

| | |
|---|---|
| **Status** | Closed |
| **What it does** | Central collection of VM metrics (CPU, memory, disk, response time, uptime), threshold evaluation, alerts (e-mail, Slack, SMS), and Prometheus exposition on VM04. Runs health_check.sh remotely; unreachable VM returns error without hanging. |
| **Module README** | [automation_scripts/orchestrators/health_monitor/README.md](../automation_scripts/orchestrators/health_monitor/README.md) — requirements, config, usage, Prometheus/Grafana, tests. |
| **Configuration** | [Configuration Guide](CONFIGURATION.md): `health_monitoring` section (check_interval, health_check_script_path, thresholds, alert_channels, prometheus_expose_port). |
| **Testing** | [Testing Guide — Health Monitoring tests](TESTING.md#health-monitoring-service-tests-step-04): unit and integration tests. |

---

---

## Step 1.1 — Playbook Structure with data_sources

| | |
|---|---|
| **Status** | In place |
| **What it does** | Playbook structure with `technique_description` and `data_sources` in metadata.yml. Validator rejects playbooks without required fields. Query loader reads .sql, .json, .kql files. Five example playbooks (T1055, T1059, T1562, T1082, T1486). |
| **Module README** | [docs/PLAYBOOKS.md](PLAYBOOKS.md) — format, examples, API. |
| **Testing** | Unit: `tests/unit/test_playbook_validator.py`, `test_query_loader.py`. Integration: `tests/integration/run_playbooks_integration.sh`. |

---

## Upcoming steps

Further steps (for example VM setup scripts, database configuration, and other components) will be added here as they are defined. Each new step will follow the same layout: status, short description, and links to the module README, configuration, and testing.
