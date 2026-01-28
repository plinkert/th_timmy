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

## Upcoming steps

Further steps (for example VM setup scripts, database configuration, and other components) will be added here as they are defined. Each new step will follow the same layout: status, short description, and links to the module README, configuration, and testing.
