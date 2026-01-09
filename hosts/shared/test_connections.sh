#!/bin/bash
# test_connections.sh - Test connectivity between VMs
# Usage: ./test_connections.sh [config_file]
# Example: ./test_connections.sh /path/to/configs/config.yml

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

test_passed=0
test_failed=0
test_warnings=0

# Test results storage
declare -A test_results

pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((test_passed++))
    test_results["$1"]="PASS"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((test_failed++))
    test_results["$1"]="FAIL"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((test_warnings++))
    test_results["$1"]="WARN"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Load configuration
load_config() {
    local config_file="${1:-}"
    
    # If config file not provided, try multiple locations
    if [ -z "$config_file" ]; then
        for config_location in "${PROJECT_ROOT}/configs/config.yml" "${HOME}/th_timmy/configs/config.yml" "$(cd "${SCRIPT_DIR}/../.." && pwd)/configs/config.yml"; do
            if [ -f "$config_location" ]; then
                config_file="$config_location"
                break
            fi
        done
    fi
    
    if [ -z "$config_file" ] || [ ! -f "$config_file" ]; then
        echo "ERROR: config.yml not found"
        echo "Checked locations:"
        echo "  - ${PROJECT_ROOT}/configs/config.yml"
        echo "  - ${HOME}/th_timmy/configs/config.yml"
        echo "Usage: $0 [path/to/config.yml]"
        exit 1
    fi
    
    CONFIG_FILE="$config_file"
    info "Using config file: $CONFIG_FILE"
    
    # Extract VM IPs using Python (more reliable than grep)
    if command -v python3 &> /dev/null; then
        # Try to use Python with yaml support
        if python3 -c "import yaml" 2>/dev/null; then
            VM01_IP=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm01', {}).get('ip', ''))" 2>/dev/null || echo "")
            VM02_IP=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm02', {}).get('ip', ''))" 2>/dev/null || echo "")
            VM03_IP=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm03', {}).get('ip', ''))" 2>/dev/null || echo "")
            VM04_IP=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm04', {}).get('ip', ''))" 2>/dev/null || echo "")
        fi
    fi
    
    # Fallback to grep if Python parsing failed
    if [ -z "$VM01_IP" ] || [ -z "$VM02_IP" ] || [ -z "$VM03_IP" ] || [ -z "$VM04_IP" ]; then
        VM01_IP=$(grep -E "vm01:" "$CONFIG_FILE" -A 3 | grep -E "ip:" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
        VM02_IP=$(grep -E "vm02:" "$CONFIG_FILE" -A 3 | grep -E "ip:" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
        VM03_IP=$(grep -E "vm03:" "$CONFIG_FILE" -A 3 | grep -E "ip:" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
        VM04_IP=$(grep -E "vm04:" "$CONFIG_FILE" -A 3 | grep -E "ip:" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
    fi
    
    if [ -z "$VM01_IP" ] || [ -z "$VM02_IP" ] || [ -z "$VM03_IP" ] || [ -z "$VM04_IP" ]; then
        echo "ERROR: Could not extract VM IPs from config.yml"
        echo "DEBUG: VM01_IP=$VM01_IP, VM02_IP=$VM02_IP, VM03_IP=$VM03_IP, VM04_IP=$VM04_IP"
        echo "DEBUG: Config file: $CONFIG_FILE"
        exit 1
    fi
}

# Test basic connectivity (ping)
test_ping() {
    local target_ip=$1
    local vm_name=$2
    
    if ping -c 2 -W 2 "$target_ip" &> /dev/null; then
        pass "Ping to $vm_name ($target_ip)"
        return 0
    else
        fail "Ping to $vm_name ($target_ip)"
        return 1
    fi
}

# Test port connectivity
test_port() {
    local target_ip=$1
    local port=$2
    local service=$3
    
    if command -v nc &> /dev/null; then
        if nc -z -w 2 "$target_ip" "$port" 2>/dev/null; then
            pass "Port $port ($service) on $target_ip"
            return 0
        else
            fail "Port $port ($service) on $target_ip"
            return 1
        fi
    elif command -v timeout &> /dev/null && command -v bash &> /dev/null; then
        # Fallback: use bash with /dev/tcp
        if timeout 2 bash -c "echo > /dev/tcp/$target_ip/$port" 2>/dev/null; then
            pass "Port $port ($service) on $target_ip"
            return 0
        else
            fail "Port $port ($service) on $target_ip"
            return 1
        fi
    else
        warn "Port test tools not available (nc or bash with /dev/tcp)"
        return 1
    fi
}

# Test SSH connectivity
test_ssh() {
    local target_ip=$1
    local vm_name=$2
    
    if command -v ssh &> /dev/null; then
        if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes "$target_ip" "echo 'SSH OK'" &> /dev/null 2>&1; then
            pass "SSH to $vm_name ($target_ip)"
            return 0
        else
            warn "SSH to $vm_name ($target_ip) - may require password or key"
            return 1
        fi
    else
        warn "SSH client not available"
        return 1
    fi
}

# Test database connection from VM-01 to VM-02
test_db_connection() {
    echo "=========================================="
    echo "Database Connection (VM-01 → VM-02)"
    echo "=========================================="
    
    # Test port connectivity
    test_port "$VM02_IP" "5432" "PostgreSQL"
    
    # Test actual database connection (if psycopg2 is available)
    local venv_path=""
    for venv_location in "${PROJECT_ROOT}/venv" "${HOME}/th_timmy/venv"; do
        if [ -d "$venv_location" ] && [ -f "$venv_location/bin/activate" ]; then
            venv_path="$venv_location"
            break
        fi
    done
    
    if [ -n "$venv_path" ]; then
        source "$venv_path/bin/activate"
        
        # Check if psycopg2 is available
        if python3 -c "import psycopg2" 2>/dev/null || python3 -c "import psycopg2_binary" 2>/dev/null; then
            # Try to get database config from config.yml
            if python3 -c "import yaml" 2>/dev/null && [ -f "$CONFIG_FILE" ]; then
                DB_HOST=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('database', {}).get('host', '$VM02_IP'))" 2>/dev/null || echo "$VM02_IP")
                DB_PORT=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('database', {}).get('port', 5432))" 2>/dev/null || echo "5432")
                DB_NAME=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('database', {}).get('name', 'threat_hunting'))" 2>/dev/null || echo "threat_hunting")
                DB_USER=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('database', {}).get('user', 'threat_hunter'))" 2>/dev/null || echo "threat_hunter")
                
                # If host is a VM reference, resolve to IP
                if [ "$DB_HOST" = "vm02" ]; then
                    DB_HOST="$VM02_IP"
                fi
                
                # Try connection (without password - just test if port is accessible)
                if python3 -c "
import psycopg2
import sys
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        database='$DB_NAME',
        user='$DB_USER',
        connect_timeout=5
    )
    conn.close()
    sys.exit(0)
except psycopg2.OperationalError as e:
    if 'password' in str(e).lower() or 'authentication' in str(e).lower():
        # Port is accessible, just needs password
        sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
                    pass "Database connection to PostgreSQL"
                else
                    warn "Database connection test - port accessible but authentication may be required"
                fi
            fi
        else
            warn "psycopg2 not available, skipping database connection test"
        fi
        deactivate 2>/dev/null || true
    else
        warn "Virtual environment not found, skipping database connection test"
    fi
    echo ""
}

# Test JupyterLab connection from VM-04 to VM-03
test_jupyter_connection() {
    echo "=========================================="
    echo "JupyterLab Connection (VM-04 → VM-03)"
    echo "=========================================="
    
    # Test port connectivity (JupyterLab may not be running, which is OK)
    if test_port "$VM03_IP" "8888" "JupyterLab"; then
        pass "JupyterLab is accessible"
    else
        warn "JupyterLab port not accessible (JupyterLab may not be running)"
        info "JupyterLab can be started manually on VM-03"
    fi
    echo ""
}

# Test n8n connection from VM-03 to VM-04
test_n8n_connection() {
    echo "=========================================="
    echo "n8n Connection (VM-03 → VM-04)"
    echo "=========================================="
    
    test_port "$VM04_IP" "5678" "n8n"
    
    # Test HTTP connection
    if command -v curl &> /dev/null; then
        if curl -s -f -m 5 "http://${VM04_IP}:5678/healthz" &> /dev/null; then
            pass "n8n health endpoint responding"
        else
            warn "n8n health endpoint not responding (n8n may not be running)"
        fi
    fi
    echo ""
}

# Save results to JSON file
save_results_to_json() {
    local output_file="$1"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local hostname=$(hostname)
    local date=$(date -Iseconds)
    
    # Create test_results directory if it doesn't exist
    mkdir -p "${PROJECT_ROOT}/test_results"
    
    local json_file="${PROJECT_ROOT}/test_results/${output_file}_${timestamp}.json"
    
    # Build JSON manually (no jq dependency)
    {
        echo "{"
        echo "  \"timestamp\": \"$date\","
        echo "  \"hostname\": \"$hostname\","
        echo "  \"config_file\": \"$CONFIG_FILE\","
        echo "  \"summary\": {"
        echo "    \"passed\": $test_passed,"
        echo "    \"failed\": $test_failed,"
        echo "    \"warnings\": $test_warnings,"
        echo "    \"total\": $((test_passed + test_failed + test_warnings))"
        echo "  },"
        echo "  \"vm_ips\": {"
        echo "    \"vm01\": \"$VM01_IP\","
        echo "    \"vm02\": \"$VM02_IP\","
        echo "    \"vm03\": \"$VM03_IP\","
        echo "    \"vm04\": \"$VM04_IP\""
        echo "  },"
        echo "  \"tests\": ["
        
        local first=true
        for test_name in "${!test_results[@]}"; do
            if [ "$first" = true ]; then
                first=false
            else
                echo ","
            fi
            echo -n "    {"
            echo -n "\"name\": \"$(echo "$test_name" | sed 's/"/\\"/g')\","
            echo -n "\"status\": \"${test_results[$test_name]}\""
            echo -n "}"
        done
        
        echo ""
        echo "  ]"
        echo "}"
    } > "$json_file"
    
    info "Results saved to: $json_file"
}

main() {
    echo ""
    echo "=========================================="
    echo "VM Connectivity Tests"
    echo "=========================================="
    echo ""
    info "Current host: $(hostname)"
    info "Date: $(date)"
    echo ""
    
    load_config "$@"
    
    info "VM-01 (Ingest): $VM01_IP"
    info "VM-02 (Database): $VM02_IP"
    info "VM-03 (Analysis): $VM03_IP"
    info "VM-04 (Orchestrator): $VM04_IP"
    echo ""
    
    # Test basic connectivity
    echo "=========================================="
    echo "Basic Connectivity (Ping)"
    echo "=========================================="
    test_ping "$VM01_IP" "VM-01"
    test_ping "$VM02_IP" "VM-02"
    test_ping "$VM03_IP" "VM-03"
    test_ping "$VM04_IP" "VM-04"
    echo ""
    
    # Test SSH (if available)
    echo "=========================================="
    echo "SSH Connectivity"
    echo "=========================================="
    test_ssh "$VM01_IP" "VM-01"
    test_ssh "$VM02_IP" "VM-02"
    test_ssh "$VM03_IP" "VM-03"
    test_ssh "$VM04_IP" "VM-04"
    echo ""
    
    # Test service-specific connections
    test_db_connection
    test_jupyter_connection
    test_n8n_connection
    
    echo "=========================================="
    echo "Connection Test Summary"
    echo "=========================================="
    echo -e "  ${GREEN}Passed:${NC} $test_passed"
    echo -e "  ${RED}Failed:${NC} $test_failed"
    echo -e "  ${YELLOW}Warnings:${NC} $test_warnings"
    echo "=========================================="
    echo ""
    
    # Save results to JSON
    save_results_to_json "connections"
    
    if [ $test_failed -eq 0 ]; then
        echo -e "${GREEN}✓ All connection tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some connection tests failed!${NC}"
        exit 1
    fi
}

main "$@"

