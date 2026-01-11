# Configuration Guide

This guide walks you through configuring the Threat Hunting Lab system. We'll cover the central configuration file, VM-specific settings, and some common scenarios you might encounter.

## Central Configuration File

Everything starts with the central configuration file at `configs/config.yml`. This file holds all the network settings, VM IP addresses, and service configurations that the system needs to operate.

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

By default, the system keeps data for **90 days** before automatically cleaning it up. This works well for most production environments and helps with compliance requirements. If you need a different retention period, you can change it.

### Changing Retention Period

Edit the `results` section in `configs/config.yml`:

```yaml
results:
  retention_days: 30  # Keep data for 30 days instead of 90
```

**Important:** After changing this, you'll also need to update the retention setting in VM-02's configuration file (`hosts/vm02-database/config.yml`) and restart the cleanup job. Check the VM-02 README for the exact steps.

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

### Can't connect to VMs?

First, double-check your IP addresses in `configs/config.yml` - typos happen! Then try:

```bash
# Test basic connectivity
ping <vm_ip>

# Check if SSH is working
ssh user@<vm_ip>
```

If ping works but SSH doesn't, check the firewall on the target VM. The hardening scripts should have opened port 22, but it's worth verifying with `sudo ufw status`.

### Database connection failing?

This is usually one of three things:

1. **PostgreSQL isn't running:**
   ```bash
   sudo systemctl status postgresql
   # If it's stopped, start it:
   sudo systemctl start postgresql
   ```

2. **Wrong password:** Check your `.env` file or the password you set in VM-02's config.yml

3. **Firewall blocking:** Make sure port 5432 is open and your IP is in the `allowed_ips` list in VM-02's config

### Configuration file not found?

If scripts complain about missing config files:

```bash
# Make sure you're in the project root
cd ~/th_timmy

# Check if the file exists
ls -l configs/config.yml

# If it doesn't exist, copy from example
cp configs/config.example.yml configs/config.yml
```

## Best Practices

Here are some tips we've learned the hard way:

1. **Always start from example files** - Don't create config files from scratch. Copy the `.example.yml` files first. They have all the required fields and comments explaining what each setting does.

2. **Never commit sensitive data** - The `.gitignore` file should already exclude `config.yml` and `.env`, but double-check before committing. We've seen passwords in repos before, and it's not pretty.

3. **Use environment variables for secrets** - Store passwords and API keys in `.env` files, not in the YAML configs. This makes it easier to manage different environments (dev, staging, prod).

4. **Test after changes** - After modifying configuration, run the connection tests (`./hosts/shared/test_connections.sh`) to make sure everything still works. It only takes a minute and can save you hours of debugging later.

5. **Document your customizations** - If you change something from the defaults, make a note somewhere. Future you (or your teammates) will thank you.

