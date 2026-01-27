#!/bin/bash
#
# run_python.sh – single entrypoint for running Python under project .venv
#
# Rule: n8n (and any automation) must never call "python" directly.
# Always call run_python.sh. This ensures .venv is correct before every run.
#
# Flow (idempotent):
#   1) Run bootstrap_env.sh (creates/verifies .venv, deps, self-test)
#   2) cd to PROJECT_ROOT
#   3) exec .venv/bin/python "$@"
#
# Usage:
#   ./run_python.sh -m pytest tests/unit/ -v
#   ./run_python.sh -c "from automation_scripts.orchestrators.remote_executor import execute_remote_command; print('ok')"
#   BOOTSTRAP_PROJECT_ROOT=/path/to/th_timmy ./run_python.sh -m pytest tests/unit/
#
# From n8n: configure "Execute Command" to run this script with desired args.
# Working directory of the node should be PROJECT_ROOT, or pass project root
# via BOOTSTRAP_PROJECT_ROOT when invoking.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Project root: BOOTSTRAP_PROJECT_ROOT, or PROJECT_ROOT, or two levels up from this script
if [ -n "${BOOTSTRAP_PROJECT_ROOT:-}" ]; then
    PROJECT_ROOT="$BOOTSTRAP_PROJECT_ROOT"
elif [ -n "${PROJECT_ROOT:-}" ]; then
    PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"
else
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

export BOOTSTRAP_PROJECT_ROOT="$PROJECT_ROOT"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# 1) Bootstrap on demand (idempotent: fast if env OK, repairs if broken)
"$SCRIPT_DIR/bootstrap_env.sh" || exit 1

# 2) Run Python from .venv; cwd = PROJECT_ROOT so "tests/unit/" etc. resolve
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT"
export PROJECT_ROOT="$PROJECT_ROOT"
exec "$VENV_PYTHON" "$@"
