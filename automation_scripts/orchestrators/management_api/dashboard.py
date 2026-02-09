"""
Dashboard API – status cards, sync repo, backup config (Step 0.5).

Integrates with health_monitor, repo_sync, config_manager.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

# Status → color mapping per spec
STATUS_COLORS = {
    "healthy": "green",
    "warning": "orange",
    "critical": "red",
    "unreachable": "red",
    "degraded": "red",
    "unknown": "gray",
}

VALID_VM_IDS = {"vm01", "vm02", "vm03", "vm04"}
ADMIN_ACTIONS = {"sync-repo", "backup-config"}
HUNTER_OR_ADMIN_ACTIONS = {"refresh"}


def _resolve_project_root() -> Path:
    root = os.environ.get("BOOTSTRAP_PROJECT_ROOT") or os.environ.get("PROJECT_ROOT")
    if root:
        return Path(root).resolve()
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_role_from_header(x_user_role: Optional[str] = Header(None, alias="X-User-Role")) -> str:
    """Get user role from X-User-Role header. Default: read_only."""
    if not x_user_role:
        return "read_only"
    r = (x_user_role or "").strip().lower()
    if r in ("admin", "hunter", "read_only"):
        return r
    return "read_only"


def _check_api_key(request: Request) -> bool:
    """Validate API key if TH_DASHBOARD_API_KEY is set. Returns True if allowed."""
    api_key = os.environ.get("TH_DASHBOARD_API_KEY")
    if not api_key:
        return True  # No key configured = allow (dev mode)
    provided = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    return provided == api_key


def _require_role(role: str, required: str) -> None:
    if required == "admin" and role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    if required == "admin_or_hunter" and role not in ("admin", "hunter"):
        raise HTTPException(status_code=403, detail="Admin or hunter role required")


@router.get("/status")
def get_dashboard_status(
    refresh: bool = False,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    """
    Return status of all VMs (vm01–vm04) with colors for UI cards.
    healthy→green, warning→orange, critical/unreachable/degraded→red.
    """
    root = _resolve_project_root()
    config_path = root / "configs" / "config.yml"
    if not config_path.is_file():
        return {
            "vm01": {"status": "unknown", "color": "gray", "message": "Config not found", "metrics": None},
            "vm02": {"status": "unknown", "color": "gray", "message": "Config not found", "metrics": None},
            "vm03": {"status": "unknown", "color": "gray", "message": "Config not found", "metrics": None},
            "vm04": {"status": "unknown", "color": "gray", "message": "Config not found", "metrics": None},
        }

    try:
        from automation_scripts.orchestrators.health_monitor import get_health_status

        statuses = get_health_status(
            config_path=str(config_path),
            refresh=refresh,
        )
    except Exception as e:
        logger.exception("get_health_status failed: %s", e)
        return {
            "vm01": {"status": "unknown", "color": "gray", "message": str(e), "metrics": None},
            "vm02": {"status": "unknown", "color": "gray", "message": str(e), "metrics": None},
            "vm03": {"status": "unknown", "color": "gray", "message": str(e), "metrics": None},
            "vm04": {"status": "unknown", "color": "gray", "message": str(e), "metrics": None},
        }

    result: Dict[str, Any] = {}
    for vm_id in VALID_VM_IDS:
        st = statuses.get(vm_id)
        if st is None:
            result[vm_id] = {"status": "unknown", "color": "gray", "message": "No data", "metrics": None}
            continue
        color = STATUS_COLORS.get(st.status, "gray")
        metrics = None
        if st.metrics:
            metrics = {
                "cpu_percent": st.metrics.cpu_percent,
                "memory_percent": st.metrics.memory_percent,
                "disk_percent": st.metrics.disk_percent,
                "response_time_sec": st.metrics.response_time_sec,
                "uptime_sec": st.metrics.uptime_sec,
            }
        result[vm_id] = {
            "status": st.status,
            "color": color,
            "message": st.message or "",
            "metrics": metrics,
        }
    return result


@router.post("/sync-repo")
def sync_repo(
    request: Request,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    """Trigger sync_repository_to_all_vms. Admin only."""
    if not _check_api_key(request):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    role = _get_role_from_header(x_user_role)
    _require_role(role, "admin")

    root = _resolve_project_root()
    config_path = root / "configs" / "config.yml"
    if not config_path.is_file():
        raise HTTPException(status_code=500, detail="Config not found")

    try:
        from automation_scripts.orchestrators.repo_sync import sync_repository_to_all_vms

        out = sync_repository_to_all_vms(config_path=str(config_path))
        result = {}
        for vm_id, st in out.items():
            result[vm_id] = {
                "success": st.is_synced and not st.error,
                "error": st.error,
                "commit_hash": st.commit_hash,
            }
        return {"success": True, "results": result}
    except Exception as e:
        logger.exception("sync_repository_to_all_vms failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/backup-config")
def backup_config(
    request: Request,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    """Trigger backup of central config (vm04, central). Admin only."""
    if not _check_api_key(request):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    role = _get_role_from_header(x_user_role)
    _require_role(role, "admin")

    root = _resolve_project_root()
    config_path = root / "configs" / "config.yml"
    if not config_path.is_file():
        raise HTTPException(status_code=500, detail="Config not found")

    try:
        from automation_scripts.orchestrators.config_manager import backup_config as _backup_config

        backup_id = _backup_config("vm04", "central", config_path=str(config_path))
        return {"success": True, "backup_id": backup_id}
    except Exception as e:
        logger.exception("backup_config failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/refresh")
def refresh_status(
    request: Request,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    """Force refresh of health status (get_health_status(refresh=True)). Hunter or admin."""
    if not _check_api_key(request):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    role = _get_role_from_header(x_user_role)
    _require_role(role, "admin_or_hunter")

    return get_dashboard_status(refresh=True, x_user_role=x_user_role)
