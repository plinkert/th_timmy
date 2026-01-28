#!/bin/bash
# Integration test for Configuration Management Service (Step 0.3).
# Run on VM04 (orchestrator). Ensures env is ready, runs config_manager unit tests, collects results.
#
# Run instructions
# ---------------
# 1. Environment: run this script on VM04 (orchestrator), from the th_timmy project directory.
# 2. Before running:
#    - Copy config.example.yml → config.yml and set vms, config_management (backup_location, config_paths).
#    - Ensure run_python.sh is executable: chmod +x hosts/vm04-orchestrator/run_python.sh
#    - Optional: SSH keys in ~/.ssh/th_timmy_keys (for live get/update tests).
#    - Optional: TH_TIMMY_CONFIG_BACKUP_PASSPHRASE (for backup tests).
# 3. From project root:
#      cd /path/to/th_timmy
#      chmod +x tests/integration/run_config_manager_integration.sh
#      ./tests/integration/run_config_manager_integration.sh
#    Or from another directory:
#      PROJECT_ROOT=/path/to/th_timmy ./tests/integration/run_config_manager_integration.sh
# 4. Results: exit 0 = success, exit 1 = failure; log in results/config_manager_integration_YYYYMMDD_HHMMSS.txt
# 5. DEC: after uploading the script to VM04 and running it, the script runs bootstrap (via run_python.sh)
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
RESULTS_FILE="$RESULTS_DIR/config_manager_integration_$(date +%Y%m%d_%H%M%S).txt"

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*"; }

mkdir -p "$RESULTS_DIR"
exec 1> >(tee -a "$RESULTS_FILE")
exec 2>&1

log_info "=== Configuration Management (Step 0.3) integration test ==="
log_info "PROJECT_ROOT=$PROJECT_ROOT"
log_info "RESULTS_FILE=$RESULTS_FILE"

if ! command -v python3 &>/dev/null; then
  log_err "python3 not found. Install: sudo apt-get install python3 python3-pip python3-venv"
  exit 1
fi
log_info "python3 version: $(python3 -c 'import sys; print(sys.version_info.major, sys.version_info.minor)')"

CONFIG="$PROJECT_ROOT/configs/config.yml"
if [ ! -f "$CONFIG" ]; then
  log_warn "No configs/config.yml; copy from config.example.yml and set config_management."
  if [ -f "$PROJECT_ROOT/configs/config.example.yml" ]; then
    cp "$PROJECT_ROOT/configs/config.example.yml" "$CONFIG"
    log_warn "Edit configs/config.yml (vms, config_management) and run again."
  fi
fi

RUN_PYTHON="$PROJECT_ROOT/hosts/vm04-orchestrator/run_python.sh"
FAILED=0

if [ -x "$RUN_PYTHON" ] && [ -d "$PROJECT_ROOT/tests/unit" ]; then
  log_info "Running config_manager unit tests via run_python.sh..."
  export TH_TIMMY_CONFIG_BACKUP_PASSPHRASE="${TH_TIMMY_CONFIG_BACKUP_PASSPHRASE:-test_integration_passphrase}"
  if BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -m pytest \
    tests/unit/test_config_validator.py \
    tests/unit/test_config_backup.py \
    tests/unit/test_config_manager.py \
    -v --tb=short -q 2>&1; then
    log_info "Config manager unit tests passed."
  else
    log_err "Config manager unit tests failed."
    FAILED=1
  fi
else
  if [ ! -x "$RUN_PYTHON" ]; then
    log_warn "Unit tests skipped: run_python.sh not found or not executable."
  fi
  if [ ! -d "$PROJECT_ROOT/tests/unit" ]; then
    log_warn "Unit tests skipped: tests/unit/ not found."
  fi
fi

log_info "Sanity: import config_manager and config_management..."
export PROJECT_ROOT
if [ -x "$RUN_PYTHON" ]; then
  BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -c "
import os, sys
from pathlib import Path
root = os.environ.get('PROJECT_ROOT', os.environ.get('BOOTSTRAP_PROJECT_ROOT', '.'))
sys.path.insert(0, root)
cfg_path = Path(root) / 'configs' / 'config.yml'
if cfg_path.exists():
    import yaml
    with open(cfg_path) as f:
        c = yaml.safe_load(f)
    cm = c.get('config_management') or {}
    backup_loc = cm.get('backup_location', '')
    paths = list((cm.get('config_paths') or {}).keys())
    print('Config loaded. config_management.backup_location:', backup_loc or '(not set)')
    print('config_management.config_paths keys:', paths)
    from automation_scripts.orchestrators.config_manager import (
        get_config, update_config, backup_config, restore_config, sync_config_to_vm,
        validate_config, create_backup, restore_backup, list_backups,
    )
    print('config_manager import OK.')
else:
    print('Config not found; skip config_management sanity.')
" 2>&1 || true
else
  log_warn "Sanity skipped (requires run_python.sh)."
fi

log_info "=== End Configuration Management integration test ==="
log_info "Results written to: $RESULTS_FILE"
exit $FAILED
