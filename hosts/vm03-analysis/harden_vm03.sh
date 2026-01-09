#!/bin/bash
# harden_vm03.sh - Hardening script for VM-03: Analysis/Jupyter
# Usage: sudo ./harden_vm03.sh
#
# This script applies security hardening to VM-03 (Analysis/Jupyter).
# It configures firewall, SSH, fail2ban, log rotation, and JupyterLab security.
#
# Requirements:
#   - Must be run as root (use sudo)
#   - Internet access for package installation
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
CENTRAL_CONFIG="${PROJECT_ROOT}/configs/config.yml"

# Get user who ran sudo
if [ -z "$SUDO_USER" ]; then
    echo -e "${RED}ERROR: Cannot determine user. Use: sudo -u user ./harden_vm03.sh${NC}"
    exit 1
fi

USER_HOME=$(eval echo ~$SUDO_USER)

# Source common hardening functions
if [ -f "${SCRIPT_DIR}/../shared/hardening_common.sh" ]; then
    source "${SCRIPT_DIR}/../shared/hardening_common.sh"
else
    echo -e "${RED}ERROR: hardening_common.sh not found at ${SCRIPT_DIR}/../shared/hardening_common.sh${NC}"
    exit 1
fi

# Load configuration from central config.yml
if [ -f "$CENTRAL_CONFIG" ] && command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
    # Read hardening configuration from config.yml
    SSH_PORT=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('ssh', {}).get('port', 22))" 2>/dev/null || echo "22")
    SSH_TIMEOUT=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('ssh', {}).get('timeout', 300))" 2>/dev/null || echo "300")
    DISABLE_ROOT_LOGIN=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('ssh', {}).get('disable_root_login', True))" 2>/dev/null || echo "True")
    ALLOWED_NETWORK=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('firewall', {}).get('allowed_network', ''))" 2>/dev/null || echo "")
    ENABLE_AUDITD=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('vm03', {}).get('enable_auditd', False))" 2>/dev/null || echo "False")
    
    # Read JupyterLab port from config
    JUPYTER_PORT=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('services', {}).get('jupyter', {}).get('port', 8888))" 2>/dev/null || echo "8888")
    
    log_info "Configuration loaded from: $CENTRAL_CONFIG"
else
    # Fallback to environment variables or defaults
    log_warn "Central config.yml not found or Python/yaml not available, using defaults or environment variables"
    SSH_PORT="${SSH_PORT:-22}"
    SSH_TIMEOUT="${SSH_TIMEOUT:-300}"
    DISABLE_ROOT_LOGIN="${DISABLE_ROOT_LOGIN:-true}"
    ALLOWED_NETWORK="${ALLOWED_NETWORK:-}"
    ENABLE_AUDITD="${ENABLE_AUDITD:-false}"
    JUPYTER_PORT="${JUPYTER_PORT:-8888}"
fi

# Build firewall ports list (SSH + JupyterLab)
FIREWALL_PORTS="$SSH_PORT,$JUPYTER_PORT"

echo ""
echo "=========================================="
echo "  VM-03 Hardening Script"
echo "=========================================="
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo ""
log_info "Starting VM-03 hardening process..."
echo ""

# ============================================
# 1. Firewall Configuration
# ============================================
echo "=========================================="
echo "  1. Firewall Configuration (ufw)"
echo "=========================================="
log_info "Configuring firewall for VM-03 (Analysis/Jupyter)"

# Configure firewall with SSH and JupyterLab ports
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

if [ "$DISABLE_ROOT_LOGIN" = "True" ] || [ "$DISABLE_ROOT_LOGIN" = "true" ]; then
    configure_ssh true "$SSH_PORT" "$SSH_TIMEOUT"
else
    log_warn "Root login is enabled (not recommended)"
    configure_ssh false "$SSH_PORT" "$SSH_TIMEOUT"
fi

echo ""

# ============================================
# 3. Fail2ban Configuration
# ============================================
echo "=========================================="
echo "  3. Fail2ban Configuration"
echo "=========================================="
log_info "Installing and configuring Fail2ban"

install_fail2ban "sshd"

echo ""

# ============================================
# 4. Logrotate Configuration
# ============================================
echo "=========================================="
echo "  4. Logrotate Configuration"
echo "=========================================="
log_info "Configuring log rotation for JupyterLab"

# Create logrotate configuration for JupyterLab
JUPYTER_LOGROTATE="/etc/logrotate.d/jupyter"
if [ ! -f "$JUPYTER_LOGROTATE" ]; then
    cat > "$JUPYTER_LOGROTATE" << EOF
$USER_HOME/.jupyter/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $SUDO_USER $SUDO_USER
}
EOF
    log_success "Created logrotate configuration for JupyterLab"
else
    log_info "JupyterLab logrotate configuration already exists"
fi

echo ""

# ============================================
# 5. Automatic Updates
# ============================================
echo "=========================================="
echo "  5. Automatic Security Updates"
echo "=========================================="
log_info "Configuring automatic security updates"

configure_auto_updates

echo ""

# ============================================
# 6. Auditd Configuration (Optional)
# ============================================
if [ "$ENABLE_AUDITD" = "True" ] || [ "$ENABLE_AUDITD" = "true" ]; then
    echo "=========================================="
    echo "  6. Auditd Configuration"
    echo "=========================================="
    log_info "Installing and configuring auditd"
    
    configure_auditd
    
    echo ""
fi

# ============================================
# 7. JupyterLab Security Verification
# ============================================
echo "=========================================="
echo "  7. JupyterLab Security Verification"
echo "=========================================="
log_info "Verifying JupyterLab security configuration"

verify_jupyter_upload_config() {
    local config_file="$USER_HOME/.jupyter/jupyter_lab_config.py"
    
    if [ -f "$config_file" ]; then
        log_info "Checking JupyterLab configuration: $config_file"
        
        # Check if allow_hidden is disabled
        if grep -q "allow_hidden = False" "$config_file" 2>/dev/null; then
            log_success "JupyterLab allow_hidden is properly configured (disabled)"
        else
            log_warn "JupyterLab allow_hidden not properly configured (should be False)"
        fi
        
        # Check if delete_to_trash is enabled
        if grep -q "delete_to_trash = True" "$config_file" 2>/dev/null; then
            log_success "JupyterLab delete_to_trash is properly configured (enabled)"
        else
            log_warn "JupyterLab delete_to_trash not properly configured (should be True)"
        fi
        
        # Check if token or password is set
        if grep -qE "c\.ServerApp\.(token|password) = " "$config_file" 2>/dev/null; then
            log_success "JupyterLab authentication is configured (token or password)"
        else
            log_warn "JupyterLab authentication may not be configured (no token or password found)"
        fi
    else
        log_warn "JupyterLab configuration file not found: $config_file"
        log_info "Run install_vm03.sh first to generate JupyterLab configuration"
    fi
}

verify_jupyter_upload_config

echo ""

# ============================================
# 8. Summary
# ============================================
echo "=========================================="
echo "  Hardening Summary"
echo "=========================================="
log_success "VM-03 hardening completed successfully!"
echo ""
echo "Applied configurations:"
echo "  ✓ Firewall (ufw): SSH ($SSH_PORT), JupyterLab ($JUPYTER_PORT)"
echo "  ✓ SSH hardening: port=$SSH_PORT, timeout=$SSH_TIMEOUT, disable_root=$DISABLE_ROOT_LOGIN"
echo "  ✓ Fail2ban: SSH protection"
echo "  ✓ Logrotate: JupyterLab logs"
echo "  ✓ Automatic security updates"
if [ "$ENABLE_AUDITD" = "True" ] || [ "$ENABLE_AUDITD" = "true" ]; then
    echo "  ✓ Auditd: System auditing enabled"
fi
echo ""
echo "Next steps:"
echo "  1. Verify JupyterLab is still accessible: http://$(hostname -I | awk '{print $1}'):$JUPYTER_PORT"
echo "  2. Test SSH connection from another machine"
echo "  3. Check firewall status: sudo ufw status"
echo "  4. Check Fail2ban status: sudo fail2ban-client status sshd"
echo ""

