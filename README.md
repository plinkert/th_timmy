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
├── automation-scripts/       # Core automation modules
│   ├── collectors/          # Data collection
│   ├── parsers/             # Data parsing
│   ├── normalizers/         # Data normalization
│   ├── orchestrators/       # Orchestration
│   └── utils/               # Utility modules
├── playbooks/               # Threat hunting playbooks
│   └── template/            # Playbook template
├── configs/                 # Configuration files
├── docs/                    # Documentation
└── results/                 # Analysis results
```

## Current Status

**Phase 1: Deployment and Configuration** - In Progress
- [x] Project structure created
- [x] Git repository initialized
- [ ] VM setup scripts
- [ ] Database configuration
- [ ] Component implementation

## Quick Start

### Prerequisites

- 4 Virtual Machines with Ubuntu Server 22.04 LTS
- Python 3.10+
- PostgreSQL 14+
- Docker (for n8n)

### Installation

See [docs/PHASE1_DEPLOYMENT.md](docs/PHASE1_DEPLOYMENT.md) for detailed installation instructions.

## Documentation

- [Phase 1 Deployment Guide](docs/PHASE1_DEPLOYMENT.md) - Installation and setup
- [Architecture Documentation](docs/ARCHITECTURE.md) - System architecture
- [User Interface Guide](docs/USER_INTERFACE.md) - UI documentation

**Note**: Planning documents are located in `project plan/` directory (excluded from Git).

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

1. Copy example configuration files:
   ```bash
   cp configs/config.example.yml configs/config.yml
   cp configs/env.example .env
   ```

2. Edit configuration files with your settings (never commit these!)

## License

[To be determined]

## Authors

Threat Hunting Team

