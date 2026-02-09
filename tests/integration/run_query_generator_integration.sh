#!/bin/bash
# Integration test for Query Generator (Step 1.2).
# Run on VM04 (orchestrator). Ensures env is ready, runs query_generator unit tests,
# generates queries from 3 playbooks (T1059, T1055, T1562), 2 tools (elk, ms_defender),
# mode manual. Verifies files in queries_generated/.
#
# Run instructions
# ----------------------------------------
# 1. Environment: run script on VM04 (orchestrator), from project directory th_timmy.
# 2. Before running:
#    - Copy config.example.yml → config.yml if needed.
#    - Make run_python.sh executable: chmod +x hosts/vm04-orchestrator/run_python.sh
# 3. Z roota projektu:
#      cd /path/to/th_timmy
#      chmod +x tests/integration/run_query_generator_integration.sh
#      ./tests/integration/run_query_generator_integration.sh
#    Z innego katalogu:
#      PROJECT_ROOT=/path/to/th_timmy ./tests/integration/run_query_generator_integration.sh
# 4. Results: exit 0 = success, exit 1 = failure; log in results/query_generator_integration_YYYYMMDD_HHMMSS.txt
# 5. DEC: after uploading script to VM04 and running, script performs bootstrap (via run_python.sh)
#    and tests; dependencies are fetched automatically. Results in results/ allow DEV to apply fixes.
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
RESULTS_FILE="$RESULTS_DIR/query_generator_integration_$(date +%Y%m%d_%H%M%S).txt"

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*"; }

mkdir -p "$RESULTS_DIR"
exec 1> >(tee -a "$RESULTS_FILE")
exec 2>&1

log_info "=== Query Generator (Step 1.2) integration test ==="
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
  log_info "Running query_generator unit tests via run_python.sh..."
  if BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -m pytest \
    tests/unit/test_query_templates.py tests/unit/test_query_generator.py \
    -v --tb=short -q 2>&1; then
    log_info "Query generator unit tests passed."
  else
    log_err "Query generator unit tests failed."
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

# Sanity: generate_queries with 3 playbooks, 2 tools, mode manual
log_info "Sanity: generate_queries with T1059, T1055, T1562, elk+ms_defender, manual..."
if [ -x "$RUN_PYTHON" ]; then
  BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -c "
from pathlib import Path
from automation_scripts.playbooks import generate_queries

root = Path('$PROJECT_ROOT')
playbooks_dir = root / 'playbooks'
out_dir = root / 'queries_generated'

# Generate queries for 3 playbooks, 2 tools, manual mode
paths = generate_queries(
    hunt_list=['T1059', 'T1055', 'T1562'],
    tool_list=['elk', 'ms_defender'],
    mode='manual',
    output_dir=out_dir,
    playbooks_dir=playbooks_dir,
    project_root=root,
)
assert len(paths) >= 1, f'Expected at least 1 generated file, got {len(paths)}'
print(f'generate_queries: {len(paths)} files generated')

# Verify no placeholders in output
for p in paths:
    content = p.read_text()
    assert '{{' not in content, f'File {p} contains placeholders'
print('All generated files: no placeholders')

# Verify files exist in queries_generated/
assert out_dir.is_dir(), f'Output dir not created: {out_dir}'
files = list(out_dir.glob('*'))
assert len(files) >= len(paths), f'Expected {len(paths)} files, found {len(files)}'
print(f'queries_generated/: {len(files)} files OK')
" 2>&1 || { log_err "Query generator sanity check failed"; FAILED=1; }
fi

log_info "=== End Query Generator integration test ==="
log_info "Results written to: $RESULTS_FILE"
exit $FAILED
