# VM-04: Orchestrator - Installation

Installation and verification scripts for VM-04 (Orchestrator - n8n in Docker).

## Files

- `install_vm04.sh` - Installation script for all required tools
- `health_check.sh` - Installation verification script (includes optional connection tests)
- `harden_vm04.sh` - Security hardening script
- `setup_ssh_keys.sh` - Automatic SSH key generation and configuration for VM01-VM03
- `requirements.txt` - List of Python packages required for VM-04
- `docker-compose.yml` - n8n configuration in Docker container
- `config.example.yml` - Example configuration file
- `config.yml` - Configuration file (to be created by user)
- `.env` - Environment variables file for docker-compose (created automatically)

## Requirements

- Ubuntu Server 22.04 LTS
- Root privileges (sudo)
- Internet access
- **IMPORTANT**: Configuration file `config.yml` with n8n password set

## Preparation

### 1. Create configuration file

**REQUIRED** before running installation:

```bash
cd /path/to/timmy_developer/th_timmy/hosts/vm04-orchestrator
cp config.example.yml config.yml
nano config.yml
```

**Must fill in:**
- `basic_auth_password` - strong password for n8n user

## Installation

### Running

```bash
cd /path/to/timmy_developer/th_timmy/hosts/vm04-orchestrator
sudo ./install_vm04.sh [PROJECT_ROOT] [CONFIG_FILE]
```

**Example:**
```bash
# Using default PROJECT_ROOT and config.yml
sudo ./install_vm04.sh

# Or with custom path
sudo ./install_vm04.sh $HOME/th_timmy config.yml
```

### What does the script install?

1. **Basic system tools**: git, curl, wget, vim, nano, etc.
2. **Docker Engine** from official Docker repository:
   - docker-ce, docker-ce-cli
   - containerd.io
   - docker-buildx-plugin
   - docker-compose-plugin
3. **Python 3.10+** with pip and venv
4. **System libraries**: libssl-dev, libffi-dev
5. **Python packages** from `requirements.txt`:
   - pyyaml, python-dotenv, requests
   - loguru
   - docker (Python SDK)
6. **n8n configuration**:
   - docker-compose.yml
   - .env with credentials
   - Automatic startup (if auto_start=true)
7. **Firewall configuration** (port 5678)

### Post-installation structure

```
$HOME/th_timmy/
├── hosts/
│   └── vm04-orchestrator/
│       ├── install_vm04.sh
│       ├── health_check.sh
│       ├── requirements.txt
│       ├── docker-compose.yml
│       ├── config.example.yml
│       ├── config.yml (created by user)
│       └── .env (created automatically)
└── venv/                    # Virtual environment
```

## Installation Verification

After installation, run the verification script:

```bash
./health_check.sh [PROJECT_ROOT] [CONFIG_FILE]
```

**Example:**
```bash
./health_check.sh $HOME/th_timmy config.yml
```

### What does health_check verify?

- ✅ Operating system version (Ubuntu 22.04)
- ✅ Installed system tools
- ✅ Docker and Docker Compose (version, service status)
- ✅ Python 3.10+
- ✅ Virtual environment
- ✅ All required Python packages
- ✅ docker-compose.yml and .env
- ✅ n8n Docker container (status)
- ✅ Port 5678 and firewall
- ✅ Locale configuration
- ✅ **Optional:** Connection test to VM-03 (JupyterLab) if `configs/config.yml` exists

## Managing n8n

### Starting n8n

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose up -d
```

### Stopping n8n

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose down
```

### Restarting n8n

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose restart
```

### Checking status

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose ps
```

### n8n logs

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose logs -f n8n
```

### Accessing n8n

Open in browser:
```
http://VM04_IP:5678
```

Login using:
- **Username**: value from `config.yml` → `basic_auth_user`
- **Password**: value from `config.yml` → `basic_auth_password`

## Troubleshooting

### Problem: "Cannot connect to the Docker daemon"

**Solution:**
1. Log out and log back in (after adding to docker group)
2. Or use `sudo` before docker commands
3. Check status: `sudo systemctl status docker`

### Problem: "n8n container won't start"

**Solution:**
1. Check logs: `cd $VM04_DIR && docker compose logs n8n`
2. Check if port 5678 is free: `netstat -tlnp | grep 5678`
3. Check if .env exists and has correct values
4. Check docker-compose.yml: `docker compose config`

### Problem: "n8n password doesn't work"

**Solution:**
1. Check `.env` file in `$VM04_DIR/.env`
2. Make sure password in `.env` matches password in `config.yml`
3. Restart container: `docker compose restart n8n`

### Problem: "Permission denied" with docker commands

**Solution:**
1. Check if user is in docker group: `groups`
2. If not, add: `sudo usermod -aG docker $USER`
3. Log out and log back in

### Problem: "Port 5678 already in use"

**Solution:**
1. Check what's using the port: `sudo lsof -i :5678`
2. Stop other services using this port
3. Or change port in `config.yml` and `docker-compose.yml`

## Documentation

For detailed system documentation, see:
- [Architecture Documentation](../../docs/ARCHITECTURE_ENHANCED.md)
- [Configuration Guide](../../docs/CONFIGURATION.md)

## Hardening

After installation, you can apply security hardening to VM-04:

```bash
cd /path/to/th_timmy/hosts/vm04-orchestrator
sudo ./harden_vm04.sh
```

**What does hardening do?**
- Configures firewall (ufw): SSH and n8n port (5678)
- Hardens SSH configuration (port, timeout, disable root login)
- Configures Docker security (log rotation, no-new-privileges)
- Updates docker-compose.yml with security options (security_opt, resource limits, non-root user)
- Installs and configures Fail2ban for SSH protection
- Configures Logrotate for Docker and n8n logs
- Verifies n8n security settings (basic auth, container security)
- Optionally enables auditd for system auditing

**Configuration:**
Hardening settings are read from `configs/config.yml`:
```yaml
hardening:
  ssh:
    port: 22
    timeout: 300
    disable_root_login: true
  firewall:
    allowed_network: "10.0.0.0/24"  # Optional: restrict access
  vm04:
    enable_auditd: false  # Optional: enable system auditing
```

**Important:** After hardening, restart n8n container to apply security settings:
```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose down
docker compose up -d
```

**Note:** The hardening script sources `hosts/shared/hardening_common.sh` for common functions.

## SSH Key Management

The `setup_ssh_keys.sh` script automates SSH key generation and configuration for secure communication between VM04 (orchestrator) and VM01-VM03.

### Purpose

This script:
- Generates SSH keys (ed25519) for each target VM (VM01, VM02, VM03)
- Copies public keys to remote hosts
- Configures SSH servers to require key-based authentication (disables password authentication)
- Creates local `~/.ssh/config` file for easy connection using host aliases

### Requirements

- Python 3 with PyYAML (`pip3 install pyyaml`)
- SSH tools: `ssh`, `ssh-keygen`, `ssh-copy-id`
- Access to remote hosts (VM01-VM03) via SSH
- Sudo privileges on remote hosts (for SSH server configuration)
- Valid `configs/config.yml` file with VM configuration

### Configuration

The script reads VM configuration from `configs/config.yml`:

```yaml
vms:
  vm01:
    ip: "10.0.0.10"
    ssh_user: "thadmin"
    ssh_port: 22
  vm02:
    ip: "10.0.0.11"
    ssh_user: "thadmin"
    ssh_port: 22
  vm03:
    ip: "10.0.0.12"
    ssh_user: "thadmin"
    ssh_port: 22
```

### Usage

**Basic usage (recommended - without sudo):**
```bash
cd /path/to/th_timmy/hosts/vm04-orchestrator
./setup_ssh_keys.sh
```

**With sudo (if needed for file permissions):**
```bash
sudo ./setup_ssh_keys.sh
```

**Note:** The script automatically fixes file ownership if run with sudo, ensuring files belong to the correct user.

### What the script does

1. **Reads configuration** from `configs/config.yml`
2. **Generates SSH keys** for each VM (stored in `~/.ssh/th_timmy_keys/`)
3. **Copies public keys** to remote hosts using `ssh-copy-id` or manual method
4. **Tests SSH connections** to verify key-based authentication works
5. **Configures remote SSH servers** (requires sudo on remote hosts):
   - Disables password authentication (`PasswordAuthentication no`)
   - Enables public key authentication (`PubkeyAuthentication yes`)
   - Disables root login (`PermitRootLogin no`)
   - Applies additional security settings
6. **Creates local SSH config** (`~/.ssh/config`) with host aliases:
   ```
   Host vm01
       HostName 10.0.0.10
       User thadmin
       IdentityFile ~/.ssh/th_timmy_keys/id_ed25519_vm01
       IdentitiesOnly yes
   ```

### After running the script

You can connect to hosts using simple aliases:
```bash
ssh vm01
ssh vm02
ssh vm03
```

### Troubleshooting

**Problem: "SUDO_USER: unbound variable"**
- Solution: The script now handles this automatically. If you see this error, update to the latest version.

**Problem: "Files belong to root"**
- Solution: The script automatically fixes file ownership. If files still belong to root, run:
  ```bash
  sudo chown -R $USER:$USER ~/.ssh/config ~/.ssh/th_timmy_keys
  ```

**Problem: "Could not resolve hostname vm01"**
- Solution: Check that `~/.ssh/config` exists and has correct permissions:
  ```bash
  ls -la ~/.ssh/config
  chmod 600 ~/.ssh/config
  ```

**Problem: "Sudo requires password on remote hosts"**
- Solution: The script will prompt for sudo password interactively. For automation, configure passwordless sudo on remote hosts or use SSH keys with sudo NOPASSWD.

**Problem: "Cannot copy key to remote host"**
- Solution: Ensure you can connect to the host with password first. The script will prompt for password during initial key copy.

### Security Notes

⚠️ **IMPORTANT:**
- After running this script, password authentication is **disabled** on remote hosts
- Ensure SSH key-based authentication works before the script modifies remote SSH configuration
- Keep your private keys secure (`~/.ssh/th_timmy_keys/` should have 600 permissions)
- The script creates backups of remote SSH configurations before modification
- Keys are generated with ed25519 algorithm (recommended for security and performance)

## Security

⚠️ **IMPORTANT:**
- Never commit `config.yml` or `.env` files to repository (they're in .gitignore)
- Use strong passwords for n8n
- Limit firewall access only to trusted IPs
- Regularly update Docker and container images
- Consider using HTTPS in production (requires additional configuration)
- Run hardening script after installation for production environments

## Updating n8n

To update n8n to the latest version:

```bash
cd $HOME/th_timmy/hosts/vm04-orchestrator
docker compose pull
docker compose up -d
```
