"""
Playbook structure and validation (Step 1.1), Query Generator (Step 1.2), Playbook Engine (Step 2.1).

Provides playbook_validator for metadata.yml validation (technique_description, data_sources),
query_loader for loading query files from playbook queries/ directory,
query_generator for generating ready-to-use query files,
cli_helpers for browsing playbooks,
and playbook_engine for deterministic analysis (run_analysis, Finding).
"""

from .playbook_validator import validate_playbook, ValidationResult
from .playbook_engine import Finding, run_analysis
from .query_loader import load_queries, QueryEntry, QueryLoadError
from .query_generator import generate_queries, resolve_playbook_dir, QueryGeneratorError
from .query_templates import (
    SUPPORTED_TOOLS,
    get_timestamp_substitutions,
    substitute_placeholders,
)
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
    "generate_queries",
    "resolve_playbook_dir",
    "QueryGeneratorError",
    "SUPPORTED_TOOLS",
    "get_timestamp_substitutions",
    "substitute_placeholders",
    "list_playbooks",
    "show_playbook",
    "get_queries_resolved",
    "get_playbooks_dir",
    "validate_playbook_cli",
    "Finding",
    "run_analysis",
]
