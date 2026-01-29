"""
Playbook structure and validation (Step 1.1).

Provides playbook_validator for metadata.yml validation (technique_description, data_sources)
and query_loader for loading query files from playbook queries/ directory.
"""

from .playbook_validator import validate_playbook, ValidationResult
from .query_loader import load_queries, QueryEntry, QueryLoadError

__all__ = [
    "validate_playbook",
    "ValidationResult",
    "load_queries",
    "QueryEntry",
    "QueryLoadError",
]
