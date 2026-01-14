#!/usr/bin/env python3
"""
Entry point for dashboard API in Docker container.

This script creates a Python package structure that allows relative imports
to work correctly by creating automation_scripts as an importable package.
"""

import sys
import os
from pathlib import Path
import importlib.util

# Get /app directory (where run_dashboard_api.py is located)
app_root = Path(__file__).parent  # /app
automation_scripts_dir = app_root / "automation-scripts"  # /app/automation-scripts

# Add /app to Python path so we can import automation_scripts
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))

# Create automation_scripts as an importable package by creating a symlink
# Python cannot import directories with hyphens, so we need to make it importable
# We'll use importlib to load the module directly
automation_scripts_path = automation_scripts_dir / "__init__.py"
if not automation_scripts_path.exists():
    # Create empty __init__.py if it doesn't exist (it should, but just in case)
    automation_scripts_path.touch()

# Set environment variables
os.environ.setdefault('PYTHONPATH', str(app_root))
os.environ.setdefault('CONFIG_PATH', str(app_root / "configs" / "config.yml"))
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Now import and run using importlib to handle the hyphenated directory name
if __name__ == "__main__":
    import uvicorn
    
    # Load dashboard_api module using importlib to handle automation-scripts (with hyphen)
    # We need to manually construct the module path
    dashboard_api_path = automation_scripts_dir / "api" / "dashboard_api.py"
    
    # Use importlib to load the module
    spec = importlib.util.spec_from_file_location(
        "api.dashboard_api",
        dashboard_api_path,
        submodule_search_locations=[str(automation_scripts_dir)]
    )
    
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {dashboard_api_path}")
    
    # Create a mock package structure for relative imports
    # Add automation-scripts to sys.path so relative imports work
    if str(automation_scripts_dir) not in sys.path:
        sys.path.insert(0, str(automation_scripts_dir))
    
    # Change to automation-scripts directory
    original_cwd = os.getcwd()
    try:
        os.chdir(str(automation_scripts_dir))
        
        # Now import the module - relative imports should work
        module = importlib.util.module_from_spec(spec)
        sys.modules['api.dashboard_api'] = module
        spec.loader.exec_module(module)
        
        # Get the app from the module
        app = module.app
        
        # Run uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    finally:
        os.chdir(original_cwd)
