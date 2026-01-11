# Quick Start Guide

This guide will help you get the Threat Hunting Automation Lab up and running quickly.

## Prerequisites

Before you begin, ensure you have:

- **4 Virtual Machines** with Ubuntu Server 22.04 LTS installed
- **Network connectivity** between all VMs
- **SSH access** to all VMs (preferably with SSH keys)
- **Root/sudo privileges** on all VMs
- **Internet access** on all VMs for package installation

### Minimum VM Specifications

- **VM-01 (Ingest)**: 2 CPU, 4GB RAM, 20GB disk
- **VM-02 (Database)**: 2 CPU, 4GB RAM, 50GB disk (more for larger datasets)
- **VM-03 (Analysis)**: 4 CPU, 8GB RAM, 30GB disk
- **VM-04 (Orchestrator)**: 2 CPU, 4GB RAM, 20GB disk

## Step 1: Clone and Configure

### 1.1 Clone the Repository

On VM-04 (or your management machine), clone the repository:

```bash
cd ~
git clone <repository-url> th_timmy
cd th_timmy
```

### 1.2 Configure the System

Copy the example configuration and edit it:

```bash
cp configs/config.example.yml configs/config.yml
nano configs/config.yml
```

**Important settings to configure:**
- Replace all placeholder IP addresses (`10.0.0.10`, `10.0.0.11`, etc.) with your actual VM IPs
- Set your network subnet and gateway
- Configure service ports if different from defaults
- Set data retention period (default: 90 days)

**Example configuration:**
```yaml
vms:
  vm01:
    ip: "192.168.1.10"  # Your VM-01 IP
  vm02:
    ip: "192.168.1.11"  # Your VM-02 IP
  vm03:
    ip: "192.168.1.12"  # Your VM-03 IP
  vm04:
    ip: "192.168.1.13"  # Your VM-04 IP

network:
  subnet: "192.168.1.0/24"
  gateway: "192.168.1.1"
```

### 1.3 Set Up SSH Keys (Recommended)

For easier remote management, set up SSH keys:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "th_timmy"

# Copy key to all VMs
ssh-copy-id user@VM01_IP
ssh-copy-id user@VM02_IP
ssh-copy-id user@VM03_IP
ssh-copy-id user@VM04_IP
```

## Step 2: Install on Each VM

Installation must be done in a specific order. Start with VM-02 (database), then VM-01, VM-03, and finally VM-04.

### 2.1 Install VM-02 (Database)

**This must be installed first** as other VMs depend on it.

```bash
# On VM-02
cd ~/th_timmy/hosts/vm02-database

# Create configuration file
cp config.example.yml config.yml
nano config.yml  # Set database_password and allowed_ips

# Run installation
sudo ./install_vm02.sh

# Verify installation
./health_check.sh
```

**Important:** Note the database password you set - you'll need it for other VMs.

### 2.2 Install VM-01 (Ingest/Parser)

```bash
# On VM-01
cd ~/th_timmy/hosts/vm01-ingest

# Run installation
sudo ./install_vm01.sh

# Verify installation
./health_check.sh
```

### 2.3 Install VM-03 (Analysis/Jupyter)

```bash
# On VM-03
cd ~/th_timmy/hosts/vm03-analysis

# Optional: Create configuration file for custom JupyterLab settings
cp config.example.yml config.yml
nano config.yml  # Configure JupyterLab IP, port, token

# Run installation
sudo ./install_vm03.sh

# Verify installation
./health_check.sh

# Start JupyterLab (if not configured as service)
source ~/th_timmy/venv/bin/activate
jupyter lab --ip=0.0.0.0 --port=8888
```

**Note:** Save the JupyterLab token from the output - you'll need it to access the interface.

### 2.4 Install VM-04 (Orchestrator)

```bash
# On VM-04
cd ~/th_timmy/hosts/vm04-orchestrator

# Create configuration file
cp config.example.yml config.yml
nano config.yml  # Set basic_auth_password for n8n

# Run installation
sudo ./install_vm04.sh

# Verify installation
./health_check.sh

# Start n8n (if not auto-started)
cd ~/th_timmy/hosts/vm04-orchestrator
docker compose up -d
```

## Step 3: Verify Installation

### 3.1 Test Connectivity

From any VM, run the connection test:

```bash
cd ~/th_timmy
./hosts/shared/test_connections.sh
```

This will test:
- Ping connectivity to all VMs
- Service ports (PostgreSQL, JupyterLab, n8n)
- Database connection

### 3.2 Test Data Flow

Test the data pipeline:

```bash
cd ~/th_timmy
export POSTGRES_PASSWORD="your_database_password"
./hosts/shared/test_data_flow.sh
```

This verifies:
- Database write from VM-01
- Database read from VM-03
- n8n connectivity

### 3.3 Access Services

**JupyterLab (VM-03):**
- Open browser: `http://VM03_IP:8888`
- Use token from installation output

**n8n (VM-04):**
- Open browser: `http://VM04_IP:5678`
- Login with credentials from `config.yml`

## Step 4: Apply Security Hardening (Optional but Recommended)

After installation, apply security hardening on all VMs:

```bash
# On each VM
cd ~/th_timmy/hosts/vmXX-*/
sudo ./harden_vmXX.sh
```

**Important:** Test connectivity after hardening to ensure you're not locked out!

## Step 5: Create Your First Playbook

1. **Access JupyterLab** on VM-03
2. **Navigate to** `playbooks/template/`
3. **Copy the template** to create a new playbook
4. **Edit** `metadata.yml` with your hunt details
5. **Add queries** in the `queries/` directory
6. **Write analysis scripts** in `scripts/`

## Common Issues and Solutions

### Issue: Cannot connect to database

**Solution:**
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check firewall: `sudo ufw status`
- Verify IP is in `allowed_ips` in VM-02 config
- Check database password in `.env` or environment

### Issue: JupyterLab not accessible

**Solution:**
- Check if JupyterLab is running: `ps aux | grep jupyter`
- Verify port 8888 is open: `netstat -tlnp | grep 8888`
- Check firewall rules
- Verify IP binding in JupyterLab config

### Issue: n8n container won't start

**Solution:**
- Check Docker status: `sudo systemctl status docker`
- View logs: `docker compose logs n8n`
- Verify port 5678 is not in use: `netstat -tlnp | grep 5678`
- Check `.env` file exists and has correct values

### Issue: SSH connection fails

**Solution:**
- Verify SSH service: `sudo systemctl status ssh`
- Check firewall allows SSH port
- Verify SSH keys are properly set up
- Test with: `ssh -v user@VM_IP`

## Next Steps

1. **Read the documentation:**
   - [Architecture Documentation](docs/ARCHITECTURE.md)
   - [Configuration Guide](docs/CONFIGURATION.md)
   - [Testing Guide](docs/TESTING.md)
   - [Hardening Guide](docs/HARDENING.md)

2. **Explore the system:**
   - Access n8n dashboard and explore workflows
   - Open JupyterLab and review playbook template
   - Check database schema and sample data

3. **Start threat hunting:**
   - Create your first playbook
   - Import sample data
   - Run your first hunt

## Getting Help

- **Documentation**: Check `docs/` directory
- **VM-specific help**: See `hosts/vmXX-*/README.md`
- **Test suite**: See `tests/README.md`
- **Issues**: Check GitHub issues or create a new one

## Production Deployment Checklist

Before deploying to production:

- [ ] All VMs hardened (see [Hardening Guide](docs/HARDENING.md))
- [ ] Strong passwords set for all services
- [ ] Firewall rules configured and tested
- [ ] SSH keys configured (no password authentication)
- [ ] Backups configured for database
- [ ] Monitoring and alerting set up
- [ ] Documentation reviewed and updated
- [ ] Team trained on system usage

