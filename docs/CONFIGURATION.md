# Configuration Guide

This guide explains how to configure the Threat Hunting Lab system.

## Central Configuration File

The central configuration file (`configs/config.yml`) contains network settings, VM IP addresses, and service configurations for all VMs.

### Setup

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

## Remote Execution (Step 0.1)

The Remote Execution Service uses VM and SSH settings from the central config. Relevant sections:

### `remote_execution` section

In `configs/config.yml` (see `configs/config.example.yml`), the `remote_execution` section controls timeouts, retries, key storage, and checksums:

```yaml
remote_execution:
  default_timeout: 30        # Command timeout (seconds)
  default_retry: 3           # Retries on transient failure
  key_storage_path: "~/.ssh/th_timmy_keys"  # SSH key directory (used by Remote Executor)
  checksum_algorithm: "sha256" # For file transfer verification
  # allowed_vm_ids: ["vm01", "vm02", "vm03", "vm04"]  # optional; default from vms.enabled
```

- **key_storage_path**: Directory where SSH keys for VM01–VM04 are stored. Use `hosts/vm04-orchestrator/setup_ssh_keys.sh` to generate and deploy keys; the script prepares keys for this path.
- VM data (IP, user, port) is taken from the `vms` section: `vms.vm01.ip`, `vms.vm01.ssh_user`, `vms.vm01.ssh_port`, `vms.vm01.enabled`, and similarly for vm02, vm03, vm04.

See [automation_scripts/orchestrators/remote_executor/README.md](../automation_scripts/orchestrators/remote_executor/README.md) for installation, usage, and troubleshooting.

### Configuration Structure

```yaml
vms:
  vm01:
    name: "threat-hunt-vm01"
    ip: "10.0.0.10"  # Replace with your VM-01 IP
    role: "ingest-parser"
    enabled: true
  
  vm02:
    name: "threat-hunt-vm02"
    ip: "10.0.0.11"  # Replace with your VM-02 IP
    role: "database"
    enabled: true
  
  vm03:
    name: "threat-hunt-vm03"
    ip: "10.0.0.12"  # Replace with your VM-03 IP
    role: "analysis-jupyter"
    enabled: true
  
  vm04:
    name: "threat-hunt-vm04"
    ip: "10.0.0.13"  # Replace with your VM-04 IP
    role: "orchestrator-n8n"
    enabled: true

network:
  subnet: "10.0.0.0/24"  # Replace with your subnet
  gateway: "10.0.0.1"     # Replace with your gateway

services:
  postgresql:
    port: 5432
    host: "vm02"
  jupyterlab:
    port: 8888
    host: "vm03"
  n8n:
    port: 5678
    host: "vm04"

database:
  host: "vm02"  # Or use IP address
  port: 5432
  name: "threat_hunting"
  user: "threat_hunter"
  # password: Set in .env file

results:
  retention_days: 90  # Data retention: 90 days
```

## Data Retention Configuration

The system is configured with a **90-day data retention** policy by default. This is production-ready and ensures compliance with most data retention requirements.

### Changing Retention Period

To change the retention period, edit `configs/config.yml`:

```yaml
results:
  retention_days: 30  # Change to desired number of days
```

**Note**: The actual implementation of data retention is done in VM-02 (PostgreSQL) - see VM-02 documentation for details.

## Hardening Configuration

Security hardening configuration is centralized in `configs/config.yml`:

```yaml
hardening:
  # SSH Configuration (common for all VMs)
  ssh:
    port: 22                    # SSH port
    timeout: 300                # SSH connection timeout
    disable_root_login: true    # Disable root login
  
  # Firewall Configuration
  firewall:
    allowed_network: ""         # Network CIDR to restrict access
  
  # VM-specific settings
  vm01:
    collector_ports: ""         # Collector ports for VM-01
    enable_auditd: false        # Enable auditd
  
  vm02:
    enable_auditd: false        # Enable auditd
  
  vm03:
    enable_auditd: false        # Enable auditd
  
  vm04:
    enable_auditd: false        # Enable auditd
```

All hardening scripts (`harden_vm01.sh`, `harden_vm02.sh`, etc.) automatically read from this central configuration.

## VM-Specific Configuration

Each VM has its own configuration file in `hosts/vmXX-*/config.example.yml`:

### VM-02: Database Configuration

- PostgreSQL settings
- Allowed IP addresses for database connections
- Database user and password settings
- Data retention configuration (90 days)

### VM-03: JupyterLab Configuration

- JupyterLab IP and port
- Token/password for authentication
- Notebook directory settings

### VM-04: n8n Configuration

- n8n port
- Basic auth credentials
- Workflow storage location

## Environment Variables

Sensitive configuration (passwords, API keys) should be stored in `.env` file:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# JupyterLab
JUPYTER_TOKEN=your_jupyter_token

# n8n
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your_secure_password
```

**Important**: Never commit `.env` file to the repository!

## Configuration Examples

### Development Environment

```yaml
vms:
  vm01:
    ip: "192.168.1.10"
  vm02:
    ip: "192.168.1.11"
  vm03:
    ip: "192.168.1.12"
  vm04:
    ip: "192.168.1.13"

network:
  subnet: "192.168.1.0/24"
  gateway: "192.168.1.1"
```

### Production Environment

```yaml
vms:
  vm01:
    ip: "10.0.0.10"
  vm02:
    ip: "10.0.0.11"
  vm03:
    ip: "10.0.0.12"
  vm04:
    ip: "10.0.0.13"

network:
  subnet: "10.0.0.0/24"
  gateway: "10.0.0.1"

results:
  retention_days: 90
```

## Troubleshooting

### Problem: Cannot connect to VMs

- Check IP addresses in `configs/config.yml`
- Verify network connectivity: `ping <vm_ip>`
- Check firewall rules on VMs

### Problem: Database connection fails

- Verify PostgreSQL is running: `systemctl status postgresql`
- Check database credentials in `.env`
- Verify firewall allows connections on port 5432

### Problem: Configuration file not found

- Ensure `configs/config.yml` exists (copy from `configs/config.example.yml`)
- Check file permissions: `ls -l configs/config.yml`
- Verify you're running scripts from the project root directory

## Best Practices

1. **Always use example files**: Copy `*.example.yml` files before editing
2. **Never commit sensitive data**: Keep `config.yml` and `.env` in `.gitignore`
3. **Use environment variables**: Store passwords and tokens in `.env`
4. **Document changes**: Keep notes of any custom configurations
5. **Test after changes**: Run connection tests after modifying configuration

