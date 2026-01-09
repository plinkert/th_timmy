#!/bin/bash
# harden_vm02.sh - Hardening script for VM-02: Database
# Usage: sudo ./harden_vm02.sh [CONFIG_FILE]
#
# This script applies security hardening to VM-02 (Database - PostgreSQL).
# It configures firewall, SSH, PostgreSQL access, fail2ban, backups, and log rotation.
#
# Requirements:
#   - Must be run as root (use sudo)
#   - Internet access for package installation
#   - config.yml file with database and network configuration
#   - Backup of system files will be created automatically

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_FILE="${1:-$SCRIPT_DIR/config.yml}"

# Source common hardening functions
if [ -f "${SCRIPT_DIR}/../shared/hardening_common.sh" ]; then
    source "${SCRIPT_DIR}/../shared/hardening_common.sh"
else
    echo -e "${RED}ERROR: hardening_common.sh not found at ${SCRIPT_DIR}/../shared/hardening_common.sh${NC}"
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Configuration file not found: $CONFIG_FILE"
    log_error "Copy config.example.yml to config.yml and fill in values"
    exit 1
fi

# Load configuration from central config.yml
CENTRAL_CONFIG="${PROJECT_ROOT}/configs/config.yml"

if [ -f "$CENTRAL_CONFIG" ] && command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
    # Read hardening configuration from config.yml
    SSH_PORT=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('ssh', {}).get('port', 22))" 2>/dev/null || echo "22")
    SSH_TIMEOUT=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('ssh', {}).get('timeout', 300))" 2>/dev/null || echo "300")
    ALLOWED_NETWORK=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('firewall', {}).get('allowed_network', ''))" 2>/dev/null || echo "")
    ENABLE_AUDITD=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('vm02', {}).get('enable_auditd', False))" 2>/dev/null || echo "False")
    
    # Get VM IPs from central config
    VM01_IP=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm01', {}).get('ip', ''))" 2>/dev/null || echo "")
    VM03_IP=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm03', {}).get('ip', ''))" 2>/dev/null || echo "")
    
    log_info "Configuration loaded from: $CENTRAL_CONFIG"
else
    # Fallback to environment variables or defaults
    log_warn "Central config.yml not found or Python/yaml not available, using defaults or environment variables"
    SSH_PORT="${SSH_PORT:-22}"
    SSH_TIMEOUT="${SSH_TIMEOUT:-300}"
    ALLOWED_NETWORK="${ALLOWED_NETWORK:-}"
    ENABLE_AUDITD="${ENABLE_AUDITD:-false}"
    VM01_IP=""
    VM03_IP=""
fi

# Get database config
DB_NAME=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('postgresql', {}).get('database_name', 'threat_hunting'))" 2>/dev/null || echo "threat_hunting")
DB_USER=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('postgresql', {}).get('database_user', 'threat_hunter'))" 2>/dev/null || echo "threat_hunter")
PG_PORT=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('postgresql', {}).get('port', 5432))" 2>/dev/null || echo "5432")

# Get PostgreSQL version
PG_VERSION=$(ls -d /etc/postgresql/*/main 2>/dev/null | head -1 | cut -d/ -f4 || echo "14")

echo ""
echo "=========================================="
echo "  VM-02 Hardening Script"
echo "=========================================="
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo "PostgreSQL version: $PG_VERSION"
echo ""
log_info "Starting VM-02 hardening process..."
echo ""

# ============================================
# 1. Firewall Configuration
# ============================================
echo "=========================================="
echo "  1. Firewall Configuration (ufw)"
echo "=========================================="
log_info "Configuring firewall for VM-02 (Database)"

# Configure firewall with SSH and PostgreSQL ports
FIREWALL_PORTS="$SSH_PORT,$PG_PORT"
ALLOWED_NETWORK="${ALLOWED_NETWORK:-}"

if [ -n "$ALLOWED_NETWORK" ]; then
    log_info "Restricting access to network: $ALLOWED_NETWORK"
    configure_firewall "$FIREWALL_PORTS" "$ALLOWED_NETWORK"
else
    log_info "Opening ports: $FIREWALL_PORTS (no network restriction)"
    configure_firewall "$FIREWALL_PORTS" ""
fi

echo ""

# ============================================
# 2. SSH Hardening
# ============================================
echo "=========================================="
echo "  2. SSH Hardening"
echo "=========================================="
log_info "Hardening SSH configuration"

configure_ssh true "$SSH_PORT" "$SSH_TIMEOUT"

echo ""

# ============================================
# 3. PostgreSQL Access Configuration (pg_hba.conf)
# ============================================
echo "=========================================="
echo "  3. PostgreSQL Access Configuration"
echo "=========================================="
log_info "Configuring PostgreSQL access restrictions"

PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

if [ -f "$PG_HBA" ]; then
    # Backup pg_hba.conf
    backup_file "$PG_HBA"
    
    log_info "Restricting PostgreSQL access to VM-01 and VM-03 only"
    
    # Get allowed IPs from config.yml
    ALLOWED_IPS=$(python3 -c "
import yaml
f=open('$CONFIG_FILE')
d=yaml.safe_load(f)
ips = d.get('network', {}).get('allowed_ips', ['127.0.0.1/32'])
for ip in ips:
    print(ip)
" 2>/dev/null || echo "127.0.0.1/32")
    
    # Remove old rules for this database/user (keep localhost)
    sed -i "/^host.*$DB_NAME.*$DB_USER.*[0-9]/d" "$PG_HBA"
    
    # Add rules for each allowed IP
    for ip in $ALLOWED_IPS; do
        if ! grep -q "host.*$DB_NAME.*$DB_USER.*$ip" "$PG_HBA"; then
            echo "host    $DB_NAME    $DB_USER    $ip    md5" >> "$PG_HBA"
            log_info "Added PostgreSQL access rule for IP: $ip"
        fi
    done
    
    # Ensure localhost access is maintained
    if ! grep -q "host.*$DB_NAME.*$DB_USER.*127.0.0.1" "$PG_HBA"; then
        echo "host    $DB_NAME    $DB_USER    127.0.0.1/32    md5" >> "$PG_HBA"
        log_info "Added localhost access rule"
    fi
    
    # Restart PostgreSQL to apply changes
    log_info "Restarting PostgreSQL to apply pg_hba.conf changes..."
    systemctl restart postgresql || log_warn "Failed to restart PostgreSQL"
    
    log_success "PostgreSQL access configured"
else
    log_warn "pg_hba.conf not found at $PG_HBA"
fi

echo ""

# ============================================
# 4. PostgreSQL Logging Configuration
# ============================================
echo "=========================================="
echo "  4. PostgreSQL Logging Configuration"
echo "=========================================="
log_info "Configuring PostgreSQL logging for security"

PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"

if [ -f "$PG_CONF" ]; then
    backup_file "$PG_CONF"
    
    # Enable logging of failed login attempts
    sed -i "s/#log_connections = off/log_connections = on/" "$PG_CONF"
    sed -i "s/#log_disconnections = off/log_disconnections = on/" "$PG_CONF"
    sed -i "s/#log_authentication_failures = off/log_authentication_failures = on/" "$PG_CONF"
    
    # Set log destination
    if ! grep -q "^log_destination" "$PG_CONF"; then
        echo "log_destination = 'stderr'" >> "$PG_CONF"
    fi
    
    # Configure logging format
    if ! grep -q "^log_line_prefix" "$PG_CONF"; then
        echo "log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '" >> "$PG_CONF"
    fi
    
    # Restart PostgreSQL
    log_info "Restarting PostgreSQL to apply logging configuration..."
    systemctl restart postgresql || log_warn "Failed to restart PostgreSQL"
    
    log_success "PostgreSQL logging configured"
else
    log_warn "postgresql.conf not found at $PG_CONF"
fi

echo ""

# ============================================
# 5. Fail2ban Installation and Configuration
# ============================================
echo "==========================================="
echo "  5. Fail2ban Configuration"
echo "==========================================="
log_info "Installing and configuring fail2ban for SSH and PostgreSQL"

# Install and configure fail2ban for SSH
install_fail2ban "sshd"

# Configure fail2ban for PostgreSQL
log_info "Configuring fail2ban for PostgreSQL"

JAIL_LOCAL="/etc/fail2ban/jail.local"
if [ -f "$JAIL_LOCAL" ]; then
    backup_file "$JAIL_LOCAL"
fi

# Add PostgreSQL jail configuration
if ! grep -q "\[postgresql\]" "$JAIL_LOCAL" 2>/dev/null; then
    cat >> "$JAIL_LOCAL" << EOF

[postgresql]
enabled = true
port = $PG_PORT
filter = postgresql
logpath = /var/log/postgresql/postgresql-*-main.log
maxretry = 3
bantime = 3600
findtime = 600
EOF
    
    # Create PostgreSQL filter
    POSTGRESQL_FILTER="/etc/fail2ban/filter.d/postgresql.conf"
    if [ ! -f "$POSTGRESQL_FILTER" ]; then
        cat > "$POSTGRESQL_FILTER" << 'FILTER_EOF'
[Definition]
failregex = ^.*authentication failed.*user=.*host=<HOST>
            ^.*password authentication failed.*user=.*host=<HOST>
            ^.*could not connect to server.*host=<HOST>
ignoreregex =
FILTER_EOF
        log_info "Created PostgreSQL fail2ban filter"
    fi
    
    systemctl restart fail2ban
    log_success "Fail2ban configured for PostgreSQL"
else
    log_info "PostgreSQL jail already configured in fail2ban"
fi

echo ""

# ============================================
# 6. Backup Configuration
# ============================================
echo "=========================================="
echo "  6. Backup Configuration"
echo "=========================================="
log_info "Configuring automatic PostgreSQL backups"

# Get backup config from config.yml
BACKUP_ENABLED=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('backup', {}).get('enabled', True))" 2>/dev/null || echo "True")
BACKUP_DIR=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('backup', {}).get('backup_dir', '/var/backups/postgresql'))" 2>/dev/null || echo "/var/backups/postgresql")
BACKUP_SCHEDULE=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('backup', {}).get('schedule', '0 2 * * *'))" 2>/dev/null || echo "0 2 * * *")

if [ "$BACKUP_ENABLED" = "True" ] || [ "$BACKUP_ENABLED" = "true" ]; then
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    chown postgres:postgres "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"
    
    # Create backup script
    BACKUP_SCRIPT="/usr/local/bin/backup_postgresql.sh"
    cat > "$BACKUP_SCRIPT" << BACKUP_EOF
#!/bin/bash
# PostgreSQL backup script
# This script is called by cron to backup PostgreSQL database

DB_NAME="$DB_NAME"
DB_USER="$DB_USER"
BACKUP_DIR="$BACKUP_DIR"
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\${BACKUP_DIR}/threat_hunting_\${DATE}.sql.gz"

# Create backup
sudo -u postgres pg_dump -Fc "\$DB_NAME" | gzip > "\$BACKUP_FILE"

# Keep only last 30 days of backups
find "\$BACKUP_DIR" -name "threat_hunting_*.sql.gz" -mtime +30 -delete

# Log backup
echo "\$(date): Backup created: \$BACKUP_FILE" >> "\${BACKUP_DIR}/backup.log"
BACKUP_EOF
    
    chmod +x "$BACKUP_SCRIPT"
    
    # Add to crontab (avoid duplicates)
    (crontab -l 2>/dev/null | grep -v "backup_postgresql.sh"; echo "$BACKUP_SCHEDULE $BACKUP_SCRIPT") | crontab -
    
    log_success "Automatic backups configured (schedule: $BACKUP_SCHEDULE)"
else
    log_info "Backups disabled in config.yml"
fi

echo ""

# ============================================
# 7. Log Rotation Configuration
# ============================================
echo "=========================================="
echo "  7. Log Rotation Configuration"
echo "=========================================="
log_info "Configuring log rotation for PostgreSQL logs"

LOG_ROTATE_CONFIG="/etc/logrotate.d/postgresql-threat-hunting"
LOG_PATH="/var/log/postgresql/*.log"

configure_logrotate "$LOG_ROTATE_CONFIG" "$LOG_PATH"

echo ""

# ============================================
# 8. Automatic Security Updates
# ============================================
echo "=========================================="
echo "  8. Automatic Security Updates"
echo "=========================================="
log_info "Configuring automatic security updates"

configure_auto_updates

echo ""

# ============================================
# 9. Optional: System Auditing (auditd)
# ============================================
if [ "$ENABLE_AUDITD" = "True" ] || [ "$ENABLE_AUDITD" = "true" ]; then
    echo "=========================================="
    echo "  9. System Auditing (auditd)"
    echo "=========================================="
    log_info "Configuring system auditing (optional)"
    
    configure_auditd
    
    echo ""
fi

# ============================================
# Summary
# ============================================
echo "=========================================="
echo "  Hardening Summary"
echo "=========================================="
log_success "VM-02 hardening completed successfully!"
echo ""
log_info "Applied configurations:"
echo "  ✓ Firewall (ufw) configured (SSH: $SSH_PORT, PostgreSQL: $PG_PORT)"
echo "  ✓ SSH hardened (root login disabled, port: $SSH_PORT)"
echo "  ✓ PostgreSQL access restricted (pg_hba.conf)"
echo "  ✓ PostgreSQL logging enabled (failed logins)"
echo "  ✓ Fail2ban installed and configured (SSH + PostgreSQL)"
echo "  ✓ Automatic backups configured"
echo "  ✓ Log rotation configured"
echo "  ✓ Automatic security updates enabled"
if [ "${ENABLE_AUDITD:-false}" = "true" ]; then
    echo "  ✓ System auditing (auditd) enabled"
fi
echo ""
log_info "Next steps:"
echo "  1. Test SSH connection to ensure you can still access the system"
echo "  2. Test database connection from VM-01 and VM-03"
echo "  3. Verify firewall rules: sudo ufw status"
echo "  4. Check fail2ban status: sudo fail2ban-client status"
echo "  5. Check PostgreSQL access: sudo cat /etc/postgresql/$PG_VERSION/main/pg_hba.conf"
echo "  6. Run health check: ./health_check.sh"
echo ""
log_warn "IMPORTANT: Make sure you can still SSH to this system!"
log_warn "IMPORTANT: Verify database connections from VM-01 and VM-03 work!"
log_warn "If you're locked out, access via console and check:"
log_warn "  - Firewall rules: sudo ufw status"
log_warn "  - SSH configuration: sudo systemctl status ssh"
log_warn "  - PostgreSQL access: sudo cat /etc/postgresql/$PG_VERSION/main/pg_hba.conf"
echo ""

