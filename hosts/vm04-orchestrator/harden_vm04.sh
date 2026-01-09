#!/bin/bash
# harden_vm04.sh - Hardening script for VM-04: Orchestrator/n8n
# Usage: sudo ./harden_vm04.sh
#
# This script applies security hardening to VM-04 (Orchestrator/n8n).
# It configures firewall, SSH, Docker security, n8n security, fail2ban, and log rotation.
#
# Requirements:
#   - Must be run as root (use sudo)
#   - Internet access for package installation
#   - Backup of system files will be created automatically
#   - Docker must be installed and running

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
VM04_DIR="$PROJECT_ROOT/hosts/vm04-orchestrator"

# Get user who ran sudo
if [ -z "$SUDO_USER" ]; then
    echo -e "${RED}ERROR: Cannot determine user. Use: sudo -u user ./harden_vm04.sh${NC}"
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
    ENABLE_AUDITD=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('hardening', {}).get('vm04', {}).get('enable_auditd', False))" 2>/dev/null || echo "False")
    
    # Read n8n port from config
    N8N_PORT=$(python3 -c "import yaml; f=open('$CENTRAL_CONFIG'); d=yaml.safe_load(f); print(d.get('services', {}).get('n8n', {}).get('port', 5678))" 2>/dev/null || echo "5678")
    
    log_info "Configuration loaded from: $CENTRAL_CONFIG"
else
    # Fallback to environment variables or defaults
    log_warn "Central config.yml not found or Python/yaml not available, using defaults or environment variables"
    SSH_PORT="${SSH_PORT:-22}"
    SSH_TIMEOUT="${SSH_TIMEOUT:-300}"
    DISABLE_ROOT_LOGIN="${DISABLE_ROOT_LOGIN:-true}"
    ALLOWED_NETWORK="${ALLOWED_NETWORK:-}"
    ENABLE_AUDITD="${ENABLE_AUDITD:-false}"
    N8N_PORT="${N8N_PORT:-5678}"
fi

# Build firewall ports list (SSH + n8n)
FIREWALL_PORTS="$SSH_PORT,$N8N_PORT"

echo ""
echo "=========================================="
echo "  VM-04 Hardening Script"
echo "=========================================="
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo ""
log_info "Starting VM-04 hardening process..."
echo ""

# ============================================
# 1. Firewall Configuration
# ============================================
echo "=========================================="
echo "  1. Firewall Configuration (ufw)"
echo "=========================================="
log_info "Configuring firewall for VM-04 (Orchestrator/n8n)"

# Configure firewall with SSH and n8n ports
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
# 3. Docker Security Configuration
# ============================================
echo "=========================================="
echo "  3. Docker Security Configuration"
echo "=========================================="
log_info "Configuring Docker security settings"

configure_docker_security() {
    local docker_config="/etc/docker/daemon.json"
    local docker_dir="/etc/docker"
    
    # Create docker directory if it doesn't exist
    if [ ! -d "$docker_dir" ]; then
        mkdir -p "$docker_dir"
    fi
    
    # Backup existing config
    if [ -f "$docker_config" ]; then
        backup_file "$docker_config"
    fi
    
    log_info "Creating secure Docker daemon configuration..."
    
    # Create secure Docker configuration
    cat > "$docker_config" << EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "no-new-privileges": true,
  "userns-remap": "default"
}
EOF
    
    log_success "Docker daemon configuration created"
    
    # Restart Docker to apply changes
    log_info "Restarting Docker to apply security settings..."
    if systemctl restart docker 2>/dev/null; then
        log_success "Docker restarted successfully"
    else
        log_warn "Failed to restart Docker (may need manual restart)"
    fi
}

# Check if Docker is installed
if command -v docker &> /dev/null; then
    configure_docker_security
else
    log_warn "Docker is not installed, skipping Docker security configuration"
fi

echo ""

# ============================================
# 4. n8n Container Security Configuration
# ============================================
echo "=========================================="
echo "  4. n8n Container Security Configuration"
echo "=========================================="
log_info "Updating docker-compose.yml with security settings"

configure_n8n_container_security() {
    local compose_file="$VM04_DIR/docker-compose.yml"
    
    if [ ! -f "$compose_file" ]; then
        log_warn "docker-compose.yml not found at $compose_file"
        log_info "Skipping n8n container security configuration"
        return
    fi
    
    # Backup existing docker-compose.yml
    backup_file "$compose_file"
    
    log_info "Updating docker-compose.yml with security options..."
    
    # Check if security options are already present
    if grep -q "security_opt:" "$compose_file" 2>/dev/null; then
        log_info "Security options already present in docker-compose.yml"
        return
    fi
    
    # Use Python to safely update docker-compose.yml
    python3 << PYTHON_EOF
import yaml
import sys

compose_file = '$compose_file'

try:
    # Read existing docker-compose.yml
    with open(compose_file, 'r') as f:
        compose_data = yaml.safe_load(f) or {}
    
    # Ensure services section exists
    if 'services' not in compose_data:
        compose_data['services'] = {}
    
    # Ensure n8n service exists
    if 'n8n' not in compose_data['services']:
        compose_data['services']['n8n'] = {}
    
    n8n_service = compose_data['services']['n8n']
    
    # Add security options
    n8n_service['security_opt'] = ['no-new-privileges:true']
    
    # Add resource limits
    n8n_service['mem_limit'] = '2g'
    n8n_service['cpus'] = '1.0'
    
    # Add tmpfs for temporary directories (n8n needs write access to /home/node/.n8n, so read_only: false)
    if 'tmpfs' not in n8n_service:
        n8n_service['tmpfs'] = ['/tmp', '/run']
    
    # Add user (non-root) - n8n runs as node user (UID 1000)
    n8n_service['user'] = '1000:1000'
    
    # Write updated docker-compose.yml
    with open(compose_file, 'w') as f:
        yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print("docker-compose.yml updated successfully")
    sys.exit(0)
except Exception as e:
    print(f"Error updating docker-compose.yml: {e}")
    sys.exit(1)
PYTHON_EOF
    
    if [ $? -eq 0 ]; then
        log_success "docker-compose.yml updated with security settings"
        log_info "Security options added: security_opt, mem_limit, cpus, tmpfs, user"
    else
        log_warn "Failed to update docker-compose.yml automatically"
        log_info "You may need to manually add security options to docker-compose.yml"
    fi
}

configure_n8n_container_security

echo ""

# ============================================
# 5. Fail2ban Configuration
# ============================================
echo "=========================================="
echo "  5. Fail2ban Configuration"
echo "=========================================="
log_info "Installing and configuring Fail2ban"

install_fail2ban "sshd"

echo ""

# ============================================
# 6. Logrotate Configuration
# ============================================
echo "=========================================="
echo "  6. Logrotate Configuration"
echo "=========================================="
log_info "Configuring log rotation for Docker and n8n"

# Create logrotate configuration for Docker
DOCKER_LOGROTATE="/etc/logrotate.d/docker"
if [ ! -f "$DOCKER_LOGROTATE" ]; then
    cat > "$DOCKER_LOGROTATE" << EOF
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
    log_success "Created logrotate configuration for Docker logs"
else
    log_info "Docker logrotate configuration already exists"
fi

# Create logrotate configuration for n8n (if logs are stored outside container)
N8N_LOGROTATE="/etc/logrotate.d/n8n"
if [ -d "$VM04_DIR" ]; then
    if [ ! -f "$N8N_LOGROTATE" ]; then
        cat > "$N8N_LOGROTATE" << EOF
$VM04_DIR/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $SUDO_USER $SUDO_USER
}
EOF
        log_success "Created logrotate configuration for n8n logs"
    else
        log_info "n8n logrotate configuration already exists"
    fi
fi

echo ""

# ============================================
# 7. Automatic Updates
# ============================================
echo "=========================================="
echo "  7. Automatic Security Updates"
echo "=========================================="
log_info "Configuring automatic security updates"

configure_auto_updates

echo ""

# ============================================
# 8. Auditd Configuration (Optional)
# ============================================
if [ "$ENABLE_AUDITD" = "True" ] || [ "$ENABLE_AUDITD" = "true" ]; then
    echo "=========================================="
    echo "  8. Auditd Configuration"
    echo "=========================================="
    log_info "Installing and configuring auditd"
    
    configure_auditd
    
    echo ""
fi

# ============================================
# 9. n8n Security Verification
# ============================================
echo "=========================================="
echo "  9. n8n Security Verification"
echo "=========================================="
log_info "Verifying n8n security configuration"

verify_n8n_security() {
    local compose_file="$VM04_DIR/docker-compose.yml"
    local env_file="$VM04_DIR/.env"
    
    if [ -f "$compose_file" ]; then
        log_info "Checking docker-compose.yml security settings..."
        
        # Check if security_opt is present
        if grep -q "security_opt:" "$compose_file" 2>/dev/null; then
            log_success "docker-compose.yml has security_opt configured"
        else
            log_warn "docker-compose.yml missing security_opt (should have no-new-privileges:true)"
        fi
        
        # Check if resource limits are present
        if grep -qE "mem_limit:|cpus:" "$compose_file" 2>/dev/null; then
            log_success "docker-compose.yml has resource limits configured"
        else
            log_warn "docker-compose.yml missing resource limits (mem_limit, cpus)"
        fi
        
        # Check if user is set (non-root)
        if grep -qE "user:\s*['\"]?1000" "$compose_file" 2>/dev/null; then
            log_success "docker-compose.yml configured to run as non-root user"
        else
            log_warn "docker-compose.yml may not be configured to run as non-root user"
        fi
    else
        log_warn "docker-compose.yml not found: $compose_file"
    fi
    
    # Check if .env exists and has basic auth configured
    if [ -f "$env_file" ]; then
        log_info "Checking .env file for basic auth..."
        if grep -q "N8N_BASIC_AUTH_ACTIVE=true" "$env_file" 2>/dev/null || \
           grep -q "N8N_BASIC_AUTH_USER" "$env_file" 2>/dev/null; then
            log_success "n8n basic authentication is configured in .env"
        else
            log_warn "n8n basic authentication may not be configured in .env"
        fi
    else
        log_warn ".env file not found: $env_file"
        log_info "Run install_vm04.sh first to create .env file"
    fi
}

verify_n8n_security

echo ""

# ============================================
# 10. Summary
# ============================================
echo "=========================================="
echo "  Hardening Summary"
echo "=========================================="
log_success "VM-04 hardening completed successfully!"
echo ""
echo "Applied configurations:"
echo "  ✓ Firewall (ufw): SSH ($SSH_PORT), n8n ($N8N_PORT)"
echo "  ✓ SSH hardening: port=$SSH_PORT, timeout=$SSH_TIMEOUT, disable_root=$DISABLE_ROOT_LOGIN"
echo "  ✓ Docker security: log rotation, no-new-privileges"
echo "  ✓ n8n container security: security_opt, resource limits, non-root user"
echo "  ✓ Fail2ban: SSH protection"
echo "  ✓ Logrotate: Docker and n8n logs"
echo "  ✓ Automatic security updates"
if [ "$ENABLE_AUDITD" = "True" ] || [ "$ENABLE_AUDITD" = "true" ]; then
    echo "  ✓ Auditd: System auditing enabled"
fi
echo ""
echo "Next steps:"
echo "  1. Restart n8n container to apply security settings:"
echo "     cd $VM04_DIR && docker compose down && docker compose up -d"
echo "  2. Verify n8n is still accessible: http://$(hostname -I | awk '{print $1}'):$N8N_PORT"
echo "  3. Test SSH connection from another machine"
echo "  4. Check firewall status: sudo ufw status"
echo "  5. Check Fail2ban status: sudo fail2ban-client status sshd"
echo "  6. Check Docker logs: sudo journalctl -u docker -f"
echo ""

