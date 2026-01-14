#!/bin/bash
#
# Installation script for VM-04: Orchestrator
# Automation of Docker, n8n and all required tools installation
#
# Usage: sudo ./install_vm04.sh [PROJECT_ROOT] [CONFIG_FILE]
# Example: sudo ./install_vm04.sh $HOME/th_timmy config.yml
#
# If PROJECT_ROOT is not provided, will use $HOME/th_timmy
# If CONFIG_FILE is not provided, will use config.yml

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
    log_error "Cannot determine user. Use: sudo -u user ./install_vm04.sh"
    exit 1
fi

# Set default PROJECT_ROOT in user's home directory
USER_HOME=$(eval echo ~$SUDO_USER)
PROJECT_ROOT="${1:-$USER_HOME/th_timmy}"

# Set path to configuration file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${2:-$SCRIPT_DIR/config.yml}"

log_info "User: $SUDO_USER"
log_info "Home directory: $USER_HOME"
log_info "PROJECT_ROOT: $PROJECT_ROOT"
log_info "CONFIG_FILE: $CONFIG_FILE"
log_info "Virtual environment will be in: $PROJECT_ROOT/venv"

# Check if configuration file exists
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Configuration file not found: $CONFIG_FILE"
    log_error "Copy config.example.yml to config.yml and fill in values"
    exit 1
fi

# ============================================
# CONFIGURATION FILE VALIDATION (at the beginning)
# ============================================
log_info "Validating configuration file..."

# Function to parse config.yml
parse_config() {
    local key_path="$1"
    local default_value="$2"
    
    # First try system python3 with pyyaml
    if python3 -c "import yaml" 2>/dev/null; then
        python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print($key_path)" 2>/dev/null || echo "$default_value"
    else
        # Fallback - podstawowe parsowanie
        case "$key_path" in
            "d.get('n8n', {}).get('basic_auth_user', 'admin')")
                grep -A 10 "n8n:" "$CONFIG_FILE" | grep "basic_auth_user:" | awk '{print $2}' | tr -d '"' || echo "$default_value"
                ;;
            "d.get('n8n', {}).get('basic_auth_password', '')")
                grep -A 10 "n8n:" "$CONFIG_FILE" | grep "basic_auth_password:" | awk '{print $2}' | tr -d '"' || echo "$default_value"
                ;;
            *)
                echo "$default_value"
                ;;
        esac
    fi
}

# Parse basic values from config.yml
N8N_USER=$(parse_config "d.get('n8n', {}).get('basic_auth_user', 'admin')" "admin")
N8N_PASSWORD=$(parse_config "d.get('n8n', {}).get('basic_auth_password', '')" "")
N8N_PORT=$(parse_config "d.get('n8n', {}).get('port', 5678)" "5678")
DASHBOARD_API_PORT=$(parse_config "d.get('dashboard_api', {}).get('port', 8000)" "8000")
API_KEY=$(parse_config "d.get('dashboard_api', {}).get('api_key', '')" "")
API_BASE_URL=$(parse_config "d.get('dashboard_api', {}).get('base_url', 'http://localhost:8000')" "http://localhost:8000")
AUTO_START=$(parse_config "d.get('docker', {}).get('auto_start', True)" "True")

log_info "Read from config.yml: N8N_USER=$N8N_USER, N8N_PORT=$N8N_PORT, DASHBOARD_API_PORT=$DASHBOARD_API_PORT"

# Validate required values
if [ "$N8N_PASSWORD" = "CHANGE_ME_STRONG_PASSWORD" ] || [ -z "$N8N_PASSWORD" ]; then
    log_error "n8n password not set in configuration file!"
    log_error "Edit $CONFIG_FILE and set basic_auth_password"
    exit 1
fi

log_success "Configuration file is correct"

# Check if directory exists, if not - create
if [ ! -d "$PROJECT_ROOT" ]; then
    log_warn "Directory $PROJECT_ROOT does not exist. Creating..."
    mkdir -p "$PROJECT_ROOT"
    chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT"
fi

# Create hosts/vm04-orchestrator structure if it doesn't exist
VM04_DIR="$PROJECT_ROOT/hosts/vm04-orchestrator"
if [ ! -d "$VM04_DIR" ]; then
    log_info "Creating directory structure: hosts/vm04-orchestrator"
    mkdir -p "$VM04_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/hosts"
fi

log_info "Starting installation of tools for VM-04..."

# ============================================
# 1. Aktualizacja systemu
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
# 4. Instalacja Docker
# ============================================
log_info "Instalacja Docker..."

# Check if Docker is already installed
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version 2>/dev/null)
    log_warn "Docker already installed: $DOCKER_VERSION"
    log_info "Skipping Docker installation..."
else
    log_info "Adding official Docker GPG key..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    
    log_info "Adding Docker repository..."
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    log_info "Updating package list..."
    apt-get update -qq
    
    log_info "Installing Docker Engine..."
    apt-get install -y \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin
    
    log_success "Docker installed successfully"
fi

# Add user to docker group
log_info "Adding user $SUDO_USER to docker group..."
usermod -aG docker $SUDO_USER || log_warn "Failed to add user to docker group (may already be in group)"

# Start and enable Docker
log_info "Starting Docker..."
systemctl start docker || log_warn "Docker may already be running"
systemctl enable docker || log_warn "Docker may already be enabled"

# Verify Docker
log_info "Verifying Docker installation..."
if docker --version > /dev/null 2>&1; then
    DOCKER_VER=$(docker --version)
    DOCKER_COMPOSE_VER=$(docker compose version 2>/dev/null || echo "N/A")
    log_success "Docker: $DOCKER_VER"
    log_success "Docker Compose: $DOCKER_COMPOSE_VER"
    
    # Test Docker (as root, because user may not have access yet)
    log_info "Testing Docker (hello-world)..."
    docker run --rm hello-world > /dev/null 2>&1 && log_success "Docker is working correctly" || log_warn "Docker test failed"
else
    log_error "Docker was not installed correctly"
    exit 1
fi

# ============================================
# 5. Python and Environment Installation
# ============================================
log_info "Installing Python 3 and tools..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev

# ============================================
# 6. System Libraries Installation for Python
# ============================================
log_info "Installing system libraries for Python packages..."
apt-get install -y \
    libssl-dev \
    libffi-dev

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

# First install pyyaml to parse config.yml later
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
    pip list | grep -E 'pyyaml|python-dotenv|requests|loguru|docker' || true
" || {
    log_error "Error during Python package installation"
    log_error "Check if requirements.txt exists and is correct"
    exit 1
}
log_success "Python packages installed successfully"

# ============================================
# 8. Configure docker-compose.yml for n8n
# ============================================
log_info "Configuring docker-compose.yml for n8n..."

DOCKER_COMPOSE_FILE="$VM04_DIR/docker-compose.yml"
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    log_info "Copying docker-compose.yml..."
    cp "$SCRIPT_DIR/docker-compose.yml" "$DOCKER_COMPOSE_FILE"
    chown $SUDO_USER:$SUDO_USER "$DOCKER_COMPOSE_FILE"
fi

# Create .env file for docker-compose
ENV_FILE="$VM04_DIR/.env"
log_info "Creating .env file for docker-compose..."
cat > "$ENV_FILE" << EOF
# n8n Environment Variables
# Automatically generated by install_vm04.sh

N8N_BASIC_AUTH_USER=$N8N_USER
N8N_BASIC_AUTH_PASSWORD=$N8N_PASSWORD
N8N_SECURE_COOKIE=false

# Dashboard API Environment Variables
DASHBOARD_API_PORT=$DASHBOARD_API_PORT
API_KEY=$API_KEY
API_BASE_URL=$API_BASE_URL
EOF
chown $SUDO_USER:$SUDO_USER "$ENV_FILE"
chmod 600 "$ENV_FILE"
log_success ".env file created"

# ============================================
# 9. Firewall Configuration
# ============================================
log_info "Configuring firewall..."
N8N_PORT_FW=$(parse_config "d.get('network', {}).get('n8n_port', 5678)" "5678")
DASHBOARD_API_PORT_FW=$(parse_config "d.get('network', {}).get('dashboard_api_port', 8000)" "8000")
ufw allow ${N8N_PORT_FW}/tcp
ufw allow ${DASHBOARD_API_PORT_FW}/tcp
ufw reload
log_success "Firewall configured: n8n port $N8N_PORT_FW, dashboard-api port $DASHBOARD_API_PORT_FW"

# ============================================
# 10. Build and Start Docker Services (if auto_start=true)
# ============================================
if [ "$AUTO_START" = "True" ] || [ "$AUTO_START" = "true" ]; then
    log_info "Building and starting Docker services (n8n + dashboard-api)..."
    
    # User must be in docker group - use newgrp or su
    cd "$VM04_DIR"
    
    # Run as user (docker requires docker group)
    sudo -u $SUDO_USER bash -c "
        cd $VM04_DIR
        docker compose down 2>/dev/null || true
        log_info 'Building dashboard-api image...'
        docker compose build dashboard-api || log_warn 'Build failed, will try to start anyway'
        docker compose up -d
    " || {
        log_warn "Failed to start Docker services automatically"
        log_info "You can start manually: cd $VM04_DIR && docker compose up -d --build"
        log_info "Note: You may need to log out and log back in after adding to docker group"
    }
    
    # Check status after a moment
    sleep 5
    if sudo -u $SUDO_USER docker compose -f "$VM04_DIR/docker-compose.yml" ps 2>/dev/null | grep -q "threat-hunting-n8n.*Up"; then
        log_success "n8n started in Docker container"
    else
        log_warn "n8n may not be running yet"
    fi
    
    if sudo -u $SUDO_USER docker compose -f "$VM04_DIR/docker-compose.yml" ps 2>/dev/null | grep -q "threat-hunting-dashboard-api.*Up"; then
        log_success "dashboard-api started in Docker container"
    else
        log_warn "dashboard-api may not be running yet"
    fi
    
    log_info "Check status: cd $VM04_DIR && docker compose ps"
    log_info "Check logs: cd $VM04_DIR && docker compose logs"
else
    log_info "Automatic Docker services startup is disabled"
    log_info "To start services: cd $VM04_DIR && docker compose up -d --build"
fi

# ============================================
# 11. Environment Variables Configuration in .bashrc
# ============================================
log_info "Configuring environment variables..."
BASHRC="$USER_HOME/.bashrc"

if ! grep -q "LC_ALL=en_US.UTF-8" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Threat Hunting Lab - VM04 Configuration" >> "$BASHRC"
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
echo "3. Check Docker services status: cd $VM04_DIR && docker compose ps"
echo "4. Open n8n in browser: http://$(hostname -I | awk '{print $1}'):$N8N_PORT"
echo "5. Open Dashboard API docs: http://$(hostname -I | awk '{print $1}'):$DASHBOARD_API_PORT/docs"
echo ""
echo "IMPORTANT:"
echo "- You may need to log out and log back in to access Docker without sudo"
echo "- Check Docker logs:"
echo "  n8n:           cd $VM04_DIR && docker compose logs -f n8n"
echo "  dashboard-api: cd $VM04_DIR && docker compose logs -f dashboard-api"
echo "- Docker services management:"
echo "  Start:   cd $VM04_DIR && docker compose up -d"
echo "  Stop:    cd $VM04_DIR && docker compose down"
echo "  Restart: cd $VM04_DIR && docker compose restart"
echo "  Rebuild: cd $VM04_DIR && docker compose up -d --build"
echo ""

