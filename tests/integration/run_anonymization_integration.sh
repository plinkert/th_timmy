#!/bin/bash
# Integration test for Deterministic Anonymization (Step 1.3).
# Runs unit tests for mapping_store, security, deterministic_anonymizer,
# then sanity: anonymize dict, deanonymize, verify roundtrip.
#
# Run from project root:
#   ./tests/integration/run_anonymization_integration.sh
# Or: PROJECT_ROOT=/path/to/th_timmy ./tests/integration/run_anonymization_integration.sh

set -e
set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="${PROJECT_ROOT:-${BOOTSTRAP_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}}"
RESULTS_DIR="${RESULTS_DIR:-$PROJECT_ROOT/results}"
RESULTS_FILE="$RESULTS_DIR/anonymization_integration_$(date +%Y%m%d_%H%M%S).txt"

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*"; }

mkdir -p "$RESULTS_DIR"
exec 1> >(tee -a "$RESULTS_FILE")
exec 2>&1

log_info "=== Deterministic Anonymization (Step 1.3) integration test ==="
log_info "PROJECT_ROOT=$PROJECT_ROOT"

RUN_PYTHON="$PROJECT_ROOT/hosts/vm04-orchestrator/run_python.sh"
FAILED=0

# Unit tests
if [ -x "$RUN_PYTHON" ] && [ -d "$PROJECT_ROOT/tests/unit" ]; then
  log_info "Running anonymization unit tests..."
  if BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -m pytest \
    tests/unit/test_mapping_store.py tests/unit/test_security.py tests/unit/test_deterministic_anonymizer.py \
    -v --tb=short -q 2>&1; then
    log_info "Anonymization unit tests passed."
  else
    log_err "Anonymization unit tests failed."
    FAILED=1
  fi
else
  log_warn "Unit tests skipped: run_python.sh not found or not executable."
  if [ ! -d "$PROJECT_ROOT/tests/unit" ]; then
    log_warn "tests/unit/ not found."
  fi
  FAILED=1
fi

# Sanity: create_anonymizer, anonymize dict, deanonymize
log_info "Sanity: create_anonymizer + anonymize_dict + deanonymize roundtrip..."
if [ -x "$RUN_PYTHON" ]; then
  TH_ANONYMIZATION_PASSPHRASE="integration_test_secret" BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" \
    "$RUN_PYTHON" -c "
import os
os.environ['TH_ANONYMIZATION_PASSPHRASE'] = 'integration_test_secret'
from automation_scripts.anonymization import create_anonymizer

anon = create_anonymizer()
data = {'username': 'hunter1', 'ip_address': '192.168.1.50', 'count': 10}
out = anon.anonymize_dict(data)
assert out['username'] != 'hunter1'
assert out['ip_address'] != '192.168.1.50'
assert out['count'] == 10
assert anon.deanonymize(out['username']) == 'hunter1'
assert anon.deanonymize(out['ip_address']) == '192.168.1.50'
print('Anonymize/deanonymize roundtrip OK')
" 2>&1 || { log_err "Anonymization sanity check failed"; FAILED=1; }
fi

log_info "=== End Anonymization integration test ==="
log_info "Results: $RESULTS_FILE"
exit $FAILED
