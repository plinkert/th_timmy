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
| **Status** | Closed |
| **What it does** | Playbook structure with `technique_description` and `data_sources` in metadata.yml. Validator rejects playbooks without required fields. Query loader reads .sql, .json, .kql or .yml/.yaml (YAML: elk.yml, ms_defender.yml with query_id/query_ids). Five example playbooks (T1055, T1059, T1562, T1082, T1486). Sections: output, triage, response (2025-01-27 YAML migration). |
| **Module README** | [automation_scripts/playbooks/README.md](../automation_scripts/playbooks/README.md), [docs/PLAYBOOKS.md](PLAYBOOKS.md) — format, examples, API. |
| **Configuration** | TBD (schema in `configs/schemas/`). |
| **Testing** | [Testing Guide — Playbook Structure tests](TESTING.md#playbook-structure-tests-step-11): unit and integration tests. |

---

## Phase 0 (continued): Management interfaces

## Step 0.5 — Management Dashboard (n8n)

| | |
|---|---|
| **Status** | Closed |
| **What it does** | Central n8n interface for VM management: status cards (OK/warning/critical), buttons to trigger repo sync, config backup, and health checks. API endpoints in hunt_api (/api/v1/dashboard/*); workflow management-dashboard.json. |
| **Module README** | [hosts/vm04-orchestrator/README.md](../hosts/vm04-orchestrator/README.md) — Management Dashboard section. |
| **Configuration** | `management_dashboard` in config; `TH_DASHBOARD_API_KEY` optional; `X-User-Role` header (admin/hunter/read_only). |
| **Testing** | [Testing Guide — Management Dashboard tests](TESTING.md#management-dashboard-tests-step-05): unit and integration tests. |

---

## Step 0.6 — Testing Management Interface

| | |
|---|---|
| **Status** | To do |
| **What it does** | Remote execution of tests (connections, data flow, health) from n8n. Test results and history stored centrally. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Step 0.7 — Deployment Management Interface

| | |
|---|---|
| **Status** | To do |
| **What it does** | Manage VM installation and updates from n8n. Run install scripts remotely, collect logs, verify deployment. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Step 0.8 — Hardening Management Interface

| | |
|---|---|
| **Status** | To do |
| **What it does** | Run hardening scripts from n8n. Pre/post security tests, before/after reports. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Phase 1 (continued): Threat Hunting foundations

## Step 1.2 — Query Generator

| | |
|---|---|
| **Status** | Closed |
| **What it does** | Auto-generate queries for selected hunts and tools (manual/API). Loads from playbooks via query_loader, filters by tool and mode, optionally substitutes placeholders, saves to `queries_generated/`. |
| **Module README** | [automation_scripts/playbooks/README.md](../automation_scripts/playbooks/README.md) — Query Generator section, generate_queries(), adding templates. |
| **Configuration** | output_dir (default: PROJECT_ROOT/queries_generated), time_range_days (default: 7). |
| **Testing** | [Testing Guide — Query Generator tests](TESTING.md#query-generator-tests-step-12): unit and integration tests. |

---

## Step 1.3 — Deterministic Anonymization with Mapping Table

| | |
|---|---|
| **Status** | Closed |
| **What it does** | Anonymize data before AI processing; mapping table for deterministic deanonymization. Mapping stored only on VM01/VM02 (encrypted). HMAC-SHA256 pseudonymization; `DeterministicAnonymizer`, `MappingStore`, `create_anonymizer`. |
| **Module README** | [automation_scripts/anonymization/README.md](../automation_scripts/anonymization/README.md), [automation_scripts/security/README.md](../automation_scripts/security/README.md). See [ANONYMIZATION.md](ANONYMIZATION.md). |
| **Configuration** | `anonymization` in config; env: `TH_ANONYMIZATION_PASSPHRASE`, `TH_ANONYMIZATION_SECRET`, `TH_ANONYMIZATION_SECRET_PATH`. |
| **Testing** | [Testing Guide — Anonymization tests](TESTING.md#deterministic-anonymization-tests-step-13): unit and integration tests. |

---

## Step 1.4 — n8n UI: Hunt and Tool Selection Form

| | |
|---|---|
| **Status** | Closed |
| **What it does** | Form in n8n for selecting hunts, tools, and mode (manual/API). Hunt API (hunt_api.py) provides POST /generate-queries; workflow calls it and stores session_id in queries_generated/sessions/. |
| **Module README** | [hosts/vm04-orchestrator/README.md](../hosts/vm04-orchestrator/README.md) — Hunt API, workflow import, run_hunt_api.py. |
| **Configuration** | hunt_api runs in Docker (port 8000) or on host via run_hunt_api.py. Workflow: hosts/vm04-orchestrator/n8n/workflows/hunt-selection-workflow.json. |
| **Testing** | [Testing Guide — n8n Hunt Selection tests](TESTING.md#n8n-hunt-selection-tests-step-14): integration tests for hunt_api. |

---

## Step 1.5 — Data Package: Structure and Validation

| | |
|---|---|
| **Status** | Closed |
| **What it does** | Standard DataPackage format (id, source, timestamp, data, anonymized, context). JSON Schema validation; validate(), to_dict(), from_dict(); 5 MB size limit. |
| **Module README** | [automation_scripts/data_package/README.md](../automation_scripts/data_package/README.md). |
| **Configuration** | Schema: `configs/schemas/data_package_schema.json`; size limit configurable in validate(). |
| **Testing** | [Testing Guide — Data Package tests](TESTING.md#data-package-tests-step-15): unit and integration tests. |

---

## Step 1.6 — Playbook Validator (extended)

| | |
|---|---|
| **Status** | To do |
| **What it does** | Extended playbook validation: directory structure, file presence, query correctness. (Basic validator is in Step 1.1.) |
| **Module README** | TBD. See [PLAYBOOKS.md](PLAYBOOKS.md). |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Step 1.7 — Playbook Management Interface

| | |
|---|---|
| **Status** | To do |
| **What it does** | n8n interface for creating, editing, validating, and testing playbooks. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Phase 2: Playbook Engine and Analysis

## Step 2.1 — Playbook Engine (Deterministic Analysis)

| | |
|---|---|
| **Status** | Done |
| **What it does** | Deterministic analysis engine: `run_analysis(DataPackage, playbook_metadata)` applies `analysis_rules` (e.g. threshold) with optional `field_mapping`, returns `List[Finding]` with evidence_ids (indices in DataPackage.data). |
| **Module README** | [automation_scripts/playbooks/README.md](../automation_scripts/playbooks/README.md) (run_analysis, Finding, analysis_rules, field_mapping). |
| **Configuration** | Playbook `metadata.yml`: optional `analysis_rules`, `field_mapping`. Schema: [configs/schemas/playbook_metadata.json](../configs/schemas/playbook_metadata.json). |
| **Testing** | Unit: `tests/unit/test_playbook_engine.py`. Integration: `tests/integration/run_playbook_engine_integration.sh`. See [TESTING.md](TESTING.md#playbook-engine-tests-step-21). |

---

## Step 2.2 — Pipeline Integration: n8n → VM01 → VM02 → VM03

| | |
|---|---|
| **Status** | To do |
| **What it does** | End-to-end data flow: run queries on VM01, collect results, anonymize on VM02, analyze on VM03, store findings. |
| **Module README** | TBD. See [DATA_FLOW.md](DATA_FLOW.md). |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Step 2.3 — Evidence & Findings: Structure and Storage

| | |
|---|---|
| **Status** | To do |
| **What it does** | Database schema for findings and evidence. Store findings with references to evidence on VM02. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Phase 3: AI Integration

## Step 3.1 — AI Service (OpenAI API Integration)

| | |
|---|---|
| **Status** | To do |
| **What it does** | Service to validate findings and generate executive summary via OpenAI (or similar) API. Only anonymized data sent to AI. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Step 3.2 — AI Review Workflow

| | |
|---|---|
| **Status** | To do |
| **What it does** | n8n workflow: send findings to AI for validation, store `false_positive` and `ai_feedback` in database. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Step 3.3 — Executive Summary Generator

| | |
|---|---|
| **Status** | To do |
| **What it does** | Generate executive summary (Markdown) for stakeholders using AI. Stored in `/reports`. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Phase 4: Deanonymization and Reporting

## Step 4.1 — Deanonymization Service

| | |
|---|---|
| **Status** | To do |
| **What it does** | Deterministic deanonymization for final reports. Mapping table access only on VM01/VM02. |
| **Module README** | TBD. See [ANONYMIZATION.md](ANONYMIZATION.md). |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Step 4.2 — Final Report Generator

| | |
|---|---|
| **Status** | To do |
| **What it does** | Generate final report (Markdown/PDF) combining executive summary and deanonymized findings. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Step 4.3 — n8n Workflow: Full End-to-End Pipeline

| | |
|---|---|
| **Status** | To do |
| **What it does** | Complete workflow from hunt selection to final report and notification. |
| **Module README** | TBD. |
| **Configuration** | TBD. |
| **Testing** | TBD. |

---

## Documentation and Tests (DOC-01, DOC-02)

| | |
|---|---|
| **Status** | To do |
| **What it does** | Full documentation: architecture, data flow, anonymization, management dashboard, user guide for hunters. |
| **Module README** | [ARCHITECTURE_ENHANCED.md](ARCHITECTURE_ENHANCED.md), [DATA_FLOW.md](DATA_FLOW.md), [ANONYMIZATION.md](ANONYMIZATION.md), [USER_GUIDE_HUNTER.md](USER_GUIDE_HUNTER.md). |
| **Configuration** | N/A. |
| **Testing** | Documentation review, spell check, link verification. |
