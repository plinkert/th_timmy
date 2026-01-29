"""
Query loader – loads query files from playbook queries/ directory.

Supports .sql, .json, .kql extensions. Logs which queries are loaded for which tool/mode.
Raises QueryLoadError on missing file.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)


class QueryLoadError(Exception):
    """Raised when a query file cannot be loaded (e.g. missing file)."""

    pass


@dataclass
class QueryEntry:
    """Single query entry from data_sources."""

    tool: str
    mode: str
    query_path: str
    content: str
    error: Optional[str] = None


def _load_metadata(playbook_dir: Path) -> dict:
    """Load metadata.yml from playbook directory."""
    path = playbook_dir / "metadata.yml"
    if not path.is_file():
        raise QueryLoadError(f"metadata.yml not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _read_query_file(file_path: Path) -> str:
    """Read query file content as string. Handles .sql, .json, .kql."""
    if not file_path.is_file():
        raise QueryLoadError(f"Query file not found: {file_path}")
    with open(file_path) as f:
        return f.read()


def load_queries(
    playbook_dir: Union[str, Path],
    metadata: Optional[Dict] = None,
) -> List[QueryEntry]:
    """
    Load query files from playbook directory based on data_sources.

    If metadata is None, loads metadata.yml from playbook_dir. For each entry in
    data_sources, loads the file at playbook_dir/query_path. Returns list of
    QueryEntry (tool, mode, query_path, content). Raises QueryLoadError on
    missing file.
    """
    playbook_dir = Path(playbook_dir).resolve()
    if metadata is None:
        metadata = _load_metadata(playbook_dir)

    data_sources = metadata.get("data_sources") or []
    if not data_sources:
        raise QueryLoadError("data_sources is empty or missing in metadata")

    results: List[QueryEntry] = []
    for entry in data_sources:
        tool = entry.get("tool", "")
        mode = entry.get("mode", "")
        query_path = entry.get("query_path", "")
        if not query_path:
            raise QueryLoadError("query_path is required in data_sources entry")

        full_path = (playbook_dir / query_path).resolve()
        if not full_path.is_relative_to(playbook_dir):
            raise QueryLoadError(f"query_path escapes playbook dir: {query_path}")

        try:
            content = _read_query_file(full_path)
            results.append(
                QueryEntry(tool=tool, mode=mode, query_path=query_path, content=content)
            )
            logger.info("Loaded query: tool=%s mode=%s path=%s", tool, mode, query_path)
        except QueryLoadError as e:
            logger.error("Query load failed: %s", e)
            raise

    return results
