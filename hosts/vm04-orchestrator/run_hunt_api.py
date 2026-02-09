#!/usr/bin/env python3
"""
Run Hunt API (Step 1.4) – HTTP service for query generation.

Usage:
  From project root:
    ./hosts/vm04-orchestrator/run_hunt_api.py
  Or with run_python:
    ./hosts/vm04-orchestrator/run_python.sh -c "
      import uvicorn
      from automation_scripts.playbooks.hunt_api import app
      uvicorn.run(app, host='0.0.0.0', port=8000)
    "

When run on host, n8n in Docker calls http://host.docker.internal:8000
When hunt_api runs in Docker (docker-compose), n8n calls http://hunt_api:8000
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root on PYTHONPATH
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
os.environ.setdefault("PROJECT_ROOT", str(root))

if __name__ == "__main__":
    import uvicorn
    from automation_scripts.playbooks.hunt_api import app
    uvicorn.run(app, host="0.0.0.0", port=8000)
