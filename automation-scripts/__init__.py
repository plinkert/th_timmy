"""
Automation scripts for threat hunting lab.

This package provides services, utilities, and orchestrators for managing
the threat hunting lab infrastructure and executing threat hunting workflows.
"""

__version__ = "1.0.0"

# Make utils and orchestrators available as submodules
import sys
from pathlib import Path
import types

# Add this directory to path if not already there
_package_path = Path(__file__).parent
if str(_package_path) not in sys.path:
    sys.path.insert(0, str(_package_path))

# Create submodule references
if "automation_scripts.utils" not in sys.modules:
    utils_module = types.ModuleType("automation_scripts.utils")
    utils_module.__path__ = [str(_package_path / "utils")]
    sys.modules["automation_scripts.utils"] = utils_module
    # Make utils available as attribute
    import sys
    if "automation_scripts" in sys.modules:
        sys.modules["automation_scripts"].utils = utils_module

if "automation_scripts.orchestrators" not in sys.modules:
    orchestrators_module = types.ModuleType("automation_scripts.orchestrators")
    orchestrators_module.__path__ = [str(_package_path / "orchestrators")]
    sys.modules["automation_scripts.orchestrators"] = orchestrators_module
    # Make orchestrators available as attribute
    if "automation_scripts" in sys.modules:
        sys.modules["automation_scripts"].orchestrators = orchestrators_module

