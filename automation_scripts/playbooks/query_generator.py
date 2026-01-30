"""
Query generator – generates ready-to-use query files from playbooks.

Loads queries via query_loader, filters by tool and mode, optionally substitutes
placeholders ({{timestamp_start}}, {{timestamp_end}}, {{days}}), and saves to
queries_generated/.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional, Union

import yaml

from .query_loader import QueryEntry, QueryLoadError, load_queries
from .query_templates import (
    SUPPORTED_TOOLS,
    get_timestamp_substitutions,
    has_placeholders,
    substitute_placeholders,
)

logger = logging.getLogger(__name__)


class QueryGeneratorError(Exception):
    """Raised when query generation fails (invalid input, missing playbook, unsupported tool)."""

    pass


def _resolve_project_root(given: Optional[Union[str, Path]] = None) -> Path:
    """Resolve project root (th_timmy)."""
    if given is not None:
        return Path(given).resolve()
    root = Path(__file__).resolve().parent.parent.parent
    return root


def resolve_playbook_dir(
    hunt_id: str,
    playbooks_dir: Union[str, Path],
) -> Path:
    """
    Resolve hunt_id to playbook directory path.

    Args:
        hunt_id: Playbook ID (e.g. T1059, T1055 or T1059-command-scripting-interpreter)
        playbooks_dir: Base playbooks directory

    Returns:
        Path to playbook directory

    Raises:
        QueryGeneratorError: If no matching playbook found
    """
    pb_dir = Path(playbooks_dir).resolve()
    if not pb_dir.is_dir():
        raise QueryGeneratorError(f"Playbooks directory not found: {pb_dir}")

    direct = pb_dir / hunt_id
    if direct.is_dir():
        return direct

    hunt_prefix = hunt_id.rstrip("-")
    for subdir in pb_dir.iterdir():
        if subdir.is_dir() and subdir.name.startswith(hunt_prefix + "-"):
            return subdir

    raise QueryGeneratorError(f"Playbook not found for hunt_id: {hunt_id}")


def _sanitize_filename_part(s: str) -> str:
    """Sanitize string for use in filename (alphanumeric, underscore, hyphen)."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", str(s))


def _get_output_extension(tool: str, mode: str) -> str:
    """Return file extension for tool and mode."""
    mode_lower = mode.lower()
    if mode_lower == "api":
        return ".json"
    if tool == "elk":
        return ".sql"
    if tool == "ms_defender":
        return ".kql"
    return ".txt"


def generate_queries(
    hunt_list: List[str],
    tool_list: List[str],
    mode: str,
    output_dir: Optional[Union[str, Path]] = None,
    time_range_days: int = 7,
    playbooks_dir: Optional[Union[str, Path]] = None,
    project_root: Optional[Union[str, Path]] = None,
) -> List[Path]:
    """
    Generate ready-to-use query files for selected hunts and tools.

    Args:
        hunt_list: Playbook IDs (e.g. ["T1059", "T1055"] or ["T1059-command-scripting-interpreter"])
        tool_list: Tools to generate for (e.g. ["elk", "ms_defender"])
        mode: "manual" or "API"
        output_dir: Where to save files (default: PROJECT_ROOT/queries_generated)
        time_range_days: For timestamp substitution (default: 7)
        playbooks_dir: Base playbooks directory (default: PROJECT_ROOT/playbooks)
        project_root: Project root for path validation (default: auto-detect)

    Returns:
        List of paths to generated files.

    Raises:
        QueryGeneratorError: On invalid input, missing playbook, unsupported tool.
    """
    root = Path(project_root) if project_root else _resolve_project_root()
    root = root.resolve()
    out_dir = Path(output_dir) if output_dir else root / "queries_generated"
    pb_dir = Path(playbooks_dir) if playbooks_dir else root / "playbooks"

    if not hunt_list:
        raise QueryGeneratorError("hunt_list cannot be empty")
    if not tool_list:
        raise QueryGeneratorError("tool_list cannot be empty")
    mode_lower = mode.lower()
    if mode_lower not in ("manual", "api"):
        raise QueryGeneratorError(f"mode must be 'manual' or 'API', got: {mode}")

    unsupported = [t for t in tool_list if t not in SUPPORTED_TOOLS]
    if unsupported:
        raise QueryGeneratorError(f"Unsupported tools: {unsupported}. Supported: {SUPPORTED_TOOLS}")

    out_dir = out_dir.resolve()
    if not out_dir.is_relative_to(root):
        raise QueryGeneratorError(f"output_dir must be within project: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    generated: List[Path] = []
    for hunt_id in hunt_list:
        try:
            playbook_path = resolve_playbook_dir(hunt_id, pb_dir)
        except QueryGeneratorError as e:
            logger.error("Query generator: %s", e)
            raise

        try:
            entries = load_queries(playbook_path)
        except QueryLoadError as e:
            raise QueryGeneratorError(f"Failed to load queries for {hunt_id}: {e}") from e

        hunt_slug = _sanitize_filename_part(playbook_path.name)
        meta = {}
        meta_path = playbook_path / "metadata.yml"
        if meta_path.is_file():
            with open(meta_path) as f:
                meta = yaml.safe_load(f) or {}
        mitre_id = meta.get("mitre_technique_id", "")
        if mitre_id:
            hunt_slug = _sanitize_filename_part(mitre_id)

        filtered = [e for e in entries if e.tool in tool_list and e.mode.lower() == mode_lower]
        if not filtered:
            logger.warning("No queries for hunt=%s tool_list=%s mode=%s", hunt_id, tool_list, mode)

        for entry in filtered:
            content = entry.content
            if has_placeholders(content):
                try:
                    params = get_timestamp_substitutions(entry.tool, entry.mode, time_range_days)
                    content = substitute_placeholders(content, params)
                except ValueError as e:
                    logger.warning("Placeholder substitution skipped for %s: %s", entry.query_path, e)

            query_id = entry.query_id or _sanitize_filename_part(
                Path(entry.query_path).stem
            )
            ext = _get_output_extension(entry.tool, entry.mode)
            filename = f"{hunt_slug}_{entry.tool}_{mode_lower}_{query_id}{ext}"
            filepath = out_dir / filename
            filepath.write_text(content, encoding="utf-8")
            generated.append(filepath)
            logger.info("Generated: %s", filepath.name)

    return generated
