# Threat Hunting Automation Lab - th_timmy

Automated, repeatable, and reusable environment for performing Threat Hunting operations.

## Project Overview

This project provides a comprehensive threat hunting automation system with:
- Standardized MITRE ATT&CK-based playbooks
- Automated data flow from ingestion to AI/ML analysis
- Full workflow automation with n8n
- EDR/SIEM API integrations

## Architecture

The system consists of 4 virtual machines:

1. **VM-01: Ingest/Parser** - Data collection and normalization
2. **VM-02: Database** - PostgreSQL data storage
3. **VM-03: Analysis/Jupyter** - Interactive analysis and playbooks
4. **VM-04: Orchestrator** - Workflow automation with n8n

## Project Structure

```
th_timmy/
├── hosts/                    # VM-specific setup scripts
│   ├── vm01-ingest/
│   ├── vm02-database/
│   ├── vm03-analysis/
│   └── vm04-orchestrator/
├── automation_scripts/       # Core automation modules
│   ├── orchestrators/       # Orchestration
│   │   ├── remote_executor/ # Remote Execution Service (Step 0.1): remote commands & file transfer from VM04 via SSH
│   │   ├── repo_sync/       # Repository Sync (Step 0.2): sync on VM04, push to VM01–VM03 via rsync over SSH
│   │   └── config_manager/  # Configuration Management (Step 0.3): config sync, validation, backup, rollback
│   └── ...                  # (collectors, parsers, normalizers, utils — as added)
├── configs/                 # Configuration files (VM IPs, remote execution, etc.)
├── docs/                    # Documentation
├── tests/                   # Unit and integration tests
│   ├── unit/                # pytest unit tests (audit_logger, remote_executor, ssh_client, ssh_key_manager)
│   └── integration/         # e.g. run_remote_executor_integration.sh, run_repo_sync_integration.sh
├── pytest.ini               # pytest configuration
└── results/                 # Analysis results (gitignored)
```

## Current Status

**Phase 1: Deployment and Configuration** — In Progress

- [x] Project structure created
- [x] Git repository initialized
- [x] **Step 0.1 (Remote Execution)** — closed
- [x] **Step 0.2 (Repository Sync)** — closed
- [x] **Step 0.3 (Configuration Management)** — closed
- [ ] VM setup scripts
- [ ] Database configuration
- [ ] Component implementation

For a short summary of each step and links to setup, configuration, and testing, see **[docs/PHASES.md](docs/PHASES.md)**.

## Quick Start

### Prerequisites

- 4 Virtual Machines with Ubuntu Server 22.04 LTS
- Python 3.10+
- PostgreSQL 14+
- Docker (for n8n)

### Installation

See individual VM README files in `hosts/vmXX-*/README.md` for detailed installation instructions for each component.

### Automation on VM04 (orchestrator)

For running Python and automation from VM04 (including Remote Execution, Repository Sync, and Configuration Management):

- **Bootstrap environment:** `./hosts/vm04-orchestrator/bootstrap_env.sh` — prepares Python venv and dependencies (idempotent).
- **Run Python / tests:** `./hosts/vm04-orchestrator/run_python.sh` — always use this script instead of calling `python` directly (ensures env is ready; used by n8n and CI).
- **Configuration:** VM and Remote Execution settings are in `configs/config.yml`. Copy from `configs/config.example.yml` and replace placeholders (IPs, etc.). Never commit `config.yml`.

## Documentation

- [Implementation phases and status](docs/PHASES.md) — Summary of each step (what it does, status) and links to setup, configuration, and testing
- [Repository Sync Design](docs/REPO_SYNC_DESIGN.md) — How Repository Sync (Step 0.2) works and how it fits with Remote Execution
- [Enhanced Architecture Documentation](docs/ARCHITECTURE_ENHANCED.md) — System architecture
- [Data Flow Documentation](docs/DATA_FLOW.md) - Data flow through the system
- [Anonymization Policy](docs/ANONYMIZATION.md) - Data anonymization and privacy policy
- [User Guide for Hunters](docs/USER_GUIDE_HUNTER.md) - Guide for threat hunters
- [Configuration Guide](docs/CONFIGURATION.md) - System configuration
- [Hardening Guide](docs/HARDENING.md) - Security hardening procedures
- [Testing Guide](docs/TESTING.md) - Testing and validation procedures

## Development

### Setup Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

#### Central Configuration File

The central configuration file (`configs/config.yml`) contains network settings, VM IP addresses, and service configurations for all VMs.

1. Copy the example configuration file:
   ```bash
   cp configs/config.example.yml configs/config.yml
   ```

2. Edit `configs/config.yml` with your actual settings:
   - Replace placeholder IP addresses with your VM IPs
   - Configure network subnet and gateway
   - Set service ports if different from defaults
   - Configure data retention (default: 90 days)

3. **Important**: Never commit `configs/config.yml` to the repository (it's in `.gitignore`)

#### VM-Specific Configuration

Each VM has its own configuration file in `hosts/vmXX-*/config.example.yml`:
- **VM-02**: Database configuration (PostgreSQL settings, allowed IPs)
- **VM-03**: JupyterLab configuration (IP, port, token/password)
- **VM-04**: n8n configuration (port, basic auth credentials)

See [Configuration Documentation](docs/CONFIGURATION.md) for detailed instructions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Important**: This software is designed for threat hunting operations in a lab environment. Users are responsible for implementing appropriate security measures and complying with data protection regulations.

## Authors

Threat Hunting Team

