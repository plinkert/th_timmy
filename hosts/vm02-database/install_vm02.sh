#!/bin/bash
#
# Installation script for VM-02: Database
# Automation of PostgreSQL and all required tools installation
#
# Usage: sudo ./install_vm02.sh [PROJECT_ROOT] [CONFIG_FILE]
# Example: sudo ./install_vm02.sh $HOME/th_timmy config.yml
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
    log_error "Cannot determine user. Use: sudo -u user ./install_vm02.sh"
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

# Function to parse config.yml (uses system python3 or venv if available)
parse_config() {
    local key_path="$1"
    local default_value="$2"
    
    # First try system python3 with pyyaml
    if python3 -c "import yaml" 2>/dev/null; then
        python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print($key_path)" 2>/dev/null || echo "$default_value"
    # If not available, try basic parsing
    else
        # Fallback - basic parsing for key values
        case "$key_path" in
            "d['postgresql']['database_name']")
                grep -A 10 "postgresql:" "$CONFIG_FILE" | grep "database_name:" | awk '{print $2}' | tr -d '"' || echo "$default_value"
                ;;
            "d['postgresql']['database_user']")
                grep -A 10 "postgresql:" "$CONFIG_FILE" | grep "database_user:" | awk '{print $2}' | tr -d '"' || echo "$default_value"
                ;;
            "d['postgresql']['database_password']")
                grep -A 10 "postgresql:" "$CONFIG_FILE" | grep "database_password:" | awk '{print $2}' | tr -d '"' || echo "$default_value"
                ;;
            *)
                echo "$default_value"
                ;;
        esac
    fi
}

# Parse basic values from config.yml
DB_NAME=$(parse_config "d['postgresql']['database_name']" "threat_hunting")
DB_USER=$(parse_config "d['postgresql']['database_user']" "threat_hunter")
DB_PASSWORD=$(parse_config "d['postgresql']['database_password']" "")

log_info "Read from config.yml: DB=$DB_NAME, USER=$DB_USER"

# Validate required values
if [ -z "$DB_NAME" ]; then
    log_error "database_name is not set in $CONFIG_FILE"
    exit 1
fi

if [ -z "$DB_USER" ]; then
    log_error "database_user is not set in $CONFIG_FILE"
    exit 1
fi

if [ "$DB_PASSWORD" = "CHANGE_ME_STRONG_PASSWORD" ] || [ -z "$DB_PASSWORD" ]; then
    log_error "Database password not set in configuration file!"
    log_error "Edit $CONFIG_FILE and set database_password"
    exit 1
fi

log_success "Configuration file is correct"

# Check if directory exists, if not - create
if [ ! -d "$PROJECT_ROOT" ]; then
    log_warn "Directory $PROJECT_ROOT does not exist. Creating..."
    mkdir -p "$PROJECT_ROOT"
    chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT"
fi

# Create hosts/vm02-database structure if it doesn't exist
VM02_DIR="$PROJECT_ROOT/hosts/vm02-database"
if [ ! -d "$VM02_DIR" ]; then
    log_info "Creating directory structure: hosts/vm02-database"
    mkdir -p "$VM02_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/hosts"
fi

log_info "Starting installation of tools for VM-02..."

# ============================================
# 1. System update
# ============================================
log_info "Updating package list..."
# Set environment variables for non-interactive installations
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
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
# 4. PostgreSQL installation
# ============================================
log_info "Installing PostgreSQL..."
# Automatic answers for interactive questions
debconf-set-selections <<EOF
postgresql-common postgresql-common/maintainer-name string 'Threat Hunting Team'
postgresql-common postgresql-common/maintainer-email string 'threat-hunting@local'
postgresql-common postgresql-common/password-confirm password
postgresql-common postgresql-common/app-user password
postgresql-common postgresql-common/app-password-confirm password
postgresql-common postgresql-common/install-error select ignore
postgresql-common postgresql-common/start-error select ignore
postgresql-common postgresql-common/createcluster boolean true
postgresql-common postgresql-common/createdb boolean true
EOF

apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
    postgresql \
    postgresql-contrib \
    postgresql-client \
    libpq-dev

# ============================================
# 5. Backup tools installation
# ============================================
log_info "Installing backup tools..."
apt-get install -y cron rsync

# ============================================
# 6. Python and environment installation
# ============================================
log_info "Installing Python 3 and tools..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev

# ============================================
# 7. Installation of system libraries for Python
# ============================================
log_info "Installing system libraries for Python packages..."
apt-get install -y \
    libssl-dev \
    libffi-dev

# ============================================
# 8. Create virtual environment and install Python packages
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

# First install pyyaml to be able to parse config.yml later
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
    pip list | grep -E 'psycopg2|sqlalchemy|pyyaml|python-dotenv|loguru' || true
" || {
    log_error "Error during Python package installation"
    log_error "Check if requirements.txt exists and is correct"
    exit 1
}
log_success "Python packages installed successfully"

# ============================================
# 9. PostgreSQL configuration
# ============================================
log_info "Configuring PostgreSQL..."

# Check PostgreSQL version
# First check directories in /etc/postgresql (this is most reliable)
PG_VERSION=$(ls -d /etc/postgresql/*/main 2>/dev/null | head -1 | cut -d/ -f4)

# If not found, try through psql
if [ -z "$PG_VERSION" ]; then
    PG_VERSION_FULL=$(sudo -u postgres psql --version 2>/dev/null | awk '{print $3}')
    if [ -n "$PG_VERSION_FULL" ]; then
        # Extract only major version (14 from 14.20)
        PG_VERSION=$(echo "$PG_VERSION_FULL" | cut -d. -f1,2 | cut -d. -f1)
    fi
fi

if [ -z "$PG_VERSION" ]; then
    log_error "Cannot determine PostgreSQL version"
    exit 1
fi

log_info "Detected PostgreSQL version: $PG_VERSION"

# Values from config.yml were already read during validation at the beginning of the script
# We use DB_NAME, DB_USER, DB_PASSWORD variables which were already validated

# Create database and user
log_info "Creating database: $DB_NAME"
if sudo -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    log_warn "Database $DB_NAME already exists"
else
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" || {
        log_error "Failed to create database $DB_NAME"
        exit 1
    }
    log_success "Database $DB_NAME created"
fi

log_info "Creating user: $DB_USER"
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null | grep -q 1; then
    log_warn "User $DB_USER already exists, updating password..."
    sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || log_warn "Failed to update password"
else
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || {
        log_error "Failed to create user $DB_USER"
        exit 1
    }
    log_success "User $DB_USER created"
fi

log_info "Granting privileges..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" || log_warn "Failed to grant privileges to database"
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;" || log_warn "Failed to grant privileges to schema"
log_success "Privileges granted"

# postgresql.conf configuration
PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
if [ -f "$PG_CONF" ]; then
    log_info "Configuring postgresql.conf..."
    
    # Get values from config.yml
    LISTEN_ADDRESSES=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d['postgresql'].get('listen_addresses', '*'))" 2>/dev/null || echo "*")
    MAX_CONNECTIONS=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d['postgresql'].get('max_connections', 100))" 2>/dev/null || echo "100")
    SHARED_BUFFERS=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d['postgresql'].get('shared_buffers', '256MB'))" 2>/dev/null || echo "256MB")
    EFFECTIVE_CACHE=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d['postgresql'].get('effective_cache_size', '1GB'))" 2>/dev/null || echo "1GB")
    
    # Backup original file
    cp "$PG_CONF" "${PG_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update configuration
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '$LISTEN_ADDRESSES'/" "$PG_CONF"
    sed -i "s/listen_addresses = 'localhost'/listen_addresses = '$LISTEN_ADDRESSES'/" "$PG_CONF"
    sed -i "s/#max_connections = 100/max_connections = $MAX_CONNECTIONS/" "$PG_CONF"
    sed -i "s/max_connections = [0-9]*/max_connections = $MAX_CONNECTIONS/" "$PG_CONF"
    sed -i "s/#shared_buffers = 128MB/shared_buffers = $SHARED_BUFFERS/" "$PG_CONF"
    sed -i "s/#effective_cache_size = 4GB/effective_cache_size = $EFFECTIVE_CACHE/" "$PG_CONF"
    
    log_info "Updated postgresql.conf"
fi

# pg_hba.conf configuration
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
if [ -f "$PG_HBA" ]; then
    log_info "Configuring pg_hba.conf..."
    
    # Backup original file
    cp "$PG_HBA" "${PG_HBA}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Get list of allowed IPs from config.yml
    ALLOWED_IPS=$(python3 -c "
import yaml
f=open('$CONFIG_FILE')
d=yaml.safe_load(f)
ips = d.get('network', {}).get('allowed_ips', ['127.0.0.1/32'])
for ip in ips:
    print(ip)
" 2>/dev/null || echo "127.0.0.1/32")
    
    # Add rules for each IP
    for ip in $ALLOWED_IPS; do
        if ! grep -q "host.*$DB_NAME.*$DB_USER.*$ip" "$PG_HBA"; then
            echo "host    $DB_NAME    $DB_USER    $ip    md5" >> "$PG_HBA"
            log_info "Added access rule for IP: $ip"
        fi
    done
fi

# Restart PostgreSQL
log_info "Restarting PostgreSQL..."
# Automatic restart without questions
systemctl restart postgresql || log_warn "Failed to restart PostgreSQL"
systemctl enable postgresql || log_warn "Failed to enable PostgreSQL autostart"

# ============================================
# 10. Firewall configuration
# ============================================
log_info "Configuring firewall..."
PG_PORT=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d['postgresql'].get('port', 5432))" 2>/dev/null || echo "5432")
ufw allow ${PG_PORT}/tcp
ufw reload

# ============================================
# 11. Environment variables configuration in .bashrc
# ============================================
log_info "Configuring environment variables..."
BASHRC="$USER_HOME/.bashrc"

if ! grep -q "LC_ALL=en_US.UTF-8" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Threat Hunting Lab - VM02 Configuration" >> "$BASHRC"
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
echo "2. Check connection: psql -h localhost -U $DB_USER -d $DB_NAME"
echo "3. Activate virtual environment: source $VENV_DIR/bin/activate"
echo ""
echo "IMPORTANT:"
echo "- Check if PostgreSQL is listening: sudo systemctl status postgresql"
echo "- Check logs if there are problems: sudo tail -f /var/log/postgresql/postgresql-*-main.log"
echo ""

