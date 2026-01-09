#!/bin/bash
#
# Installation verification script for VM-01: Ingest/Parser
# Checks correctness of installation of all required tools
#
# Usage: ./health_check.sh [PROJECT_ROOT]
# Example: ./health_check.sh $HOME/th_timmy
#
# If PROJECT_ROOT is not provided, will use $HOME/th_timmy

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
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

# If not in script directory, check in main project directory
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
            local version=$(eval "$command" 2>/dev/null | head -n1)
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
        local version=$(python3 --version 2>&1 | awk '{print $2}')
        local major=$(echo $version | cut -d. -f1)
        local minor=$(echo $version | cut -d. -f2)
        
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
            local version=$(pip show "$package" | grep Version | awk '{print $2}')
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

echo "=========================================="
echo "  Health Check - VM-01: Ingest/Parser"
echo "=========================================="
echo "Użytkownik: $(whoami)"
echo "USER_HOME: $USER_HOME"
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "VENV_DIR: $PROJECT_ROOT/venv"
echo ""

# ============================================
# 1. Operating system check
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
        log_warn "Ubuntu: $release (oczekiwano 22.04)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    log_error "lsb_release: NOT FOUND"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
echo ""

# ============================================
# 2. Basic system tools check
# ============================================
echo "--- Basic System Tools ---"
check "git" "git --version" "git version"
check "curl" "curl --version" "curl"
check "wget" "wget --version" "GNU Wget"
check "vim" "vim --version" "VIM"
check "nano" "nano --version" "GNU nano"
check "file" "file --version" "file"
check "unzip" "unzip -v" "UnZip"

# Check zip - use different method
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Checking: zip"
if command -v zip &> /dev/null; then
    # zip -v returns license information, check if command works
    if zip -v > /dev/null 2>&1; then
        zip_version=$(zip -v 2>&1 | head -n1)
        log_success "zip: installed ($zip_version)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        log_success "zip: installed"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
else
    log_error "zip: NOT FOUND"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
echo ""

# ============================================
# 3. Python check
# ============================================
echo "--- Python and Environment ---"
check_python_version
check "pip3" "pip3 --version" "pip"
check "python3-venv" "python3 -m venv --help" ""
echo ""

# ============================================
# 4. System libraries check
# ============================================
echo "--- System Libraries ---"
check "libpq-dev" "dpkg -l | grep -q 'libpq-dev'" ""
check "libssl-dev" "dpkg -l | grep -q 'libssl-dev'" ""
check "libffi-dev" "dpkg -l | grep -q 'libffi-dev'" ""
check "libxml2-dev" "dpkg -l | grep -q 'libxml2-dev'" ""
check "libxslt1-dev" "dpkg -l | grep -q 'libxslt1-dev'" ""
echo ""

# ============================================
# 5. Build tools check
# ============================================
echo "--- Build Tools ---"
check "gcc" "gcc --version" "gcc"
check "g++" "g++ --version" "g++"
check "make" "make --version" "GNU Make"
echo ""

# ============================================
# 6. Virtual environment check
# ============================================
echo "--- Virtual Environment ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -d "$PROJECT_ROOT/venv" ]; then
    log_success "Virtual environment exists in $PROJECT_ROOT/venv"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    # Check if can be activated
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
# 7. Python packages check
# ============================================
echo "--- Python Packages ---"

# Check if requirements.txt exists
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    log_error "requirements.txt file not found"
    log_error "Searched in: $SCRIPT_DIR/requirements.txt"
    log_error "Searched in: $PROJECT_ROOT/requirements.txt"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
    log_success "requirements.txt file exists: $REQUIREMENTS_FILE"
    
    # Lista pakietów do sprawdzenia
    PACKAGES=(
        "pandas"
        "numpy"
        "pyarrow"
        "psycopg2-binary"
        "sqlalchemy"
        "pyyaml"
        "python-dateutil"
        "requests"
        "cryptography"
        "python-dotenv"
        "loguru"
    )
    
    for package in "${PACKAGES[@]}"; do
        # Usuń wersję z nazwy pakietu dla sprawdzenia
        package_name=$(echo "$package" | cut -d'>' -f1 | cut -d'=' -f1)
        check_python_package "$package_name"
    done
fi
echo ""

# ============================================
# 8. Locale check
# ============================================
echo "--- Locale Configuration ---"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
log_info "Checking: Locale en_US.UTF-8"

# Check if locale is available
if locale -a 2>/dev/null | grep -qi "en_US.utf8"; then
    # Check if it's set as default
    current_lang="${LANG:-$(locale 2>/dev/null | grep "^LANG=" | cut -d= -f2 | tr -d '"')}"
    current_lc_all="${LC_ALL:-$(locale 2>/dev/null | grep "^LC_ALL=" | cut -d= -f2 | tr -d '"')}"
    
    # If environment variables are not set, check in locale
    if [ -z "$current_lang" ]; then
        current_lang=$(locale 2>/dev/null | grep "^LANG=" | cut -d= -f2 | tr -d '"')
    fi
    
    if echo "$current_lang" | grep -qi "en_US.UTF-8\|en_US.utf8" || \
       echo "$current_lc_all" | grep -qi "en_US.UTF-8\|en_US.utf8"; then
        log_success "Locale configured: LANG=$current_lang"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        # Locale is available, but not set as default - this is OK, just information
        log_success "Locale en_US.UTF-8 available (LANG=$current_lang)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
else
    log_warn "Locale en_US.UTF-8 is not available (may require: sudo locale-gen en_US.UTF-8)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# ============================================
# 9. Summary
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

