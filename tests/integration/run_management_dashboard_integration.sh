#!/bin/bash
# Integration test for Management Dashboard (Step 0.5).
# Tests dashboard API endpoints via TestClient: GET /status, POST sync-repo, backup-config, refresh.
# Verifies role-based access (403 for read_only on POST).
#
# Run instructions
# ----------------------------------------
# 1. Environment: run script on VM04 (orchestrator), from project directory th_timmy.
# 2. Before running:
#    - chmod +x hosts/vm04-orchestrator/run_python.sh
#    - pip install fastapi uvicorn (via bootstrap/requirements.txt)
# 3. From project root:
#      cd /path/to/th_timmy
#      chmod +x tests/integration/run_management_dashboard_integration.sh
#      ./tests/integration/run_management_dashboard_integration.sh
# 4. Results: exit 0 = success; log in results/management_dashboard_integration_YYYYMMDD_HHMMSS.txt
#
# Usage: run from project root or set PROJECT_ROOT/BOOTSTRAP_PROJECT_ROOT.

set -e
set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="${PROJECT_ROOT:-${BOOTSTRAP_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}}"
RESULTS_DIR="${RESULTS_DIR:-$PROJECT_ROOT/results}"
RESULTS_FILE="$RESULTS_DIR/management_dashboard_integration_$(date +%Y%m%d_%H%M%S).txt"

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*"; }

mkdir -p "$RESULTS_DIR"
exec 1> >(tee -a "$RESULTS_FILE")
exec 2>&1

log_info "=== Management Dashboard (Step 0.5) integration test ==="
log_info "PROJECT_ROOT=$PROJECT_ROOT"

RUN_PYTHON="$PROJECT_ROOT/hosts/vm04-orchestrator/run_python.sh"
FAILED=0

# Unit tests
if [ -x "$RUN_PYTHON" ] && [ -d "$PROJECT_ROOT/tests/unit" ]; then
  log_info "Running management dashboard unit tests..."
  if BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -m pytest \
    tests/unit/test_management_dashboard.py -v --tb=short -q 2>&1; then
    log_info "Management dashboard unit tests passed."
  else
    log_err "Management dashboard unit tests failed."
    FAILED=1
  fi
else
  log_warn "Unit tests skipped: run_python.sh not found or not executable."
  FAILED=1
fi

# Integration: TestClient against live app (requires config)
if [ -x "$RUN_PYTHON" ] && [ -f "$PROJECT_ROOT/configs/config.yml" ]; then
  log_info "Sanity: GET /api/v1/dashboard/status (with real config)..."
  BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -c "
from fastapi.testclient import TestClient
from automation_scripts.playbooks.hunt_api import app

client = TestClient(app)
r = client.get('/api/v1/dashboard/status')
assert r.status_code == 200, f'Expected 200, got {r.status_code}: {r.text}'
data = r.json()
assert 'vm01' in data and 'vm04' in data, f'Missing VM keys: {list(data.keys())}'
for vm_id in ['vm01','vm02','vm03','vm04']:
    assert 'status' in data[vm_id], f'Missing status for {vm_id}'
    assert 'color' in data[vm_id], f'Missing color for {vm_id}'
print('GET /api/v1/dashboard/status: OK')
" 2>&1 || { log_err "Dashboard status sanity failed"; FAILED=1; }
else
  if [ ! -f "$PROJECT_ROOT/configs/config.yml" ]; then
    log_warn "configs/config.yml not found - skipping status sanity (copy from config.example.yml)"
  fi
fi

# Verify workflow file exists
WORKFLOW_FILE="$PROJECT_ROOT/hosts/vm04-orchestrator/n8n/workflows/management-dashboard.json"
if [ -f "$WORKFLOW_FILE" ]; then
  log_info "Workflow file exists: $WORKFLOW_FILE"
else
  log_err "Workflow file not found: $WORKFLOW_FILE"
  FAILED=1
fi

log_info "=== End Management Dashboard integration test ==="
log_info "Results written to: $RESULTS_FILE"
exit $FAILED
