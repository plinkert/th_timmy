#!/bin/bash

# Automatic SSH key creation and configuration for VM01-VM03
# Run on VM04 (orchestrator)

# set -e  # Disabled - allow loop to continue on per-host errors
set -u   # Check for unset variables
set -o pipefail  # Check pipeline errors

# Colors for readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/configs/config.yml"

# Use HOME of user who ran the script (not root when run with sudo)
# Safe check for SUDO_USER (may be unset)
if [ -n "${SUDO_USER:-}" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    REAL_USER="${USER:-$(whoami)}"
    REAL_HOME="$HOME"
fi

SSH_DIR="$REAL_HOME/.ssh"
SSH_KEYS_DIR="$SSH_DIR/th_timmy_keys"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Fix file ownership when script is run with sudo
fix_file_ownership() {
    local file_or_dir="$1"
    if [ -n "${SUDO_USER:-}" ] && [ -e "$file_or_dir" ]; then
        # When root (via sudo), we can chown directly
        if [ "$(id -u)" -eq 0 ]; then
            chown -R "$REAL_USER:$REAL_USER" "$file_or_dir" 2>/dev/null || {
                log_warning "Could not change owner of $file_or_dir to $REAL_USER"
            }
        fi
    fi
}

# Check that config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Config file not found: $CONFIG_FILE"
    exit 1
fi

log_info "Using config file: $CONFIG_FILE"

# SSH path info
if [ -n "${SUDO_USER:-}" ]; then
    log_warning "Note: Script run with sudo. Using SSH dir for user: $SSH_DIR"
    log_warning "Files will be owned by: $REAL_USER"
else
    log_info "Using SSH directory: $SSH_DIR"
fi

# Check write access to SSH directory
if [ ! -w "$SSH_DIR" ] && [ ! -w "$(dirname "$SSH_DIR")" ]; then
    log_error "No write permission for SSH directory: $SSH_DIR"
    log_error "Run script as user with access to ~/.ssh/"
    exit 1
fi

# Check Python and PyYAML availability
if ! command -v python3 &> /dev/null; then
    log_error "python3 not installed. Install: sudo apt-get install python3"
    exit 1
fi

# Check PyYAML availability
if ! python3 -c "import yaml" 2>/dev/null; then
    log_warning "PyYAML not installed. Attempting to install..."
    if command -v pip3 &> /dev/null; then
        pip3 install --user pyyaml 2>/dev/null || {
            log_error "Could not install PyYAML. Install manually: pip3 install pyyaml"
            exit 1
        }
    else
        log_error "pip3 not available. Install PyYAML manually: pip3 install pyyaml"
        exit 1
    fi
fi

# Parse YAML and extract VM info
parse_vm_config() {
    local vm_id=$1
    local exit_code=0
    local output
    
    output=$(python3 << EOF 2>&1
import yaml
import sys

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)
    
    vms = config.get('vms', {})
    vm = vms.get('$vm_id', {})
    
    if not vm:
        print(f"ERROR: VM $vm_id nie znaleziony w konfiguracji", file=sys.stderr)
        sys.exit(1)
    
    ip = vm.get('ip', '')
    ssh_user = vm.get('ssh_user', 'thadmin')
    ssh_port = vm.get('ssh_port', 22)
    enabled = vm.get('enabled', True)
    
    if not enabled:
        print(f"ERROR: VM $vm_id is disabled in config", file=sys.stderr)
        sys.exit(1)
    
    if not ip:
        print(f"ERROR: Brak adresu IP dla VM $vm_id", file=sys.stderr)
        sys.exit(1)
    
    print(f"{ip}|{ssh_user}|{ssh_port}")
except Exception as e:
    print(f"ERROR: YAML parse error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
)
    exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        echo "$output" >&2
        return $exit_code
    fi
    
    echo "$output"
    return 0
}

# Funkcja do generowania klucza SSH
generate_ssh_key() {
    local vm_id=$1
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}"
    
    if [ -f "${key_file}" ]; then
        log_warning "Key already exists for $vm_id: ${key_file}"
        if [ -t 0 ]; then
            # Only when interactive terminal
            read -p "Overwrite existing key? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Pomijam generowanie klucza dla $vm_id"
                return 0
            fi
        else
            # Tryb nieinteraktywny - nie nadpisuj
            log_info "Non-interactive mode - skipping key generation for $vm_id (key already exists)"
            return 0
        fi
        # Backup starego klucza
        if [ -f "${key_file}" ]; then
            mv "${key_file}" "${key_file}.backup.$(date +%Y%m%d_%H%M%S)" || true
        fi
        if [ -f "${key_file}.pub" ]; then
            mv "${key_file}.pub" "${key_file}.pub.backup.$(date +%Y%m%d_%H%M%S)" || true
        fi
    fi
    
    log_step "Generowanie klucza SSH dla $vm_id..."
    
    # Create directory if it does not exist
    mkdir -p "$SSH_KEYS_DIR"
    chmod 700 "$SSH_KEYS_DIR"
    fix_file_ownership "$SSH_KEYS_DIR"
    
    # Generate ed25519 key (recommended, secure and fast)
    if ssh-keygen -t ed25519 -f "${key_file}" -N "" -C "th_timmy_${vm_id}_$(date +%Y%m%d)"; then
        chmod 600 "${key_file}"
        chmod 644 "${key_file}.pub"
        # Change owner to correct user (when run with sudo)
        fix_file_ownership "${key_file}"
        fix_file_ownership "${key_file}.pub"
        log_success "Klucz wygenerowany: ${key_file}"
        return 0
    else
        log_error "Error generating key for $vm_id"
        return 1
    fi
}

# Funkcja do kopiowania klucza publicznego na host
copy_public_key() {
    local vm_id=$1
    local ip=$2
    local ssh_user=$3
    local ssh_port=$4
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}.pub"
    
    if [ ! -f "$key_file" ]; then
        log_error "Klucz publiczny nie istnieje: $key_file"
        return 1
    fi
    
    log_step "Kopiowanie klucza publicznego na $vm_id ($ssh_user@$ip:$ssh_port)..."
    
    # Check if ssh-copy-id is available
    if command -v ssh-copy-id &> /dev/null; then
        # Use ssh-copy-id (simplest)
        if ssh-copy-id -i "$key_file" -p "$ssh_port" "$ssh_user@$ip" 2>/dev/null; then
            log_success "Key copied using ssh-copy-id"
            return 0
        else
            log_warning "ssh-copy-id failed, trying manually..."
        fi
    fi
    
    # Manual key copy (when ssh-copy-id does not work)
    log_info "Attempting manual key copy..."
    
    # Check if we can connect via SSH (may require password)
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "$ssh_port" "$ssh_user@$ip" "mkdir -p ~/.ssh && chmod 700 ~/.ssh" 2>/dev/null; then
        # Copy public key
        if cat "$key_file" | ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "$ssh_port" "$ssh_user@$ip" "cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"; then
            log_success "Key copied manually"
            return 0
        fi
    fi
    
    # Or use sshpass if available (for automatic password entry)
    if command -v sshpass &> /dev/null && [ -t 0 ]; then
        log_info "Using sshpass to copy key..."
        read -sp "Enter password for $ssh_user@$ip: " password
        echo
        if [ -n "$password" ] && sshpass -p "$password" ssh-copy-id -i "$key_file" -p "$ssh_port" -o StrictHostKeyChecking=no "$ssh_user@$ip" 2>/dev/null; then
            log_success "Key copied using sshpass"
            return 0
        fi
    fi
    
    log_error "Could not copy key to $vm_id"
    log_warning "You can copy the key manually:"
    log_warning "  cat $key_file | ssh -p $ssh_port $ssh_user@$ip 'cat >> ~/.ssh/authorized_keys'"
    return 1
}

# Test SSH connection
test_ssh_connection() {
    local vm_id=$1
    local ip=$2
    local ssh_user=$3
    local ssh_port=$4
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}"
    
    log_step "Testing SSH connection to $vm_id..."
    
    if ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" "echo 'SSH connection successful'" 2>/dev/null; then
        log_success "SSH connection OK for $vm_id"
        return 0
    else
        log_error "Could not connect via SSH to $vm_id"
        return 1
    fi
}

# Enforce key-based SSH login and disable password login
configure_ssh_server() {
    local vm_id=$1
    local ip=$2
    local ssh_user=$3
    local ssh_port=$4
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}"
    
    log_step "Configuring SSH server on $vm_id (enforce keys, disable password)..."
    log_warning "WARNING: This operation requires sudo on the target host!"
    log_warning "After this, password login will be disabled - ensure key auth works first!"
    
    # Check we can connect using the key
    if ! ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" "true" 2>/dev/null; then
        log_error "Cannot connect to $vm_id using key. Skipping SSH server configuration."
        log_error "IMPORTANT: Cannot enforce keys if key-based connection does not work!"
        return 1
    fi
    
    # Check if user has sudo privileges
    log_info "Checking sudo privileges..."
    if ! ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" "sudo -n true" 2>/dev/null; then
        log_warning "User $ssh_user may lack sudo or a password may be required."
        log_warning "Attempting configuration (may prompt for sudo password)..."
    else
        log_success "Uprawnienia sudo potwierdzone"
    fi
    
    # Backup oryginalnego pliku konfiguracyjnego
    log_info "Tworzenie kopii zapasowej /etc/ssh/sshd_config..."
    ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" \
        "sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || {
        log_warning "Could not create backup (may lack sudo privileges)"
    }
    
    # Modify SSH configuration
    log_info "Modifying SSH configuration..."
    
    # Build script to run on remote host
    local remote_script=$(cat << 'REMOTE_SCRIPT_END'
#!/bin/bash
set -e

# Backup configuration
SSHD_CONFIG="/etc/ssh/sshd_config"
BACKUP_FILE="${SSHD_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$SSHD_CONFIG" "$BACKUP_FILE"
echo "Backup created: $BACKUP_FILE"

# Set option in config file
set_ssh_option() {
    local option="$1"
    local value="$2"
    local config_file="$3"
    
    # Check if option already exists (commented or not)
    if grep -qE "^[[:space:]]*#?[[:space:]]*${option}[[:space:]]+" "$config_file" 2>/dev/null; then
        # Update existing option (uncomment if needed)
        sed -i "s/^[[:space:]]*#\?[[:space:]]*${option}[[:space:]]*.*/${option} ${value}/" "$config_file"
        echo "Updated: ${option} ${value}"
    else
        # Append new option at end of file
        echo "${option} ${value}" >> "$config_file"
        echo "Added: ${option} ${value}"
    fi
}

# Set SSH security options
set_ssh_option "PasswordAuthentication" "no" "$SSHD_CONFIG"
set_ssh_option "PubkeyAuthentication" "yes" "$SSHD_CONFIG"
set_ssh_option "ChallengeResponseAuthentication" "no" "$SSHD_CONFIG"
set_ssh_option "UsePAM" "no" "$SSHD_CONFIG"
set_ssh_option "PermitRootLogin" "no" "$SSHD_CONFIG"

# Optional: additional security options
set_ssh_option "X11Forwarding" "no" "$SSHD_CONFIG"
set_ssh_option "MaxAuthTries" "3" "$SSHD_CONFIG"
set_ssh_option "ClientAliveInterval" "300" "$SSHD_CONFIG"
set_ssh_option "ClientAliveCountMax" "2" "$SSHD_CONFIG"

# Check config syntax before reload
echo "Checking SSH config syntax..."
if sshd -t 2>/dev/null; then
    echo "SSH config is valid"
    # Reload SSH (do not restart to avoid dropping connection)
    if command -v systemctl &> /dev/null; then
        systemctl reload sshd 2>/dev/null && echo "SSH reloaded (systemctl)" || {
            echo "Could not reload via systemctl, trying service..."
            service ssh reload 2>/dev/null || service sshd reload 2>/dev/null || {
                echo "WARNING: Could not reload SSH. Restart may be needed: sudo systemctl restart sshd"
            }
        }
    else
        service ssh reload 2>/dev/null || service sshd reload 2>/dev/null || {
            echo "WARNING: Could not reload SSH. Restart may be needed."
        }
    fi
    echo "SSH config updated and reloaded"
    exit 0
else
    echo "ERROR: SSH config has errors! Restoring backup..."
    cp "$BACKUP_FILE" "$SSHD_CONFIG"
    exit 1
fi
REMOTE_SCRIPT_END
)
    
    # Check if sudo requires password
    local ssh_base_flags="-i $key_file -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p $ssh_port"
    local sudo_password=""
    local needs_password=false
    
    if ! ssh $ssh_base_flags "$ssh_user@$ip" "sudo -n true" 2>/dev/null; then
        needs_password=true
        log_warning "Sudo requires password on $vm_id"
        
        if [ -t 0 ]; then
            # Terminal available - prompt for password
            read -sp "Enter sudo password for $ssh_user@$ip: " sudo_password
            echo
            if [ -z "$sudo_password" ]; then
                log_error "No password entered. Skipping SSH server config for $vm_id"
                return 1
            fi
        else
            log_error "Sudo requires password but terminal is not available (non-interactive)"
            log_error "Configure sudo NOPASSWD for $ssh_user on $ip or run script interactively"
            return 1
        fi
    else
        log_info "Sudo does not require password, running configuration..."
    fi
    
    # Run script with appropriate sudo password handling
    local ssh_output
    if [ "$needs_password" = true ] && [ -n "$sudo_password" ]; then
        # Create temporary script on remote host and run with sudo
        # Avoids stdin/password piping issues
        local temp_script="/tmp/configure_ssh_$$.sh"
        
        # Send script to remote host and run with sudo -S
        ssh_output=$(ssh $ssh_base_flags "$ssh_user@$ip" bash << EOF 2>&1
cat > $temp_script << 'SCRIPT_END'
$remote_script
SCRIPT_END
chmod +x $temp_script
echo '$sudo_password' | sudo -S bash $temp_script
rm -f $temp_script
EOF
)
        local ssh_exit_code=$?
        
        # Clear password from memory
        sudo_password=""
    else
        # Sudo does not require password
        ssh_output=$(echo "$remote_script" | ssh $ssh_base_flags "$ssh_user@$ip" \
            "sudo bash" 2>&1)
        local ssh_exit_code=$?
    fi
    
    # Show output (skip blank lines and some prompts)
    echo "$ssh_output" | grep -v "^$" | while IFS= read -r line; do
        if [[ "$line" =~ ^\[sudo\].*password ]] || [[ "$line" =~ ^sudo:.*password ]]; then
            # Pomijamy prompt sudo
            :
        elif [[ "$line" =~ ^Pseudo-terminal ]]; then
            # Pomijamy komunikaty o terminalu
            :
        else
            log_info "  $line"
        fi
    done
    
    if [ $ssh_exit_code -eq 0 ]; then
        log_success "Konfiguracja serwera SSH zaktualizowana na $vm_id"
        log_info "  - PasswordAuthentication: no"
        log_info "  - PubkeyAuthentication: yes"
        log_info "  - PermitRootLogin: no"
        
        # Test that we can still connect (key-only should work)
        log_info "Testing connection after changes..."
        sleep 2
        if ssh -i "$key_file" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -p "$ssh_port" "$ssh_user@$ip" "echo 'Connection test successful'" 2>/dev/null; then
            log_success "SSH key connection works"
            
            # Password login attempt should fail
            log_info "Verifying: password login attempt should fail..."
            if ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no -p "$ssh_port" "$ssh_user@$ip" "true" 2>/dev/null; then
                log_warning "WARNING: Password login still works! SSH restart may be required."
            else
                log_success "Verification: password login is disabled"
            fi
        else
            log_error "WARNING: Cannot connect after changes! Check configuration manually."
            return 1
        fi
        return 0
    else
        log_error "Error configuring SSH server on $vm_id"
        return 1
    fi
}

# Funkcja do konfiguracji SSH config
configure_ssh_config() {
    local vm_id=$1
    local ip=$2
    local ssh_user=$3
    local ssh_port=$4
    local key_file="$SSH_KEYS_DIR/id_ed25519_${vm_id}"
    local ssh_config="$SSH_DIR/config"
    
    log_step "Konfigurowanie ~/.ssh/config dla $vm_id..."
    
    # Create .ssh directory if it does not exist
    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"
    fix_file_ownership "$SSH_DIR"
    
    # Create config file if it does not exist
    touch "$ssh_config"
    chmod 600 "$ssh_config"
    fix_file_ownership "$ssh_config"
    
    # Check if entry already exists
    if grep -q "Host $vm_id" "$ssh_config" 2>/dev/null; then
        log_warning "Entry for $vm_id already exists in ~/.ssh/config"
        if [ -t 0 ]; then
            # Only when interactive terminal
            read -p "Update existing entry? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Skipping SSH config for $vm_id"
                return 0
            fi
        else
            # Non-interactive - update automatically
            log_info "Non-interactive mode - updating existing entry"
        fi
        # Remove old entry (from "Host $vm_id" to blank or next "Host")
        sed -i "/^Host $vm_id$/,/^Host /{ /^Host $vm_id$/!{ /^Host /!d; }; }" "$ssh_config" 2>/dev/null || true
        sed -i "/^Host $vm_id$/,/^$/d" "$ssh_config" 2>/dev/null || true
    fi
    
    # Relative key path (use ~ instead of full path)
    local relative_key_path="~/.ssh/th_timmy_keys/id_ed25519_${vm_id}"
    
    # Add new entry per requirements
    # Include Port only if not default (22)
    if [ "$ssh_port" != "22" ]; then
        cat >> "$ssh_config" << EOF

Host $vm_id
    HostName $ip
    User $ssh_user
    Port $ssh_port
    IdentityFile $relative_key_path
    IdentitiesOnly yes
EOF
    else
        cat >> "$ssh_config" << EOF

Host $vm_id
    HostName $ip
    User $ssh_user
    IdentityFile $relative_key_path
    IdentitiesOnly yes
EOF
    fi
    
    # Fix config file owner (when run with sudo)
    fix_file_ownership "$ssh_config"
    
    log_success "Added entry to ~/.ssh/config for $vm_id"
    log_info "  Config: Host $vm_id -> $ssh_user@$ip"
}

# Main
main() {
    log_info "=========================================="
    log_info "Konfiguracja kluczy SSH dla VM01-VM03"
    log_info "=========================================="
    echo ""
    
    # Lista VM do konfiguracji (VM01-VM03)
    VMS=("vm01" "vm02" "vm03")
    
    # Liczniki
    SUCCESS_COUNT=0
    FAILED_COUNT=0
    FAILED_VMS=()
    
    # Iteruj przez wszystkie VM
    for VM_ID in "${VMS[@]}"; do
        log_info "=========================================="
        log_info "Konfiguracja dla: $VM_ID"
        log_info "=========================================="
        
        # Parse configuration
        VM_CONFIG=$(parse_vm_config "$VM_ID" 2>&1) || {
            log_error "Config parse error for $VM_ID"
            ((FAILED_COUNT++))
            FAILED_VMS+=("$VM_ID")
            echo ""
            continue
        }
        
        # Rozdziel informacje (format: IP|USER|PORT)
        IFS='|' read -r IP SSH_USER SSH_PORT <<< "$VM_CONFIG"
        
        log_info "IP: $IP"
        log_info "User: $SSH_USER"
        log_info "Port: $SSH_PORT"
        echo ""
        
        # Generuj klucz SSH
        if ! generate_ssh_key "$VM_ID"; then
            log_error "Could not generate key for $VM_ID"
            ((FAILED_COUNT++))
            FAILED_VMS+=("$VM_ID")
            echo ""
            continue
        fi
        
        # Kopiuj klucz publiczny
        if ! copy_public_key "$VM_ID" "$IP" "$SSH_USER" "$SSH_PORT"; then
            log_error "Could not copy key to $VM_ID"
            ((FAILED_COUNT++))
            FAILED_VMS+=("$VM_ID")
            echo ""
            continue
        fi
        
        # Test connection
        if ! test_ssh_connection "$VM_ID" "$IP" "$SSH_USER" "$SSH_PORT"; then
            log_error "Connection test failed for $VM_ID"
            ((FAILED_COUNT++))
            FAILED_VMS+=("$VM_ID")
            echo ""
            continue
        fi
        
        # Configure SSH server (enforce keys, disable password)
        if ! configure_ssh_server "$VM_ID" "$IP" "$SSH_USER" "$SSH_PORT"; then
            log_warning "Could not configure SSH server for $VM_ID, continuing..."
            # Not critical - may lack sudo on remote
        fi
        
        # Konfiguruj SSH config lokalnie
        configure_ssh_config "$VM_ID" "$IP" "$SSH_USER" "$SSH_PORT" || {
            log_warning "Could not configure SSH config for $VM_ID, continuing..."
        }
        
        log_success "Configuration completed for $VM_ID"
        ((SUCCESS_COUNT++))
        echo ""
    done
    
    # Podsumowanie
    log_info "=========================================="
    log_info "PODSUMOWANIE"
    log_info "=========================================="
    log_success "Sukces: $SUCCESS_COUNT VM"
    if [ $FAILED_COUNT -gt 0 ]; then
        log_error "Failed: $FAILED_COUNT VM"
        log_error "Failed VMs: ${FAILED_VMS[*]}"
        echo ""
        log_info "You can run the script again to retry failed VMs."
        exit 1
    else
        # Ensure all files have correct owner when run with sudo
        if [ -n "${SUDO_USER:-}" ]; then
            log_info "Fixing file ownership..."
            fix_file_ownership "$SSH_DIR"
            fix_file_ownership "$SSH_KEYS_DIR"
            log_success "File ownership corrected"
        fi
        
        log_success "All configurations completed successfully!"
        echo ""
        log_info "=========================================="
        log_info "CONFIGURATION INFO"
        log_info "=========================================="
        log_info "SSH config file created:"
        log_info "  $SSH_DIR/config"
        echo ""
        log_info "You can connect to hosts using:"
        for VM_ID in "${VMS[@]}"; do
            log_info "  ssh $VM_ID"
        done
        echo ""
        log_info "To view or edit config:"
        log_info "  cat $SSH_DIR/config"
        log_info "  nano $SSH_DIR/config"
        exit 0
    fi
}

# Run main
main
