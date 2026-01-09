#!/bin/bash
#
# Installation verification script for VM-02: Database
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
            log_success "Python: $version (wymagane: 3.10+)"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_error "Python: $version (wymagane: 3.10+)"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        fi
    else
        log_error "Python3: NIE ZNALEZIONO"
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

# Function to check PostgreSQL
check_postgresql() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: PostgreSQL"
    
    if systemctl is-active --quiet postgresql; then
        pg_version=$(sudo -u postgres psql --version 2>/dev/null | awk '{print $3}')
        log_success "PostgreSQL: $pg_version (service active)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif systemctl is-enabled --quiet postgresql 2>/dev/null; then
        log_warn "PostgreSQL: installed, but service is not active"
        WARNINGS=$((WARNINGS + 1))
    else
        log_error "PostgreSQL: NOT FOUND or service not running"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# Function to check database
check_database() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: Database and user"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file does not exist: $CONFIG_FILE"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return
    fi
    
    # Parse config.yml
    db_name=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d['postgresql']['database_name'])" 2>/dev/null || echo "")
    db_user=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d['postgresql']['database_user'])" 2>/dev/null || echo "")
    
    if [ -z "$db_name" ] || [ -z "$db_user" ]; then
        log_error "Cannot read database configuration from $CONFIG_FILE"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return
    fi
    
    # Check if database exists
    if sudo -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$db_name"; then
        # Check if user exists
        if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$db_user'" 2>/dev/null | grep -q 1; then
            log_success "Database '$db_name' and user '$db_user' exist"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_error "User '$db_user' does not exist"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        fi
    else
        log_error "Database '$db_name' does not exist"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

echo "=========================================="
echo "  Health Check - VM-02: Database"
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
# 3. PostgreSQL Check
# ============================================
echo "--- PostgreSQL ---"
check_postgresql
check "postgresql-client" "psql --version" "psql"
check "libpq-dev" "dpkg -l | grep -q 'libpq-dev'" ""
echo ""

# ============================================
# 4. Backup Tools Check
# ============================================
echo "--- Backup Tools ---"
check "cron" "systemctl is-active --quiet cron" ""
check "rsync" "rsync --version" "rsync"
echo ""

# ============================================
# 5. Python Check
# ============================================
echo "--- Python and Environment ---"
check_python_version
check "pip3" "pip3 --version" "pip"
check "python3-venv" "python3 -m venv --help" ""
echo ""

# ============================================
# 6. Virtual Environment Check
# ============================================
echo "--- Virtual Environment ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -d "$PROJECT_ROOT/venv" ]; then
    log_success "Virtual environment istnieje w $PROJECT_ROOT/venv"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        log_success "Plik activate istnieje"
    else
        log_error "Plik activate nie istnieje"
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
echo "--- Pakiety Python ---"

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    log_error "Nie znaleziono pliku requirements.txt"
    log_error "Szukano w: $SCRIPT_DIR/requirements.txt"
    log_error "Szukano w: $PROJECT_ROOT/requirements.txt"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
    log_success "Plik requirements.txt istnieje: $REQUIREMENTS_FILE"
    
    PACKAGES=(
        "psycopg2-binary"
        "sqlalchemy"
        "pyyaml"
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
# 8. Database Check
# ============================================
echo "--- Baza Danych ---"
check_database
echo ""

# ============================================
# 9. PostgreSQL Configuration Check
# ============================================
echo "--- PostgreSQL Configuration ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Checking: PostgreSQL configuration"

# First check directories in /etc/postgresql (most reliable)
pg_version=$(ls -d /etc/postgresql/*/main 2>/dev/null | head -1 | cut -d/ -f4)

# If not found, try via psql
if [ -z "$pg_version" ]; then
    pg_version_full=$(sudo -u postgres psql --version 2>/dev/null | awk '{print $3}')
    if [ -n "$pg_version_full" ]; then
        # Extract only major version (14 from 14.20)
        pg_version=$(echo "$pg_version_full" | cut -d. -f1,2 | cut -d. -f1)
    fi
fi

if [ -n "$pg_version" ]; then
    pg_conf="/etc/postgresql/$pg_version/main/postgresql.conf"
    if [ -f "$pg_conf" ]; then
        listen_addr=$(grep "^listen_addresses" "$pg_conf" 2>/dev/null | cut -d= -f2 | tr -d " '")
        if [ -n "$listen_addr" ] && [ "$listen_addr" != "localhost" ]; then
            log_success "PostgreSQL is listening on: $listen_addr"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_warn "PostgreSQL may only listen on localhost"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        log_warn "PostgreSQL configuration file not found: $pg_conf"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    log_warn "Cannot determine PostgreSQL version"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# ============================================
# 10. Firewall and Port Check
# ============================================
echo "--- Firewall i Port PostgreSQL ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Checking: PostgreSQL port and firewall"

# Get port from config.yml
pg_port=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d['postgresql'].get('port', 5432))" 2>/dev/null || echo "5432")

# First check if port is listening (most reliable)
port_listening=false
if command -v ss &> /dev/null; then
    # Use ss (modern tool)
    if ss -tlnp 2>/dev/null | grep -q ":${pg_port} "; then
        port_listening=true
    fi
elif command -v netstat &> /dev/null; then
    # Fallback to netstat
    if netstat -tlnp 2>/dev/null | grep -q ":${pg_port} "; then
        port_listening=true
    fi
fi

# Check firewall (ufw)
firewall_open=false
if command -v ufw &> /dev/null; then
    # Check ufw status - use sudo if needed
    if [ "$EUID" -eq 0 ]; then
        if ufw status 2>/dev/null | grep -qE "${pg_port}/tcp|${pg_port}\s+ALLOW"; then
            firewall_open=true
        fi
    else
        # Try with sudo
        if sudo ufw status 2>/dev/null | grep -qE "${pg_port}/tcp|${pg_port}\s+ALLOW"; then
            firewall_open=true
        fi
    fi
fi

# Evaluate results
if [ "$port_listening" = true ]; then
    if [ "$firewall_open" = true ]; then
        log_success "Port $pg_port/tcp is listening and open in firewall (ufw)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif command -v ufw &> /dev/null; then
        # Port is listening, but ufw may not be configured or disabled
        ufw_status=$(sudo ufw status 2>/dev/null | head -n1 || echo "")
        if echo "$ufw_status" | grep -qi "inactive\|disabled"; then
            log_success "Port $pg_port/tcp is listening (ufw is disabled - port accessible)"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_warn "Port $pg_port/tcp is listening, but may not be open in firewall (ufw active)"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        # Port is listening, ufw not installed - assume firewall is not blocking
        log_success "Port $pg_port/tcp is listening (ufw not installed)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
else
    log_error "Port $pg_port/tcp is not listening!"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
echo ""

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
# 12. Data Retention Configuration Check
# ============================================
if [ -f "$CONFIG_FILE" ]; then
    echo "=========================================="
    echo "  Data Retention Configuration"
    echo "=========================================="
    
    # Check retention configuration
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: Data retention configuration"
    
    # Parse retention config
    RETENTION_DAYS=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('retention', {}).get('retention_days', 0))" 2>/dev/null || echo "0")
    AUTO_CLEANUP=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('retention', {}).get('auto_cleanup', False))" 2>/dev/null || echo "False")
    
    if [ "$RETENTION_DAYS" -gt 0 ]; then
        if [ "$RETENTION_DAYS" -eq 90 ]; then
            log_success "Data retention configured: $RETENTION_DAYS days (production-ready)"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_warn "Data retention configured: $RETENTION_DAYS days (expected 90 days)"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        log_warn "Data retention not configured in config.yml"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    # Check if cleanup function exists
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: cleanup_old_data() function"
    
    # Get database name and user from config
    DB_NAME=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('postgresql', {}).get('database_name', 'threat_hunting'))" 2>/dev/null || echo "threat_hunting")
    
    if sudo -u postgres psql -d "$DB_NAME" -tAc "SELECT 1 FROM pg_proc WHERE proname='cleanup_old_data'" 2>/dev/null | grep -q 1; then
        log_success "cleanup_old_data() function exists"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_warn "cleanup_old_data() function not found (may need to run install_vm02.sh)"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    # Check if cleanup_log table exists
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Checking: cleanup_log table"
    
    if sudo -u postgres psql -d "$DB_NAME" -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='cleanup_log'" 2>/dev/null | grep -q 1; then
        log_success "cleanup_log table exists"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_warn "cleanup_log table not found (will be created on first cleanup run)"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    # Check if automatic cleanup is configured (pg_cron or system cron)
    if [ "$AUTO_CLEANUP" = "True" ] || [ "$AUTO_CLEANUP" = "true" ]; then
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        log_info "Checking: Automatic cleanup scheduling"
        
        # Check pg_cron
        PG_CRON_EXISTS=false
        if sudo -u postgres psql -d "$DB_NAME" -tAc "SELECT 1 FROM pg_extension WHERE extname='pg_cron'" 2>/dev/null | grep -q 1; then
            if sudo -u postgres psql -d "$DB_NAME" -tAc "SELECT 1 FROM cron.job WHERE jobname='cleanup-old-data'" 2>/dev/null | grep -q 1; then
                log_success "Automatic cleanup scheduled via pg_cron"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
                PG_CRON_EXISTS=true
            fi
        fi
        
        # Check system cron if pg_cron not found
        if [ "$PG_CRON_EXISTS" = "false" ]; then
            if crontab -l 2>/dev/null | grep -q "cleanup_postgres_data.sh"; then
                log_success "Automatic cleanup scheduled via system cron"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
            else
                log_warn "Automatic cleanup enabled but no cron job found"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
    else
        log_info "Automatic cleanup is disabled (set auto_cleanup: true to enable)"
    fi
    
    echo ""
else
    log_info "Skipping retention checks (config.yml not found)"
    echo ""
fi

# ============================================
# 13. Summary
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

