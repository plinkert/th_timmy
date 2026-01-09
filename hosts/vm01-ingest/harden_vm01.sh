#!/bin/bash
# harden_vm01.sh - Hardening script for VM-01: Ingest/Parser
# Usage: sudo ./harden_vm01.sh
#
# This script applies security hardening to VM-01 (Ingest/Parser).
# It configures firewall, SSH, fail2ban, log rotation, and automatic updates.
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

# Source common hardening functions
if [ -f "${SCRIPT_DIR}/../shared/hardening_common.sh" ]; then
    source "${SCRIPT_DIR}/../shared/hardening_common.sh"
else
    echo -e "${RED}ERROR: hardening_common.sh not found at ${SCRIPT_DIR}/../shared/hardening_common.sh${NC}"
    exit 1
fi

# Configuration
# Default SSH port (can be changed via environment variable)
SSH_PORT="${SSH_PORT:-22}"
SSH_TIMEOUT="${SSH_TIMEOUT:-300}"

# Firewall configuration
# Ports to open: SSH (required), and any collector ports
# Collector ports can be customized via environment variable
COLLECTOR_PORTS="${COLLECTOR_PORTS:-}"
ALLOWED_NETWORK="${ALLOWED_NETWORK:-}"

# Build firewall ports list
FIREWALL_PORTS="$SSH_PORT"
if [ -n "$COLLECTOR_PORTS" ]; then
    FIREWALL_PORTS="$FIREWALL_PORTS,$COLLECTOR_PORTS"
fi

echo ""
echo "=========================================="
echo "  VM-01 Hardening Script"
echo "=========================================="
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo ""
log_info "Starting VM-01 hardening process..."
echo ""

# ============================================
# 1. Firewall Configuration
# ============================================
echo "=========================================="
echo "  1. Firewall Configuration (ufw)"
echo "=========================================="
log_info "Configuring firewall for VM-01 (Ingest/Parser)"

# Configure firewall with SSH and collector ports
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

# Disable root login, set port and timeout
configure_ssh true "$SSH_PORT" "$SSH_TIMEOUT"

echo ""

# ============================================
# 3. Fail2ban Installation and Configuration
# ============================================
echo "=========================================="
echo "  3. Fail2ban Configuration"
echo "=========================================="
log_info "Installing and configuring fail2ban for SSH protection"

# Install and configure fail2ban for SSH
install_fail2ban "sshd"

echo ""

# ============================================
# 4. Log Rotation Configuration
# ============================================
echo "=========================================="
echo "  4. Log Rotation Configuration"
echo "=========================================="
log_info "Configuring log rotation for application logs"

# Configure log rotation for threat hunting logs
LOG_ROTATE_CONFIG="/etc/logrotate.d/threat-hunting-vm01"
LOG_PATH="${PROJECT_ROOT}/logs/*.log"

# Create logs directory if it doesn't exist
mkdir -p "${PROJECT_ROOT}/logs"

# Configure logrotate
configure_logrotate "$LOG_ROTATE_CONFIG" "$LOG_PATH"

echo ""

# ============================================
# 5. Automatic Security Updates
# ============================================
echo "=========================================="
echo "  5. Automatic Security Updates"
echo "=========================================="
log_info "Configuring automatic security updates"

configure_auto_updates

echo ""

# ============================================
# 6. Optional: System Auditing (auditd)
# ============================================
if [ "${ENABLE_AUDITD:-false}" = "true" ]; then
    echo "=========================================="
    echo "  6. System Auditing (auditd)"
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
log_success "VM-01 hardening completed successfully!"
echo ""
log_info "Applied configurations:"
echo "  ✓ Firewall (ufw) configured"
echo "  ✓ SSH hardened (root login disabled, port: $SSH_PORT)"
echo "  ✓ Fail2ban installed and configured"
echo "  ✓ Log rotation configured"
echo "  ✓ Automatic security updates enabled"
if [ "${ENABLE_AUDITD:-false}" = "true" ]; then
    echo "  ✓ System auditing (auditd) enabled"
fi
echo ""
log_info "Next steps:"
echo "  1. Test SSH connection to ensure you can still access the system"
echo "  2. Verify firewall rules: sudo ufw status"
echo "  3. Check fail2ban status: sudo fail2ban-client status"
echo "  4. Run health check: ./health_check.sh"
echo ""
log_warn "IMPORTANT: Make sure you can still SSH to this system!"
log_warn "If you're locked out, access via console and check:"
log_warn "  - Firewall rules: sudo ufw status"
log_warn "  - SSH configuration: sudo systemctl status ssh"
echo ""

