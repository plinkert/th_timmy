#!/usr/bin/env python3
"""
Entry point for dashboard API in Docker container.

This script sets up the Python path correctly and runs uvicorn
to avoid relative import issues with 'api.dashboard_api'.

Problem: dashboard_api.py uses relative imports (from ..services)
which fail when imported as 'api.dashboard_api' because Python
treats 'api' as top-level package.

Solution: Set up sys.path BEFORE importing, so relative imports work.
"""

import sys
import os
from pathlib import Path

# Get /app directory (where run_dashboard_api.py is located)
app_root = Path(__file__).parent  # /app
automation_scripts_dir = app_root / "automation-scripts"  # /app/automation-scripts

# Add to Python path BEFORE any imports
# This ensures relative imports in dashboard_api.py work correctly
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
if str(automation_scripts_dir) not in sys.path:
    sys.path.insert(0, str(automation_scripts_dir))

# Set environment variables if not set
os.environ.setdefault('PYTHONPATH', f"{app_root}:{automation_scripts_dir}")
os.environ.setdefault('CONFIG_PATH', str(app_root / "configs" / "config.yml"))
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Now import and run - relative imports will work because sys.path is set up
if __name__ == "__main__":
    import uvicorn
    
    # Import dashboard_api - this will work because sys.path includes automation-scripts
    # Change to automation-scripts directory so 'api' package can be found
    original_cwd = os.getcwd()
    try:
        os.chdir(str(automation_scripts_dir))
        from api.dashboard_api import app
        
        # Run uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    finally:
        os.chdir(original_cwd)
