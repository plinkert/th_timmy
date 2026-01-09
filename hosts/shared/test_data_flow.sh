#!/bin/bash
# test_data_flow.sh - Test data flow between VMs
# Usage: ./test_data_flow.sh [config_file]
# Example: ./test_data_flow.sh /path/to/configs/config.yml

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

set -uo pipefail

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
    
    if [ -z "$config_file" ]; then
        for config_location in "${PROJECT_ROOT}/configs/config.yml" "${HOME}/th_timmy/configs/config.yml"; do
            if [ -f "$config_location" ]; then
                config_file="$config_location"
                break
            fi
        done
    fi
    
    if [ -z "$config_file" ] || [ ! -f "$config_file" ]; then
        echo "ERROR: config.yml not found"
        exit 1
    fi
    
    CONFIG_FILE="$config_file"
    
    # Extract database config
    if command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
        DB_HOST=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); h=d.get('database', {}).get('host', ''); print(d.get('vms', {}).get('vm02', {}).get('ip', '') if h == 'vm02' else h)" 2>/dev/null || echo "")
        DB_PORT=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('database', {}).get('port', 5432))" 2>/dev/null || echo "5432")
        DB_NAME=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('database', {}).get('name', 'threat_hunting'))" 2>/dev/null || echo "threat_hunting")
        DB_USER=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('database', {}).get('user', 'threat_hunter'))" 2>/dev/null || echo "threat_hunter")
        VM02_IP=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm02', {}).get('ip', ''))" 2>/dev/null || echo "")
        VM03_IP=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm03', {}).get('ip', ''))" 2>/dev/null || echo "")
        VM04_IP=$(python3 -c "import yaml; f=open('$CONFIG_FILE'); d=yaml.safe_load(f); print(d.get('vms', {}).get('vm04', {}).get('ip', ''))" 2>/dev/null || echo "")
    fi
    
    # If DB_HOST is empty or vm02, use VM02_IP
    if [ -z "$DB_HOST" ] || [ "$DB_HOST" = "vm02" ]; then
        DB_HOST="$VM02_IP"
    fi
    
    if [ -z "$DB_HOST" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
        echo "ERROR: Could not extract database configuration from config.yml"
        exit 1
    fi
}

# Find virtual environment
find_venv() {
    local venv_path=""
    for venv_location in "${PROJECT_ROOT}/venv" "${HOME}/th_timmy/venv"; do
        if [ -d "$venv_location" ] && [ -f "$venv_location/bin/activate" ]; then
            venv_path="$venv_location"
            break
        fi
    done
    echo "$venv_path"
}

# Test database write (VM-01 → VM-02)
test_db_write() {
    echo "=========================================="
    echo "Database Write Test (VM-01 → VM-02)"
    echo "=========================================="
    
    local venv_path=$(find_venv)
    if [ -z "$venv_path" ]; then
        warn "Virtual environment not found, skipping database write test"
        return 1
    fi
    
    source "$venv_path/bin/activate"
    
    # Check if psycopg2 is available
    if ! python3 -c "import psycopg2" 2>/dev/null && ! python3 -c "import psycopg2_binary" 2>/dev/null; then
        warn "psycopg2 not available, skipping database write test"
        deactivate 2>/dev/null || true
        return 1
    fi
    
    # Try to get password from environment or config
    local db_password="${POSTGRES_PASSWORD:-}"
    if [ -z "$db_password" ]; then
        warn "Database password not set (POSTGRES_PASSWORD), skipping write test"
        info "To enable database tests, set: export POSTGRES_PASSWORD='your_password'"
        info "Or create .env file with: POSTGRES_PASSWORD=your_password"
        deactivate 2>/dev/null || true
        return 1
    fi
    
    # Test write operation
    if python3 << 'PYTHON_EOF'
import psycopg2
import os
import sys
import uuid
from datetime import datetime

try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=int(os.environ.get('DB_PORT', 5432)),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        connect_timeout=5
    )
    
    cur = conn.cursor()
    
    # Create test table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_data_flow (
            id SERIAL PRIMARY KEY,
            test_id VARCHAR(255) UNIQUE NOT NULL,
            test_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert test data
    test_id = f"test_{uuid.uuid4().hex[:8]}"
    test_data = f"Data flow test at {datetime.now().isoformat()}"
    
    cur.execute(
        "INSERT INTO test_data_flow (test_id, test_data) VALUES (%s, %s)",
        (test_id, test_data)
    )
    
    conn.commit()
    
    # Verify write
    cur.execute("SELECT test_id, test_data FROM test_data_flow WHERE test_id = %s", (test_id,))
    result = cur.fetchone()
    
    if result and result[0] == test_id:
        print(f"SUCCESS: Test data written and verified (test_id: {test_id})")
        # Store test_id for cleanup
        with open('/tmp/test_data_flow_id', 'w') as f:
            f.write(test_id)
        sys.exit(0)
    else:
        print("FAILED: Test data not found after write")
        sys.exit(1)
        
except psycopg2.Error as e:
    print(f"Database error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
finally:
    if 'conn' in locals():
        conn.close()
PYTHON_EOF
    then
        export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD="$db_password"
        pass "Database write test (VM-01 → VM-02)"
    else
        fail "Database write test (VM-01 → VM-02)"
    fi
    
    deactivate 2>/dev/null || true
    echo ""
}

# Test database read (VM-02 → VM-03)
test_db_read() {
    echo "=========================================="
    echo "Database Read Test (VM-02 → VM-03)"
    echo "=========================================="
    
    local venv_path=$(find_venv)
    if [ -z "$venv_path" ]; then
        warn "Virtual environment not found, skipping database read test"
        return 1
    fi
    
    source "$venv_path/bin/activate"
    
    if ! python3 -c "import psycopg2" 2>/dev/null && ! python3 -c "import psycopg2_binary" 2>/dev/null; then
        warn "psycopg2 not available, skipping database read test"
        deactivate 2>/dev/null || true
        return 1
    fi
    
    local db_password="${POSTGRES_PASSWORD:-}"
    if [ -z "$db_password" ]; then
        warn "Database password not set (POSTGRES_PASSWORD), skipping read test"
        info "To enable database tests, set: export POSTGRES_PASSWORD='your_password'"
        deactivate 2>/dev/null || true
        return 1
    fi
    
    # Read test data
    if python3 << 'PYTHON_EOF'
import psycopg2
import os
import sys

try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=int(os.environ.get('DB_PORT', 5432)),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        connect_timeout=5
    )
    
    cur = conn.cursor()
    
    # Read latest test data
    cur.execute("""
        SELECT test_id, test_data, created_at 
        FROM test_data_flow 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    
    results = cur.fetchall()
    
    if results:
        print(f"SUCCESS: Read {len(results)} test records")
        for row in results:
            print(f"  - {row[0]}: {row[1][:50]}...")
        sys.exit(0)
    else:
        print("WARNING: No test data found (write test may not have run)")
        sys.exit(0)
        
except psycopg2.Error as e:
    print(f"Database error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
finally:
    if 'conn' in locals():
        conn.close()
PYTHON_EOF
    then
        export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD="$db_password"
        pass "Database read test (VM-02 → VM-03)"
    else
        fail "Database read test (VM-02 → VM-03)"
    fi
    
    deactivate 2>/dev/null || true
    echo ""
}

# Test n8n integration (VM-04 with other VMs)
test_n8n_integration() {
    echo "=========================================="
    echo "n8n Integration Test (VM-04)"
    echo "=========================================="
    
    # Test n8n HTTP endpoint
    if command -v curl &> /dev/null; then
        if curl -s -f -m 5 "http://${VM04_IP}:5678/healthz" &> /dev/null; then
            pass "n8n health endpoint accessible"
        else
            warn "n8n health endpoint not accessible (n8n may not be running)"
        fi
        
        # Test if n8n can be accessed (basic connectivity)
        if curl -s -f -m 5 "http://${VM04_IP}:5678" &> /dev/null; then
            pass "n8n web interface accessible"
        else
            warn "n8n web interface not accessible"
        fi
    else
        warn "curl not available, skipping n8n integration test"
    fi
    
    echo ""
}

# Cleanup test data
cleanup_test_data() {
    local venv_path=$(find_venv)
    if [ -z "$venv_path" ]; then
        return
    fi
    
    source "$venv_path/bin/activate"
    
    if ! python3 -c "import psycopg2" 2>/dev/null && ! python3 -c "import psycopg2_binary" 2>/dev/null; then
        deactivate 2>/dev/null || true
        return
    fi
    
    local db_password="${POSTGRES_PASSWORD:-}"
    if [ -z "$db_password" ]; then
        deactivate 2>/dev/null || true
        return
    fi
    
    python3 << 'PYTHON_EOF'
import psycopg2
import os

try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=int(os.environ.get('DB_PORT', 5432)),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        connect_timeout=5
    )
    
    cur = conn.cursor()
    
    # Delete test data older than 1 hour
    cur.execute("""
        DELETE FROM test_data_flow 
        WHERE created_at < NOW() - INTERVAL '1 hour'
    """)
    
    deleted = cur.rowcount
    conn.commit()
    
    if deleted > 0:
        print(f"Cleaned up {deleted} old test records")
    
    conn.close()
except Exception:
    pass
PYTHON_EOF
    
    deactivate 2>/dev/null || true
}

# Save results to JSON
save_results_to_json() {
    local output_file="$1"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local hostname=$(hostname)
    local date=$(date -Iseconds)
    
    mkdir -p "${PROJECT_ROOT}/test_results"
    
    local json_file="${PROJECT_ROOT}/test_results/${output_file}_${timestamp}.json"
    
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
    echo "Data Flow Tests"
    echo "=========================================="
    echo ""
    info "Current host: $(hostname)"
    info "Date: $(date)"
    echo ""
    
    load_config "$@"
    
    info "Database: $DB_HOST:$DB_PORT/$DB_NAME"
    echo ""
    
    # Run tests (continue even if one fails)
    test_db_write || true
    test_db_read || true
    test_n8n_integration || true
    
    # Cleanup
    info "Cleaning up test data..."
    cleanup_test_data
    
    echo "=========================================="
    echo "Data Flow Test Summary"
    echo "=========================================="
    echo -e "  ${GREEN}Passed:${NC} $test_passed"
    echo -e "  ${RED}Failed:${NC} $test_failed"
    echo -e "  ${YELLOW}Warnings:${NC} $test_warnings"
    echo "=========================================="
    echo ""
    
    # Save results
    save_results_to_json "data_flow"
    
    if [ $test_failed -eq 0 ]; then
        echo -e "${GREEN}✓ All data flow tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some data flow tests failed!${NC}"
        exit 1
    fi
}

main "$@"

