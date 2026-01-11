# Threat Hunting Automation Lab - th_timmy

Automated, repeatable, and reusable environment for performing Threat Hunting operations based on MITRE ATT&CK framework.

## Project Overview

This project provides a comprehensive threat hunting automation system that standardizes and automates the entire threat hunting workflow. The system is designed to help security teams efficiently hunt for threats across their infrastructure using a structured, repeatable approach.

**Key Features:**
- Standardized MITRE ATT&CK-based playbooks
- Automated data flow from ingestion to AI/ML analysis
- Full workflow automation with n8n
- Centralized management dashboard
- Remote execution and repository synchronization
- EDR/SIEM API integrations (planned)

## Architecture

The system consists of 4 virtual machines, each serving a specific role in the threat hunting pipeline:

1. **VM-01: Ingest/Parser** - Data collection, parsing, and normalization from various sources
2. **VM-02: Database** - PostgreSQL data storage with 90-day retention policy
3. **VM-03: Analysis/Jupyter** - Interactive analysis environment with JupyterLab and playbooks
4. **VM-04: Orchestrator** - Workflow automation with n8n and central management dashboard

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

**Phase 0: Central Management Infrastructure** - Completed
- [x] Remote execution service
- [x] Repository synchronization
- [x] Configuration management
- [x] Health monitoring
- [x] Management dashboard (basic)

**Phase 1: Threat Hunting Foundations** - In Progress
- [x] Project structure created
- [x] VM setup scripts
- [x] Database configuration
- [x] Basic automation scripts
- [ ] Playbook engine
- [ ] Query generator
- [ ] Data anonymization

**Phase 2: AI Integration** - Planned
- [ ] AI service integration
- [ ] Findings validation
- [ ] Executive summary generation

## Quick Start

### Prerequisites

- 4 Virtual Machines with Ubuntu Server 22.04 LTS
- Python 3.10+
- PostgreSQL 14+
- Docker (for n8n)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd th_timmy
   ```

2. **Configure the system:**
   ```bash
   cp configs/config.example.yml configs/config.yml
   # Edit configs/config.yml with your VM IP addresses
   ```

3. **Install on each VM:**
   - VM-01: `cd hosts/vm01-ingest && sudo ./install_vm01.sh`
   - VM-02: `cd hosts/vm02-database && sudo ./install_vm02.sh`
   - VM-03: `cd hosts/vm03-analysis && sudo ./install_vm03.sh`
   - VM-04: `cd hosts/vm04-orchestrator && sudo ./install_vm04.sh`

4. **Verify installation:**
   Run `health_check.sh` on each VM to verify the installation.

For detailed installation instructions, see the VM-specific README files in `hosts/vmXX-*/README.md`.

## Documentation

### Core Documentation
- [Quick Start Guide](docs/QUICK_START.md) - Get up and running quickly
- [Architecture Documentation](docs/ARCHITECTURE.md) - System architecture and design
- [Configuration Guide](docs/CONFIGURATION.md) - System configuration and setup
- [Testing Guide](docs/TESTING.md) - Testing procedures and validation
- [Hardening Guide](docs/HARDENING.md) - Security hardening procedures

### VM-Specific Documentation
- [VM-01: Ingest/Parser](hosts/vm01-ingest/README.md) - Installation and setup
- [VM-02: Database](hosts/vm02-database/README.md) - PostgreSQL setup and configuration
- [VM-03: Analysis/Jupyter](hosts/vm03-analysis/README.md) - JupyterLab setup
- [VM-04: Orchestrator](hosts/vm04-orchestrator/README.md) - n8n setup and workflows

### Testing
- [Test Suite Documentation](tests/README.md) - Test suite overview and usage

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

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide for Python code
- Write tests for new features
- Update documentation for any changes
- Ensure all tests pass before submitting PR

## Troubleshooting

### Common Issues

**Problem: Cannot connect to VMs**
- Check IP addresses in `configs/config.yml`
- Verify network connectivity: `ping <vm_ip>`
- Check firewall rules on VMs

**Problem: Database connection fails**
- Verify PostgreSQL is running: `systemctl status postgresql`
- Check database credentials in `.env` file
- Verify firewall allows connections on port 5432

**Problem: JupyterLab not accessible**
- Check if JupyterLab is running: `systemctl status jupyter`
- Verify port 8888 is open: `netstat -tlnp | grep 8888`
- Check firewall rules

For more troubleshooting tips, see the VM-specific README files.

## Security

⚠️ **Important Security Notes:**
- Never commit `config.yml` files with real IP addresses or passwords
- Use strong passwords for all services
- Apply security hardening after installation (see [Hardening Guide](docs/HARDENING.md))
- Keep all systems updated with latest security patches
- Review firewall rules regularly

## License

This project is licensed under the Business Source License 1.1 (BUSL 1.1). 

**Key Points:**
- ✅ Open source - you can view, use, and modify the code
- ✅ Free for personal, educational, and research use
- ✅ Free for internal business use (non-commercial)
- ❌ **Commercial use requires written permission** - you cannot sell, license, or commercialize this software without explicit authorization from the copyright holder

The license will automatically convert to Apache License 2.0 on **January 1, 2029**, making it fully open source at that time.

For commercial use inquiries, please contact the project maintainers. See the [LICENSE](LICENSE) file for full terms and conditions.

## Authors

Threat Hunting Team

## Acknowledgments

- MITRE ATT&CK framework for threat hunting methodology
- n8n for workflow automation
- PostgreSQL community for database support

