#!/bin/bash
#
# Installation verification script for VM-04: Orchestrator
# Checks correctness of installation of all required tools
#
# Usage: ./health_check.sh [PROJECT_ROOT] [CONFIG_FILE]
# Example: ./health_check.sh $HOME/th_timmy config.yml
#
# If PROJECT_ROOT is not provided, will use $HOME/th_timmy
# If CONFIG_FILE is not provided, will use config.yml

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Set PROJECT_ROOT
# If run as root, use SUDO_USER, otherwise use current user
if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    # Run as root via sudo - use user who ran sudo
    USER_HOME=$(eval echo ~$SUDO_USER)
elif [ "$EUID" -eq 0 ]; then
    # Run as root without sudo - use root
    USER_HOME="$HOME"
else
    # Run as regular user
    USER_HOME="${HOME:-$(eval echo ~$USER)}"
fi

PROJECT_ROOT="${1:-$USER_HOME/th_timmy}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${2:-$SCRIPT_DIR/config.yml}"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
VM04_DIR="$PROJECT_ROOT/hosts/vm04-orchestrator"

# If not in script directory, check in project root
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
fi

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Check function
check() {
    local name="$1"
    local command="$2"
    local expected="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: $name"
    
    if eval "$command" > /dev/null 2>&1; then
        if [ -n "$expected" ]; then
            version=$(eval "$command" 2>/dev/null | head -n1)
            if echo "$version" | grep -qi "$expected"; then
                log_success "$name: $version"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "$name: found '$version', expected containing '$expected'"
                WARNINGS=$((WARNINGS + 1))
            fi
        else
            log_success "$name: installed"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        fi
    else
        log_error "$name: NOT FOUND"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# Function to check Python version
check_python_version() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: Python 3.10+"
    
    if command -v python3 &> /dev/null; then
        version=$(python3 --version 2>&1 | awk '{print $2}')
        major=$(echo $version | cut -d. -f1)
        minor=$(echo $version | cut -d. -f2)
        
        if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then
            log_success "Python: $version (required: 3.10+)"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_error "Python: $version (required: 3.10+)"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        fi
    else
        log_error "Python3: NOT FOUND"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# Function to check Python package in venv
check_python_package() {
    local package="$1"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking Python package: $package"
    
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        if pip show "$package" > /dev/null 2>&1; then
            version=$(pip show "$package" | grep Version | awk '{print $2}')
            log_success "$package: $version"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            deactivate
        else
            log_error "$package: NOT INSTALLED"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            deactivate
        fi
    else
        log_error "Virtual environment does not exist in $PROJECT_ROOT/venv"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# Function to check Docker
check_docker() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: Docker"
    
    if command -v docker &> /dev/null; then
        if systemctl is-active --quiet docker 2>/dev/null; then
            docker_version=$(docker --version 2>&1)
            log_success "Docker: $docker_version (service active)"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        elif systemctl is-enabled --quiet docker 2>/dev/null; then
            docker_version=$(docker --version 2>&1)
            log_warn "Docker: $docker_version (installed, but service is not active)"
            WARNINGS=$((WARNINGS + 1))
        else
            docker_version=$(docker --version 2>&1)
            log_warn "Docker: $docker_version (installed, but service may not be running)"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        log_error "Docker: NOT FOUND"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# Function to check n8n container
check_n8n_container() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: n8n Docker container"
    
    if [ ! -f "$VM04_DIR/docker-compose.yml" ]; then
        log_error "docker-compose.yml not found in $VM04_DIR"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return
    fi
    
    # Get port from config.yml or use default
    if [ -f "$CONFIG_FILE" ]; then
        n8n_port=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('n8n', {}).get('port', 5678))" 2>/dev/null || echo "5678")
    else
        n8n_port="5678"
    fi
    
    # Check if port is listening (most reliable check)
    port_listening=false
    if command -v ss &> /dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ":${n8n_port} "; then
            port_listening=true
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tlnp 2>/dev/null | grep -q ":${n8n_port} "; then
            port_listening=true
        fi
    fi
    
    if [ "$port_listening" = true ]; then
        log_success "n8n container: running (port $n8n_port is listening)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_warn "n8n container: port $n8n_port is not listening"
        log_info "Run: cd $VM04_DIR && docker compose up -d"
        WARNINGS=$((WARNINGS + 1))
    fi
}

echo "=========================================="
echo "  Health Check - VM-04: Orchestrator"
echo "=========================================="
echo "User: $(whoami)"
echo "USER_HOME: $USER_HOME"
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "CONFIG_FILE: $CONFIG_FILE"
echo "VENV_DIR: $PROJECT_ROOT/venv"
echo ""

# ============================================
# 1. Operating System Check
# ============================================
echo "--- Operating System ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Checking: Ubuntu 22.04"
if command -v lsb_release &> /dev/null; then
    release=$(lsb_release -rs 2>/dev/null)
    if [ "$release" = "22.04" ]; then
        codename=$(lsb_release -cs 2>/dev/null)
        log_success "Ubuntu: $release ($codename)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_warn "Ubuntu: $release (expected 22.04)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    log_error "lsb_release: NOT FOUND"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
echo ""

# ============================================
# 2. Basic System Tools Check
# ============================================
echo "--- Basic System Tools ---"
check "git" "git --version" "git version"
check "curl" "curl --version" "curl"
check "wget" "wget --version" "GNU Wget"
check "vim" "vim --version" "VIM"
check "nano" "nano --version" "GNU nano"
echo ""

# ============================================
# 3. Sprawdzenie Docker
# ============================================
echo "--- Docker ---"
check_docker
check "docker-compose" "docker compose version" "Docker Compose"
check "docker-buildx" "docker buildx version" "buildx"
echo ""

# ============================================
# 4. Python Check
# ============================================
echo "--- Python and Environment ---"
check_python_version
check "pip3" "pip3 --version" "pip"
check "python3-venv" "python3 -m venv --help" ""
echo ""

# ============================================
# 5. Virtual Environment Check
# ============================================
echo "--- Virtual Environment ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -d "$PROJECT_ROOT/venv" ]; then
    log_success "Virtual environment exists in $PROJECT_ROOT/venv"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        log_success "activate file exists"
    else
        log_error "activate file does not exist"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
else
    log_error "Virtual environment does not exist in $PROJECT_ROOT/venv"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
echo ""

# ============================================
# 6. Python Packages Check
# ============================================
echo "--- Python Packages ---"

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    log_error "requirements.txt file not found"
    log_error "Searched in: $SCRIPT_DIR/requirements.txt"
    log_error "Searched in: $PROJECT_ROOT/requirements.txt"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
    log_success "requirements.txt file exists: $REQUIREMENTS_FILE"
    
    PACKAGES=(
        "pyyaml"
        "python-dotenv"
        "requests"
        "loguru"
        "docker"
    )
    
    for package in "${PACKAGES[@]}"; do
        package_name=$(echo "$package" | cut -d'>' -f1 | cut -d'=' -f1)
        check_python_package "$package_name"
    done
fi
echo ""

# ============================================
# 7. docker-compose.yml and .env Check
# ============================================
echo "--- n8n Configuration ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -f "$VM04_DIR/docker-compose.yml" ]; then
    log_success "docker-compose.yml exists: $VM04_DIR/docker-compose.yml"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    log_error "docker-compose.yml does not exist: $VM04_DIR/docker-compose.yml"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -f "$VM04_DIR/.env" ]; then
    log_success ".env file exists: $VM04_DIR/.env"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    log_warn ".env file does not exist (may be created automatically)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# ============================================
# 8. n8n Container Check
# ============================================
echo "--- n8n Container ---"
check_n8n_container
echo ""

# ============================================
# 9. Firewall and n8n Port Check
# ============================================
echo "--- Firewall and n8n Port ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Checking: n8n port and firewall"

# Get port from config.yml or use default
if [ -f "$CONFIG_FILE" ]; then
    n8n_port=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('n8n', {}).get('port', 5678))" 2>/dev/null || echo "5678")
else
    n8n_port="5678"
fi

# Check if port is listening
port_listening=false
if command -v ss &> /dev/null; then
    if ss -tlnp 2>/dev/null | grep -q ":${n8n_port} "; then
        port_listening=true
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tlnp 2>/dev/null | grep -q ":${n8n_port} "; then
        port_listening=true
    fi
fi

# Check firewall (ufw)
firewall_open=false
if command -v ufw &> /dev/null; then
    if [ "$EUID" -eq 0 ]; then
        if ufw status 2>/dev/null | grep -qE "${n8n_port}/tcp|${n8n_port}\s+ALLOW"; then
            firewall_open=true
        fi
    else
        if sudo ufw status 2>/dev/null | grep -qE "${n8n_port}/tcp|${n8n_port}\s+ALLOW"; then
            firewall_open=true
        fi
    fi
fi

# Evaluate results
if [ "$port_listening" = true ]; then
    if [ "$firewall_open" = true ]; then
        log_success "Port $n8n_port/tcp is listening and open in firewall (ufw)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif command -v ufw &> /dev/null; then
        ufw_status=$(sudo ufw status 2>/dev/null | head -n1 || echo "")
        if echo "$ufw_status" | grep -qi "inactive\|disabled"; then
            log_success "Port $n8n_port/tcp is listening (ufw is disabled - port accessible)"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_warn "Port $n8n_port/tcp is listening, but may not be open in firewall (ufw active)"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        log_success "Port $n8n_port/tcp is listening (ufw not installed)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
else
    log_info "Port $n8n_port/tcp is not listening (n8n may not be running - this is OK)"
    log_info "To start n8n: cd $VM04_DIR && docker compose up -d"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi
echo ""

# ============================================
# 10. Connection Tests (Optional)
# ============================================
# These tests are optional - only run if configs/config.yml exists
if [ -f "$PROJECT_ROOT/configs/config.yml" ]; then
    echo "=========================================="
    echo "  Connection Tests (Optional)"
    echo "=========================================="
    
    # Function to test JupyterLab connection from VM-04 to VM-03
    test_jupyter_connection_from_vm04() {
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Testing connection to JupyterLab on VM-03"
        
        # Extract VM-03 IP from config.yml
        local vm03_ip=""
        if command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
            vm03_ip=$(python3 -c "import yaml; f=open('$PROJECT_ROOT/configs/config.yml'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm03', {}).get('ip', ''))" 2>/dev/null || echo "")
        fi
        
        # Fallback to grep if Python parsing failed
        if [ -z "$vm03_ip" ]; then
            vm03_ip=$(grep -E "vm03:" "$PROJECT_ROOT/configs/config.yml" -A 3 | grep -E "ip:" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
        fi
        
        if [ -z "$vm03_ip" ]; then
            log_warn "Could not extract VM-03 IP from config.yml"
            WARNINGS=$((WARNINGS + 1))
            return 1
        fi
        
        log_info "VM-03 IP: $vm03_ip"
        
        # Get JupyterLab port from config.yml or use default
        local jupyter_port="8888"
        if command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
            jupyter_port=$(python3 -c "import yaml; f=open('$PROJECT_ROOT/configs/config.yml'); d=yaml.safe_load(f); print(d.get('services', {}).get('jupyter', {}).get('port', 8888))" 2>/dev/null || echo "8888")
        fi
        
        # Test 1: Ping to VM-03
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Testing ping to VM-03 ($vm03_ip)"
        if ping -c 2 -W 2 "$vm03_ip" &> /dev/null; then
            log_success "Ping to VM-03: OK"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_error "Ping to VM-03: FAILED"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            return 1
        fi
        
        # Test 2: Port connectivity (JupyterLab port 8888)
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Testing JupyterLab port ($jupyter_port) on VM-03"
        if command -v nc &> /dev/null; then
            if nc -z -w 2 "$vm03_ip" "$jupyter_port" 2>/dev/null; then
                log_success "JupyterLab port ($jupyter_port) on VM-03: accessible"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "JupyterLab port ($jupyter_port) on VM-03: not accessible (JupyterLab may not be running)"
                WARNINGS=$((WARNINGS + 1))
            fi
        elif command -v timeout &> /dev/null && command -v bash &> /dev/null; then
            # Fallback: use bash with /dev/tcp
            if timeout 2 bash -c "echo > /dev/tcp/$vm03_ip/$jupyter_port" 2>/dev/null; then
                log_success "JupyterLab port ($jupyter_port) on VM-03: accessible"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "JupyterLab port ($jupyter_port) on VM-03: not accessible (JupyterLab may not be running)"
                WARNINGS=$((WARNINGS + 1))
            fi
        else
            log_warn "Port test tools not available (nc or bash with /dev/tcp)"
            WARNINGS=$((WARNINGS + 1))
        fi
        
        # Test 3: HTTP connectivity (if curl is available)
        if command -v curl &> /dev/null; then
            TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
            log_info "Testing HTTP connectivity to JupyterLab"
            http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "http://$vm03_ip:$jupyter_port" 2>/dev/null || echo "000")
            if echo "$http_code" | grep -qE "200|301|302|401|403"; then
                log_success "HTTP connection to JupyterLab: OK (HTTP $http_code)"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "HTTP connection to JupyterLab: failed (HTTP $http_code) - JupyterLab may not be running or not responding"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
        
        echo ""
    }
    
    # Run the test
    test_jupyter_connection_from_vm04
else
    log_info "Skipping connection tests (config.yml not found at $PROJECT_ROOT/configs/config.yml)"
    log_info "Connection tests are optional and require config.yml with VM IPs"
    echo ""
fi

# ============================================
# 11. Locale Check
# ============================================
echo "--- Locale Configuration ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Checking: Locale en_US.UTF-8"

if locale -a 2>/dev/null | grep -qi "en_US.utf8"; then
    current_lang="${LANG:-$(locale 2>/dev/null | grep "^LANG=" | cut -d= -f2 | tr -d '"')}"
    current_lc_all="${LC_ALL:-$(locale 2>/dev/null | grep "^LC_ALL=" | cut -d= -f2 | tr -d '"')}"
    
    if [ -z "$current_lang" ]; then
        current_lang=$(locale 2>/dev/null | grep "^LANG=" | cut -d= -f2 | tr -d '"')
    fi
    
    if echo "$current_lang" | grep -qi "en_US.UTF-8\|en_US.utf8" || \
       echo "$current_lc_all" | grep -qi "en_US.UTF-8\|en_US.utf8"; then
        log_success "Locale configured: LANG=$current_lang"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_success "Locale en_US.UTF-8 available (LANG=$current_lang)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
else
    log_warn "Locale en_US.UTF-8 is not available (may require: sudo locale-gen en_US.UTF-8)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# ============================================
# 12. Summary
# ============================================
echo "=========================================="
echo "  Summary"
echo "=========================================="
echo "Total checks: $TOTAL_CHECKS"
echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed successfully!${NC}"
    else
        echo -e "${GREEN}✓ All critical checks passed successfully!${NC}"
        echo -e "${YELLOW}⚠ There are warnings - check logs above.${NC}"
    fi
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Check logs above.${NC}"
    exit 1
fi

