#!/bin/bash
# Integration test for Remote Execution Service (Step 0.1).
# Run on VM04 (orchestrator). Ensures env is ready, runs Python tests, collects results.
# Usage: copy this script to VM04, chmod +x, run from project root or set PROJECT_ROOT.
# Results: exit 0 = success, exit 1 = failure; stdout/stderr and results file for DEV.

set -e
set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="${PROJECT_ROOT:-${BOOTSTRAP_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}}"
RESULTS_DIR="${RESULTS_DIR:-$PROJECT_ROOT/results}"
RESULTS_FILE="$RESULTS_DIR/remote_executor_integration_$(date +%Y%m%d_%H%M%S).txt"

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERR]${NC} $*"; }

mkdir -p "$RESULTS_DIR"
exec 1> >(tee -a "$RESULTS_FILE")
exec 2>&1

log_info "=== Remote Executor integration test ==="
log_info "PROJECT_ROOT=$PROJECT_ROOT"
log_info "RESULTS_FILE=$RESULTS_FILE"

# 1) Prerequisites (run_python.sh runs bootstrap and supplies .venv + requirements)
if ! command -v python3 &>/dev/null; then
  log_err "python3 not found. Install: sudo apt-get install python3 python3-pip python3-venv"
  exit 1
fi
PY_VER=$(python3 -c "import sys; print(sys.version_info.major, sys.version_info.minor)")
log_info "python3 version: $PY_VER"

# 2) Config
CONFIG="$PROJECT_ROOT/configs/config.yml"
if [ ! -f "$CONFIG" ]; then
  log_warn "No configs/config.yml; using config.example.yml if present."
  if [ -f "$PROJECT_ROOT/configs/config.example.yml" ]; then
    cp "$PROJECT_ROOT/configs/config.example.yml" "$CONFIG"
    log_warn "Edit configs/config.yml with real VM IPs and run again."
  else
    log_err "No config file. Create configs/config.yml from config.example.yml."
    exit 1
  fi
fi

# 3) Keys (this phase: ~/.ssh/th_timmy_keys)
KEY_DIR="$HOME/.ssh/th_timmy_keys"
if [ ! -d "$KEY_DIR" ]; then
  log_warn "Key dir $KEY_DIR missing. Run hosts/vm04-orchestrator/setup_ssh_keys.sh first."
fi

# 4) Run unit tests – only via run_python.sh (bootstrap + .venv, same guarantee as n8n)
RUN_PYTHON="$PROJECT_ROOT/hosts/vm04-orchestrator/run_python.sh"
FAILED=0
if [ -x "$RUN_PYTHON" ] && [ -d "$PROJECT_ROOT/tests/unit" ]; then
  log_info "Running unit tests via run_python.sh (bootstrap + .venv)..."
  if BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT" "$RUN_PYTHON" -m pytest tests/unit/ -v --tb=short -q 2>&1; then
    log_info "Unit tests passed."
  else
    log_err "Unit tests failed."
    FAILED=1
  fi
else
  if [ ! -x "$RUN_PYTHON" ]; then
    log_warn "Unit tests skipped: run_python.sh not found or not executable."
    log_warn "  Run from full project root: ./hosts/vm04-orchestrator/run_python.sh -m pytest tests/unit/ -v"
  fi
  if [ ! -d "$PROJECT_ROOT/tests/unit" ]; then
    log_warn "Unit tests skipped: tests/unit/ not found."
  fi
fi

# 5) Sanity: import and config load (only via run_python.sh – same venv/requirements guarantee)
log_info "Sanity: import and config load..."
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
    vms = list((c.get('vms') or {}).keys())
    print('Config loaded. VMs in config:', vms)
else:
    print('Config not found; skip execution test.')
"
else
  log_warn "Sanity check skipped (requires run_python.sh)."
fi

log_info "=== End integration test ==="
log_info "Results written to: $RESULTS_FILE"
exit $FAILED
