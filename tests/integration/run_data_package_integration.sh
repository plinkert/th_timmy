#!/bin/bash
# Integration test for Data Package (Step 1.5).
# Runs unit tests for DataPackage, sanity: create, validate, to_json, from_json.
#
# Run instructions
# ----------------------------------------
# 1. Environment: run script on VM04 (orchestrator) or any host with project.
# 2. From project root:
#      cd /path/to/th_timmy
#      chmod +x tests/integration/run_data_package_integration.sh
#      ./tests/integration/run_data_package_integration.sh
# 3. Results: exit 0 = success; log in results/data_package_integration_YYYYMMDD_HHMMSS.txt
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
RESULTS_FILE="$RESULTS_DIR/data_package_integration_$(date +%Y%m%d_%H%M%S).txt"

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*"; }

mkdir -p "$RESULTS_DIR"
exec 1> >(tee -a "$RESULTS_FILE")
exec 2>&1

log_info "=== Data Package (Step 1.5) integration test ==="
log_info "PROJECT_ROOT=$PROJECT_ROOT"

RUN_PYTHON="$PROJECT_ROOT/hosts/vm04-orchestrator/run_python.sh"
FAILED=0

# Unit tests
if [ -x "$RUN_PYTHON" ] && [ -d "$PROJECT_ROOT/tests/unit" ]; then
  log_info "Running DataPackage unit tests..."
  if BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -m pytest \
    tests/unit/test_data_package.py -v --tb=short -q 2>&1; then
    log_info "DataPackage unit tests passed."
  else
    log_err "DataPackage unit tests failed."
    FAILED=1
  fi
else
  log_warn "Unit tests skipped: run_python.sh not found or not executable."
  FAILED=1
fi

# Sanity: create, validate, to_json, from_json
log_info "Sanity: DataPackage create, validate, to_json, from_json..."
if [ -x "$RUN_PYTHON" ]; then
  BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -c "
from pathlib import Path
from automation_scripts.data_package import DataPackage, DataPackageValidationError

root = Path('$PROJECT_ROOT')
schema = root / 'configs' / 'schemas' / 'data_package_schema.json'
assert schema.is_file(), f'Schema not found: {schema}'

dp = DataPackage(
    id='int-test-001',
    source='elk',
    timestamp='2025-01-27T12:00:00Z',
    data=[{'event_id': '1', 'host': 'vm01'}, {'event_id': '2', 'host': 'vm02'}],
    anonymized=True,
    context={'playbook_id': 'T1059'},
)
dp.validate(schema_path=schema)
print('Validate: OK')

s = dp.to_json()
assert '\"id\": \"int-test-001\"' in s
dp2 = DataPackage.from_json(s, validate_on_load=True, schema_path=schema)
assert dp2.id == dp.id
assert len(dp2.data) == 2
print('to_json/from_json: OK')

# Invalid: data as string
try:
    DataPackage.from_dict({'id': 'x', 'source': 'y', 'timestamp': '2025-01-27T12:00:00Z', 'data': 'string', 'anonymized': True})
except DataPackageValidationError as e:
    print(f'from_dict data string: raises (expected): {type(e).__name__}')
print('All sanity checks OK')
" 2>&1 || { log_err "DataPackage sanity failed"; FAILED=1; }
fi

# Verify schema exists
SCHEMA_FILE="$PROJECT_ROOT/configs/schemas/data_package_schema.json"
if [ -f "$SCHEMA_FILE" ]; then
  log_info "Schema file exists: $SCHEMA_FILE"
else
  log_err "Schema file not found: $SCHEMA_FILE"
  FAILED=1
fi

log_info "=== End Data Package integration test ==="
log_info "Results written to: $RESULTS_FILE"
exit $FAILED
