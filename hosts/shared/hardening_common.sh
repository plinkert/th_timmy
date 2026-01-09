#!/bin/bash
# hardening_common.sh - Common hardening functions
# This file is sourced by VM-specific hardening scripts
# Usage: source hardening_common.sh

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Colors for logging
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Backup file before modification
backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        local backup="${file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$file" "$backup"
        log_info "Backed up $file to $backup"
        echo "$backup"
    fi
}

# Configure firewall (ufw)
# Usage: configure_firewall ports allowed_ips
# Example: configure_firewall "22,5432,8888" "10.0.0.0/24"
configure_firewall() {
    local ports="$1"
    local allowed_ips="${2:-}"
    
    log_info "Configuring firewall (ufw)..."
    
    # Check if ufw is installed
    if ! command -v ufw &> /dev/null; then
        log_warn "ufw not installed, installing..."
        apt-get update -qq && apt-get install -y ufw
    fi
    
    # Reset ufw to defaults (if not already configured)
    if ! ufw status | grep -q "Status: active"; then
        log_info "Resetting ufw to defaults..."
        ufw --force reset
        ufw default deny incoming
        ufw default allow outgoing
    fi
    
    # Allow SSH (critical - don't lock yourself out)
    log_info "Allowing SSH (port 22)..."
    ufw allow 22/tcp comment 'SSH'
    
    # Allow specified ports
    if [ -n "$ports" ]; then
        IFS=',' read -ra PORT_ARRAY <<< "$ports"
        for port in "${PORT_ARRAY[@]}"; do
            port=$(echo "$port" | xargs)  # Trim whitespace
            if [ -n "$port" ]; then
                if [ -n "$allowed_ips" ]; then
                    log_info "Allowing port $port from $allowed_ips..."
                    ufw allow from "$allowed_ips" to any port "$port" comment "Port $port"
                else
                    log_info "Allowing port $port..."
                    ufw allow "$port/tcp" comment "Port $port"
                fi
            fi
        done
    fi
    
    # Enable ufw (non-interactive)
    if ! ufw status | grep -q "Status: active"; then
        log_info "Enabling ufw..."
        ufw --force enable
        log_success "Firewall configured and enabled"
    else
        log_success "Firewall already active"
    fi
}

# Configure SSH
# Usage: configure_ssh disable_root port timeout
# Example: configure_ssh true 22 300
configure_ssh() {
    local disable_root="${1:-true}"
    local port="${2:-22}"
    local timeout="${3:-300}"
    
    log_info "Configuring SSH..."
    
    local sshd_config="/etc/ssh/sshd_config"
    backup_file "$sshd_config"
    
    # Disable root login
    if [ "$disable_root" = "true" ]; then
        log_info "Disabling root login..."
        sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' "$sshd_config"
    fi
    
    # Change SSH port (if different from default)
    if [ "$port" != "22" ]; then
        log_info "Changing SSH port to $port..."
        sed -i "s/^#*Port.*/Port $port/" "$sshd_config"
    fi
    
    # Set connection timeout
    log_info "Setting SSH timeout to $timeout seconds..."
    sed -i "s/^#*ClientAliveInterval.*/ClientAliveInterval $timeout/" "$sshd_config"
    sed -i "s/^#*ClientAliveCountMax.*/ClientAliveCountMax 0/" "$sshd_config"
    
    # Additional security settings
    log_info "Applying additional SSH security settings..."
    sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' "$sshd_config"
    sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' "$sshd_config"
    sed -i 's/^#*Protocol.*/Protocol 2/' "$sshd_config"
    
    # Restart SSH service
    log_info "Restarting SSH service..."
    if systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null; then
        log_success "SSH configured and restarted"
    else
        log_warn "SSH service restart failed (may need manual restart)"
    fi
}

# Install and configure fail2ban
# Usage: install_fail2ban services
# Example: install_fail2ban "sshd,postgresql"
install_fail2ban() {
    local services="${1:-sshd}"
    
    log_info "Installing and configuring fail2ban..."
    
    # Install fail2ban
    if ! command -v fail2ban-client &> /dev/null; then
        log_info "Installing fail2ban..."
        apt-get update -qq && apt-get install -y fail2ban
    fi
    
    # Configure fail2ban
    local jail_local="/etc/fail2ban/jail.local"
    backup_file "$jail_local"
    
    log_info "Configuring fail2ban for services: $services"
    
    {
        echo "[DEFAULT]"
        echo "bantime = 3600"
        echo "findtime = 600"
        echo "maxretry = 5"
        echo ""
        
        IFS=',' read -ra SERVICE_ARRAY <<< "$services"
        for service in "${SERVICE_ARRAY[@]}"; do
            service=$(echo "$service" | xargs)  # Trim whitespace
            if [ -n "$service" ]; then
                echo "[$service]"
                echo "enabled = true"
                echo ""
            fi
        done
    } > "$jail_local"
    
    # Enable and start fail2ban
    systemctl enable fail2ban
    systemctl restart fail2ban
    
    log_success "fail2ban installed and configured"
}

# Configure logrotate
# Usage: configure_logrotate config_file log_path
# Example: configure_logrotate "/etc/logrotate.d/threat-hunting" "/var/log/threat-hunting/*.log"
configure_logrotate() {
    local config_file="$1"
    local log_path="$2"
    
    log_info "Configuring logrotate for $log_path..."
    
    backup_file "$config_file"
    
    {
        echo "$log_path {"
        echo "    daily"
        echo "    rotate 30"
        echo "    compress"
        echo "    delaycompress"
        echo "    missingok"
        echo "    notifempty"
        echo "    create 0640 root root"
        echo "}"
    } > "$config_file"
    
    log_success "logrotate configured for $log_path"
}

# Configure automatic security updates
# Usage: configure_auto_updates
configure_auto_updates() {
    log_info "Configuring automatic security updates..."
    
    # Install unattended-upgrades if not present
    if ! command -v unattended-upgrade &> /dev/null; then
        log_info "Installing unattended-upgrades..."
        apt-get update -qq && apt-get install -y unattended-upgrades
    fi
    
    # Configure automatic updates
    local config_file="/etc/apt/apt.conf.d/50unattended-upgrades"
    backup_file "$config_file"
    
    # Enable automatic security updates
    sed -i 's|//Unattended-Upgrade::Remove-Unused-Kernel-Packages|Unattended-Upgrade::Remove-Unused-Kernel-Packages|' "$config_file"
    sed -i 's|//Unattended-Upgrade::Remove-Unused-Dependencies|Unattended-Upgrade::Remove-Unused-Dependencies|' "$config_file"
    
    # Enable automatic updates
    local auto_upgrade="/etc/apt/apt.conf.d/20auto-upgrades"
    backup_file "$auto_upgrade"
    
    {
        echo "APT::Periodic::Update-Package-Lists \"1\";"
        echo "APT::Periodic::Unattended-Upgrade \"1\";"
        echo "APT::Periodic::Download-Upgradeable-Packages \"1\";"
        echo "APT::Periodic::AutocleanInterval \"7\";"
    } > "$auto_upgrade"
    
    log_success "Automatic security updates configured"
}

# Configure auditd (optional)
# Usage: configure_auditd
configure_auditd() {
    log_info "Configuring auditd..."
    
    # Install auditd if not present
    if ! command -v auditd &> /dev/null; then
        log_info "Installing auditd..."
        apt-get update -qq && apt-get install -y auditd audispd-plugins
    fi
    
    # Enable auditd
    systemctl enable auditd
    systemctl start auditd
    
    log_success "auditd configured and started"
}

# Show available functions and usage information
show_help() {
    cat << EOF
hardening_common.sh - Common Hardening Functions Library

This is a library of hardening functions that should be SOURCED by other scripts,
not executed directly.

USAGE:
    source hardening_common.sh
    
    # Then use the functions:
    configure_firewall "22,5432,8888" "10.0.0.0/24"
    configure_ssh true 22 300
    install_fail2ban "sshd,postgresql"

AVAILABLE FUNCTIONS:

1. configure_firewall(ports, allowed_ips)
   - Configures ufw firewall
   - Example: configure_firewall "22,5432,8888" "10.0.0.0/24"

2. configure_ssh(disable_root, port, timeout)
   - Configures SSH security settings
   - Example: configure_ssh true 22 300

3. install_fail2ban(services)
   - Installs and configures fail2ban
   - Example: install_fail2ban "sshd,postgresql"

4. configure_logrotate(config_file, log_path)
   - Configures log rotation
   - Example: configure_logrotate "/etc/logrotate.d/app" "/var/log/app/*.log"

5. configure_auto_updates()
   - Configures automatic security updates
   - Example: configure_auto_updates

6. configure_auditd()
   - Configures system auditing (optional)
   - Example: configure_auditd

LOGGING FUNCTIONS:
- log_info(message)    - Blue info message
- log_success(message)  - Green success message
- log_warn(message)      - Yellow warning message
- log_error(message)     - Red error message

EXAMPLE SCRIPT:
    #!/bin/bash
    source hardening_common.sh
    
    configure_firewall "22,5432" "10.0.0.0/24"
    configure_ssh true 22 300
    install_fail2ban "sshd"
    configure_auto_updates

EOF
}

# If script is executed directly (not sourced), show help
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "ERROR: This is a library file and should be SOURCED, not executed directly."
    echo ""
    echo "Usage: source $(basename "${BASH_SOURCE[0]}")"
    echo ""
    show_help
    exit 1
fi

