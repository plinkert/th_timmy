#!/bin/bash
#
# Installation script for VM-03: Analysis/Jupyter
# Automation of JupyterLab and all required tools installation
#
# Usage: sudo ./install_vm03.sh [PROJECT_ROOT] [CONFIG_FILE]
# Example: sudo ./install_vm03.sh $HOME/th_timmy config.yml
#
# If PROJECT_ROOT is not provided, will use $HOME/th_timmy
# If CONFIG_FILE is not provided, will use config.yml (optional)

set -e  # Stop on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
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

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then 
    log_error "Script must be run as root (use sudo)"
    exit 1
fi

# Get user who ran sudo
if [ -z "$SUDO_USER" ]; then
    log_error "Cannot determine user. Use: sudo -u user ./install_vm03.sh"
    exit 1
fi

# Set default PROJECT_ROOT in user's home directory
USER_HOME=$(eval echo ~$SUDO_USER)
PROJECT_ROOT="${1:-$USER_HOME/th_timmy}"

# Set path to configuration file (optional)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${2:-$SCRIPT_DIR/config.yml}"

log_info "User: $SUDO_USER"
log_info "Home directory: $USER_HOME"
log_info "PROJECT_ROOT: $PROJECT_ROOT"
log_info "CONFIG_FILE: $CONFIG_FILE (optional)"
log_info "Virtual environment will be in: $PROJECT_ROOT/venv"

# Check if configuration file exists (optional)
CONFIG_EXISTS=false
if [ -f "$CONFIG_FILE" ]; then
    CONFIG_EXISTS=true
    log_info "Found configuration file: $CONFIG_FILE"
else
    log_warn "Configuration file does not exist (optional): $CONFIG_FILE"
    log_info "Default configuration values will be used"
fi

# Check if directory exists, if not - create
if [ ! -d "$PROJECT_ROOT" ]; then
    log_warn "Directory $PROJECT_ROOT does not exist. Creating..."
    mkdir -p "$PROJECT_ROOT"
    chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT"
fi

# Create hosts/vm03-analysis structure if it doesn't exist
VM03_DIR="$PROJECT_ROOT/hosts/vm03-analysis"
if [ ! -d "$VM03_DIR" ]; then
    log_info "Creating directory structure: hosts/vm03-analysis"
    mkdir -p "$VM03_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/hosts"
fi

log_info "Starting installation of tools for VM-03..."

# ============================================
# 1. System Update
# ============================================
log_info "Updating package list..."
# Set environment variables for non-interactive installations
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
apt-get update -qq

# ============================================
# 2. Install Basic System Tools
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
# 3. Locale Configuration
# ============================================
log_info "Configuring locale..."
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# ============================================
# 4. Python and Environment Installation (extended)
# ============================================
log_info "Installing Python 3 and tools (with Tkinter)..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-tk

# ============================================
# 5. Instalacja bibliotek systemowych (rozszerzone dla matplotlib/seaborn)
# ============================================
log_info "Installing system libraries for Python packages..."
apt-get install -y \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    pkg-config

# ============================================
# 6. Node.js Installation (for JupyterLab extensions)
# ============================================
log_info "Installing Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version 2>/dev/null | cut -d'v' -f2 | cut -d. -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        log_warn "Node.js version $NODE_VERSION already installed. Skipping installation..."
    else
        log_info "Node.js version $NODE_VERSION is too old, updating..."
        # Remove old versions if they exist
        apt-get remove -y nodejs npm 2>/dev/null || true
    fi
fi

# Add NodeSource repository for Node.js 18.x LTS
if ! command -v node &> /dev/null || [ "${NODE_VERSION:-0}" -lt 18 ]; then
    log_info "Adding NodeSource repository..."
    
    # Remove old nodejs/npm packages if they exist (may cause conflicts)
    apt-get remove -y nodejs npm 2>/dev/null || true
    apt-get autoremove -y 2>/dev/null || true
    
    # Add NodeSource repository
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - || {
        log_warn "Failed to add NodeSource repository, trying alternative method..."
        # Alternative method - use snap or nvm
        if command -v snap &> /dev/null; then
            log_info "Installing Node.js via snap..."
            snap install node --classic || log_warn "Failed to install Node.js via snap"
        else
            log_warn "Node.js was not installed (some JupyterLab extensions may not work)"
            log_info "You can install Node.js manually later"
        fi
    }
    
    # If repository was added, install nodejs
    if apt-cache policy nodejs | grep -q "nodesource"; then
        log_info "Installing Node.js from NodeSource repository..."
        apt-get install -y nodejs || {
            log_warn "Failed to install Node.js from NodeSource"
            log_info "Node.js is optional - JupyterLab will work without it"
        }
    fi
fi

if command -v node &> /dev/null; then
    NODE_VER=$(node --version)
    NPM_VER=$(npm --version 2>/dev/null || echo "N/A")
    log_success "Node.js: $NODE_VER, npm: $NPM_VER"
else
    log_warn "Node.js was not installed (some JupyterLab extensions may not work)"
    log_info "JupyterLab will work without Node.js, but some extensions may require manual installation"
fi

# ============================================
# 7. Create Virtual Environment and Install Python Packages
# ============================================
log_info "Configuring Python environment..."

# Check if requirements.txt exists
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    log_error "requirements.txt file not found"
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
log_info "Using requirements.txt: $REQUIREMENTS_FILE"

# First install pyyaml to parse config.yml later (if exists)
log_info "Installing pyyaml (required for parsing config.yml)..."
sudo -u $SUDO_USER bash -c "
    source $VENV_DIR/bin/activate
    pip install --upgrade pip --quiet
    pip install pyyaml --quiet
" || log_warn "Failed to install pyyaml, using basic parsing"

# Now install all packages
log_info "Installing all packages from requirements.txt..."
sudo -u $SUDO_USER bash -c "
    set -e
    source $VENV_DIR/bin/activate
    pip install -r $REQUIREMENTS_FILE
    echo 'Installed packages:'
    pip list | grep -E 'jupyter|pandas|numpy|matplotlib|seaborn|scikit-learn' || true
" || {
    log_error "Error during Python package installation"
    log_error "Check if requirements.txt exists and is correct"
    exit 1
}
log_success "Python packages installed successfully"

# ============================================
# 8. Konfiguracja JupyterLab
# ============================================
log_info "Konfiguracja JupyterLab..."

# Parse config.yml if exists
JUPYTER_IP="0.0.0.0"
JUPYTER_PORT="8888"
JUPYTER_TOKEN=""
JUPYTER_PASSWORD=""
ENABLE_SERVICE=false

if [ "$CONFIG_EXISTS" = true ]; then
    log_info "Parsing configuration file..."
    
    # Function to parse config.yml
    parse_config() {
        local key_path="$1"
        local default_value="$2"
        
        if [ -f "$VENV_DIR/bin/activate" ]; then
            sudo -u $SUDO_USER bash -c "source $VENV_DIR/bin/activate && python3 -c \"import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print($key_path)\"" 2>/dev/null || echo "$default_value"
        elif python3 -c "import yaml" 2>/dev/null; then
            python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print($key_path)" 2>/dev/null || echo "$default_value"
        else
            echo "$default_value"
        fi
    }
    
    JUPYTER_IP=$(parse_config "d.get('jupyter', {}).get('ip', '0.0.0.0')" "0.0.0.0")
    JUPYTER_PORT=$(parse_config "d.get('jupyter', {}).get('port', 8888)" "8888")
    JUPYTER_TOKEN=$(parse_config "d.get('jupyter', {}).get('token', '')" "")
    JUPYTER_PASSWORD=$(parse_config "d.get('jupyter', {}).get('password', '')" "")
    ENABLE_SERVICE=$(parse_config "d.get('jupyter', {}).get('enable_service', False)" "False")
    ALLOW_FILE_UPLOAD=$(parse_config "d.get('jupyter', {}).get('allow_file_upload', True)" "True")
    
    log_info "Read from config.yml: IP=$JUPYTER_IP, PORT=$JUPYTER_PORT, allow_file_upload=$ALLOW_FILE_UPLOAD"
fi

# Generate JupyterLab configuration
log_info "Generating JupyterLab configuration..."
sudo -u $SUDO_USER bash -c "
    source $VENV_DIR/bin/activate
    jupyter lab --generate-config 2>/dev/null || true
"

JUPYTER_CONFIG="$USER_HOME/.jupyter/jupyter_lab_config.py"
if [ -f "$JUPYTER_CONFIG" ]; then
    log_info "JupyterLab configuration: $JUPYTER_CONFIG"
    
    # Backup original file
    cp "$JUPYTER_CONFIG" "${JUPYTER_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update configuration
    # Hash password if provided
    if [ -n "$JUPYTER_PASSWORD" ]; then
        log_info "Hashing password for JupyterLab..."
        JUPYTER_PASSWORD_HASH=$(sudo -u $SUDO_USER bash -c "
            source $VENV_DIR/bin/activate
            python3 -c \"from jupyter_server.auth import passwd; print(passwd('$JUPYTER_PASSWORD'))\" 2>/dev/null || \
            python3 -c \"from notebook.auth import passwd; print(passwd('$JUPYTER_PASSWORD'))\" 2>/dev/null || \
            echo ''
        ")
        
        if [ -z "$JUPYTER_PASSWORD_HASH" ]; then
            log_warn "Failed to hash password, using token instead"
            JUPYTER_PASSWORD_HASH=""
        else
            log_success "Password has been hashed"
        fi
    else
        JUPYTER_PASSWORD_HASH=""
    fi
    
    sudo -u $SUDO_USER bash -c "
        source $VENV_DIR/bin/activate
        python3 << 'PYTHON_EOF'
import os
config_file = '$JUPYTER_CONFIG'

# Read existing configuration
with open(config_file, 'r') as f:
    content = f.read()

# Check and update settings
updates = []
if 'c.ServerApp.ip' not in content or 'c.ServerApp.ip = ' not in content.split('c.ServerApp.ip')[1].split('\\n')[0]:
    updates.append(\"c.ServerApp.ip = '$JUPYTER_IP'\")
if 'c.ServerApp.port' not in content or 'c.ServerApp.port = ' not in content.split('c.ServerApp.port')[1].split('\\n')[0]:
    updates.append(\"c.ServerApp.port = $JUPYTER_PORT\")
if 'c.ServerApp.open_browser' not in content:
    updates.append('c.ServerApp.open_browser = False')

# Add settings if they don't exist
if updates:
    with open(config_file, 'a') as f:
        f.write('\\n# Automatically configured by install_vm03.sh\\n')
        for update in updates:
            f.write(update + '\\n')
        if '$JUPYTER_TOKEN' and '$JUPYTER_TOKEN' != '':
            f.write(\"c.ServerApp.token = '$JUPYTER_TOKEN'\\n\")
        if '$JUPYTER_PASSWORD_HASH' and '$JUPYTER_PASSWORD_HASH' != '':
            f.write(\"c.ServerApp.password = '$JUPYTER_PASSWORD_HASH'\\n\")
        
        # File upload configuration
        if '$ALLOW_FILE_UPLOAD' and '$ALLOW_FILE_UPLOAD' == 'True':
            f.write('\\n# File upload security settings\\n')
            f.write('c.ContentsManager.allow_hidden = False\\n')
            f.write('c.ContentsManager.pre_save_hook = None\\n')
            f.write('c.FileContentsManager.delete_to_trash = True\\n')
            f.write('# Note: JupyterLab does not enforce file size limits natively.\\n')
            f.write('# Consider using nginx reverse proxy with client_max_body_size for production.\\n')
PYTHON_EOF
    " || log_warn "Failed to update JupyterLab configuration"
    
    log_success "JupyterLab configuration updated"
else
    log_warn "JupyterLab configuration file not found"
fi

# ============================================
# 9. Configure JupyterLab as Service (optional)
# ============================================
if [ "$ENABLE_SERVICE" = "True" ] || [ "$ENABLE_SERVICE" = "true" ]; then
    log_info "Configuring JupyterLab as systemd service..."
    
    SERVICE_FILE="/etc/systemd/system/jupyter.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=JupyterLab
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/jupyter lab --ip=$JUPYTER_IP --port=$JUPYTER_PORT --no-browser
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable jupyter
    systemctl start jupyter || log_warn "Failed to start JupyterLab service"
    log_success "JupyterLab configured as systemd service"
else
    log_info "JupyterLab service is not enabled (can be enabled in config.yml)"
fi

# ============================================
# 10. Firewall Configuration
# ============================================
log_info "Configuring firewall..."
if [ "$CONFIG_EXISTS" = true ]; then
    JUPYTER_PORT_FW=$(parse_config "d.get('network', {}).get('jupyter_port', 8888)" "8888")
else
    JUPYTER_PORT_FW="$JUPYTER_PORT"
fi

ufw allow ${JUPYTER_PORT_FW}/tcp
ufw reload

# ============================================
# 11. Environment Variables Configuration in .bashrc
# ============================================
log_info "Configuring environment variables..."
BASHRC="$USER_HOME/.bashrc"

if ! grep -q "LC_ALL=en_US.UTF-8" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Threat Hunting Lab - VM03 Configuration" >> "$BASHRC"
    echo "export LC_ALL=en_US.UTF-8" >> "$BASHRC"
    echo "export LANG=en_US.UTF-8" >> "$BASHRC"
    log_info "Added environment variables to $BASHRC"
fi

# ============================================
# 12. Summary
# ============================================
log_info "Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Run health_check.sh script to verify installation"
echo "2. Activate virtual environment: source $VENV_DIR/bin/activate"
echo "3. Start JupyterLab: jupyter lab --ip=$JUPYTER_IP --port=$JUPYTER_PORT"
echo "4. Open in browser: http://$(hostname -I | awk '{print $1}'):$JUPYTER_PORT"
echo ""
if [ "$ENABLE_SERVICE" = "True" ] || [ "$ENABLE_SERVICE" = "true" ]; then
    echo "JupyterLab jest uruchomiony jako service:"
    echo "  Status: sudo systemctl status jupyter"
    echo "  Logi: sudo journalctl -u jupyter -f"
fi
echo ""

