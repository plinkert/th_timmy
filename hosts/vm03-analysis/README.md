# VM-03: Analysis/Jupyter - Installation

Installation and verification scripts for VM-03 (Analysis/Jupyter - JupyterLab).

## Files

- `install_vm03.sh` - Installation script for all required tools
- `health_check.sh` - Installation verification script (includes optional connection tests)
- `harden_vm03.sh` - Security hardening script
- `requirements.txt` - List of Python packages required for VM-03
- `config.example.yml` - Example configuration file (optional)
- `config.yml` - Configuration file (optional, to be created by user)

## Requirements

- Ubuntu Server 22.04 LTS
- Root privileges (sudo)
- Internet access
- **Optional**: Configuration file `config.yml` for advanced JupyterLab configuration

## Preparation

### 1. Create configuration file (optional)

The configuration file is **optional**. If it doesn't exist, the script will use default values.

```bash
cd /path/to/timmy_developer/th_timmy/hosts/vm03-analysis
cp config.example.yml config.yml
nano config.yml
```

**You can configure:**
- JupyterLab IP and port
- Access token
- Password (optional)
- Enable as systemd service

## Installation

### Running

```bash
cd /path/to/timmy_developer/th_timmy/hosts/vm03-analysis
sudo ./install_vm03.sh [PROJECT_ROOT] [CONFIG_FILE]
```

**Example:**
```bash
# Using default PROJECT_ROOT and config.yml (if exists)
sudo ./install_vm03.sh

# Or with custom path
sudo ./install_vm03.sh $HOME/th_timmy config.yml
```

### What does the script install?

1. **Basic system tools**: git, curl, wget, vim, nano, etc.
2. **Python 3.10+** with pip, venv and Tkinter
3. **System libraries**: libpq-dev, libssl-dev, libffi-dev, libjpeg-dev, libpng-dev, libfreetype6-dev, pkg-config
4. **Node.js 18.x LTS** (for JupyterLab extensions)
5. **Python packages** from `requirements.txt`:
   - JupyterLab, notebook, ipykernel, ipywidgets
   - pandas, numpy, pyarrow
   - psycopg2-binary, sqlalchemy
   - scikit-learn, matplotlib, seaborn, openai
   - pyyaml, python-dateutil, requests
   - python-dotenv, loguru
6. **JupyterLab configuration**:
   - Configuration generation
   - IP, port, token settings (from config.yml or defaults)
   - Optionally: systemd service
7. **Firewall configuration** (port 8888)

### Post-installation structure

```
$HOME/th_timmy/
├── hosts/
│   └── vm03-analysis/
│       ├── install_vm03.sh
│       ├── health_check.sh
│       ├── requirements.txt
│       ├── config.example.yml
│       └── config.yml (optional)
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
- ✅ Node.js 18+
- ✅ Python 3.10+
- ✅ System libraries (including for matplotlib/seaborn)
- ✅ Virtual environment
- ✅ All required Python packages
- ✅ JupyterLab and configuration
- ✅ JupyterLab service (if enabled)
- ✅ Port 8888 and firewall
- ✅ Locale configuration
- ✅ **Optional:** Connection tests to VM-02 (PostgreSQL) and VM-04 (n8n) if `configs/config.yml` exists

## Running JupyterLab

### Manual start

```bash
source $HOME/th_timmy/venv/bin/activate
jupyter lab --ip=0.0.0.0 --port=8888
```

### As systemd service (if enabled in config.yml)

```bash
# Status
sudo systemctl status jupyter

# Logs
sudo journalctl -u jupyter -f

# Restart
sudo systemctl restart jupyter
```

### Accessing JupyterLab

Open in browser:
```
http://VM03_IP:8888
```

If using a token, you can find it in:
- JupyterLab logs
- Configuration file: `~/.jupyter/jupyter_lab_config.py`
- Or generate a new one: `jupyter lab --generate-config`

## Troubleshooting

### Problem: "JupyterLab won't start"

**Solution:**
1. Check if venv is activated: `source venv/bin/activate`
2. Check if packages are installed: `pip list | grep jupyter`
3. Check logs: `jupyter lab --debug`

### Problem: "Cannot connect to JupyterLab"

**Solution:**
1. Check if port 8888 is open: `netstat -tlnp | grep 8888`
2. Check firewall: `sudo ufw status`
3. Check IP configuration in `~/.jupyter/jupyter_lab_config.py`

### Problem: "Node.js not installed"

**Solution:**
- Node.js is optional, but recommended for some extensions
- You can install manually: `curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs`

### Problem: "Matplotlib not displaying plots"

**Solution:**
- Check if system libraries are installed: `dpkg -l | grep -E "libjpeg|libpng|libfreetype"`
- Check if python3-tk is installed: `python3 -c "import tkinter"`

## Documentation

For detailed system documentation, see:
- [Architecture Documentation](../../docs/ARCHITECTURE_ENHANCED.md)
- [User Guide for Hunters](../../docs/USER_GUIDE_HUNTER.md)
- [Configuration Guide](../../docs/CONFIGURATION.md)

## Hardening

After installation, you can apply security hardening to VM-03:

```bash
cd /path/to/th_timmy/hosts/vm03-analysis
sudo ./harden_vm03.sh
```

**What does hardening do?**
- Configures firewall (ufw): SSH and JupyterLab port (8888)
- Hardens SSH configuration (port, timeout, disable root login)
- Installs and configures Fail2ban for SSH protection
- Configures Logrotate for JupyterLab logs
- Verifies JupyterLab security settings (file upload restrictions)
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
    allowed_network: "192.168.244.0/24"  # Optional: restrict access
  vm03:
    enable_auditd: false  # Optional: enable system auditing
```

**Note:** The hardening script sources `hosts/shared/hardening_common.sh` for common functions.

## Security

⚠️ **IMPORTANT:**
- Never commit `config.yml` file to repository if it contains tokens/passwords
- Use tokens instead of passwords for security
- Limit firewall access only to trusted IPs
- Regularly update JupyterLab and Python packages
- Run hardening script after installation for production environments
