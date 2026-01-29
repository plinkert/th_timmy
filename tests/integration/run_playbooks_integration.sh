#!/bin/bash
# Integration test for Playbook Structure (Step 1.1).
# Run on VM04 (orchestrator). Ensures env is ready, runs playbook unit tests,
# validates playbooks, loads queries. Results in results/.
#
# Run instructions
# ----------------------------------------
# 1. Środowisko: skrypt uruchamiać na VM04 (orchestrator), z katalogu projektu th_timmy.
# 2. Przed uruchomieniem:
#    - Skopiować config.example.yml → config.yml jeśli potrzeba.
#    - Ustawić run_python.sh jako wykonywalny: chmod +x hosts/vm04-orchestrator/run_python.sh
# 3. Z roota projektu:
#      cd /path/to/th_timmy
#      chmod +x tests/integration/run_playbooks_integration.sh
#      ./tests/integration/run_playbooks_integration.sh
#    Z innego katalogu:
#      PROJECT_ROOT=/path/to/th_timmy ./tests/integration/run_playbooks_integration.sh
# 4. Wyniki: exit 0 = sukces, exit 1 = błąd; log w results/playbooks_integration_YYYYMMDD_HHMMSS.txt
# 5. DEC: po przesłaniu skryptu na VM04 i uruchomieniu, skrypt wykonuje bootstrap (przez run_python.sh)
#    i testy; zależności są pobierane automatycznie. Wyniki w results/ pozwalają DEV na poprawki.
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
RESULTS_FILE="$RESULTS_DIR/playbooks_integration_$(date +%Y%m%d_%H%M%S).txt"

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*"; }

mkdir -p "$RESULTS_DIR"
exec 1> >(tee -a "$RESULTS_FILE")
exec 2>&1

log_info "=== Playbook Structure (Step 1.1) integration test ==="
log_info "PROJECT_ROOT=$PROJECT_ROOT"
log_info "RESULTS_FILE=$RESULTS_FILE"

if ! command -v python3 &>/dev/null; then
  log_err "python3 not found. Install: sudo apt-get install python3 python3-pip python3-venv"
  exit 1
fi
log_info "python3 version: $(python3 -c 'import sys; print(sys.version_info.major, sys.version_info.minor)')"

RUN_PYTHON="$PROJECT_ROOT/hosts/vm04-orchestrator/run_python.sh"
FAILED=0

# Unit tests
if [ -x "$RUN_PYTHON" ] && [ -d "$PROJECT_ROOT/tests/unit" ]; then
  log_info "Running playbook unit tests via run_python.sh..."
  if BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -m pytest \
    tests/unit/test_playbook_validator.py tests/unit/test_query_loader.py tests/unit/test_cli_helpers.py \
    -v --tb=short -q 2>&1; then
    log_info "Playbook unit tests passed."
  else
    log_err "Playbook unit tests failed."
    FAILED=1
  fi
else
  if [ ! -x "$RUN_PYTHON" ]; then
    log_warn "Unit tests skipped: run_python.sh not found or not executable."
  fi
  if [ ! -d "$PROJECT_ROOT/tests/unit" ]; then
    log_warn "Unit tests skipped: tests/unit/ not found."
  fi
  FAILED=1
fi

# Sanity: validate playbook_valid fixture
log_info "Sanity: validate playbook_valid fixture..."
if [ -x "$RUN_PYTHON" ]; then
  BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -c "
from pathlib import Path
from automation_scripts.playbooks import validate_playbook, load_queries

root = Path('$PROJECT_ROOT')
valid_dir = root / 'tests' / 'fixtures' / 'playbook_valid'
invalid_dir = root / 'tests' / 'fixtures' / 'playbook_invalid'

# playbook_valid should pass
r = validate_playbook(valid_dir)
assert r.success, f'playbook_valid failed: {r.errors}'
print('playbook_valid: validation OK')

# playbook_invalid should fail
r = validate_playbook(invalid_dir)
assert not r.success, 'playbook_invalid should fail validation'
print('playbook_invalid: correctly rejected')

# load_queries on playbook_valid
entries = load_queries(valid_dir)
assert len(entries) >= 1, f'Expected at least 1 query, got {len(entries)}'
print(f'load_queries: loaded {len(entries)} queries')

# tool_class filter: T1055 edr=3, siem=5 (YAML format with query_ids expands to multiple entries)
from automation_scripts.playbooks.cli_helpers import get_queries_resolved
edr = get_queries_resolved('T1055-process-injection', playbooks_dir=root/'playbooks', tool_class='edr')
siem = get_queries_resolved('T1055-process-injection', playbooks_dir=root/'playbooks', tool_class='siem')
assert len(edr) == 3, f'Expected 3 EDR queries, got {len(edr)}'
assert len(siem) == 5, f'Expected 5 SIEM queries, got {len(siem)}'
print('tool_class filter: edr=3, siem=4 OK')
" 2>&1 || { log_err "Playbook sanity check failed"; FAILED=1; }
fi

# Validate all 5 MITRE playbooks
log_info "Validating 5 MITRE ATT&CK playbooks..."
for pb in T1055-process-injection T1059-command-scripting-interpreter T1562-impair-defenses T1082-system-information-discovery T1486-data-encrypted-for-impact; do
  pb_dir="$PROJECT_ROOT/playbooks/$pb"
  if [ -d "$pb_dir" ]; then
    if BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -c "
from pathlib import Path
from automation_scripts.playbooks import validate_playbook, load_queries
root = Path('$PROJECT_ROOT')
r = validate_playbook(root / 'playbooks' / '$pb')
if not r.success:
    raise SystemExit(f'$pb validation failed: {r.errors}')
entries = load_queries(root / 'playbooks' / '$pb')
if len(entries) < 1:
    raise SystemExit(f'$pb: no queries loaded')
print('$pb: OK')
" 2>&1; then
      log_info "  $pb: OK"
    else
      log_err "  $pb: FAILED"
      FAILED=1
    fi
  else
    log_warn "  $pb: directory not found"
  fi
done

log_info "=== End Playbook Structure integration test ==="
log_info "Results written to: $RESULTS_FILE"
exit $FAILED
