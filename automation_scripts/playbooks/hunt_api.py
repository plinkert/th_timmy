"""
Hunt API – HTTP service for query generation (Step 1.4).

Provides POST /generate-queries endpoint for n8n workflow integration.
Accepts hunts, tools, mode; calls generate_queries; returns session_id and paths.
Session data stored in queries_generated/sessions/{session_id}.json.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .query_generator import QueryGeneratorError, generate_queries

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hunt API",
    description="Query generation and Management Dashboard API (Steps 1.4, 0.5)",
    version="1.0.0",
)

# Mount Management Dashboard routes (Step 0.5)
from automation_scripts.orchestrators.management_api import dashboard_router

app.include_router(dashboard_router)


def _resolve_project_root() -> Path:
    """Resolve project root (th_timmy)."""
    root = os.environ.get("BOOTSTRAP_PROJECT_ROOT") or os.environ.get("PROJECT_ROOT")
    if root:
        return Path(root).resolve()
    return Path(__file__).resolve().parent.parent.parent


class GenerateQueriesRequest(BaseModel):
    """Request body for POST /generate-queries."""

    hunts: List[str] = Field(..., min_length=1, description="Playbook IDs (e.g. T1059, T1055)")
    tools: List[str] = Field(..., min_length=1, description="Tools (elk, ms_defender)")
    mode: str = Field(default="manual", description="manual or API")
    time_range_days: int = Field(default=7, ge=1, le=365, description="Time range in days")


class GenerateQueriesResponse(BaseModel):
    """Response for POST /generate-queries."""

    session_id: str
    count: int
    paths: List[str]
    status: str = "success"


def _save_session(session_id: str, hunts: List[str], tools: List[str], mode: str, paths: List[str]) -> Path:
    """Save session data to queries_generated/sessions/{session_id}.json."""
    root = _resolve_project_root()
    sessions_dir = root / "queries_generated" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / f"{session_id}.json"
    data = {
        "session_id": session_id,
        "hunts": hunts,
        "tools": tools,
        "mode": mode,
        "paths": paths,
        "count": len(paths),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    session_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Session saved: %s (%d files)", session_id, len(paths))
    return session_file


@app.post("/generate-queries", response_model=GenerateQueriesResponse)
def generate_queries_endpoint(req: GenerateQueriesRequest) -> GenerateQueriesResponse:
    """
    Generate ready-to-use query files for selected hunts and tools.

    Returns session_id, count, and list of generated file paths.
    """
    root = _resolve_project_root()
    try:
        paths = generate_queries(
            hunt_list=req.hunts,
            tool_list=req.tools,
            mode=req.mode,
            time_range_days=req.time_range_days,
            project_root=root,
        )
    except QueryGeneratorError as e:
        logger.warning("Generate queries failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e

    session_id = str(uuid.uuid4())
    path_strs = [str(p) for p in paths]
    _save_session(session_id, req.hunts, req.tools, req.mode, path_strs)

    return GenerateQueriesResponse(
        session_id=session_id,
        count=len(paths),
        paths=path_strs,
    )


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "hunt_api"}


@app.get("/playbooks")
def list_playbooks_endpoint() -> dict:
    """List available playbooks (for dynamic form options)."""
    from .cli_helpers import list_playbooks

    root = _resolve_project_root()
    playbooks_dir = root / "playbooks"
    items = list_playbooks(playbooks_dir=playbooks_dir, include_template=False)
    return {
        "playbooks": [
            {"id": p["id"], "name": p["name"], "mitre_technique_id": p.get("mitre_technique_id", "")}
            for p in items
        ]
}
