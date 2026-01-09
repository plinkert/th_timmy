# VM-01: Ingest/Parser - Installation

Installation and verification scripts for VM-01 (Ingest/Parser).

## Files

- `install_vm01.sh` - Installation script for all required tools
- `health_check.sh` - Installation verification script (includes optional connection tests)
- `harden_vm01.sh` - Security hardening script
- `hardening.conf.example` - Example hardening configuration file
- `requirements.txt` - List of Python packages required for VM-01

## Installation

### Requirements

- Ubuntu Server 22.04 LTS
- Root privileges (sudo)
- Internet access

### Running

```bash
cd /path/to/th_timmy/hosts/vm01-ingest
sudo ./install_vm01.sh [PROJECT_ROOT]
```

**Example:**
```bash
# Using default PROJECT_ROOT ($HOME/th_timmy)
sudo ./install_vm01.sh

# Or with custom path
sudo ./install_vm01.sh $HOME/th_timmy
```

### What does the script install?

1. **Basic system tools**: git, curl, wget, vim, nano, etc.
2. **Python 3.10+** with pip and venv
3. **System libraries**: libpq-dev, libssl-dev, libffi-dev, etc.
4. **File handling tools**: file, unzip, zip
5. **Python packages** from `requirements.txt`:
   - pandas, numpy
   - pyarrow
   - psycopg2-binary, sqlalchemy
   - pyyaml, python-dateutil, requests
   - cryptography, python-dotenv
   - loguru

### Post-installation structure

The script will automatically create the following structure:
```
$HOME/th_timmy/
├── hosts/
│   └── vm01-ingest/
│       ├── install_vm01.sh
│       ├── health_check.sh
│       └── requirements.txt
└── venv/                    # Virtual environment
```

## Installation Verification

After installation, run the verification script:

```bash
./health_check.sh [PROJECT_ROOT]
```

**Example:**
```bash
# Using default PROJECT_ROOT
./health_check.sh

# Or with custom path
./health_check.sh $HOME/th_timmy
```

### What does health_check verify?

- ✅ Operating system version (Ubuntu 22.04)
- ✅ Installed system tools
- ✅ Python 3.10+
- ✅ System libraries
- ✅ Virtual environment
- ✅ All required Python packages
- ✅ Locale configuration
- ✅ Connection to VM-02 (PostgreSQL) - optional, requires `configs/config.yml`

## Using Virtual Environment

After installation, activate the virtual environment:

```bash
source $HOME/th_timmy/venv/bin/activate
```

## Troubleshooting

### Problem: "Cannot determine user"

**Solution:** Use `sudo -u username` instead of just `sudo`:
```bash
sudo -u $USER ./install_vm01.sh
```

### Problem: Virtual environment was not created

**Solution:** Check if you have `python3-venv` installed:
```bash
sudo apt-get install python3-venv
```

### Problem: Errors during Python package installation

**Solution:** 
1. Check if all system libraries are installed
2. Make sure you have internet access
3. Check installation logs

## Security Hardening

After installation, you can apply security hardening:

```bash
cd /path/to/th_timmy/hosts/vm01-ingest
sudo ./harden_vm01.sh
```

### Hardening Configuration

You can customize hardening by creating a `hardening.conf` file:

```bash
# Copy example configuration
cp hardening.conf.example hardening.conf

# Edit configuration
nano hardening.conf

# Source it before running hardening
source hardening.conf
sudo ./harden_vm01.sh
```

### What does hardening configure?

- ✅ Firewall (ufw) - opens SSH and collector ports
- ✅ SSH hardening - disables root login, configurable port/timeout
- ✅ Fail2ban - protection against brute-force attacks
- ✅ Log rotation - automatic log file rotation
- ✅ Automatic security updates - keeps system up-to-date
- ✅ Optional: System auditing (auditd)

### Important Notes

- **Always test SSH access** after hardening to ensure you're not locked out
- Firewall rules can be checked with: `sudo ufw status`
- SSH configuration can be checked with: `sudo systemctl status ssh`
- Fail2ban status: `sudo fail2ban-client status`

## Connection Tests

The `health_check.sh` script includes optional connection tests to VM-02 (Database):

- Tests ping connectivity to VM-02
- Tests PostgreSQL port (5432) accessibility
- Tests database authentication (if `POSTGRES_PASSWORD` is set)

These tests only run if `configs/config.yml` exists with VM IP addresses configured.

## Documentation

Detailed requirements can be found in:
- `../../project plan/VM01_TOOLS_REQUIREMENTS.md`

