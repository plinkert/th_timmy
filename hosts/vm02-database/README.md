# VM-02: Database - Installation

Installation and verification scripts for VM-02 (Database - PostgreSQL).

## Files

- `install_vm02.sh` - Installation script for all required tools
- `health_check.sh` - Installation verification script (includes retention checks)
- `harden_vm02.sh` - Security hardening script
- `hardening.conf.example` - Example hardening configuration file
- `requirements.txt` - List of Python packages required for VM-02
- `config.example.yml` - Example configuration file
- `config.yml` - Configuration file (to be created by user)

## Requirements

- Ubuntu Server 22.04 LTS
- Root privileges (sudo)
- Internet access
- **IMPORTANT**: Configuration file `config.yml` with database password set

## Preparation

### 1. Create configuration file

**REQUIRED** before running installation:

```bash
cd /path/to/timmy_developer/th_timmy/hosts/vm02-database
cp config.example.yml config.yml
nano config.yml
```

**Must fill in:**
- `database_password` - strong password for database user
- `allowed_ips` - IP addresses of other VMs that will connect to the database

**Optional (data retention):**
- `retention.retention_days` - Data retention period (default: 90 days)
- `retention.auto_cleanup` - Enable automatic cleanup (default: true)
- `retention.cleanup_schedule` - Cleanup schedule in cron format (default: "0 3 * * *")

## Installation

### Running

```bash
cd /path/to/timmy_developer/th_timmy/hosts/vm02-database
sudo ./install_vm02.sh [PROJECT_ROOT] [CONFIG_FILE]
```

**Example:**
```bash
# Using default PROJECT_ROOT and config.yml
sudo ./install_vm02.sh

# Or with custom path
sudo ./install_vm02.sh $HOME/th_timmy config.yml
```

### What does the script install?

1. **Basic system tools**: git, curl, wget, vim, nano, etc.
2. **PostgreSQL 14+** with contrib modules and client
3. **Backup tools**: cron, rsync
4. **Python 3.10+** with pip and venv
5. **System libraries**: libpq-dev, libssl-dev, libffi-dev
6. **Python packages** from `requirements.txt`:
   - psycopg2-binary, sqlalchemy
   - pyyaml, python-dotenv
   - loguru
7. **PostgreSQL configuration**:
   - Database and user creation
   - postgresql.conf configuration
   - pg_hba.conf configuration (access from other VMs)
   - Firewall configuration

### Post-installation structure

```
$HOME/th_timmy/
├── hosts/
│   └── vm02-database/
│       ├── install_vm02.sh
│       ├── health_check.sh
│       ├── requirements.txt
│       ├── config.example.yml
│       └── config.yml (created by user)
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
- ✅ PostgreSQL (version, service status)
- ✅ Database and user
- ✅ Backup tools (cron, rsync)
- ✅ Python 3.10+
- ✅ Virtual environment
- ✅ All required Python packages
- ✅ PostgreSQL configuration
- ✅ Firewall (port 5432)
- ✅ Locale configuration
- ✅ Data retention configuration (90 days)
- ✅ cleanup_old_data() function
- ✅ Automatic cleanup scheduling (pg_cron or system cron)

## Connection Test

After installation, you can test the database connection:

```bash
# Locally
psql -h localhost -U threat_hunter -d threat_hunting

# From another VM (if IP is in allowed_ips)
psql -h VM02_IP -U threat_hunter -d threat_hunting
```

## PostgreSQL Configuration

### Configuration files

- **postgresql.conf**: `/etc/postgresql/14/main/postgresql.conf`
- **pg_hba.conf**: `/etc/postgresql/14/main/pg_hba.conf`

The script automatically creates backups before modification (with date and time).

### Important settings

The script configures:
- `listen_addresses` - listening addresses
- `max_connections` - maximum number of connections
- `shared_buffers` - shared buffer
- `effective_cache_size` - effective cache size

All values are read from `config.yml`.

## Troubleshooting

### Problem: "Database password not set"

**Solution:** Edit `config.yml` and set `database_password`:
```bash
nano config.yml
# Change: database_password: "CHANGE_ME_STRONG_PASSWORD"
# To: database_password: "your_strong_password"
```

### Problem: "PostgreSQL service not running"

**Solution:** Check status and logs:
```bash
sudo systemctl status postgresql
sudo journalctl -u postgresql -n 50
```

### Problem: "Cannot connect to database from another VM"

**Solution:**
1. Check if IP is in `allowed_ips` in `config.yml`
2. Check firewall: `sudo ufw status`
3. Check pg_hba.conf: `sudo cat /etc/postgresql/14/main/pg_hba.conf`
4. Check if PostgreSQL is listening: `sudo netstat -tlnp | grep 5432`

### Problem: "config.yml parsing error"

**Solution:** Check YAML syntax:
```bash
python3 -c "import yaml; yaml.safe_load(open('config.yml'))"
```

## Data Retention

The system is configured with **90-day data retention** by default. This means:
- Data older than 90 days is automatically cleaned up
- Cleanup runs daily at 3:00 AM (configurable)
- Cleanup operations are logged in `cleanup_log` table
- Supports pg_cron extension (preferred) or system cron (fallback)

### Configuration

Data retention is configured in `config.yml`:

```yaml
retention:
  retention_days: 90          # Retention period in days
  auto_cleanup: true          # Enable automatic cleanup
  cleanup_schedule: "0 3 * * *"  # Daily at 3:00 AM
  log_cleanup: true           # Log cleanup operations
```

### Manual Cleanup

You can manually run cleanup:

```bash
sudo -u postgres psql -d threat_hunting -c "SELECT cleanup_old_data();"
```

## Security Hardening

After installation, you can apply security hardening:

```bash
cd /path/to/th_timmy/hosts/vm02-database
sudo ./harden_vm02.sh [config.yml]
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
sudo ./harden_vm02.sh config.yml
```

### What does hardening configure?

- ✅ Firewall (ufw) - opens SSH and PostgreSQL ports
- ✅ SSH hardening - disables root login, configurable port/timeout
- ✅ PostgreSQL access restrictions - limits access to VM-01 and VM-03 only (pg_hba.conf)
- ✅ PostgreSQL logging - logs failed login attempts
- ✅ Fail2ban - protection for SSH and PostgreSQL
- ✅ Automatic backups - daily PostgreSQL backups with rotation
- ✅ Log rotation - automatic log file rotation
- ✅ Automatic security updates - keeps system up-to-date
- ✅ Optional: System auditing (auditd)

### Important Notes

- **Always test SSH access** after hardening to ensure you're not locked out
- **Verify database connections** from VM-01 and VM-03 after hardening
- Firewall rules can be checked with: `sudo ufw status`
- PostgreSQL access rules: `sudo cat /etc/postgresql/14/main/pg_hba.conf`
- Fail2ban status: `sudo fail2ban-client status`

## Documentation

Detailed requirements can be found in:
- `../../project plan/VM02_TOOLS_REQUIREMENTS.md`

## Security

⚠️ **IMPORTANT:**
- Never commit `config.yml` file to repository (it's in .gitignore)
- Use strong passwords for database
- Limit access in `allowed_ips` only to trusted IPs
- Regularly update PostgreSQL

