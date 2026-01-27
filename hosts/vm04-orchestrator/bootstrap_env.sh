#!/bin/bash
#
# bootstrap_env.sh - Single official entrypoint for preparing the environment
#
# Used by: DEV, TEST, CI, AI agents.
# Rule: NO manual "pip install", NO manual "python -m venv" outside this script.
#
# Exit code: 0 = environment ready, !=0 = STOP (do not proceed).
# Output: Verbose, deterministic, unambiguous messages.
#
# Usage:
#   ./bootstrap_env.sh
#   cd /path/to/th_timmy/hosts/vm04-orchestrator && ./bootstrap_env.sh
#   BOOTSTRAP_PROJECT_ROOT=/path/to/th_timmy ./bootstrap_env.sh
#   ./bootstrap_env.sh /path/to/th_timmy
#

set -euo pipefail

# ------------------------------------------------------------------------------
# Paths (no hardcoded config - derive from script location or caller)
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Project root: env BOOTSTRAP_PROJECT_ROOT, or 1st arg, or two levels up from script
# (script lives in hosts/vm04-orchestrator/; project root is th_timmy/)
if [ -n "${BOOTSTRAP_PROJECT_ROOT:-}" ]; then
    PROJECT_ROOT="$BOOTSTRAP_PROJECT_ROOT"
elif [ -n "${1:-}" ]; then
    PROJECT_ROOT="$1"
else
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

VENV_DIR="$PROJECT_ROOT/.venv"
REQUIREMENTS_TXT="$PROJECT_ROOT/requirements.txt"
REQUIREMENTS_DEV_TXT="$PROJECT_ROOT/requirements-dev.txt"

# ------------------------------------------------------------------------------
# Output helpers (verbose, unambiguous)
# ------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

step()  { echo -e "${BLUE}[STEP]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

abort() {
    fail "$1"
    echo "BOOTSTRAP FAILED. Exit code: 1. Do not proceed."
    exit 1
}

# ------------------------------------------------------------------------------
# A. System verification
# ------------------------------------------------------------------------------
step "A. Verifying system prerequisites..."

# Python 3 >= 3.10
if ! command -v python3 &>/dev/null; then
    abort "Python 3 not found. Install python3 >= 3.10."
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ -z "$PYTHON_VERSION" ] || [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    abort "Python 3.10+ not found (got: $PYTHON_VERSION). Aborting."
fi
ok "python3 >= 3.10 ($PYTHON_VERSION)"

# pip
if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
    abort "pip not found. Install pip for Python 3."
fi
ok "pip available"

# venv (required for .venv creation)
if ! python3 -m venv --help &>/dev/null; then
    abort "python3 -m venv not available. Install python3-venv (e.g. apt install python3-venv)."
fi
ok "python3 -m venv available"

# openssh-client
if ! command -v ssh &>/dev/null; then
    abort "openssh-client not found. Install openssh-client."
fi
ok "openssh-client (ssh) available"

step "A. System verification complete."

# ------------------------------------------------------------------------------
# B. Create / validate virtualenv
# ------------------------------------------------------------------------------
step "B. Ensuring virtualenv at $VENV_DIR..."

validate_venv() {
    [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ] && [ -x "$VENV_DIR/bin/python" ]
}

if ! validate_venv; then
    if [ -d "$VENV_DIR" ]; then
        warn "Existing .venv is broken or incomplete. Removing."
        rm -rf "$VENV_DIR"
    fi
    step "Creating .venv..."
    python3 -m venv "$VENV_DIR" || abort "Failed to create venv at $VENV_DIR"
    ok ".venv created at $VENV_DIR"
else
    ok ".venv exists and looks valid"
fi

# Activate for rest of script
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
export VIRTUAL_ENV="$VENV_DIR"

step "B. Virtualenv ready."

# ------------------------------------------------------------------------------
# C. Install dependencies
# ------------------------------------------------------------------------------
step "C. Installing dependencies..."

if [ ! -f "$REQUIREMENTS_TXT" ]; then
    abort "requirements.txt not found at $REQUIREMENTS_TXT"
fi

step "C.1 Installing from requirements.txt..."
pip install -q --upgrade pip
pip install -r "$REQUIREMENTS_TXT" || abort "pip install -r requirements.txt failed."
ok "requirements.txt installed."

if [ -f "$REQUIREMENTS_DEV_TXT" ]; then
    step "C.2 Installing from requirements-dev.txt..."
    pip install -r "$REQUIREMENTS_DEV_TXT" || abort "pip install -r requirements-dev.txt failed."
    ok "requirements-dev.txt installed."
else
    warn "requirements-dev.txt not found at $REQUIREMENTS_DEV_TXT (skipping)."
fi

step "C. Dependencies installed."

# ------------------------------------------------------------------------------
# D. Environment validation (imports – critical)
# ------------------------------------------------------------------------------
step "D. Validating environment (import tests)..."

python3 << 'PYVALIDATE'
import sys
errors = []
for mod in ("paramiko", "pytest", "yaml", "requests"):
    try:
        __import__(mod)
    except ImportError as e:
        errors.append(f"  - import {mod}: {e}")
if errors:
    print("ENV VALIDATION FAILED:", file=sys.stderr)
    for msg in errors:
        print(msg, file=sys.stderr)
    sys.exit(1)
print("ENV VALIDATION OK")
PYVALIDATE
|| abort "Environment validation failed. One or more required imports (paramiko, pytest, yaml, requests) failed."

ok "All required imports (paramiko, pytest, yaml, requests) succeeded."
step "D. Environment validation complete."

# ------------------------------------------------------------------------------
# E. Sanity self-test
# ------------------------------------------------------------------------------
step "E. Sanity self-test..."

python3 - << 'PYEOF'
import paramiko
import sys
print("ENV OK")
PYEOF
|| abort "Sanity self-test failed."

ok "Sanity self-test passed."
step "E. Sanity self-test complete."

# ------------------------------------------------------------------------------
# Success
# ------------------------------------------------------------------------------
echo ""
ok "Environment bootstrap complete."
echo "  PROJECT_ROOT=$PROJECT_ROOT"
echo "  VENV_DIR=$VENV_DIR"
echo "  ACTIVATE: source $VENV_DIR/bin/activate"
echo ""
echo "BOOTSTRAP SUCCESS. Exit code: 0. Environment is ready."
exit 0
