#!/bin/bash
#
# Installation script for VM-01: Ingest/Parser
# Automation of installation of all required tools
#
# Usage: sudo ./install_vm01.sh [PROJECT_ROOT]
# Example: sudo ./install_vm01.sh $HOME/th_timmy
#
# If PROJECT_ROOT is not provided, will use $HOME/th_timmy

set -e  # Stop on error

# Kolory dla outputu
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then 
    log_error "Script must be run as root (use sudo)"
    exit 1
fi

# Get user who ran sudo
if [ -z "$SUDO_USER" ]; then
    log_error "Cannot determine user. Use: sudo -u user ./install_vm01.sh"
    exit 1
fi

# Set default PROJECT_ROOT in user's home directory
USER_HOME=$(eval echo ~$SUDO_USER)
PROJECT_ROOT="${1:-$USER_HOME/th_timmy}"

log_info "User: $SUDO_USER"
log_info "Home directory: $USER_HOME"
log_info "PROJECT_ROOT: $PROJECT_ROOT"
log_info "Virtual environment will be in: $PROJECT_ROOT/venv"

# Check if directory exists, if not - create
if [ ! -d "$PROJECT_ROOT" ]; then
    log_warn "Directory $PROJECT_ROOT does not exist. Creating..."
    mkdir -p "$PROJECT_ROOT"
    chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT"
fi

# Create hosts/vm01-ingest structure if it doesn't exist
VM01_DIR="$PROJECT_ROOT/hosts/vm01-ingest"
if [ ! -d "$VM01_DIR" ]; then
    log_info "Creating directory structure: hosts/vm01-ingest"
    mkdir -p "$VM01_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/hosts"
fi

log_info "Starting installation of tools for VM-01..."

# ============================================
# 1. System update
# ============================================
log_info "Updating package list..."
apt-get update -qq

# ============================================
# 2. Installation of basic system tools
# ============================================
log_info "Installing basic system tools..."
apt-get install -y \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    curl \
    wget \
    gnupg \
    lsb-release \
    git \
    vim \
    nano \
    net-tools \
    iproute2 \
    ufw \
    locales

# ============================================
# 3. Locale configuration
# ============================================
log_info "Configuring locale..."
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# ============================================
# 4. Python and environment installation
# ============================================
log_info "Installing Python 3 and tools..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev

# ============================================
# 5. Installation of system libraries for Python
# ============================================
log_info "Installing system libraries for Python packages..."
apt-get install -y \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev

# ============================================
# 6. Installation of file handling tools
# ============================================
log_info "Installing file handling tools..."
apt-get install -y file unzip zip

# ============================================
# 7. Create virtual environment and install Python packages
# ============================================
log_info "Configuring Python environment..."

# Check if requirements.txt exists in script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

# If not in script directory, check in main project directory
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    log_error "requirements.txt file not found"
    log_error "Searched in: $SCRIPT_DIR/requirements.txt"
    log_error "Searched in: $PROJECT_ROOT/requirements.txt"
    exit 1
fi

log_info "Using requirements.txt from: $REQUIREMENTS_FILE"

# Create venv in project directory
VENV_DIR="$PROJECT_ROOT/venv"
log_info "Checking virtual environment in: $VENV_DIR"
if [ -d "$VENV_DIR" ]; then
    log_warn "Virtual environment already exists. Skipping creation..."
else
    log_info "Creating virtual environment in $VENV_DIR..."
    log_info "Creating as user: $SUDO_USER"
    sudo -u $SUDO_USER python3 -m venv "$VENV_DIR"
    if [ -d "$VENV_DIR" ]; then
        log_success "Virtual environment created successfully"
    else
        log_error "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate venv and install packages
log_info "Installing Python packages from requirements.txt..."
sudo -u $SUDO_USER bash -c "
    source $VENV_DIR/bin/activate
    pip install --upgrade pip --quiet
    pip install -r $REQUIREMENTS_FILE --quiet
"

# ============================================
# 8. Environment variables configuration in .bashrc
# ============================================
log_info "Configuring environment variables..."
BASHRC="$USER_HOME/.bashrc"

if ! grep -q "LC_ALL=en_US.UTF-8" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Threat Hunting Lab - VM01 Configuration" >> "$BASHRC"
    echo "export LC_ALL=en_US.UTF-8" >> "$BASHRC"
    echo "export LANG=en_US.UTF-8" >> "$BASHRC"
    log_info "Added environment variables to $BASHRC"
fi

# ============================================
# 9. Summary
# ============================================
log_info "Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Run health_check.sh script to verify installation"
echo "2. Activate virtual environment: source $VENV_DIR/bin/activate"
echo "3. Check versions of installed tools"
echo ""

