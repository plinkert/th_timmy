#!/bin/bash
# test_before_after_hardening.sh - Test before and after hardening
# Usage: ./test_before_after_hardening.sh [config_file]
# This script runs tests before hardening, waits for user to apply hardening,
# then runs tests after hardening and compares results.

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
CYAN='\033[0;36m'
NC='\033[0m'

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

section() {
    echo ""
    echo -e "${CYAN}==========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}==========================================${NC}"
    echo ""
}

# Run test script and capture output
run_test() {
    local test_script="$1"
    local output_prefix="$2"
    
    if [ ! -f "$test_script" ]; then
        error "Test script not found: $test_script"
        return 1
    fi
    
    info "Running: $test_script"
    
    # Run test and capture exit code
    if bash "$test_script" "$CONFIG_FILE" > "/tmp/${output_prefix}_output.txt" 2>&1; then
        success "Test completed: $test_script"
        return 0
    else
        local exit_code=$?
        warn "Test completed with exit code $exit_code: $test_script"
        return $exit_code
    fi
}

# Find latest JSON result file
find_latest_result() {
    local pattern="$1"
    ls -t "${PROJECT_ROOT}/test_results/${pattern}"*.json 2>/dev/null | head -1
}

# Compare JSON results
compare_results() {
    local before_file="$1"
    local after_file="$2"
    local test_type="$3"
    
    if [ ! -f "$before_file" ] || [ ! -f "$after_file" ]; then
        warn "Cannot compare $test_type: missing result files"
        return 1
    fi
    
    section "Comparison: $test_type - Before vs After Hardening"
    
    if command -v python3 &> /dev/null && python3 -c "import json" 2>/dev/null; then
        python3 << PYTHON_EOF
import json
import sys

try:
    with open('$before_file', 'r') as f:
        before = json.load(f)
    with open('$after_file', 'r') as f:
        after = json.load(f)
    
    print("Summary:")
    print(f"  Passed: {before['summary']['passed']} → {after['summary']['passed']}")
    print(f"  Failed: {before['summary']['failed']} → {after['summary']['failed']}")
    print(f"  Warnings: {before['summary']['warnings']} → {after['summary']['warnings']}")
    
    # Compare individual tests
    before_tests = {t['name']: t['status'] for t in before.get('tests', [])}
    after_tests = {t['name']: t['status'] for t in after.get('tests', [])}
    
    print("\nTest status changes:")
    all_tests = set(before_tests.keys()) | set(after_tests.keys())
    changes = []
    for test_name in sorted(all_tests):
        before_status = before_tests.get(test_name, 'N/A')
        after_status = after_tests.get(test_name, 'N/A')
        if before_status != after_status:
            changes.append((test_name, before_status, after_status))
            print(f"  {test_name}: {before_status} → {after_status}")
    
    if not changes:
        print("  No changes detected - all tests have same status")
    
except Exception as e:
    print(f"Error comparing results: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF
    else
        warn "Python not available, showing file diff instead"
        diff "$before_file" "$after_file" || true
    fi
}

main() {
    section "Before/After Hardening Test Suite"
    
    info "Current host: $(hostname)"
    info "Date: $(date)"
    echo ""
    
    # Load config
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
        error "config.yml not found"
        echo "Usage: $0 [path/to/config.yml]"
        exit 1
    fi
    
    CONFIG_FILE="$config_file"
    info "Using config file: $CONFIG_FILE"
    echo ""
    
    # Create test results directory
    mkdir -p "${PROJECT_ROOT}/test_results"
    
    # ============================================
    # PHASE 1: Run tests BEFORE hardening
    # ============================================
    section "Phase 1: Running Tests BEFORE Hardening"
    
    info "Running connection tests..."
    run_test "${SCRIPT_DIR}/test_connections.sh" "before_connections"
    
    info "Running data flow tests..."
    run_test "${SCRIPT_DIR}/test_data_flow.sh" "before_data_flow"
    
    # Find and rename result files
    local before_connections_file=$(find_latest_result "connections_")
    local before_data_flow_file=$(find_latest_result "data_flow_")
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    
    if [ -n "$before_connections_file" ]; then
        mv "$before_connections_file" "${PROJECT_ROOT}/test_results/before_hardening_connections_${timestamp}.json" 2>/dev/null || true
        before_connections_file="${PROJECT_ROOT}/test_results/before_hardening_connections_${timestamp}.json"
    fi
    
    if [ -n "$before_data_flow_file" ]; then
        mv "$before_data_flow_file" "${PROJECT_ROOT}/test_results/before_hardening_data_flow_${timestamp}.json" 2>/dev/null || true
        before_data_flow_file="${PROJECT_ROOT}/test_results/before_hardening_data_flow_${timestamp}.json"
    fi
    
    success "Before hardening tests completed"
    echo ""
    info "Results saved:"
    [ -n "$before_connections_file" ] && info "  - $before_connections_file"
    [ -n "$before_data_flow_file" ] && info "  - $before_data_flow_file"
    echo ""
    
    # ============================================
    # PHASE 2: Wait for user to apply hardening
    # ============================================
    section "Phase 2: Apply Hardening"
    
    echo -e "${YELLOW}Please apply hardening on all VMs now.${NC}"
    echo ""
    echo "After hardening is complete, press Enter to continue with post-hardening tests..."
    read -r
    
    # ============================================
    # PHASE 3: Run tests AFTER hardening
    # ============================================
    section "Phase 3: Running Tests AFTER Hardening"
    
    info "Running connection tests..."
    run_test "${SCRIPT_DIR}/test_connections.sh" "after_connections"
    
    info "Running data flow tests..."
    run_test "${SCRIPT_DIR}/test_data_flow.sh" "after_data_flow"
    
    # Find and rename result files
    local after_connections_file=$(find_latest_result "connections_")
    local after_data_flow_file=$(find_latest_result "data_flow_")
    
    timestamp=$(date +"%Y%m%d_%H%M%S")
    
    if [ -n "$after_connections_file" ]; then
        mv "$after_connections_file" "${PROJECT_ROOT}/test_results/after_hardening_connections_${timestamp}.json" 2>/dev/null || true
        after_connections_file="${PROJECT_ROOT}/test_results/after_hardening_connections_${timestamp}.json"
    fi
    
    if [ -n "$after_data_flow_file" ]; then
        mv "$after_data_flow_file" "${PROJECT_ROOT}/test_results/after_hardening_data_flow_${timestamp}.json" 2>/dev/null || true
        after_data_flow_file="${PROJECT_ROOT}/test_results/after_hardening_data_flow_${timestamp}.json"
    fi
    
    success "After hardening tests completed"
    echo ""
    info "Results saved:"
    [ -n "$after_connections_file" ] && info "  - $after_connections_file"
    [ -n "$after_data_flow_file" ] && info "  - $after_data_flow_file"
    echo ""
    
    # ============================================
    # PHASE 4: Compare results
    # ============================================
    if [ -n "$before_connections_file" ] && [ -n "$after_connections_file" ]; then
        compare_results "$before_connections_file" "$after_connections_file" "Connection Tests"
    fi
    
    if [ -n "$before_data_flow_file" ] && [ -n "$after_data_flow_file" ]; then
        compare_results "$before_data_flow_file" "$after_data_flow_file" "Data Flow Tests"
    fi
    
    section "Test Suite Complete"
    success "All tests completed. Review the comparison results above."
    echo ""
}

# Run main function
main "$@"
