#!/bin/bash
# Integration test for Playbook Engine (Step 2.1).
# Runs unit tests for playbook_engine and sanity: DataPackage + run_analysis -> findings.
#
# Run from project root:
#   ./tests/integration/run_playbook_engine_integration.sh
# Or: PROJECT_ROOT=/path/to/th_timmy ./tests/integration/run_playbook_engine_integration.sh

set -e
set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="${PROJECT_ROOT:-${BOOTSTRAP_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}}"
RESULTS_DIR="${RESULTS_DIR:-$PROJECT_ROOT/results}"
RESULTS_FILE="$RESULTS_DIR/playbook_engine_integration_$(date +%Y%m%d_%H%M%S).txt"

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*"; }

mkdir -p "$RESULTS_DIR"
exec 1> >(tee -a "$RESULTS_FILE")
exec 2>&1

log_info "=== Playbook Engine (Step 2.1) integration test ==="
log_info "PROJECT_ROOT=$PROJECT_ROOT"

RUN_PYTHON="${RUN_PYTHON:-$PROJECT_ROOT/hosts/vm04-orchestrator/run_python.sh}"
FAILED=0

# Unit tests
if [ -x "$RUN_PYTHON" ] && [ -d "$PROJECT_ROOT/tests/unit" ]; then
  log_info "Running playbook_engine unit tests..."
  if BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -m pytest \
    tests/unit/test_playbook_engine.py -v --tb=short -q 2>&1; then
    log_info "Playbook engine unit tests passed."
  else
    log_err "Playbook engine unit tests failed."
    FAILED=1
  fi
else
  log_warn "Trying python3 -m pytest from project root..."
  if ( cd "$PROJECT_ROOT" && python3 -m pytest tests/unit/test_playbook_engine.py -v --tb=short -q 2>&1 ); then
    log_info "Playbook engine unit tests passed."
  else
    log_err "Playbook engine unit tests failed."
    FAILED=1
  fi
fi

# Sanity: DataPackage + run_analysis -> findings
log_info "Sanity: DataPackage + run_analysis..."
if [ -x "$RUN_PYTHON" ]; then
  BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -c "
from automation_scripts.data_package import DataPackage
from automation_scripts.playbooks.playbook_engine import run_analysis

dp = DataPackage(
    id='int-engine-001',
    source='elk',
    timestamp='2025-01-27T12:00:00Z',
    data=[
        {'@timestamp': '2025-01-27T12:00:00Z', 'source': {'ip': '10.0.0.1'}},
        {'@timestamp': '2025-01-27T12:01:00Z', 'source': {'ip': '10.0.0.1'}},
        {'@timestamp': '2025-01-27T12:02:00Z', 'source': {'ip': '10.0.0.1'}},
    ],
    anonymized=True,
    context={},
)
meta = {
    'mitre_technique_id': 'T1059',
    'analysis_rules': [{'type': 'threshold', 'threshold': 2, 'group_by': 'src_ip'}],
}
findings = run_analysis(dp, meta)
assert len(findings) == 1, f'Expected 1 finding, got {len(findings)}'
assert findings[0].evidence_ids == [0, 1, 2], f'Expected evidence_ids [0,1,2], got {findings[0].evidence_ids}'
assert findings[0].playbook_id == 'T1059'
print('run_analysis sanity: OK')
" 2>&1 || { log_err "Playbook engine sanity failed"; FAILED=1; }
else
  ( cd "$PROJECT_ROOT" && python3 -c "
from automation_scripts.data_package import DataPackage
from automation_scripts.playbooks.playbook_engine import run_analysis

dp = DataPackage(
    id='int-engine-001',
    source='elk',
    timestamp='2025-01-27T12:00:00Z',
    data=[
        {'@timestamp': '2025-01-27T12:00:00Z', 'source': {'ip': '10.0.0.1'}},
        {'@timestamp': '2025-01-27T12:01:00Z', 'source': {'ip': '10.0.0.1'}},
        {'@timestamp': '2025-01-27T12:02:00Z', 'source': {'ip': '10.0.0.1'}},
    ],
    anonymized=True,
    context={},
)
meta = {
    'mitre_technique_id': 'T1059',
    'analysis_rules': [{'type': 'threshold', 'threshold': 2, 'group_by': 'src_ip'}],
}
findings = run_analysis(dp, meta)
assert len(findings) == 1, f'Expected 1 finding, got {len(findings)}'
assert findings[0].evidence_ids == [0, 1, 2]
print('run_analysis sanity: OK')
" 2>&1 ) || { log_err "Playbook engine sanity failed"; FAILED=1; }
fi

log_info "=== End Playbook Engine integration test ==="
log_info "Results written to: $RESULTS_FILE"
exit $FAILED
