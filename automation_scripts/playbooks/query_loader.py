"""
Query loader – loads query files from playbook queries/ directory.

Supports .sql, .json, .kql extensions and YAML format (elk.yml, ms_defender.yml).
YAML format: one file per tool, manual + api sections, reference by query_id.
Raises QueryLoadError on missing file.

Tool class mapping (tool_class → tool implementations):
  siem      → elk, splunk, ms_sentinel (SIEM products)
  edr       → ms_defender (EDR products)
  data_lake → elk (optional, large-scale analytics)
"""

from __future__ import annotations

import json
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
    tool_class: Optional[str] = None  # siem, edr, data_lake - analyst filters by this
    query_id: Optional[str] = None  # id in YAML manual/api section
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


def _is_yaml_query_path(query_path: str) -> bool:
    """Check if query_path points to YAML format file."""
    qp = query_path.lower()
    return qp.endswith(".yml") or qp.endswith(".yaml")


def _load_yaml_queries(
    playbook_dir: Path,
    query_path: str,
    tool: str,
    mode: str,
    query_ids: List[str],
    tool_class: Optional[str],
) -> List[QueryEntry]:
    """
    Load queries from YAML file. Returns list of QueryEntry for each query_id.
    """
    full_path = (playbook_dir / query_path).resolve()
    if not full_path.is_file():
        raise QueryLoadError(f"Query file not found: {full_path}")
    if not full_path.is_relative_to(playbook_dir):
        raise QueryLoadError(f"query_path escapes playbook dir: {query_path}")

    with open(full_path) as f:
        data = yaml.safe_load(f) or {}

    section = "manual" if mode.lower() == "manual" else "api"
    queries_section = data.get(section) or {}
    if not isinstance(queries_section, dict):
        raise QueryLoadError(f"Invalid YAML: {section} must be a dict in {query_path}")

    results: List[QueryEntry] = []
    for qid in query_ids:
        query_block = queries_section.get(qid)
        if not query_block or not isinstance(query_block, dict):
            raise QueryLoadError(f"query_id '{qid}' not found in {section} in {query_path}")

        # Determine content: elk manual=sql, elk api=body, ms_defender manual=kql, ms_defender api=body
        content = ""
        if tool == "elk":
            if mode.lower() == "manual":
                content = query_block.get("sql", "")
            else:
                body = query_block.get("body")
                content = json.dumps(body) if body is not None else ""
        elif tool == "ms_defender":
            if mode.lower() == "manual":
                content = query_block.get("kql", "")
            else:
                body = query_block.get("body")
                if isinstance(body, dict) and "Query" in body:
                    content = json.dumps(body)
                else:
                    content = json.dumps(body) if body is not None else ""
        else:
            # Generic: try sql, kql, body
            content = (
                query_block.get("sql")
                or query_block.get("kql")
                or (json.dumps(query_block.get("body")) if query_block.get("body") else "")
            )
            if not isinstance(content, str):
                content = json.dumps(content) if content else ""

        results.append(
            QueryEntry(
                tool=tool,
                mode=mode,
                query_path=query_path,
                content=content,
                tool_class=tool_class,
                query_id=qid,
            )
        )
        logger.info("Loaded query: tool=%s mode=%s path=%s query_id=%s", tool, mode, query_path, qid)

    return results


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

    Supports:
    - Legacy format: .sql, .kql, .json files (whole file as content)
    - YAML format: .yml/.yaml with query_id or query_ids (manual/api sections)
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
        tool_class = entry.get("tool_class")
        query_id = entry.get("query_id")
        query_ids = entry.get("query_ids")

        if not query_path:
            raise QueryLoadError("query_path is required in data_sources entry")

        full_path = (playbook_dir / query_path).resolve()
        if not full_path.is_relative_to(playbook_dir):
            raise QueryLoadError(f"query_path escapes playbook dir: {query_path}")

        try:
            if _is_yaml_query_path(query_path):
                ids: List[str] = []
                if query_ids:
                    raw = query_ids if isinstance(query_ids, list) else [query_ids]
                    ids = [str(q) for q in raw]
                elif query_id:
                    ids = [str(query_id)]
                else:
                    raise QueryLoadError(
                        f"query_id or query_ids required for YAML query_path: {query_path}"
                    )
                entries = _load_yaml_queries(
                    playbook_dir, query_path, tool, mode, ids, tool_class
                )
                results.extend(entries)
            else:
                content = _read_query_file(full_path)
                results.append(
                    QueryEntry(
                        tool=tool,
                        mode=mode,
                        query_path=query_path,
                        content=content,
                        tool_class=tool_class,
                    )
                )
                logger.info("Loaded query: tool=%s mode=%s path=%s", tool, mode, query_path)
        except QueryLoadError as e:
            logger.error("Query load failed: %s", e)
            raise

    return results
