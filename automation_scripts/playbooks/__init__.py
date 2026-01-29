"""
Playbook structure and validation (Step 1.1).

Provides playbook_validator for metadata.yml validation (technique_description, data_sources)
and query_loader for loading query files from playbook queries/ directory.
CLI helpers for browsing playbooks (list, show, get_queries_resolved).
"""

from .playbook_validator import validate_playbook, ValidationResult
from .query_loader import load_queries, QueryEntry, QueryLoadError
from .cli_helpers import (
    list_playbooks,
    show_playbook,
    get_queries_resolved,
    get_playbooks_dir,
    validate_playbook_cli,
)

__all__ = [
    "validate_playbook",
    "ValidationResult",
    "load_queries",
    "QueryEntry",
    "QueryLoadError",
    "list_playbooks",
    "show_playbook",
    "get_queries_resolved",
    "get_playbooks_dir",
    "validate_playbook_cli",
]
