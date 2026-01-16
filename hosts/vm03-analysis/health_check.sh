#!/bin/bash
#
# Installation verification script for VM-03: Analysis/Jupyter
# Checks correctness of installation of all required tools
#
# Usage: ./health_check.sh [PROJECT_ROOT] [CONFIG_FILE]
# Example: ./health_check.sh $HOME/th_timmy config.yml
#
# If PROJECT_ROOT is not provided, will use $HOME/th_timmy
# If CONFIG_FILE is not provided, will use config.yml (optional)

set -e

# Kolory dla outputu
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funkcje logowania
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

# Function to check JupyterLab
check_jupyter() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: JupyterLab"
    
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        if command -v jupyter &> /dev/null; then
            jupyter_version=$(jupyter --version 2>/dev/null | head -n1)
            log_success "Jupyter: $jupyter_version"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            deactivate
        else
            log_error "Jupyter: NOT INSTALLED"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            deactivate
        fi
    else
        log_error "Virtual environment does not exist in $PROJECT_ROOT/venv"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

echo "=========================================="
echo "  Health Check - VM-03: Analysis/Jupyter"
echo "=========================================="
echo "User: $(whoami)"
echo "USER_HOME: $USER_HOME"
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "CONFIG_FILE: $CONFIG_FILE"
echo "VENV_DIR: $PROJECT_ROOT/venv"
echo ""

# ============================================
# 1. Sprawdzenie systemu operacyjnego
# ============================================
echo "--- System Operacyjny ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Sprawdzam: Ubuntu 22.04"
if command -v lsb_release &> /dev/null; then
    release=$(lsb_release -rs 2>/dev/null)
    if [ "$release" = "22.04" ]; then
        codename=$(lsb_release -cs 2>/dev/null)
        log_success "Ubuntu: $release ($codename)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_warn "Ubuntu: $release (oczekiwano 22.04)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    log_error "lsb_release: NIE ZNALEZIONO"
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
# 3. Sprawdzenie Node.js
# ============================================
echo "--- Node.js ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Sprawdzam: Node.js 18+"
if command -v node &> /dev/null; then
    node_version=$(node --version 2>&1 | cut -d'v' -f2)
    node_major=$(echo $node_version | cut -d. -f1)
    if [ "$node_major" -ge 18 ]; then
        npm_version=$(npm --version 2>&1)
        log_success "Node.js: $node_version, npm: $npm_version"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_warn "Node.js: $node_version (zalecane: 18+)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    log_warn "Node.js: NOT FOUND (some JupyterLab extensions may not work)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# ============================================
# 4. Sprawdzenie Python
# ============================================
echo "--- Python and Environment ---"
check_python_version
check "pip3" "pip3 --version" "pip"
check "python3-venv" "python3 -m venv --help" ""
check "python3-tk" "python3 -c 'import tkinter' 2>&1" ""
echo ""

# ============================================
# 5. Sprawdzenie bibliotek systemowych
# ============================================
echo "--- Biblioteki Systemowe ---"
check "libpq-dev" "dpkg -l | grep -q 'libpq-dev'" ""
check "libssl-dev" "dpkg -l | grep -q 'libssl-dev'" ""
check "libffi-dev" "dpkg -l | grep -q 'libffi-dev'" ""
check "libjpeg-dev" "dpkg -l | grep -q 'libjpeg-dev'" ""
check "libpng-dev" "dpkg -l | grep -q 'libpng-dev'" ""
check "libfreetype6-dev" "dpkg -l | grep -q 'libfreetype6-dev'" ""
check "pkg-config" "pkg-config --version" ""
echo ""

# ============================================
# 6. Virtual Environment Check
# ============================================
echo "--- Virtual Environment ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -d "$PROJECT_ROOT/venv" ]; then
    log_success "Virtual environment exists at $PROJECT_ROOT/venv"
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
# 7. Python Packages Check
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
        "pandas"
        "numpy"
        "pyarrow"
        "psycopg2-binary"
        "sqlalchemy"
        "jupyterlab"
        "notebook"
        "ipykernel"
        "ipywidgets"
        "jupyterlab-widgets"
        "scikit-learn"
        "matplotlib"
        "seaborn"
        "openai"
        "pyyaml"
        "python-dateutil"
        "requests"
        "python-dotenv"
        "loguru"
    )
    
    for package in "${PACKAGES[@]}"; do
        package_name=$(echo "$package" | cut -d'>' -f1 | cut -d'=' -f1)
        check_python_package "$package_name"
    done
fi
echo ""

# ============================================
# 8. Sprawdzenie JupyterLab
# ============================================
echo "--- JupyterLab ---"
check_jupyter

# Sprawdzenie konfiguracji JupyterLab
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
JUPYTER_CONFIG="$USER_HOME/.jupyter/jupyter_lab_config.py"
if [ -f "$JUPYTER_CONFIG" ]; then
    log_success "JupyterLab configuration exists: $JUPYTER_CONFIG"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    log_warn "JupyterLab configuration does not exist (can generate: jupyter lab --generate-config)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# ============================================
# 9. Sprawdzenie JupyterLab Service (opcjonalnie)
# ============================================
echo "--- JupyterLab Service ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if systemctl list-unit-files | grep -q "jupyter.service"; then
    if systemctl is-active --quiet jupyter 2>/dev/null; then
        log_success "JupyterLab service jest aktywny"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif systemctl is-enabled --quiet jupyter 2>/dev/null; then
        log_warn "JupyterLab service is enabled, but not active"
        WARNINGS=$((WARNINGS + 1))
    else
        log_warn "JupyterLab service exists, but is not enabled"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    log_info "JupyterLab service is not configured (optional)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi
echo ""

# ============================================
# 10. Sprawdzenie firewall i portu JupyterLab
# ============================================
echo "--- Firewall i Port JupyterLab ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Checking: JupyterLab port and firewall"

# Get port from config.yml or use default
if [ -f "$CONFIG_FILE" ]; then
    jupyter_port=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('jupyter', {}).get('port', 8888))" 2>/dev/null || echo "8888")
else
    jupyter_port="8888"
fi

# Check if port is listening
port_listening=false
if command -v ss &> /dev/null; then
    if ss -tlnp 2>/dev/null | grep -q ":${jupyter_port} "; then
        port_listening=true
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tlnp 2>/dev/null | grep -q ":${jupyter_port} "; then
        port_listening=true
    fi
fi

# Check firewall (ufw)
firewall_open=false
if command -v ufw &> /dev/null; then
    if [ "$EUID" -eq 0 ]; then
        if ufw status 2>/dev/null | grep -qE "${jupyter_port}/tcp|${jupyter_port}\s+ALLOW"; then
            firewall_open=true
        fi
    else
        if sudo ufw status 2>/dev/null | grep -qE "${jupyter_port}/tcp|${jupyter_port}\s+ALLOW"; then
            firewall_open=true
        fi
    fi
fi

# Evaluate results
if [ "$port_listening" = true ]; then
    if [ "$firewall_open" = true ]; then
        log_success "Port $jupyter_port/tcp is listening and open in firewall (ufw)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif command -v ufw &> /dev/null; then
        ufw_status=$(sudo ufw status 2>/dev/null | head -n1 || echo "")
        if echo "$ufw_status" | grep -qi "inactive\|disabled"; then
            log_success "Port $jupyter_port/tcp is listening (ufw is disabled - port accessible)"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_warn "Port $jupyter_port/tcp is listening, but may not be open in firewall (ufw active)"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        log_success "Port $jupyter_port/tcp is listening (ufw not installed)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
else
    log_info "Port $jupyter_port/tcp is not listening (JupyterLab is not running - this is OK)"
    log_info "To start JupyterLab: source venv/bin/activate && jupyter lab"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi
echo ""

# ============================================
# 11. Connection Tests (Optional)
# ============================================
# These tests are optional - only run if configs/config.yml exists
if [ -f "$PROJECT_ROOT/configs/config.yml" ]; then
    echo "=========================================="
    echo "  Connection Tests (Optional)"
    echo "=========================================="
    
    # Function to test database connection from VM-03 to VM-02
    test_db_connection_from_vm03() {
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Testing connection to PostgreSQL on VM-02"
        
        # Extract VM-02 IP from config.yml
        local vm02_ip=""
        if command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
            vm02_ip=$(python3 -c "import yaml; f=open('$PROJECT_ROOT/configs/config.yml'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm02', {}).get('ip', ''))" 2>/dev/null || echo "")
        fi
        
        # Fallback to grep if Python parsing failed
        if [ -z "$vm02_ip" ]; then
            vm02_ip=$(grep -E "vm02:" "$PROJECT_ROOT/configs/config.yml" -A 3 | grep -E "ip:" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
        fi
        
        if [ -z "$vm02_ip" ]; then
            log_warn "Could not extract VM-02 IP from config.yml"
            WARNINGS=$((WARNINGS + 1))
            return 1
        fi
        
        log_info "VM-02 IP: $vm02_ip"
        
        # Test 1: Ping to VM-02
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Testing ping to VM-02 ($vm02_ip)"
        if ping -c 2 -W 2 "$vm02_ip" &> /dev/null; then
            log_success "Ping to VM-02: OK"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_error "Ping to VM-02: FAILED"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            return 1
        fi
        
        # Test 2: Port connectivity (PostgreSQL port 5432)
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Testing PostgreSQL port (5432) on VM-02"
        if command -v nc &> /dev/null; then
            if nc -z -w 2 "$vm02_ip" 5432 2>/dev/null; then
                log_success "PostgreSQL port (5432) on VM-02: accessible"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "PostgreSQL port (5432) on VM-02: not accessible (PostgreSQL may not be running)"
                WARNINGS=$((WARNINGS + 1))
            fi
        elif command -v timeout &> /dev/null && command -v bash &> /dev/null; then
            # Fallback: use bash with /dev/tcp
            if timeout 2 bash -c "echo > /dev/tcp/$vm02_ip/5432" 2>/dev/null; then
                log_success "PostgreSQL port (5432) on VM-02: accessible"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "PostgreSQL port (5432) on VM-02: not accessible (PostgreSQL may not be running)"
                WARNINGS=$((WARNINGS + 1))
            fi
        else
            log_warn "Port test tools not available (nc or bash with /dev/tcp)"
            WARNINGS=$((WARNINGS + 1))
        fi
        
        # Test 3: Database authentication (if psycopg2 is available and password is set)
        if [ -n "${POSTGRES_PASSWORD:-}" ] && [ -d "$PROJECT_ROOT/venv" ]; then
            TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
            log_info "Testing database authentication"
            
            # Activate virtual environment
            source "$PROJECT_ROOT/venv/bin/activate" 2>/dev/null || true
            
            # Check if psycopg2 is available
            if python3 -c "import psycopg2" 2>/dev/null || python3 -c "import psycopg2_binary" 2>/dev/null; then
                # Extract database config
                local db_host="$vm02_ip"
                local db_port="5432"
                local db_name="threat_hunting"
                local db_user="threat_hunter"
                
                if command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
                    db_host=$(python3 -c "import yaml; f=open('$PROJECT_ROOT/configs/config.yml'); d=yaml.safe_load(f); h=d.get('database', {}).get('host', ''); print(d.get('vms', {}).get('vm02', {}).get('ip', '') if h == 'vm02' else h or '$vm02_ip')" 2>/dev/null || echo "$vm02_ip")
                    db_port=$(python3 -c "import yaml; f=open('$PROJECT_ROOT/configs/config.yml'); d=yaml.safe_load(f); print(d.get('database', {}).get('port', 5432))" 2>/dev/null || echo "5432")
                    db_name=$(python3 -c "import yaml; f=open('$PROJECT_ROOT/configs/config.yml'); d=yaml.safe_load(f); print(d.get('database', {}).get('name', 'threat_hunting'))" 2>/dev/null || echo "threat_hunting")
                    db_user=$(python3 -c "import yaml; f=open('$PROJECT_ROOT/configs/config.yml'); d=yaml.safe_load(f); print(d.get('database', {}).get('user', 'threat_hunter'))" 2>/dev/null || echo "threat_hunter")
                fi
                
                # Try connection
                if python3 << PYTHON_EOF
import psycopg2
import os
import sys

try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', '$db_host'),
        port=int(os.environ.get('DB_PORT', $db_port)),
        database=os.environ.get('DB_NAME', '$db_name'),
        user=os.environ.get('DB_USER', '$db_user'),
        password=os.environ.get('DB_PASSWORD', os.environ.get('POSTGRES_PASSWORD', '')),
        connect_timeout=5
    )
    conn.close()
    sys.exit(0)
except psycopg2.OperationalError as e:
    if 'password' in str(e).lower() or 'authentication' in str(e).lower():
        # Port is accessible, authentication issue
        sys.exit(2)
    sys.exit(1)
except Exception as e:
    sys.exit(1)
PYTHON_EOF
                then
                    log_success "Database authentication: OK"
                    PASSED_CHECKS=$((PASSED_CHECKS + 1))
                else
                    local exit_code=$?
                    if [ $exit_code -eq 2 ]; then
                        log_warn "Database port accessible but authentication failed (check POSTGRES_PASSWORD)"
                        WARNINGS=$((WARNINGS + 1))
                    else
                        log_warn "Database connection failed (PostgreSQL may not be running or configured)"
                        WARNINGS=$((WARNINGS + 1))
                    fi
                fi
                
                deactivate 2>/dev/null || true
            else
                log_warn "psycopg2 not available, skipping database authentication test"
                WARNINGS=$((WARNINGS + 1))
            fi
        else
            log_info "Skipping database authentication test (POSTGRES_PASSWORD not set or venv not found)"
        fi
        
        echo ""
    }
    
    # Function to test n8n connection from VM-03 to VM-04
    test_n8n_connection_from_vm03() {
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Testing connection to n8n on VM-04"
        
        # Extract VM-04 IP from config.yml
        local vm04_ip=""
        if command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
            vm04_ip=$(python3 -c "import yaml; f=open('$PROJECT_ROOT/configs/config.yml'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm04', {}).get('ip', ''))" 2>/dev/null || echo "")
        fi
        
        # Fallback to grep if Python parsing failed
        if [ -z "$vm04_ip" ]; then
            vm04_ip=$(grep -E "vm04:" "$PROJECT_ROOT/configs/config.yml" -A 3 | grep -E "ip:" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
        fi
        
        if [ -z "$vm04_ip" ]; then
            log_warn "Could not extract VM-04 IP from config.yml"
            WARNINGS=$((WARNINGS + 1))
            return 1
        fi
        
        log_info "VM-04 IP: $vm04_ip"
        
        # Test 1: Ping to VM-04
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Testing ping to VM-04 ($vm04_ip)"
        if ping -c 2 -W 2 "$vm04_ip" &> /dev/null; then
            log_success "Ping to VM-04: OK"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_error "Ping to VM-04: FAILED"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            return 1
        fi
        
        # Test 2: Port connectivity (n8n port 5678)
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Testing n8n port (5678) on VM-04"
        if command -v nc &> /dev/null; then
            if nc -z -w 2 "$vm04_ip" 5678 2>/dev/null; then
                log_success "n8n port (5678) on VM-04: accessible"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "n8n port (5678) on VM-04: not accessible (n8n may not be running)"
                WARNINGS=$((WARNINGS + 1))
            fi
        elif command -v timeout &> /dev/null && command -v bash &> /dev/null; then
            # Fallback: use bash with /dev/tcp
            if timeout 2 bash -c "echo > /dev/tcp/$vm04_ip/5678" 2>/dev/null; then
                log_success "n8n port (5678) on VM-04: accessible"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "n8n port (5678) on VM-04: not accessible (n8n may not be running)"
                WARNINGS=$((WARNINGS + 1))
            fi
        else
            log_warn "Port test tools not available (nc or bash with /dev/tcp)"
            WARNINGS=$((WARNINGS + 1))
        fi
        
        # Test 3: HTTP connectivity (if curl is available)
        if command -v curl &> /dev/null; then
            TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
            log_info "Testing HTTP connectivity to n8n"
            if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "http://$vm04_ip:5678" 2>/dev/null | grep -qE "200|301|302|401|403"; then
                log_success "HTTP connection to n8n: OK"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "HTTP connection to n8n: failed (n8n may not be running or not responding)"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
        
        echo ""
    }
    
    # Run the tests
    test_db_connection_from_vm03
    test_n8n_connection_from_vm03
else
    log_info "Skipping connection tests (config.yml not found at $PROJECT_ROOT/configs/config.yml)"
    log_info "Connection tests are optional and require config.yml with VM IPs"
    echo ""
fi

# ============================================
# 12. Sprawdzenie locale
# ============================================
echo "--- Konfiguracja Locale ---"
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
# 13. Podsumowanie
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

