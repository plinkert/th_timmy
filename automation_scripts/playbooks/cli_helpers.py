"""
CLI helpers for playbook browsing – list, show, load queries with placeholder resolution.

Usable from CLI (scripts/th_playbook.py) and from Jupyter Notebook.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union

import yaml

from .query_loader import QueryEntry, load_queries
from .playbook_validator import validate_playbook, ValidationResult


def _resolve_project_root(given: Optional[Union[str, Path]] = None) -> Path:
    """Resolve project root (th_timmy). Uses env vars or script location."""
    if given is not None:
        return Path(given).resolve()
    root = Path(__file__).resolve().parent.parent.parent
    return root


def get_playbooks_dir(project_root: Optional[Union[str, Path]] = None) -> Path:
    """Return path to playbooks directory."""
    root = _resolve_project_root(project_root)
    return root / "playbooks"


def list_playbooks(
    playbooks_dir: Optional[Union[str, Path]] = None,
    include_template: bool = False,
) -> List[dict]:
    """
    List available playbooks with summary info.

    Returns list of dicts: id, name, mitre_technique_id, mitre_technique_name, description.
    """
    pb_dir = Path(playbooks_dir) if playbooks_dir else get_playbooks_dir()
    if not pb_dir.is_dir():
        return []

    result: List[dict] = []
    for subdir in sorted(pb_dir.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name == "template" and not include_template:
            continue
        meta_path = subdir / "metadata.yml"
        if not meta_path.is_file():
            continue
        try:
            with open(meta_path) as f:
                meta = yaml.safe_load(f) or {}
        except Exception:
            meta = {}
        env_req = meta.get("environment_requirements") or {}
        tool_classes = env_req.get("tool_classes", []) if isinstance(env_req, dict) else []
        result.append(
            {
                "id": subdir.name,
                "name": meta.get("name", subdir.name),
                "mitre_technique_id": meta.get("mitre_technique_id", ""),
                "mitre_technique_name": meta.get("mitre_technique_name", ""),
                "description": (meta.get("description") or "")[:120],
                "tool_classes": tool_classes,
            }
        )
    return result


def show_playbook(
    playbook_id: str,
    playbooks_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Load and return full metadata for a playbook.

    Raises FileNotFoundError if playbook or metadata.yml not found.
    """
    pb_dir = Path(playbooks_dir) if playbooks_dir else get_playbooks_dir()
    playbook_path = pb_dir / playbook_id
    meta_path = playbook_path / "metadata.yml"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Playbook not found: {playbook_id}")
    with open(meta_path) as f:
        return yaml.safe_load(f) or {}


def get_queries_resolved(
    playbook_id: str,
    hours: int = 24,
    playbooks_dir: Optional[Union[str, Path]] = None,
    tool_class: Optional[str] = None,
) -> List[QueryEntry]:
    """
    Load queries. Optionally filter by tool_class (siem, edr, data_lake).
    Queries use relative time (ago(7d), now-7d) - no placeholder substitution needed.
    For legacy queries with {{timestamp_start}}/{{timestamp_end}}, substitutes timestamps.
    """
    pb_dir = Path(playbooks_dir) if playbooks_dir else get_playbooks_dir()
    playbook_path = pb_dir / playbook_id
    if not playbook_path.is_dir():
        raise FileNotFoundError(f"Playbook not found: {playbook_id}")

    entries = load_queries(playbook_path)

    if tool_class:
        entries = [e for e in entries if getattr(e, "tool_class", None) == tool_class]

    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    ts_start = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_end = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    resolved: List[QueryEntry] = []
    for e in entries:
        content = e.content.replace("{{timestamp_start}}", ts_start).replace(
            "{{timestamp_end}}", ts_end
        )
        resolved.append(
            QueryEntry(
                tool=e.tool,
                mode=e.mode,
                query_path=e.query_path,
                content=content,
                tool_class=getattr(e, "tool_class", None),
            )
        )
    return resolved


def validate_playbook_cli(
    playbook_id: Optional[str] = None,
    playbooks_dir: Optional[Union[str, Path]] = None,
) -> List[tuple[str, ValidationResult]]:
    """
    Validate playbook(s). If playbook_id given, validate only that one.

    Returns list of (playbook_id, ValidationResult).
    """
    pb_dir = Path(playbooks_dir) if playbooks_dir else get_playbooks_dir()
    if not pb_dir.is_dir():
        return []

    if playbook_id:
        path = pb_dir / playbook_id
        if path.is_dir():
            return [(playbook_id, validate_playbook(path))]
        return []

    results: List[tuple[str, ValidationResult]] = []
    for subdir in sorted(pb_dir.iterdir()):
        if subdir.is_dir() and (subdir / "metadata.yml").is_file():
            r = validate_playbook(subdir)
            results.append((subdir.name, r))
    return results
