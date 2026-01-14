#!/usr/bin/env python3
"""
Entry point for dashboard API in Docker container.

This script sets up the Python path correctly and runs uvicorn
to avoid relative import issues.
"""

import sys
from pathlib import Path

# Add automation-scripts to Python path
app_dir = Path(__file__).parent.parent.parent / "automation-scripts"
sys.path.insert(0, str(app_dir.parent))  # Add /app to path
sys.path.insert(0, str(app_dir))  # Add /app/automation-scripts to path

# Now import and run
if __name__ == "__main__":
    import uvicorn
    from api.dashboard_api import app
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
