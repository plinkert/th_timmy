#!/bin/bash
# Integration test for n8n Hunt Selection (Step 1.4).
# Tests hunt_api service: POST /generate-queries, session storage.
# Run on VM04 (orchestrator). Ensures env is ready, runs hunt_api tests.
#
# Run instructions
# ----------------------------------------
# 1. Environment: run script on VM04 (orchestrator), from project directory th_timmy.
# 2. Before running:
#    - Make run_python.sh executable: chmod +x hosts/vm04-orchestrator/run_python.sh
#    - pip install fastapi uvicorn (via bootstrap/requirements.txt)
# 3. Z roota projektu:
#      cd /path/to/th_timmy
#      chmod +x tests/integration/run_n8n_hunt_selection_integration.sh
#      ./tests/integration/run_n8n_hunt_selection_integration.sh
# 4. Results: exit 0 = success, exit 1 = failure; log in results/n8n_hunt_selection_integration_YYYYMMDD_HHMMSS.txt
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
RESULTS_FILE="$RESULTS_DIR/n8n_hunt_selection_integration_$(date +%Y%m%d_%H%M%S).txt"

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*"; }

mkdir -p "$RESULTS_DIR"
exec 1> >(tee -a "$RESULTS_FILE")
exec 2>&1

log_info "=== n8n Hunt Selection (Step 1.4) integration test ==="
log_info "PROJECT_ROOT=$PROJECT_ROOT"
log_info "RESULTS_FILE=$RESULTS_FILE"

RUN_PYTHON="$PROJECT_ROOT/hosts/vm04-orchestrator/run_python.sh"
FAILED=0

# Test hunt_api logic (without starting server)
log_info "Testing hunt_api /generate-queries via TestClient..."
if [ -x "$RUN_PYTHON" ]; then
  BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -c "
from pathlib import Path
from fastapi.testclient import TestClient
from automation_scripts.playbooks.hunt_api import app

client = TestClient(app)
root = Path('$PROJECT_ROOT')

# POST /generate-queries
r = client.post('/generate-queries', json={
    'hunts': ['T1059', 'T1055'],
    'tools': ['elk', 'ms_defender'],
    'mode': 'manual',
})
assert r.status_code == 200, f'Expected 200, got {r.status_code}: {r.text}'
data = r.json()
assert 'session_id' in data, f'Missing session_id: {data}'
assert 'count' in data, f'Missing count: {data}'
assert 'paths' in data, f'Missing paths: {data}'
assert data['count'] >= 1, f'Expected at least 1 file, got {data[\"count\"]}'
assert len(data['paths']) == data['count'], 'paths length != count'
print(f'hunt_api /generate-queries: OK (session_id={data[\"session_id\"][:8]}..., count={data[\"count\"]})')

# Verify session file
sessions_dir = root / 'queries_generated' / 'sessions'
assert sessions_dir.is_dir(), f'Sessions dir not created: {sessions_dir}'
session_files = list(sessions_dir.glob('*.json'))
assert len(session_files) >= 1, f'No session files in {sessions_dir}'
print(f'Session storage: OK ({len(session_files)} session file(s))')

# Validation: empty hunts
r2 = client.post('/generate-queries', json={'hunts': [], 'tools': ['elk'], 'mode': 'manual'})
assert r2.status_code == 422 or r2.status_code == 400, f'Expected 400/422 for empty hunts, got {r2.status_code}'
print('Validation (empty hunts): OK')

# GET /health
r3 = client.get('/health')
assert r3.status_code == 200, f'Health check failed: {r3.status_code}'
print('GET /health: OK')

# GET /playbooks
r4 = client.get('/playbooks')
assert r4.status_code == 200, f'Playbooks failed: {r4.status_code}'
data4 = r4.json()
assert 'playbooks' in data4, f'Missing playbooks: {data4}'
assert len(data4['playbooks']) >= 5, f'Expected at least 5 playbooks, got {len(data4[\"playbooks\"])}'
print(f'GET /playbooks: OK ({len(data4[\"playbooks\"])} playbooks)')
" 2>&1 || { log_err "hunt_api test failed"; FAILED=1; }
else
  log_warn "run_python.sh not found or not executable - skipping hunt_api test"
  FAILED=1
fi

# Verify workflow file exists
WORKFLOW_FILE="$PROJECT_ROOT/hosts/vm04-orchestrator/n8n/workflows/hunt-selection-workflow.json"
if [ -f "$WORKFLOW_FILE" ]; then
  log_info "Workflow file exists: $WORKFLOW_FILE"
else
  log_err "Workflow file not found: $WORKFLOW_FILE"
  FAILED=1
fi

log_info "=== End n8n Hunt Selection integration test ==="
log_info "Results written to: $RESULTS_FILE"
exit $FAILED
